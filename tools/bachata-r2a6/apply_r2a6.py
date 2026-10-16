#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed R2A.6 staging patch: BSF1 guest-path adapter and IOFile read-only FD adoption.

This does NOT connect the Android broker into guest kernel open/stat/getdents
until tested with a real broker. No APK signing, runtime.zip changes or PanVK edits.
"""
import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
# Original pinned upstream source blobs, NOT mutated by R2A..R2A5 patches.
BLOBS = {
    "src/common/io_file.h": "d4e4b2e47ccc859580c70a749976cd4fc21d2526",
    "src/common/io_file.cpp": "249d0e0f4768062b41e0ab1a5d4cf41de994380b",
}
CMAKE_BEFORE = """        src/platform/bachata/saf_bsf1_client.cpp
        src/platform/bachata/saf_bsf1_client.h
"""
CMAKE_AFTER = """        src/platform/bachata/saf_bsf1_client.cpp
        src/platform/bachata/saf_bsf1_client.h
        src/platform/bachata/saf_vfs_readonly.cpp
        src/platform/bachata/saf_vfs_readonly.h
"""
HEADER_BEFORE = """    int Open(const std::filesystem::path& path, FileAccessMode mode,
             FileType type = FileType::BinaryFile,
             FileShareFlag flag = FileShareFlag::ShareReadOnly);
    void Close();"""
HEADER_AFTER = """    int Open(const std::filesystem::path& path, FileAccessMode mode,
             FileType type = FileType::BinaryFile,
             FileShareFlag flag = FileShareFlag::ShareReadOnly);
#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
    // Takes ownership of fd EVEN ON ERROR. Never accepts writable/nonregular FDs.
    int AdoptReadOnlyFd(int fd, const std::filesystem::path& logical_guest_path);
    bool IsSafBacked() const { return saf_backed_; }
#endif
    void Close();"""
HEADER_PRIVATE_BEFORE = """    FileType file_type{};

    uintptr_t file_mapping = 0;"""
HEADER_PRIVATE_AFTER = """    FileType file_type{};
#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
    bool saf_backed_ = false;
#endif

    uintptr_t file_mapping = 0;"""
CPP_INCLUDE_BEFORE = """#else
#include <unistd.h>
#endif"""
CPP_INCLUDE_AFTER = """#else
#include <unistd.h>
#if defined(__linux__)
#include <fcntl.h>
#include <sys/stat.h>
#endif
#endif"""
CPP_MOVE_BEFORE = """    std::swap(file_type, other.file_type);
    std::swap(file, other.file);"""
CPP_MOVE_AFTER = """    std::swap(file_type, other.file_type);
    std::swap(file, other.file);
#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
    std::swap(saf_backed_, other.saf_backed_);
#endif"""
CPP_OPEN_BEFORE = """    file_path = path;
    file_access_mode = mode;
    file_type = type;"""
CPP_OPEN_AFTER = """    file_path = path;
    file_access_mode = mode;
    file_type = type;
#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
    saf_backed_ = false;
#endif"""
CPP_CLOSE_BEFORE = """void IOFile::Close() {
    if (!IsOpen()) {
        return;
    }"""
CPP_CLOSE_AFTER = """void IOFile::Close() {
    if (!IsOpen()) {
#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
        saf_backed_ = false;
#endif
        return;
    }"""
CPP_CLOSE_END_BEFORE = """    file = nullptr;

#ifdef _WIN64"""
CPP_CLOSE_END_AFTER = """    file = nullptr;
#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
    saf_backed_ = false;
#endif

#ifdef _WIN64"""
CPP_UNLINK_BEFORE = """void IOFile::Unlink() {
    if (!IsOpen()) {
        return;
    }"""
