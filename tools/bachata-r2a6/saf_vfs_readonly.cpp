// SPDX-License-Identifier: GPL-2.0-or-later
#include "saf_vfs_readonly.h"
#include <utility>

namespace Bachata::Saf::Vfs {
ReadOnlyMount::ReadOnlyMount(const BSF1::Client& broker, std::string broker_root)
    : broker_(broker), broker_root_(std::move(broker_root)) {}

bool ReadOnlyMount::IsScoped(std::string_view path) {
    return path == GuestRoot ||
           (path.size() > GuestRoot.size() &&
            path.substr(0, GuestRoot.size()) == GuestRoot &&
            path[GuestRoot.size()] == '/');
}
bool ReadOnlyMount::ValidRoot(std::string_view path) {
    return BSF1::Client::ValidatePath(path);
}
std::optional<std::string> ReadOnlyMount::Resolve(std::string_view guest) const {
    if (!IsScoped(guest) || !ValidRoot(broker_root_)) return std::nullopt;
    if (guest == GuestRoot) return broker_root_;
    const std::string_view rest = guest.substr(GuestRoot.size() + 1);
    if (!BSF1::Client::ValidatePath(rest)) return std::nullopt;
    std::string candidate = broker_root_;
    candidate.push_back('/');
    candidate.append(rest);
    if (!BSF1::Client::ValidatePath(candidate)) return std::nullopt;
    return candidate;
}
BSF1::Result<BSF1::Metadata> ReadOnlyMount::Stat(std::string_view guest) const {
    auto path = Resolve(guest);
    if (!path) return {{}, BSF1::Error::InvalidPath};
    return broker_.Stat(*path);
}
BSF1::Result<std::vector<BSF1::Entry>> ReadOnlyMount::List(std::string_view guest) const {
    auto path = Resolve(guest);
    if (!path) return {{}, BSF1::Error::InvalidPath};
    return broker_.List(*path);
}
BSF1::Result<BSF1::ReadFd> ReadOnlyMount::OpenRead(std::string_view guest) const {
    auto path = Resolve(guest);
    if (!path) return {{}, BSF1::Error::InvalidPath};
    return broker_.OpenRead(*path);
}
} // namespace Bachata::Saf::Vfs
