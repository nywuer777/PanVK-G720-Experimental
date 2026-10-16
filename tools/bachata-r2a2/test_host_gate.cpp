// SPDX-License-Identifier: GPL-2.0-or-later
// Host Linux unit tests only; does not impersonate Android signing verification.
#include "f43dev_identity_gate.h"
#include <cassert>
#include <iostream>

int main() {
    using namespace Platform::Bachata::R2A2;
    assert(AppPrivatePath("/data/user/0/com.bachatas4.android.f43dev"));
    assert(AppPrivatePath("/data/user/0/com.bachatas4.android.f43dev/files"));
    assert(AppPrivatePath("/data/data/com.bachatas4.android.f43dev/files"));
    assert(AppPrivatePath("/data/user_de/0/com.bachatas4.android.f43dev/files"));
    assert(!AppPrivatePath("/data/user/0/com.bachatas4.android.github/files"));
    assert(!AppPrivatePath("/data/user/0/com.bachatas4.android.f43dev.evil/files"));
    assert(!AppPrivatePath("/data/user/10/com.bachatas4.android.f43dev"));
    assert(!AppPrivatePath("/tmp/com.bachatas4.android.f43dev"));
    assert(!AppPrivatePath("/data/user/0/com.bachatas4.android.f43dev_evil"));
    const std::filesystem::path root="/data/user/0/com.bachatas4.android.f43dev";
    assert(InsideRoot(root/"files"/"runtime.sock", root));
    assert(!InsideRoot(root, root));
    assert(!InsideRoot("/data/user/0/com.bachatas4.android.f43dev.evil/runtime.sock", root));
    assert(!VerifyManagedSocket("/tmp/nonexistent.sock", "/tmp"));
    assert(!VerifyPeer(-1));
    int pair[2]={-1,-1};
    assert(::socketpair(AF_UNIX, SOCK_STREAM, 0, pair)==0);
    assert(VerifyPeer(pair[0]));
    assert(VerifyPeer(pair[1]));
    ::close(pair[0]); ::close(pair[1]);
    std::cout << "R2A2_HOST_GATE_TESTS_PASS\n";
}
