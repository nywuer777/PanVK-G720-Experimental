// SPDX-License-Identifier: GPL-2.0-or-later
// R2A.6/P2: metadata-only authenticated broker probe; no game, GPU, or file content reads.
// The broker itself verifies the session token. This module does not replace Android signing.
#pragma once
#include <string_view>
#include "saf_bsf1_client.h"

namespace Bachata::Saf::Probe {
enum class Outcome {
    FileOk,
    DirectoryOk,
    InvalidPath,
    StatFailed,
    ListFailed,
    OpenReadFailed,
    DescriptorRejected,
};
struct Result {
    Outcome outcome{Outcome::InvalidPath};
    bool passed() const {
        return outcome == Outcome::FileOk || outcome == Outcome::DirectoryOk;
    }
};
Result Run(const BSF1::Client& client, std::string_view broker_relative_path);
const char* SafeDiagnostic(Outcome outcome); // Never contain path, token, or response data.
} // namespace Bachata::Saf::Probe
