// SPDX-License-Identifier: GPL-2.0-or-later
// P59: read an authenticated broker FD directly, stage ephemeral private copy.
// Never copy into a public directory. No content, paths, FD or token in logs.
// Deliberately does not implement the PS4 /app0 guest filesystem.
#pragma once
#include <algorithm>
#include <array>
#include <cstdlib>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <filesystem>
#include <string>
#include <utility>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace Bachata::Saf::P59 {

inline constexpr std::uint64_t kMaxExecutableBytes = 2ULL * 1024ULL * 1024ULL * 1024ULL;
enum class Status {
    NotStaged,
    UnsafeRoot,
    InvalidSource,
    TooLarge,
    CreateFailed,
    ReadFailed,
    WriteFailed,
    EmptySource,
    Staged,
};
inline constexpr const char* Marker(Status value) {
    switch (value) {
    case Status::NotStaged: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_NOT_STARTED";
    case Status::UnsafeRoot: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_UNSAFE_ROOT";
    case Status::InvalidSource: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_INVALID_FD";
    case Status::TooLarge: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_TOO_LARGE";
    case Status::CreateFailed: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_CREATE_FAILED";
    case Status::ReadFailed: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_READ_FAILED";
    case Status::WriteFailed: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_WRITE_FAILED";
    case Status::EmptySource: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_EMPTY_SOURCE";
    case Status::Staged: return "BACHATA_P59_EBOOT_PRIVATE_STAGE_READY";
    }
    return "BACHATA_P59_EBOOT_PRIVATE_STAGE_UNKNOWN";
}

struct ScopedFd {
    int value = -1;
    explicit ScopedFd(int input = -1) : value(input) {}
    ScopedFd(const ScopedFd&) = delete;
    ScopedFd& operator=(const ScopedFd&) = delete;
    ~ScopedFd() { if (value >= 0) ::close(value); }
};

struct PrivateStage {
    Status status = Status::NotStaged;
    std::filesystem::path path;
    PrivateStage() = default;
    PrivateStage(Status s, std::filesystem::path p) : status(s), path(std::move(p)) {}
    PrivateStage(const PrivateStage&) = delete;
    PrivateStage& operator=(const PrivateStage&) = delete;
    PrivateStage(PrivateStage&& other) noexcept
        : status(other.status), path(std::move(other.path)) { other.path.clear(); }
    PrivateStage& operator=(PrivateStage&& other) noexcept {
        if (this != &other) {
            Release();
            status = other.status;
            path = std::move(other.path);
            other.path.clear();
        }
        return *this;
    }
    ~PrivateStage() { Release(); }
    explicit operator bool() const { return status == Status::Staged && !path.empty(); }
private:
    void Release() noexcept {
        if (!path.empty()) {
            ::unlink(path.c_str());
            path.clear();
        }
    }
};

inline PrivateStage StageAuthenticatedFd(
    int authorized_fd, const std::filesystem::path& trusted_root) {
    // The caller has already authenticated the SAF broker, session token, and UID.
    // This routine neither reconnects nor reopens /proc/self/fd/N.
    if (!trusted_root.is_absolute() ||
        trusted_root != trusted_root.lexically_normal())
        return {Status::UnsafeRoot, {}};
    ScopedFd dir(::open(trusted_root.c_str(),
                        O_RDONLY | O_DIRECTORY | O_NOFOLLOW | O_CLOEXEC));
    if (dir.value < 0) return {Status::UnsafeRoot, {}};
    struct stat dir_stat{};
    if (::fstat(dir.value, &dir_stat) != 0 ||
        !S_ISDIR(dir_stat.st_mode) || dir_stat.st_uid != ::geteuid() ||
        (dir_stat.st_mode & (S_IWGRP | S_IWOTH)) != 0)
        return {Status::UnsafeRoot, {}};

    struct stat source{};
    if (authorized_fd < 0 || ::fstat(authorized_fd, &source) != 0 ||
        !S_ISREG(source.st_mode) || source.st_size < 0)
        return {Status::InvalidSource, {}};
    if (static_cast<std::uint64_t>(source.st_size) > kMaxExecutableBytes)
        return {Status::TooLarge, {}};

    // mkstemp atomically creates an unguessable 0600 name. The directory
    // above must be private and owned by this process's UID.
    std::string candidate = (trusted_root / ".p59-eboot-XXXXXX").string();
    int raw_output = ::mkstemp(candidate.data());
    if (raw_output < 0) return {Status::CreateFailed, {}};
    ScopedFd output(raw_output);
    PrivateStage stage{Status::CreateFailed, candidate};
    if (::fcntl(output.value, F_SETFD, FD_CLOEXEC) != 0 ||
        ::fchmod(output.value, S_IRUSR | S_IWUSR) != 0)
        return {Status::CreateFailed, {}};
    // Verify mkstemp created the file in the same trusted root that was opened.
    struct stat staged{};
    if (::fstat(output.value, &staged) != 0 || !S_ISREG(staged.st_mode) ||
        staged.st_uid != ::geteuid() || staged.st_nlink != 1 ||
        staged.st_dev != dir_stat.st_dev)
        return {Status::CreateFailed, {}};

    std::array<std::uint8_t, 256 * 1024> block{};
    std::uint64_t copied = 0;
    while (true) {
        if (copied >= kMaxExecutableBytes) {
            // A full 2 GiB file is supported; if more bytes exist, fail closed.
            std::uint8_t extra{};
            const ssize_t next = ::pread(authorized_fd, &extra, 1,
                                         static_cast<off_t>(copied));
            if (next == 0) break;
            return {next < 0 ? Status::ReadFailed : Status::TooLarge, {}};
        }
        const std::size_t capacity = static_cast<std::size_t>(
            std::min<std::uint64_t>(block.size(), kMaxExecutableBytes - copied));
        const ssize_t received = ::pread(authorized_fd, block.data(), capacity,
                                          static_cast<off_t>(copied));
        if (received < 0 && errno == EINTR) continue;
        if (received < 0) return {Status::ReadFailed, {}};
        if (received == 0) break;
        std::size_t done = 0;
        while (done < static_cast<std::size_t>(received)) {
            const ssize_t sent = ::write(output.value, block.data() + done,
                                          static_cast<std::size_t>(received) - done);
            if (sent < 0 && errno == EINTR) continue;
            if (sent <= 0) return {Status::WriteFailed, {}};
            done += static_cast<std::size_t>(sent);
        }
        copied += static_cast<std::uint64_t>(received);
    }
    if (copied < 64) return {Status::EmptySource, {}};
    // Never stage a changing or truncated regular file as though it succeeded.
    if (source.st_size > 0 &&
        copied != static_cast<std::uint64_t>(source.st_size))
        return {Status::ReadFailed, {}};
    stage.status = Status::Staged;
    return stage;
}
} // namespace Bachata::Saf::P59
