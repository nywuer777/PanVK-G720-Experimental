// SPDX-License-Identifier: GPL-2.0-or-later
// F43DEV R2A.2 experimental gate. This is NOT a replacement for Android signing validation.
// The unmodified Bionic runtime is required to verify the developer certificate.
#pragma once
#if !defined(__linux__)
#error "F43DEV GLIBC host gate requires Linux"
#endif
#include <filesystem>
#include <string>
#include <string_view>
#include <system_error>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

namespace Platform::Bachata {
namespace R2A2 {
constexpr std::string_view Package = "com.bachatas4.android.f43dev";

inline bool AppPrivatePath(std::string_view value) {
    constexpr std::string_view bases[] = {"/data/user/0/", "/data/data/", "/data/user_de/0/"};
    for (const auto prefix : bases) {
        std::string base{prefix};
        base += Package;
        if (value == base || (value.size() > base.size() &&
                              value.substr(0, base.size()) == base &&
                              value[base.size()] == '/')) {
            return true;
        }
    }
    return false;
}

inline bool InsideRoot(const std::filesystem::path& child,
                       const std::filesystem::path& root) {
    auto a = child.begin(), b = root.begin();
    for (; b != root.end(); ++b, ++a) {
        if (a == child.end() || *a != *b) return false;
    }
    return a != child.end();  // Must be below root, not the root directory itself.
}

inline bool VerifyManagedSocket(const std::filesystem::path& socket,
                                const std::filesystem::path& root) {
    if (!socket.is_absolute() || !root.is_absolute() ||
        !AppPrivatePath(root.lexically_normal().generic_string())) return false;
    std::error_code error;
    auto real_root = std::filesystem::canonical(root, error);
    if (error || !AppPrivatePath(real_root.generic_string())) return false;
    const auto real_parent = std::filesystem::canonical(socket.parent_path(), error);
    if (error || (real_parent != real_root && !InsideRoot(real_parent, real_root))) return false;
    struct stat root_st{}, socket_st{};
    if (::stat(real_root.c_str(), &root_st) != 0 || !S_ISDIR(root_st.st_mode) ||
        root_st.st_uid != ::geteuid()) return false;
    // lstat deliberately rejects symlink socket files.
    if (::lstat(socket.c_str(), &socket_st) != 0 ||
        !S_ISSOCK(socket_st.st_mode) ||
        socket_st.st_uid != ::geteuid()) return false;
    return true;
}

inline bool VerifyPeer(int fd) {
    if (fd < 0) return false;
#ifdef SO_PEERCRED
    struct ucred peer{};
    socklen_t peer_size = sizeof(peer);
    if (::getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &peer, &peer_size) != 0 ||
        peer_size != sizeof(peer) || peer.pid <= 0) return false;
    return peer.uid == ::geteuid();
#else
    return false;  // Fail closed if kernel/API cannot authenticate the peer UID.
#endif
}
} // namespace R2A2
} // namespace Platform::Bachata
