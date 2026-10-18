// SPDX-License-Identifier: GPL-2.0-or-later
// P54: auth-scoped, read-only first eboot FD bridge. NOT a full SAF game VFS.
// No direct game content, token, socket or path is logged.
#pragma once

#include <cerrno>
#include <filesystem>
#include <optional>
#include <string>
#include <string_view>
#include <utility>

#include "platform/bachata/saf_bsf1_client.h"

namespace Bachata::Saf::P54 {
enum class Outcome {
    NotApplicable,
    InvalidOverrideRoot,
    BrokerUnavailable,
    BrokerDenied,
    BrokerProtocolMismatch,
    BrokerRequestSendFailed,
    BrokerResponseFrameInvalid,
    BrokerResponsePayloadInvalid,
    BrokerFdInvalid,
    EbootFdReady,
};

struct Probe {
    Outcome outcome = Outcome::NotApplicable;
    BSF1::ReadFd fd;
    std::filesystem::path proc_fd_path;
    explicit operator bool() const { return outcome == Outcome::EbootFdReady; }
};

inline constexpr const char* Marker(Outcome status) {
    switch (status) {
    case Outcome::NotApplicable:
        return "BACHATA_P54_BSF1_EBOOT_NOT_APPLICABLE";
    case Outcome::InvalidOverrideRoot:
        return "BACHATA_P54_BSF1_EBOOT_ROOT_INVALID";
    case Outcome::BrokerUnavailable:
        return "BACHATA_P54_BSF1_EBOOT_BROKER_UNAVAILABLE";
    case Outcome::BrokerDenied:
        return "BACHATA_P54_BSF1_EBOOT_BROKER_DENIED";
    case Outcome::BrokerProtocolMismatch:
        return "BACHATA_P54_BSF1_EBOOT_BROKER_PROTOCOL_MISMATCH";
    case Outcome::BrokerRequestSendFailed:
        return "BACHATA_P55_BSF1_EBOOT_REQUEST_SEND_FAILED";
    case Outcome::BrokerResponseFrameInvalid:
        return "BACHATA_P55_BSF1_EBOOT_RESPONSE_FRAME_INVALID";
    case Outcome::BrokerResponsePayloadInvalid:
        return "BACHATA_P55_BSF1_EBOOT_RESPONSE_PAYLOAD_INVALID";
    case Outcome::BrokerFdInvalid:
        return "BACHATA_P54_BSF1_EBOOT_FD_INVALID";
    case Outcome::EbootFdReady:
        return "BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY";
    }
    return "BACHATA_P54_BSF1_EBOOT_UNKNOWN_ERROR";
}

inline Outcome Classify(BSF1::Error code) {
    switch (code) {
    case BSF1::Error::Connection:
    case BSF1::Error::PeerMismatch:
    case BSF1::Error::InvalidConfig:
        return Outcome::BrokerUnavailable;
    case BSF1::Error::RemoteError:
    case BSF1::Error::InvalidPath:
        return Outcome::BrokerDenied;
    case BSF1::Error::MissingFd:
    case BSF1::Error::UnexpectedFd:
        return Outcome::BrokerFdInvalid;
    case BSF1::Error::Io:
        return Outcome::BrokerRequestSendFailed;
    case BSF1::Error::InvalidFrame:
        return Outcome::BrokerResponseFrameInvalid;
    case BSF1::Error::PayloadInvalid:
        return Outcome::BrokerResponsePayloadInvalid;
    default:
        return Outcome::BrokerProtocolMismatch;
    }
}

// Only called *after* Host V2 accepted HELLO and SO_PEERCRED.
// The Android app has already supplied session-scoped socket + token.
// Never guess a game ID or enumerate the broker; request only the exact
// relative eboot.bin that the trusted app passed with -g eboot.bin.
// Returns a procfs descriptor path suitable for the early ELF loader.
// Keeping Probe.fd alive is mandatory until Emulator::Run returns.
// This does not implement /app0, param.sfo, DLC, getdents or saves.
inline Probe TryOpenInitialEboot(
    const BSF1::Client& broker,
    std::string_view requested_game,
    const std::optional<std::filesystem::path>& override_root) {
    if (requested_game != "eboot.bin")
        return {Outcome::NotApplicable, {}, {}};
    if (!override_root || !override_root->is_absolute() ||
        *override_root != override_root->lexically_normal())
        return {Outcome::InvalidOverrideRoot, {}, {}};
    // The original F43DEV launcher stages a private direct-runtime directory.
    // Reject symlink directories, and never attempt to construct/open a host
    // pathname out of the SAF document name.
    std::error_code err;
    const auto info = std::filesystem::symlink_status(*override_root, err);
    if (err || info.type() != std::filesystem::file_type::directory)
        return {Outcome::InvalidOverrideRoot, {}, {}};

    auto supplied = broker.OpenRead("eboot.bin");
    if (!supplied)
        return {Classify(supplied.error), {}, {}};
    if (!supplied.value || !*supplied.value)
        return {Outcome::BrokerFdInvalid, {}, {}};
    const int fd = supplied.value->get();
    std::filesystem::path proc_fd =
        std::filesystem::path("/proc/self/fd") / std::to_string(fd);
    err.clear();
    if (!std::filesystem::is_regular_file(proc_fd, err) || err)
        return {Outcome::BrokerFdInvalid, {}, {}};
    return {Outcome::EbootFdReady, std::move(*supplied.value), std::move(proc_fd)};
}
} // namespace Bachata::Saf::P54
