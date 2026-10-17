// SPDX-License-Identifier: GPL-2.0-or-later
// Opt-in control and fail-closed guest path smoke tests. Uses synthetic credentials.
#include "saf_guest_mount.h"
#include "saf_vfs_readonly.h"
#include <cassert>
#include <iostream>

using Bachata::Saf::BSF1::Client;
using Bachata::Saf::BSF1::Config;
using Bachata::Saf::BSF1::Error;
namespace Guest = Bachata::Saf::Guest;

int main() {
    int count=0;
    auto check=[&](bool v){assert(v);++count;};
    const Config valid{"r2a6p1-test", "0123456789abcdef0123456789abcdef", 250};
    check(!Guest::Enabled());
    check(!Guest::Scoped("/app0/eboot.bin"));
    check(!Guest::EnableExperimental({"",valid.token,250},"games/test"));
    check(!Guest::EnableExperimental(valid,"games/../../unsafe"));
    check(!Guest::EnableExperimental(valid,""));
    check(!Guest::Enabled());
    check(Guest::EnableExperimental(valid,"games/CUSA00325"));
    check(Guest::Enabled());
    check(Guest::Scoped("/app0"));
    check(Guest::Scoped("/app0/eboot.bin"));
    check(!Guest::Scoped("/app0-invalid/eboot.bin"));
    check(!Guest::Scoped("/savedata/eboot.bin"));
    check(!Guest::EnableExperimental(valid,"games/CUSA00325"));
    const auto invalid = Guest::Stat("/app0/../../private");
    check(!invalid && invalid.error == Error::InvalidPath);
    const auto bad_list = Guest::List("/app0/..");
    check(!bad_list && bad_list.error == Error::InvalidPath);
    const auto bad_fd = Guest::OpenRead("/app0/a/../b");
    check(!bad_fd && bad_fd.error == Error::InvalidPath);
    std::cout<<"R2A6P1_GUEST_MOUNT_TESTS_PASS count="<<count<<"\n";
}
