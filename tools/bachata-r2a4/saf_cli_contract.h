// SPDX-License-Identifier: GPL-2.0-or-later
// R2A.4 P0: CLI contract validation and sensitive-argv redaction, NOT an SAF file backend.
#pragma once
#include <cstddef>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

namespace Platform::Bachata::R2A4 {
constexpr std::string_view ContractFlag = "--bachata-contract";
constexpr std::string_view SocketFlag = "--bachata-saf-socket";
constexpr std::string_view TokenFlag = "--bachata-saf-token";

inline bool IsHex32(std::string_view value) {
    if (value.size() != 32) return false;
    for (unsigned char c : value) {
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') ||
              (c >= 'A' && c <= 'F'))) return false;
    }
    return true;
}

// Abstract AF_UNIX address label (Linux sun_path includes leading zero).
// This only checks launch syntax; authentication and SAF I/O need broker protocol tests.
inline bool IsAbstractSocketLabel(std::string_view value) {
    if (value.empty() || value.size() > 106) return false;
    if (value.front() == '/' || value.front() == '@') return false;
    for (unsigned char c : value) {
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '-' || c == '_' || c == '.'))
            return false;
    }
    return true;
}

inline bool ValidateContractCli(const std::optional<std::string>& nonce,
                                const std::optional<std::string>& abstract_socket,
                                const std::optional<std::string>& session_token) {
    // For F43DEV managed Linux runtime, all three values are mandatory.
    return nonce && abstract_socket && session_token &&
           IsHex32(*nonce) && IsAbstractSocketLabel(*abstract_socket) &&
           IsHex32(*session_token);
}

inline bool IsSensitiveFlag(std::string_view value) {
    return value == ContractFlag || value == SocketFlag || value == TokenFlag;
}

inline bool SensitiveAssignment(std::string_view value, std::string& name) {
    for (const auto flag : {ContractFlag, SocketFlag, TokenFlag}) {
        if (value.size() > flag.size() && value.substr(0, flag.size()) == flag &&
            value[flag.size()] == '=') {
            name.assign(flag);
            return true;
        }
    }
    return false;
}

inline std::vector<std::string> RedactArgv(int argc, char* const argv[]) {
    std::vector<std::string> output;
    output.reserve(argc > 0 ? static_cast<size_t>(argc) : 0);
    bool redact_next = false;
    for (int i = 0; i < argc; ++i) {
        const std::string_view value = argv && argv[i] ? std::string_view(argv[i]) : "";
        if (redact_next) {
            output.emplace_back("[REDACTED]");
            redact_next = false;
        } else if (IsSensitiveFlag(value)) {
            output.emplace_back(value);
            redact_next = true;
        } else {
            std::string name;
            if (SensitiveAssignment(value, name)) {
                output.emplace_back(name + "=[REDACTED]");
            } else {
                output.emplace_back(value);
            }
        }
    }
    // Invalid missing-sensitive-value CLI is rejected by CLI11 before logging.
    return output;
}
} // namespace Platform::Bachata::R2A4
