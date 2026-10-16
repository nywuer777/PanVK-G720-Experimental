// SPDX-License-Identifier: GPL-2.0-or-later
#include "saf_bsf1_client.h"
#include <algorithm>
#include <array>
#include <cstddef>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <poll.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <unistd.h>
#include <utility>

namespace Bachata::Saf::BSF1 {
namespace {
constexpr size_t MaxPayload = 4 * 1024 * 1024;
constexpr size_t MaxRequestPath = 4096;
constexpr size_t MaxListEntries = 4096;
constexpr uint8_t Version = 1;
constexpr std::array<uint8_t, 4> Magic{'B', 'S', 'F', '1'};

void AppendBe32(std::vector<uint8_t>& data, uint32_t value) {
    for (int n = 24; n >= 0; n -= 8) data.push_back(static_cast<uint8_t>(value >> n));
}
uint32_t Be32(const uint8_t* p) {
    return (uint32_t(p[0]) << 24) | (uint32_t(p[1]) << 16) |
           (uint32_t(p[2]) << 8) | uint32_t(p[3]);
}
uint64_t Be64(const uint8_t* p) {
    uint64_t result = 0;
    for (int i = 0; i < 8; ++i) result = (result << 8) | p[i];
    return result;
}
bool IsHex32(std::string_view value) {
    if (value.size() != 32) return false;
    for (const unsigned char c : value) {
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
              (c >= 'A' && c <= 'F'))) return false;
    }
    return true;
}
bool IsSocketName(std::string_view value) {
    if (value.empty() || value.size() > sizeof(sockaddr_un::sun_path) - 2) return false;
    for (const unsigned char c : value) {
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.')) return false;
    }
    return true;
}
bool SendAll(int fd, const uint8_t* src, size_t size) {
    while (size) {
        ssize_t n = ::send(fd, src, size, MSG_NOSIGNAL);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;
        src += n;
        size -= static_cast<size_t>(n);
    }
    return true;
}
bool SetTimeout(int fd, int ms) {
    const timeval tv{ms / 1000, (ms % 1000) * 1000};
    return setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv)) == 0 &&
           setsockopt(fd, SOL_SOCKET, SO_SNDTIMEO, &tv, sizeof(tv)) == 0;
}
ReadFd Connect(const Config& config) {
    ReadFd sock(::socket(AF_UNIX, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0));
    if (!sock) return {};
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    // Abstract socket label starts at sun_path[1]. Never resolve a filesystem path.
    std::memcpy(addr.sun_path + 1, config.abstract_socket_label.data(),
                config.abstract_socket_label.size());
    const socklen_t addr_length = static_cast<socklen_t>(
        offsetof(sockaddr_un, sun_path) + 1 + config.abstract_socket_label.size());
    int rc = ::connect(sock.get(), reinterpret_cast<sockaddr*>(&addr), addr_length);
    if (rc < 0 && errno == EINPROGRESS) {
        pollfd p{sock.get(), POLLOUT, 0};
        do { rc = ::poll(&p, 1, config.timeout_ms); } while (rc < 0 && errno == EINTR);
        if (rc <= 0) return {};
        int socket_error = 0;
        socklen_t error_len = sizeof(socket_error);
        if (::getsockopt(sock.get(), SOL_SOCKET, SO_ERROR, &socket_error, &error_len) ||
            error_len != sizeof(socket_error) || socket_error) return {};
    } else if (rc < 0) {
        return {};
    }
    int flags = ::fcntl(sock.get(), F_GETFL, 0);
    if (flags < 0 || ::fcntl(sock.get(), F_SETFL, flags & ~O_NONBLOCK) < 0 ||
        !SetTimeout(sock.get(), config.timeout_ms)) return {};
    return sock;
}
bool SameUidPeer(int fd) {
#ifdef SO_PEERCRED
    struct ucred cred{};
    socklen_t n = sizeof(cred);
    return ::getsockopt(fd, SOL_SOCKET, SO_PEERCRED, &cred, &n) == 0 &&
           n == sizeof(cred) && cred.pid > 0 && cred.uid == ::geteuid();
#else
    (void)fd;
    return false;
#endif
}

