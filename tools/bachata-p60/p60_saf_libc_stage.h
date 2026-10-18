// SPDX-License-Identifier: GPL-2.0-or-later
// P60: broker-authorized, exact-scope sce_module/libc.prx preflight and staging.
// This is NOT a general /app0 VFS. Never log secrets or game bytes.
#pragma once
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstddef>
#include <cstdint>
#include <filesystem>
#include <optional>
#include <string>
#include <utility>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include "platform/bachata/saf_bsf1_client.h"

namespace Bachata::Saf::P60 {
inline constexpr const char* kRelativeModule = "sce_module/libc.prx";
inline constexpr std::uint64_t kMaxModuleSize = 256ULL * 1024ULL * 1024ULL;

enum class Status {
    NotAttempted,
    UnsafeRoot,
    BrokerStatRejected,
    BrokerStatInvalid,
    BrokerStatUnavailable,
    BrokerNotRegular,
    BrokerOpenRejected,
    BrokerOpenFailed,
    InvalidFd,
    TooLarge,
    CreateDirectoryFailed,
    UnsafeDirectory,
    ExistingFile,
    CreateFileFailed,
    ReadFailed,
    WriteFailed,
    EmptyFile,
    Ready,
};
inline constexpr const char* Marker(Status s) noexcept {
    switch (s) {
    case Status::NotAttempted: return "BACHATA_P60_LIBC_NOT_ATTEMPTED";
    case Status::UnsafeRoot: return "BACHATA_P60_LIBC_UNSAFE_ROOT";
    case Status::BrokerStatRejected: return "BACHATA_P60_LIBC_BROKER_STAT_REJECTED";
    case Status::BrokerStatInvalid: return "BACHATA_P60_LIBC_BROKER_STAT_PAYLOAD_INVALID";
    case Status::BrokerStatUnavailable: return "BACHATA_P60_LIBC_BROKER_STAT_UNAVAILABLE";
    case Status::BrokerNotRegular: return "BACHATA_P60_LIBC_BROKER_NOT_REGULAR";
    case Status::BrokerOpenRejected: return "BACHATA_P60_LIBC_BROKER_OPEN_REJECTED";
    case Status::BrokerOpenFailed: return "BACHATA_P60_LIBC_BROKER_OPEN_FAILED";
    case Status::InvalidFd: return "BACHATA_P60_LIBC_FD_INVALID";
    case Status::TooLarge: return "BACHATA_P60_LIBC_TOO_LARGE";
    case Status::CreateDirectoryFailed: return "BACHATA_P60_LIBC_CREATE_DIR_FAILED";
    case Status::UnsafeDirectory: return "BACHATA_P60_LIBC_UNSAFE_DIR";
    case Status::ExistingFile: return "BACHATA_P60_LIBC_ALREADY_EXISTS_NOT_OVERWRITTEN";
    case Status::CreateFileFailed: return "BACHATA_P60_LIBC_CREATE_FILE_FAILED";
    case Status::ReadFailed: return "BACHATA_P60_LIBC_READ_FAILED";
    case Status::WriteFailed: return "BACHATA_P60_LIBC_WRITE_FAILED";
    case Status::EmptyFile: return "BACHATA_P60_LIBC_EMPTY_FILE";
    case Status::Ready: return "BACHATA_P60_LIBC_SAF_PRIVATE_STAGE_READY";
    }
    return "BACHATA_P60_LIBC_UNKNOWN";
}

class ScopedFd {
public:
    explicit ScopedFd(int fd = -1) noexcept : fd_(fd) {}
    ~ScopedFd() { if (fd_ >= 0) ::close(fd_); }
    ScopedFd(const ScopedFd&) = delete;
    ScopedFd& operator=(const ScopedFd&) = delete;
    int get() const noexcept { return fd_; }
private:
    int fd_;
};

struct Stage {
    Status status = Status::NotAttempted;
    std::filesystem::path path;
    // Only entries this instance successfully created may be removed.
    std::filesystem::path private_root;
    bool created_directory = false;
    Stage() = default;
    explicit Stage(Status s) : status(s) {}
    Stage(Status s, std::filesystem::path p, std::filesystem::path root, bool dir)
        : status(s), path(std::move(p)), private_root(std::move(root)),
          created_directory(dir) {}
    Stage(const Stage&) = delete;
    Stage& operator=(const Stage&) = delete;
    Stage(Stage&& other) noexcept
        : status(other.status), path(std::move(other.path)),
          private_root(std::move(other.private_root)),
          created_directory(other.created_directory) {
        other.path.clear();
        other.private_root.clear();
        other.created_directory = false;
    }
    Stage& operator=(Stage&& other) noexcept {
        if (this != &other) {
            Cleanup();
            status = other.status;
            path = std::move(other.path);
            private_root = std::move(other.private_root);
            created_directory = other.created_directory;
            other.path.clear();
            other.private_root.clear();
            other.created_directory = false;
        }
        return *this;
    }
    ~Stage() { Cleanup(); }
    explicit operator bool() const noexcept { return status == Status::Ready; }
private:
    void Cleanup() noexcept {
        if (!path.empty()) {
            ::unlink(path.c_str());
            path.clear();
        }
        if (created_directory && !private_root.empty()) {
            // Only remove an empty directory created by P60.
            const auto directory = private_root / "sce_module";
            ::rmdir(directory.c_str());
        }
        private_root.clear();
        created_directory = false;
    }
};

inline bool SafeDirectory(int fd) noexcept {
    struct stat st{};
    return fd >= 0 && ::fstat(fd, &st) == 0 &&
           S_ISDIR(st.st_mode) && st.st_uid == ::geteuid() &&
           (st.st_mode & (S_IWGRP | S_IWOTH)) == 0;
}

// Testable separately, with a synthetic read-only descriptor and no broker.
inline Stage StageAuthorizedLibc(int authorized_fd,
                                const std::filesystem::path& trusted_root) {
    if (!trusted_root.is_absolute() ||
        trusted_root != trusted_root.lexically_normal())
        return Stage(Status::UnsafeRoot);
    ScopedFd root(::open(trusted_root.c_str(),
                         O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (!SafeDirectory(root.get())) return Stage(Status::UnsafeRoot);
    struct stat source{};
    if (authorized_fd < 0 || ::fstat(authorized_fd, &source) != 0 ||
        !S_ISREG(source.st_mode) || source.st_size < 0)
        return Stage(Status::InvalidFd);
    if (static_cast<std::uint64_t>(source.st_size) > kMaxModuleSize)
        return Stage(Status::TooLarge);

    bool directory_created = false;
    if (::mkdirat(root.get(), "sce_module", 0700) == 0) {
        directory_created = true;
    } else if (errno != EEXIST) {
        return Stage(Status::CreateDirectoryFailed);
    }
    ScopedFd modules(::openat(root.get(), "sce_module",
                               O_RDONLY | O_DIRECTORY | O_CLOEXEC | O_NOFOLLOW));
    if (!SafeDirectory(modules.get())) {
        if (directory_created) ::unlinkat(root.get(), "sce_module", AT_REMOVEDIR);
        return Stage(Status::UnsafeDirectory);
    }
    // Exact untrusted-content destination, no symlinks, no overwrite.
    const auto stage_path = trusted_root / "sce_module" / "libc.prx";
    const int raw_fd = ::openat(modules.get(), "libc.prx",
                                O_WRONLY | O_CREAT | O_EXCL |
                                O_CLOEXEC | O_NOFOLLOW, 0600);
    if (raw_fd < 0) {
        if (directory_created) ::unlinkat(root.get(), "sce_module", AT_REMOVEDIR);
        return Stage(errno == EEXIST ? Status::ExistingFile : Status::CreateFileFailed);
    }
    ScopedFd output(raw_fd);
    Stage stage(Status::CreateFileFailed, stage_path, trusted_root, directory_created);
    struct stat output_st{};
    if (::fstat(output.get(), &output_st) != 0 ||
        !S_ISREG(output_st.st_mode) || output_st.st_uid != ::geteuid() ||
        output_st.st_nlink != 1)
        return stage; // fail closed; Stage destructor unlinks only our new file.
    // Verify storage root's device, not SAF FD's potentially unrelated device.
    struct stat root_st{};
    if (::fstat(root.get(), &root_st) != 0 || output_st.st_dev != root_st.st_dev ||
        (output_st.st_mode & 0777) != 0600)
        return stage;
    std::array<unsigned char, 128 * 1024> buffer{};
    std::uint64_t copied = 0;
    for (;;) {
        if (copied == kMaxModuleSize) {
            unsigned char next{};
            const ssize_t n = ::pread(authorized_fd, &next, 1,
                                      static_cast<off_t>(copied));
            if (n < 0 && errno == EINTR) continue;
            if (n != 0) {
                stage.status = n < 0 ? Status::ReadFailed : Status::TooLarge;
                return stage;
            }
            break;
        }
        const size_t request = static_cast<size_t>(
            std::min<std::uint64_t>(buffer.size(), kMaxModuleSize - copied));
        const ssize_t n = ::pread(authorized_fd, buffer.data(), request,
                                  static_cast<off_t>(copied));
        if (n < 0 && errno == EINTR) continue;
        if (n < 0) { stage.status = Status::ReadFailed; return stage; }
        if (n == 0) break;
        size_t offset = 0;
        while (offset < static_cast<size_t>(n)) {
            const ssize_t w = ::write(output.get(), buffer.data() + offset,
                                       static_cast<size_t>(n) - offset);
            if (w < 0 && errno == EINTR) continue;
            if (w <= 0) { stage.status = Status::WriteFailed; return stage; }
            offset += static_cast<size_t>(w);
        }
        copied += static_cast<std::uint64_t>(n);
    }
    if (copied < 64) { stage.status = Status::EmptyFile; return stage; }
    if (source.st_size > 0 && copied != static_cast<std::uint64_t>(source.st_size)) {
        stage.status = Status::ReadFailed;
        return stage;
    }
    stage.status = Status::Ready;
    return stage;
}

inline Stage ProbeAndStageLibc(const BSF1::Client& broker,
                              const std::filesystem::path& trusted_root) {
    // Never infer absence from a remote rejection: remote errors also cover
    // permission failures. Do not create a synthetic substitute.
    auto meta = broker.Stat(kRelativeModule);
    if (!meta) {
        if (meta.error == BSF1::Error::RemoteError)
            return Stage(Status::BrokerStatRejected);
        if (meta.error == BSF1::Error::PayloadInvalid)
            return Stage(Status::BrokerStatInvalid);
        return Stage(Status::BrokerStatUnavailable);
    }
    if (meta.value->is_directory) return Stage(Status::BrokerNotRegular);
    auto supplied = broker.OpenRead(kRelativeModule);
    if (!supplied) {
        return Stage(supplied.error == BSF1::Error::RemoteError
                         ? Status::BrokerOpenRejected : Status::BrokerOpenFailed);
    }
    if (!supplied.value || !*supplied.value) return Stage(Status::InvalidFd);
    return StageAuthorizedLibc(supplied.value->get(), trusted_root);
}
} // namespace Bachata::Saf::P60
