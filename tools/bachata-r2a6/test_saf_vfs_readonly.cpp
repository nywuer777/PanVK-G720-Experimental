// SPDX-License-Identifier: GPL-2.0-or-later
// R2A.6 fail-closed path and mount-scope tests. No real Android broker required.
#include "saf_vfs_readonly.h"
#include <cassert>
#include <iostream>
#include <string>
#include <string_view>

using Bachata::Saf::BSF1::Client;
using Bachata::Saf::BSF1::Config;
using Bachata::Saf::BSF1::Error;
using Bachata::Saf::Vfs::ReadOnlyMount;

int main() {
    int checks = 0;
    auto verify = [&](bool condition) { assert(condition); ++checks; };
    Client broker(Config{"r2a6-test-abstract", "0123456789abcdef0123456789abcdef", 250});
    ReadOnlyMount mount(broker, "games/CUSA00325");
    verify(ReadOnlyMount::GuestRoot == "/app0");
    verify(!ReadOnlyMount::Writable());
    verify(ReadOnlyMount::ValidRoot("games/CUSA00325"));
    verify(!ReadOnlyMount::ValidRoot(""));
    verify(!ReadOnlyMount::ValidRoot("/games"));
    verify(!ReadOnlyMount::ValidRoot("games/../evil"));
    verify(ReadOnlyMount::IsScoped("/app0"));
    verify(ReadOnlyMount::IsScoped("/app0/eboot.bin"));
    verify(!ReadOnlyMount::IsScoped("/app01/file"));
    verify(!ReadOnlyMount::IsScoped("/app0.evil/file"));
    verify(!ReadOnlyMount::IsScoped("/savedata/file"));
    verify(!ReadOnlyMount::IsScoped("app0/file"));
    const auto root = mount.Resolve("/app0");
    verify(root && *root == "games/CUSA00325");
    const auto file = mount.Resolve("/app0/eboot.bin");
    verify(file && *file == "games/CUSA00325/eboot.bin");
    const auto nested = mount.Resolve("/app0/sce_module/libScePad.prx");
    verify(nested && *nested == "games/CUSA00325/sce_module/libScePad.prx");
    for (const std::string_view path : {
         "/app0/", "/app0//foo", "/app0/./foo", "/app0/../foo",
         "/app0/foo/..", "/app0/foo/.", "/app0/foo//bar",
         "/app0/file\\name", "/app0/file\nname", "/app0/fo\0o",
         "/app0.evil/file", "/app01/file", "/hostapp/eboot.bin",
         "app0/eboot.bin", "/data/user/0/private"
    }) {
        verify(!mount.Resolve(path));
    }
    ReadOnlyMount bad(broker, "games/../../tmp");
    verify(!bad.Resolve("/app0/eboot.bin"));
    ReadOnlyMount bad2(broker, "");
    verify(!bad2.Resolve("/app0/eboot.bin"));
    verify(!mount.Stat("/hostapp/eboot.bin") &&
           mount.Stat("/hostapp/eboot.bin").error == Error::InvalidPath);
    verify(!mount.List("/app0/../data") &&
           mount.List("/app0/../data").error == Error::InvalidPath);
    verify(!mount.OpenRead("/app0/../../etc/passwd") &&
           mount.OpenRead("/app0/../../etc/passwd").error == Error::InvalidPath);
    std::cout << "R2A6_READONLY_VFS_PATH_TESTS_PASS count=" << checks << '\n';
}