// Always use recvmsg for response framing: SCM_RIGHTS may arrive together with
// a fragmented header. Every ancillary fd is either kept or closed immediately.
bool RecvAllWithFd(int fd, uint8_t* dest, size_t size, ReadFd& received,
                   bool allow_fd) {
    while (size) {
        std::array<char, CMSG_SPACE(sizeof(int) * 4)> ancillary{};
        iovec iov{dest, size};
        msghdr msg{};
        msg.msg_iov = &iov;
        msg.msg_iovlen = 1;
        msg.msg_control = ancillary.data();
        msg.msg_controllen = ancillary.size();
        const ssize_t n = ::recvmsg(fd, &msg, MSG_CMSG_CLOEXEC);
        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;
        bool unexpected = (msg.msg_flags & (MSG_CTRUNC | MSG_TRUNC)) != 0;
        for (cmsghdr* c = CMSG_FIRSTHDR(&msg); c; c = CMSG_NXTHDR(&msg, c)) {
            if (c->cmsg_level != SOL_SOCKET || c->cmsg_type != SCM_RIGHTS ||
                c->cmsg_len < CMSG_LEN(0)) {
                unexpected = true;
                continue;
            }
            const size_t count = (c->cmsg_len - CMSG_LEN(0)) / sizeof(int);
            auto* p = reinterpret_cast<const int*>(CMSG_DATA(c));
            for (size_t i = 0; i < count; ++i) {
                ReadFd offered(p[i]);
                if (!allow_fd || received || i != 0 || count != 1) {
                    unexpected = true;
                } else {
                    received = std::move(offered);
                }
            }
        }
        if (unexpected) return false;
        size -= static_cast<size_t>(n);
        dest += n;
    }
    return true;
}
} // namespace

ReadFd::~ReadFd() { if (fd_ >= 0) ::close(fd_); }
ReadFd::ReadFd(ReadFd&& other) noexcept : fd_(std::exchange(other.fd_, -1)) {}
ReadFd& ReadFd::operator=(ReadFd&& other) noexcept {
    if (this != &other) {
        if (fd_ >= 0) ::close(fd_);
        fd_ = std::exchange(other.fd_, -1);
    }
    return *this;
}

bool Client::ValidateConfig(const Config& config) {
    return IsSocketName(config.abstract_socket_label) && IsHex32(config.token) &&
           config.timeout_ms >= 100 && config.timeout_ms <= 30000;
}
bool Client::ValidatePath(std::string_view path) {
    if (path.empty() || path.size() > MaxRequestPath || path.front() == '/' ||
        path.front() == '\\') return false;
    size_t start = 0;
    for (size_t i = 0; i <= path.size(); ++i) {
        if (i < path.size() && (path[i] == '\0' || path[i] == '\\' ||
                                static_cast<unsigned char>(path[i]) < 0x20)) return false;
        if (i == path.size() || path[i] == '/') {
            const auto component = path.substr(start, i - start);
            if (component.empty() || component == "." || component == "..") return false;
            start = i + 1;
        }
    }
    return true;
}
Result<Client::Reply> Client::Request(uint8_t opcode, std::string_view path,
                                      bool want_fd) const {
    if (!ValidateConfig(config_)) return {{}, Error::InvalidConfig};
    if (!ValidatePath(path)) return {{}, Error::InvalidPath};
    ReadFd sock = Connect(config_);
    if (!sock) return {{}, Error::Connection};
    if (!SameUidPeer(sock.get())) return {{}, Error::PeerMismatch};
    std::vector<uint8_t> packet;
    packet.reserve(14 + config_.token.size() + path.size());
    packet.insert(packet.end(), Magic.begin(), Magic.end());
    packet.push_back(Version);
    packet.push_back(opcode);
    AppendBe32(packet, static_cast<uint32_t>(config_.token.size()));
    packet.insert(packet.end(), config_.token.begin(), config_.token.end());
    AppendBe32(packet, static_cast<uint32_t>(path.size()));
    packet.insert(packet.end(), path.begin(), path.end());
    if (!SendAll(sock.get(), packet.data(), packet.size())) return {{}, Error::Io};
    std::array<uint8_t, 10> header{};
    ReadFd recv_fd;
    if (!RecvAllWithFd(sock.get(), header.data(), header.size(), recv_fd, want_fd))
        return {{}, Error::InvalidFrame};
    if (!std::equal(Magic.begin(), Magic.end(), header.begin()) || header[4] != Version ||
        Be32(header.data() + 6) > MaxPayload) return {{}, Error::InvalidFrame};
    if (header[5] != 0) return {{}, Error::RemoteError};
    Reply reply;
    reply.data.resize(Be32(header.data() + 6));
    reply.fd = std::move(recv_fd);
    if (!reply.data.empty() && !RecvAllWithFd(sock.get(), reply.data.data(),
                                              reply.data.size(), reply.fd, want_fd))
        return {{}, Error::InvalidFrame};
    if (want_fd && !reply.fd) return {{}, Error::MissingFd};
    if (!want_fd && reply.fd) return {{}, Error::UnexpectedFd};
    if (want_fd) {
        struct stat st{};
        const int flags = ::fcntl(reply.fd.get(), F_GETFL);
        if (::fstat(reply.fd.get(), &st) != 0 || !S_ISREG(st.st_mode) ||
            flags < 0 || (flags & O_ACCMODE) != O_RDONLY)
            return {{}, Error::UnexpectedFd};
    }
    return {std::move(reply), Error::None};
}