CPP_UNLINK_AFTER = """void IOFile::Unlink() {
    if (!IsOpen()) {
        return;
    }
#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
    if (saf_backed_) return;  // Broker-provided FD is strictly read-only.
#endif"""
CPP_ADOPT_ANCHOR = "void IOFile::Close() {"
CPP_ADOPT_IMPL = """#if defined(__linux__) && defined(ENABLE_BACHATA_RUNTIME)
int IOFile::AdoptReadOnlyFd(int fd, const fs::path& logical_guest_path) {
    // The descriptor is consumed on success or failure. Do not expose a writable stream.
    if (fd < 0) return EBADF;
    const std::string path = logical_guest_path.generic_string();
    if (!path.starts_with("/app0/") || path.size() <= 6 ||
        fs::path(path).lexically_normal().generic_string() != path ||
        path.find("//") != std::string::npos ||
        path.find_first_of("\\r\\n\\t") != std::string::npos) {
        ::close(fd);
        return EINVAL;
    }
    struct stat st{};
    const int status = ::fcntl(fd, F_GETFL);
    if (status < 0 || ::fstat(fd, &st) != 0 || !S_ISREG(st.st_mode) ||
        (status & O_ACCMODE) != O_RDONLY) {
        const int error = errno ? errno : EACCES;
        ::close(fd);
        return error;
    }
    std::FILE* new_file = ::fdopen(fd, "rb");
    if (!new_file) {
        const int error = errno ? errno : EIO;
        ::close(fd);
        return error;
    }
    Close();
    file = new_file;
    file_path = logical_guest_path; // Display-only, never use for syscalls.
    file_access_mode = FileAccessMode::Read;
    file_type = FileType::BinaryFile;
    saf_backed_ = true;
    return 0;
}
#endif

"""
def exact(data: str, before: str, after: str, count: int=1) -> str:
    found = data.count(before)
    if found != count:
        raise ValueError(f"Source anchor expected {count}, found {found}: {before[:65]!r}")
    return data.replace(before, after, count)

def apply(upstream: Path, own: Path):
    upstream,own=upstream.resolve(),own.resolve()
    if not (upstream / ".git").is_dir():
        raise ValueError("Not a pinned git checkout")
    commit = subprocess.check_output(["git","-C",str(upstream),"rev-parse","HEAD"],text=True).strip()
    if commit != PIN: raise ValueError(f"Expected pinned SHA {PIN}, got {commit}")
    cmake=upstream/"CMakeLists.txt"
    if "saf_bsf1_client.cpp" not in cmake.read_text():
        raise ValueError("Missing R2A5 BSF1 transport integration")
    main=(upstream/"src/main.cpp").read_text()
    if "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED" not in main:
        raise ValueError("Missing R2A5 VFS-off gate")
    for name, expected in BLOBS.items():
        if expected == "PLACEHOLDER": continue
        blob=subprocess.check_output(["git","-C",str(upstream),"hash-object",name],text=True).strip()
        if blob!=expected: raise ValueError(f"Original blob differs for {name}: {blob}")
    header_path=upstream/"src/common/io_file.h"
    cpp_path=upstream/"src/common/io_file.cpp"
    header=header_path.read_text(encoding="utf-8")
    cpp=cpp_path.read_text(encoding="utf-8")
    cmake_data=cmake.read_text(encoding="utf-8")
    header=exact(header,HEADER_BEFORE,HEADER_AFTER)
    header=exact(header,HEADER_PRIVATE_BEFORE,HEADER_PRIVATE_AFTER)
    cpp=exact(cpp,CPP_INCLUDE_BEFORE,CPP_INCLUDE_AFTER)
    cpp=exact(cpp,CPP_MOVE_BEFORE,CPP_MOVE_AFTER,count=2)
    cpp=exact(cpp,CPP_OPEN_BEFORE,CPP_OPEN_AFTER)
    cpp=exact(cpp,CPP_CLOSE_BEFORE,CPP_CLOSE_AFTER)
    cpp=exact(cpp,CPP_CLOSE_END_BEFORE,CPP_CLOSE_END_AFTER)
    cpp=exact(cpp,CPP_UNLINK_BEFORE,CPP_UNLINK_AFTER)
    cpp=exact(cpp,CPP_ADOPT_ANCHOR,CPP_ADOPT_IMPL+CPP_ADOPT_ANCHOR)
    cmake_data=exact(cmake_data,CMAKE_BEFORE,CMAKE_AFTER)
    files={}
    for name in ("saf_vfs_readonly.cpp","saf_vfs_readonly.h"):
        source=own/name
        if not source.is_file(): raise ValueError(f"Missing {source}")
        target=upstream/"src/platform/bachata"/name
        if target.exists(): raise ValueError(f"File already exists {target}")
        files[target]=source.read_bytes()
    # Everything validated before we mutate pinned upstream source.
    header_path.write_text(header,encoding="utf-8",newline="")
    cpp_path.write_text(cpp,encoding="utf-8",newline="")
    cmake.write_text(cmake_data,encoding="utf-8",newline="")
    for path,payload in files.items(): path.write_bytes(payload)
    print("R2A6_VFS_STAGED_READONLY")
    print("R2A6_GUEST_MOUNT=OFF")
    print("R2A6_ANDROID_REAL_BROKER=NOT_TESTED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("upstream",type=Path)
    p.add_argument("--source-dir",type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args()
    apply(a.upstream,a.source_dir)
