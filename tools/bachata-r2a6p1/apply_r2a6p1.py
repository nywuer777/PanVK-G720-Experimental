#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""R2A6/P1 experimental PS4 kernel SAF syscalls, strictly opt-in and read-only.

Apply after R2A,R2A2,R2A4,R2A5,R2A6. Does NOT build an APK.
No fabricated broker response and no silent fallback to host paths.
"""
import argparse
import subprocess
from pathlib import Path

PIN="be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
CHANGED_PATHS=[
"CMakeLists.txt", "src/main.cpp", "src/core/file_sys/fs.cpp",
"src/core/libraries/kernel/file_system.cpp",
"src/platform/bachata/saf_cli_contract.h",
]
NEW_FILES={
 "saf_guest_mount.h":"src/platform/bachata/saf_guest_mount.h",
 "saf_guest_mount.cpp":"src/platform/bachata/saf_guest_mount.cpp",
 "saf_directory.h":"src/core/file_sys/directories/saf_directory.h",
 "saf_directory.cpp":"src/core/file_sys/directories/saf_directory.cpp",
}

def one(src,before,after,label):
    n=src.count(before)
    if n!=1: raise ValueError(f"{label}: anchor count={n}: {before[:85]!r}")
    return src.replace(before,after,1)

def amend_function(src,name,needle,patch):
    start=src.find(name)
    if start<0 or src.find(name,start+1)>=0:
        raise ValueError(f"Ambiguous function {name}")
    end=src.find("\n}\n",start)
    if end<0: raise ValueError(f"Function body not found {name}")
    body=src[start:end]
    body=one(body,needle,patch+needle,name)
    return src[:start]+body+src[end:]

def patch_all(root:Path,local:Path):
    root=root.resolve();local=local.resolve()
    if not (root/".git").exists(): raise ValueError("Not a source checkout")
    pin=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if pin!=PIN:raise ValueError(f"Unexpected upstream source revision {pin}")
    source={p:(root/p).read_text() for p in CHANGED_PATHS}
    for phrase in ("BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED",
                   "ValidateContractCli","VerifyManagedSocket"):
        if phrase not in source["src/main.cpp"]:raise ValueError("Missing prerequisite "+phrase)
    for phrase in ("AdoptReadOnlyFd","IsSafBacked"):
        if phrase not in (root/"src/common/io_file.cpp").read_text() + (root/"src/common/io_file.h").read_text():
            raise ValueError("Missing R2A6 IOFile prerequisite "+phrase)
    for name,path in NEW_FILES.items():
        if (root/path).exists() or not (local/name).is_file():
            raise ValueError(f"Missing input or output exists {name}")
    cmake=source["CMakeLists.txt"]
    cmake=one(cmake,"""        src/platform/bachata/saf_vfs_readonly.cpp
        src/platform/bachata/saf_vfs_readonly.h
""","""        src/platform/bachata/saf_vfs_readonly.cpp
        src/platform/bachata/saf_vfs_readonly.h
        src/platform/bachata/saf_guest_mount.cpp
        src/platform/bachata/saf_guest_mount.h
        src/core/file_sys/directories/saf_directory.cpp
        src/core/file_sys/directories/saf_directory.h
