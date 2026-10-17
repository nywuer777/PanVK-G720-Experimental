// SPDX-License-Identifier: GPL-2.0-or-later
#include "saf_guest_mount.h"
#include "saf_vfs_readonly.h"
#include <atomic>
#include <memory>
#include <mutex>
#include <utility>

namespace Bachata::Saf::Guest {
namespace {
std::mutex init_mutex;
std::unique_ptr<BSF1::Client> broker;
std::unique_ptr<Vfs::ReadOnlyMount> mount;
std::atomic<bool> ready{false};
} // namespace

bool EnableExperimental(BSF1::Config config, std::string root) {
    if (!BSF1::Client::ValidateConfig(config) ||
        !Vfs::ReadOnlyMount::ValidRoot(root)) return false;
    std::scoped_lock lock(init_mutex);
    if (ready.load(std::memory_order_acquire)) return false;
    auto new_broker = std::make_unique<BSF1::Client>(std::move(config));
    auto new_mount = std::make_unique<Vfs::ReadOnlyMount>(*new_broker, std::move(root));
    broker = std::move(new_broker);
    mount = std::move(new_mount);
    ready.store(true, std::memory_order_release);
    return true;
}
bool Enabled() noexcept {
    return ready.load(std::memory_order_acquire);
}
bool Scoped(std::string_view path) noexcept {
    return Enabled() && Vfs::ReadOnlyMount::IsScoped(path);
}
BSF1::Result<BSF1::Metadata> Stat(std::string_view guest) {
    if (!Scoped(guest)) return {{}, BSF1::Error::InvalidPath};
    return mount->Stat(guest);
}
BSF1::Result<std::vector<BSF1::Entry>> List(std::string_view guest) {
    if (!Scoped(guest)) return {{}, BSF1::Error::InvalidPath};
    return mount->List(guest);
}
BSF1::Result<BSF1::ReadFd> OpenRead(std::string_view guest) {
    if (!Scoped(guest)) return {{}, BSF1::Error::InvalidPath};
    return mount->OpenRead(guest);
}
} // namespace Bachata::Saf::Guest
