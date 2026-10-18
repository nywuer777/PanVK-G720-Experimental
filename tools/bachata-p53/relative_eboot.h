// SPDX-License-Identifier: GPL-2.0-or-later
// P53: conservative CLI -g eboot.bin resolution for F43DEV extracted game roots.
#pragma once
#include <filesystem>
#include <optional>
#include <string_view>
#include <system_error>

namespace Platform::Bachata::P53 {
inline std::optional<std::filesystem::path> ResolveEboot(
    std::string_view game, const std::optional<std::filesystem::path>& root) {
    // Never reinterpret arbitrary guest paths, absolute host paths, IDs or
    // user-controlled ".." sequences. Only the exact observed relative
    // eboot.bin launch from the trusted Android host is eligible.
    if (game != "eboot.bin" || !root || !root->is_absolute()) return std::nullopt;
    std::error_code err;
    const auto real_root = std::filesystem::canonical(*root, err);
    if (err || !std::filesystem::is_directory(real_root, err) || err)
        return std::nullopt;
    const auto entry = real_root / "eboot.bin";
    // Never follow a symlink from a game root to unrelated host data.
    if (std::filesystem::is_symlink(std::filesystem::symlink_status(entry, err)) || err)
        return std::nullopt;
    if (!std::filesystem::is_regular_file(entry, err) || err)
        return std::nullopt;
    const auto resolved = std::filesystem::canonical(entry, err);
    if (err || resolved.parent_path() != real_root)
        return std::nullopt;
    return resolved;
}
} // namespace Platform::Bachata::P53
