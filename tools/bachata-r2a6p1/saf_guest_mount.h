// SPDX-License-Identifier: GPL-2.0-or-later
// Explicitly opt-in, read-only guest /app0 mount. Not enabled by default.
#pragma once
#include <string>
#include <string_view>
#include <vector>
#include "saf_bsf1_client.h"

namespace Bachata::Saf::Guest {
bool EnableExperimental(BSF1::Config config, std::string verified_relative_game_root);
bool Enabled() noexcept;
bool Scoped(std::string_view guest_path) noexcept;
// All functions fail closed when not enabled, invalid paths or broker I/O fails.
BSF1::Result<BSF1::Metadata> Stat(std::string_view guest_path);
BSF1::Result<std::vector<BSF1::Entry>> List(std::string_view guest_path);
BSF1::Result<BSF1::ReadFd> OpenRead(std::string_view guest_path);
} // namespace Bachata::Saf::Guest
