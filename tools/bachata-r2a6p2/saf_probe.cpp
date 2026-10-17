// SPDX-License-Identifier: GPL-2.0-or-later
#include "saf_probe.h"
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

namespace Bachata::Saf::Probe {
Result Run(const BSF1::Client& broker, std::string_view path) {
    if (!BSF1::Client::ValidatePath(path)) {
        return {Outcome::InvalidPath};
    }
    const auto st = broker.Stat(path);
    if (!st) {
        return {Outcome::StatFailed};
    }
    if (st.value->is_directory) {
        // List is parsed by BSF1; this probe does not log names/count or contents.
        auto listing = broker.List(path);
        return {listing ? Outcome::DirectoryOk : Outcome::ListFailed};
    }
    auto fd = broker.OpenRead(path);
    if (!fd) {
        return {Outcome::OpenReadFailed};
    }
    // Opening a descriptor and fstat do not read or copy PS4 game data.
    struct stat meta{};
    const int flags = ::fcntl(fd.value->get(), F_GETFL);
    if (::fstat(fd.value->get(), &meta) != 0 || !S_ISREG(meta.st_mode) ||
        flags < 0 || (flags & O_ACCMODE) != O_RDONLY) {
        return {Outcome::DescriptorRejected};
    }
    return {Outcome::FileOk};
}
const char* SafeDiagnostic(Outcome state) {
    switch (state) {
        case Outcome::FileOk: return "BSF1_LAB_PROBE_FILE_OK";
        case Outcome::DirectoryOk: return "BSF1_LAB_PROBE_DIRECTORY_OK";
        case Outcome::InvalidPath: return "BSF1_LAB_PROBE_INVALID_PATH";
        case Outcome::StatFailed: return "BSF1_LAB_PROBE_STAT_FAILED";
        case Outcome::ListFailed: return "BSF1_LAB_PROBE_LIST_FAILED";
        case Outcome::OpenReadFailed: return "BSF1_LAB_PROBE_OPEN_FAILED";
        case Outcome::DescriptorRejected: return "BSF1_LAB_PROBE_FD_REJECTED";
    }
    return "BSF1_LAB_PROBE_UNKNOWN";
}
} // namespace Bachata::Saf::Probe