""","CMake SAF")
    source["CMakeLists.txt"]=cmake

    cli=source["src/platform/bachata/saf_cli_contract.h"]
    cli=one(cli,'''constexpr std::string_view TokenFlag = "--bachata-saf-token";''',
      '''constexpr std::string_view TokenFlag = "--bachata-saf-token";
constexpr std::string_view VfsRootFlag = "--bachata-saf-vfs-root";''',"CLI sensitive root flag")
    cli=one(cli,'''return value == ContractFlag || value == SocketFlag || value == TokenFlag;''',
      '''return value == ContractFlag || value == SocketFlag || value == TokenFlag ||
           value == VfsRootFlag;''',"CLI redact root value")
    cli=one(cli,'''for (const auto flag : {ContractFlag, SocketFlag, TokenFlag}) {''',
      '''for (const auto flag : {ContractFlag, SocketFlag, TokenFlag, VfsRootFlag}) {''',"CLI redact assignment")
    source["src/platform/bachata/saf_cli_contract.h"]=cli

    main=source["src/main.cpp"]
    main=one(main,'''#include "platform/bachata/saf_bsf1_client.h"''',
      '''#include "platform/bachata/saf_bsf1_client.h"
#include "platform/bachata/saf_guest_mount.h"''',"main include")
    main=one(main,'''    std::optional<std::string> bachataSafToken;
#endif''',
      '''    std::optional<std::string> bachataSafToken;
    std::optional<std::string> bachataSafVfsRoot;
    bool bachataSafVfsLab = false;
#endif''',"main vars")
    main=one(main,'''    app.add_option("--bachata-saf-token", bachataSafToken,
                   "Android SAF broker session token (sensitive)");''',
      '''    app.add_option("--bachata-saf-token", bachataSafToken,
                   "Android SAF broker session token (sensitive)");
    app.add_option("--bachata-saf-vfs-root", bachataSafVfsRoot,
                   "Broker-relative game root, experimental and sensitive");
    app.add_flag("--bachata-saf-vfs-lab", bachataSafVfsLab,
                 "Enable read-only BSF1 /app0 mount for controlled laboratory tests");''',"main options")
    main=one(main,'''    if (!bachataSafVfsLab''', '''    if (!bachataSafVfsLab''',"no-op") if False else main
    main=one(main,'''    const Bachata::Saf::BSF1::Client saf_broker(saf_config);
    (void)saf_broker;''',
      '''    const Bachata::Saf::BSF1::Client saf_broker(saf_config);
    (void)saf_broker;
    if (!bachataSafVfsLab && bachataSafVfsRoot.has_value()) {
        std::cerr << "SAF root supplied without explicit laboratory opt-in\\n";
        return 1;
    }
    if (bachataSafVfsLab && (!bachataSafVfsRoot.has_value() ||
                              !Bachata::Saf::Vfs::ReadOnlyMount::ValidRoot(*bachataSafVfsRoot))) {
        std::cerr << "Invalid/missing broker-relative laboratory root\\n";
        return 1;
    }''',"main lab options")
    # ReadOnlyMount type used in main: include its declaration.
    main=one(main,'''#include "platform/bachata/saf_guest_mount.h"''',
      '''#include "platform/bachata/saf_guest_mount.h"
#include "platform/bachata/saf_vfs_readonly.h"''',"main include mount")
    main=one(main,'''        if (!runtime_client.SendStarting()) {
            std::cerr << "Failed to send Bachata Starting event\\n";
            return 1;
        }''',
      '''        if (!runtime_client.SendStarting()) {
            std::cerr << "Failed to send Bachata Starting event\\n";
            return 1;
        }
#if defined(__linux__) && defined(__aarch64__)
        // Enable mount only after R2A2 app-path and same-UID host handshake pass.
        if (bachataSafVfsLab &&
            !Bachata::Saf::Guest::EnableExperimental(saf_config, *bachataSafVfsRoot)) {
            std::cerr << "SAF laboratory mount activation rejected\\n";
            return 1;
        }
#endif''',"activate only after verified host handshake")
    main=one(main,'''    std::cerr << "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED\n";''',
      '''    if (bachataSafVfsLab) {
        std::cerr << "BACHATA_F43DEV_R2A6P1_LAB_VFS_OPTIN_REAL_BROKER_UNVERIFIED\n";
    } else {
        std::cerr << "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED\n";
    }''',"accurate lab/runtime marker")
    source["src/main.cpp"]=main

    fs=source["src/core/file_sys/fs.cpp"]
    fs=one(fs,'''#include "core/file_sys/fs.h"''',
      '''#include "core/file_sys/fs.h"
#ifdef ENABLE_BACHATA_RUNTIME
#include "platform/bachata/saf_guest_mount.h"
#endif''',"fs include")
    fs=one(fs,'''    std::string corrected_path(path);''',
      '''#ifdef ENABLE_BACHATA_RUNTIME
    // No fallback from an enabled SAF mount to a local host path.
    if (Bachata::Saf::Guest::Scoped(path)) return {};
#endif
    std::string corrected_path(path);''',"fs prevent silent local fallthrough")
    source["src/core/file_sys/fs.cpp"]=fs

    k=source["src/core/libraries/kernel/file_system.cpp"]
    k=one(k,'''#include "core/file_sys/directories/pfs_directory.h"''',
      '''#include "core/file_sys/directories/pfs_directory.h"
#ifdef ENABLE_BACHATA_RUNTIME
#include <fcntl.h>
#include "core/file_sys/directories/saf_directory.h"
#include "platform/bachata/saf_guest_mount.h"
#endif''',"kernel includes")
    open_code='''#ifdef ENABLE_BACHATA_RUNTIME
    if (Bachata::Saf::Guest::Scoped(path)) {
        // SAF is read-only: disallow all flags that may mutate guest content.
        if (!read || create || truncate || append || excl) {
            *__Error() = POSIX_EROFS;
            return -1;
        }
        auto metadata = Bachata::Saf::Guest::Stat(path);
        if (!metadata) { *__Error() = POSIX_EIO; return -1; }
        if (directory && !metadata.value->is_directory) {
            *__Error() = POSIX_ENOTDIR;
            return -1;
        }
        const u32 fd = h->CreateHandle();
        auto* saf_file = h->GetFile(fd);
        saf_file->m_guest_name = std::string(path);
        if (metadata.value->is_directory) {
            auto listing = Bachata::Saf::Guest::List(path);
            if (!listing || !Core::Directories::SafDirectory::ValidEntries(*listing.value)) {
                h->DeleteHandle(fd);
                *__Error() = POSIX_EIO;
                return -1;
            }
            saf_file->type = Core::FileSys::FileType::Directory;
            saf_file->directory =
                std::make_shared<Core::Directories::SafDirectory>(
                    std::move(*listing.value));
        } else {
            auto remote_file = Bachata::Saf::Guest::OpenRead(path);
            if (!remote_file) { h->DeleteHandle(fd); *__Error() = POSIX_EIO; return -1; }
            // Duplicate: IOFile::AdoptReadOnlyFd consumes ownership regardless of result.
            const int copy = ::fcntl(remote_file.value->get(), F_DUPFD_CLOEXEC, 0);
            if (copy < 0) { h->DeleteHandle(fd); *__Error() = POSIX_EIO; return -1; }
            const int result = saf_file->f.AdoptReadOnlyFd(copy, fs::path(path));
            if (result != 0) {
                h->DeleteHandle(fd);
                SetPosixErrno(result);
                return -1;
            }
            saf_file->type = Core::FileSys::FileType::Regular;
        }
        saf_file->is_opened = true;
        return fd;
    }
#endif
'''
    k=one(k,'''    std::string_view path{raw_path};
    u32 handle = h->CreateHandle();''',
      '''    std::string_view path{raw_path};
'''+open_code+'''    u32 handle = h->CreateHandle();''',"kernel open routed /app0")
    # Guard both sequential and vectored writes. Reads/seek still operate on adopted rb FILE*.
    for signature in (
        "s64 PS4_SYSV_ABI write(s32 fd, const void* buf, u64 nbytes) {",
        "s64 PS4_SYSV_ABI writev(s32 fd, const OrbisKernelIovec* iov, s32 iovcnt) {",
        "s64 PS4_SYSV_ABI posix_pwritev(s32 fd, const OrbisKernelIovec* iov, s32 iovcnt, s64 offset) {",
        "s32 PS4_SYSV_ABI posix_ftruncate(s32 fd, s64 length) {",
    ):
        # All checked when each File handle is retrieved; avoid modifying other file types.
        chunkstart=k.index(signature)
        chunkend=k.index("\n}\n",chunkstart)
        chunk=k[chunkstart:chunkend]
        marker='''    if (file == nullptr) {
        *__Error() = POSIX_EBADF;
        return -1;
    }'''
        if marker not in chunk: raise ValueError("Missing fd null guard in "+signature)
        injected='''#ifdef ENABLE_BACHATA_RUNTIME
    if (file->f.IsSafBacked()) {
        *__Error() = POSIX_EROFS;
        return -1;
    }
#endif
'''
        chunk=one(chunk,marker,marker+'\n'+injected,signature)
        k=k[:chunkstart]+chunk+k[chunkend:]

    for signature,names in (
        ("s32 PS4_SYSV_ABI posix_mkdir(const char* path, u16 mode) {",("path",)),
        ("s32 PS4_SYSV_ABI posix_rmdir(const char* path) {",("path",)),
        ("s32 PS4_SYSV_ABI posix_rename(const char* from, const char* to) {",("from","to")),
        ("s32 PS4_SYSV_ABI posix_unlink(const char* path) {",("path",)),
    ):
        checks=" || ".join(
          f'({name} && Bachata::Saf::Guest::Scoped({name}))'
          for name in names)
        guard=f'''
#ifdef ENABLE_BACHATA_RUNTIME
    if ({checks}) {{
        *__Error() = POSIX_EROFS;
        return -1;
    }}
#endif
'''
        k=one(k,signature,signature+guard,"kernel mutator "+signature)

    stat_code='''#ifdef ENABLE_BACHATA_RUNTIME
    if (path && Bachata::Saf::Guest::Scoped(path)) {
        if (!sb) { *__Error() = POSIX_EFAULT; return -1; }
        auto metadata = Bachata::Saf::Guest::Stat(path);
        if (!metadata) { *__Error() = POSIX_EIO; return -1; }
        std::memset(sb, 0, sizeof(*sb));
        if (metadata.value->is_directory) {
            sb->st_mode = 0040000u | 0000555u;
            sb->st_blksize = 512;
            return ORBIS_OK;
        }
        auto read_handle = Bachata::Saf::Guest::OpenRead(path);
        if (!read_handle) { *__Error() = POSIX_EIO; return -1; }
        struct stat st{};
        if (::fstat(read_handle.value->get(), &st) != 0) {
            *__Error() = POSIX_EIO;
            return -1;
        }
        sb->st_mode = 0100000u | 0000444u;
        sb->st_size = st.st_size;
        sb->st_blksize = 512;
        sb->st_blocks = (sb->st_size + 511) / 512;
        sb->st_atim.tv_sec = st.st_atim.tv_sec;
        sb->st_atim.tv_nsec = st.st_atim.tv_nsec;
        sb->st_mtim.tv_sec = st.st_mtim.tv_sec;
        sb->st_mtim.tv_nsec = st.st_mtim.tv_nsec;
        sb->st_ctim.tv_sec = st.st_ctim.tv_sec;
        sb->st_ctim.tv_nsec = st.st_ctim.tv_nsec;
        return ORBIS_OK;
    }
#endif
'''
    k=one(k,'''s32 PS4_SYSV_ABI posix_stat(const char* path, OrbisKernelStat* sb) {''',
      '''s32 PS4_SYSV_ABI posix_stat(const char* path, OrbisKernelStat* sb) {
'''+stat_code,"kernel stat")
    k=one(k,'''s32 PS4_SYSV_ABI sceKernelCheckReachability(const char* path) {''',
      '''s32 PS4_SYSV_ABI sceKernelCheckReachability(const char* path) {
#ifdef ENABLE_BACHATA_RUNTIME
    if (path && Bachata::Saf::Guest::Scoped(path))
        return Bachata::Saf::Guest::Stat(path) ? ORBIS_OK : ORBIS_KERNEL_ERROR_ENOENT;
#endif''',"kernel reachability")
    k=one(k,'''    case Core::FileSys::FileType::Regular: {
        sb->st_mode = 0000777u | 0100000u;''',
      '''    case Core::FileSys::FileType::Regular: {
#ifdef ENABLE_BACHATA_RUNTIME
        if (file->f.IsSafBacked()) {
            const int native_fd = ::fileno(file->f.file);
            struct stat st{};
            if (native_fd < 0 || ::fstat(native_fd, &st) != 0) {
                *__Error() = POSIX_EIO; return -1;
            }
            sb->st_mode = 0100000u | 0000444u;
            sb->st_size = st.st_size;
            sb->st_blksize = 512;
            sb->st_blocks = (sb->st_size + 511) / 512;
            sb->st_atim.tv_sec = st.st_atim.tv_sec;
            sb->st_atim.tv_nsec = st.st_atim.tv_nsec;
            sb->st_mtim.tv_sec = st.st_mtim.tv_sec;
            sb->st_mtim.tv_nsec = st.st_mtim.tv_nsec;
            sb->st_ctim.tv_sec = st.st_ctim.tv_sec;
            sb->st_ctim.tv_nsec = st.st_ctim.tv_nsec;
            return ORBIS_OK;
        }
#endif
        sb->st_mode = 0000777u | 0100000u;''',"kernel fstat native fd")
    source["src/core/libraries/kernel/file_system.cpp"]=k
    # Stop if imported interface/source has drifted.
    for name,relative in NEW_FILES.items():
        payload=(local/name).read_text()
        if not payload:raise ValueError("Empty source "+name)
    for relative,updated in source.items():
        if updated == (root/relative).read_text():
            raise ValueError("Expected modified source "+relative)
    # Everything above is read-only until source anchors and input files checked.
    for relative,updated in source.items():
        (root/relative).write_text(updated,newline="")
    for name,relative in NEW_FILES.items():
        dest=root/relative
        dest.write_bytes((local/name).read_bytes())
    print("R2A6P1_SAF_KERNEL_PATCH_APPLIED")
    print("R2A6P1_DEFAULT_VFS=OFF")
    print("R2A6P1_ANDROID_BROKER=NOT_TESTED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("upstream",type=Path)
    p.add_argument("--source-dir",type=Path,default=Path(__file__).resolve().parent)
    args=p.parse_args()
    patch_all(args.upstream,args.source_dir)