Result<Metadata> Client::Stat(std::string_view path) const {
    auto answer = Request(1, path, false);
    if (!answer) return {{}, answer.error};
    if (answer.value->data.size() != 17) return {{}, Error::PayloadInvalid};
    const auto& a = answer.value->data;
    return {Metadata{a[0] != 0, Be64(a.data() + 1), Be64(a.data() + 9)}, Error::None};
}
Result<std::vector<Entry>> Client::List(std::string_view path) const {
    auto answer = Request(2, path, false);
    if (!answer) return {{}, answer.error};
    const auto& a = answer.value->data;
    if (a.size() < 4) return {{}, Error::PayloadInvalid};
    size_t pos = 4;
    uint32_t count = Be32(a.data());
    if (count > MaxListEntries || count > (a.size() - 4) / 19)
        return {{}, Error::PayloadInvalid};
    std::vector<Entry> entries;
    entries.reserve(count);
    for (uint32_t i = 0; i < count; ++i) {
        if (pos + 2 > a.size()) return {{}, Error::PayloadInvalid};
        uint16_t namelen = uint16_t(a[pos]) << 8 | uint16_t(a[pos + 1]);
        pos += 2;
        if (!namelen || a.size() - pos < size_t(namelen) + 17)
            return {{}, Error::PayloadInvalid};
        std::string_view name(reinterpret_cast<const char*>(a.data() + pos), namelen);
        if (name == "." || name == ".." || name.find('/') != name.npos ||
            name.find('\\') != name.npos || name.find('\0') != name.npos ||
            std::any_of(name.begin(), name.end(), [](unsigned char c){ return c < 0x20; }))
            return {{}, Error::PayloadInvalid};
        pos += namelen;
        Metadata meta{a[pos] != 0, Be64(a.data() + pos + 1),
                      Be64(a.data() + pos + 9)};
        pos += 17;
        entries.push_back({std::string(name), meta});
    }
    if (pos != a.size()) return {{}, Error::PayloadInvalid};
    return {std::move(entries), Error::None};
}
Result<ReadFd> Client::OpenRead(std::string_view path) const {
    auto answer = Request(3, path, true);
    if (!answer) return {{}, answer.error};
    if (!answer.value->data.empty()) return {{}, Error::PayloadInvalid};
    return {std::move(answer.value->fd), Error::None};
}

} // namespace Bachata::Saf::BSF1
