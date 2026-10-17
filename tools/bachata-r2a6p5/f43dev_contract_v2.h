// SPDX-License-Identifier: GPL-2.0-or-later
// F43DEV V2 host contract proof: exact HELLO line reconstructed from read-only
// classes.dex evidence Lyy2.a()/b() and host native runtime string references.
// This does NOT authenticate APK signing, UID, or the SAF broker.
#pragma once
#include <optional>
#include <string>
#include <string_view>

namespace Platform::Bachata::ContractV2 {
inline bool ValidNonce(std::string_view nonce) {
    if (nonce.size() != 32) return false;
    for (const unsigned char c : nonce) {
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f')))
            return false;
    }
    return true;
}

// Call only AFTER the R2A2 same-UID managed-host socket is authenticated.
// Never log this line, because the value is an ephemeral session secret.
inline std::optional<std::string> BuildHello(std::string_view nonce) {
    if (!ValidNonce(nonce)) return std::nullopt;
    std::string frame{"BACHATA/1 HELLO version=2 contract="};
    frame.append(nonce);
    frame.push_back('\n');
    return frame;
}
} // namespace Platform::Bachata::ContractV2
