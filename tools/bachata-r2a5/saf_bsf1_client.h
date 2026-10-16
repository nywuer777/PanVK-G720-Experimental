// SPDX-License-Identifier: GPL-2.0-or-later
// Experimental BSF1 client reconstructed from F43DEV V2 Bionic static evidence.
// Read-only; no real Android-broker interoperability is claimed.
#pragma once
#include <cstdint>
#include <optional>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace Bachata::Saf::BSF1 {

class ReadFd {
public:
    ReadFd() = default;
    explicit ReadFd(int fd) : fd_(fd) {}
    ~ReadFd();
    ReadFd(const ReadFd&) = delete;
    ReadFd& operator=(const ReadFd&) = delete;
    ReadFd(ReadFd&& other) noexcept;
    ReadFd& operator=(ReadFd&& other) noexcept;
    int get() const { return fd_; }
    explicit operator bool() const { return fd_ >= 0; }
private:
    int fd_ = -1;
};

struct Metadata {
    bool is_directory = false;
    uint64_t field_a = 0; // Original meaning not yet established.
    uint64_t field_b = 0; // Original meaning not yet established.
};
struct Entry {
    std::string name;
    Metadata metadata;
};

// This interface never returns tokens, raw frames, or sensitive strings in errors.
enum class Error {
    None, InvalidConfig, InvalidPath, Connection, PeerMismatch, Io,
    InvalidFrame, RemoteError, MissingFd, UnexpectedFd, PayloadInvalid,
};

template <typename T> struct Result {
    std::optional<T> value;
    Error error = Error::None;
    explicit operator bool() const { return value.has_value(); }
};

struct Config {
    std::string abstract_socket_label;  // no '@', leading NUL inserted by the transport
    std::string token;                  // 32 hex; do not print or persist
    int timeout_ms = 2000;
};

class Client {
public:
    explicit Client(Config config) : config_(std::move(config)) {}
    Client(const Client&) = delete;
    Client& operator=(const Client&) = delete;
    Result<Metadata> Stat(std::string_view path) const;
    Result<std::vector<Entry>> List(std::string_view path) const;
    Result<ReadFd> OpenRead(std::string_view path) const;
    static bool ValidatePath(std::string_view path);
    static bool ValidateConfig(const Config& config);
private:
    struct Reply {
        std::vector<uint8_t> data;
        ReadFd fd;
    };
    Result<Reply> Request(uint8_t op, std::string_view path, bool want_fd) const;
    Config config_;
};

} // namespace Bachata::Saf::BSF1
