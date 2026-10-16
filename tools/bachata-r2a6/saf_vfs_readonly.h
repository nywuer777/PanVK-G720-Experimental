// SPDX-License-Identifier: GPL-2.0-or-later
// R2A.6: scoped, read-only SAF guest-path adapter. Not enabled in the PS4 VFS.
// Real Android SAF broker integration and root selection still require live validation.
#pragma once
#include <optional>
#include <string>
#include <string_view>
#include <vector>
#include "saf_bsf1_client.h"

namespace Bachata::Saf::Vfs {

class ReadOnlyMount {
public:
    // broker_root MUST be the real, verified broker-relative game root.
    // Never guess a root from a game title or host file path.
    ReadOnlyMount(const BSF1::Client& broker, std::string broker_root);

    static constexpr std::string_view GuestRoot = "/app0";
    static bool IsScoped(std::string_view guest_path);
    static bool ValidRoot(std::string_view broker_root);

    // Empty on unscoped/invalid traversal paths, or unverified game-root.
    std::optional<std::string> Resolve(std::string_view guest_path) const;
    BSF1::Result<BSF1::Metadata> Stat(std::string_view guest_path) const;
    BSF1::Result<std::vector<BSF1::Entry>> List(std::string_view guest_path) const;
    BSF1::Result<BSF1::ReadFd> OpenRead(std::string_view guest_path) const;

    // No operations here may create/truncate/write/rename/remove guest content.
    static constexpr bool Writable() { return false; }

private:
    const BSF1::Client& broker_;
    std::string broker_root_;
};

} // namespace Bachata::Saf::Vfs
