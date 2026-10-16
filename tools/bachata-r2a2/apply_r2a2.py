#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Apply R2A.2 managed-host gate to exact R2A public candidate source.

Requires R2A patch already applied and the pinned upstream shadPS4 git revision.
Will not repack or resign APKs.
"""
import argparse
import shutil
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
MAIN_BLOB = "13733edf30905adcb65fb3e3e748256164bf3812"
INCLUDE_OLD = """#ifdef ENABLE_BACHATA_RUNTIME
#include "platform/bachata/runtime_client.h"
#endif"""
INCLUDE_NEW = """#ifdef ENABLE_BACHATA_RUNTIME
#include "platform/bachata/runtime_client.h"
#if defined(__linux__) && defined(__aarch64__)
#include "platform/bachata/f43dev_identity_gate.h"
#endif
#endif"""
PRE_OLD = """#ifdef ENABLE_BACHATA_RUNTIME
    auto runtime_client = Platform::Bachata::RuntimeClient::Disabled();
    if (bachataSocket.has_value()) {"""
PRE_NEW = """#ifdef ENABLE_BACHATA_RUNTIME
    auto runtime_client = Platform::Bachata::RuntimeClient::Disabled();
#if defined(__linux__) && defined(__aarch64__)
    // An ARM64 F43DEV runtime must be launched by its private Android host.
    // Native/Bionic signing verification remains mandatory and unchanged.
    if (!bachataSocket.has_value() || !bachataStorageRoot.has_value() ||
        !Platform::Bachata::R2A2::VerifyManagedSocket(*bachataSocket,
                                                     *bachataStorageRoot)) {
        std::cerr << "F43DEV host gate: untrusted app-private root or socket\\n";
        return 1;
    }
#endif
    if (bachataSocket.has_value()) {"""
PEER_OLD = """        auto connected = Platform::Bachata::RuntimeClient::Connect(*bachataSocket);
        if (!connected.has_value() || !connected->SendHello()) {"""
PEER_NEW = """        auto connected = Platform::Bachata::RuntimeClient::Connect(*bachataSocket);
#if defined(__linux__) && defined(__aarch64__)
        if (!connected.has_value() ||
            !Platform::Bachata::R2A2::VerifyPeer(connected->NativeHandleForTest())) {
            std::cerr << "F43DEV host gate: runtime peer not authenticated\\n";
            return 1;
        }
        std::cerr << "BACHATA_F43DEV_R2A2_HOST_GATE_OK\\n";
#endif
        if (!connected.has_value() || !connected->SendHello()) {"""

def replace_exact(data, old, new):
    n = data.count(old)
    if n != 1:
        raise ValueError(f"Expected unique pinned source anchor; got {n}: {old[:60]!r}")
    return data.replace(old, new, 1)

def apply(source: Path, guard_header: Path):
    source = source.resolve()
    if not (source / ".git").exists():
        raise ValueError("Missing source .git")
    sha = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if sha != PIN:
        raise ValueError(f"Wrong source commit {sha}, expected {PIN}")
    main = source / "src/main.cpp"
    blob = subprocess.check_output(
        ["git", "-C", str(source), "hash-object", str(main)], text=True).strip()
    if blob != MAIN_BLOB:
        raise ValueError(f"Source main.cpp blob drift {blob}")
    raster = (source / "src/video_core/renderer_vulkan/vk_rasterizer.cpp").read_text()
    image = (source / "src/video_core/texture_cache/image.h").read_text()
    if "image.binding.has_storage" not in raster or "u32 has_storage : 1;" not in image:
        raise ValueError("R2A source patch not present; refusing R2A.2 build")
    data = main.read_text()
    for old, new in [(INCLUDE_OLD, INCLUDE_NEW),
                     (PRE_OLD, PRE_NEW), (PEER_OLD, PEER_NEW)]:
        data = replace_exact(data, old, new)
    header_output = source / "src/platform/bachata/f43dev_identity_gate.h"
    if header_output.exists():
        raise ValueError("Identity gate header already exists")
    if not guard_header.is_file():
        raise ValueError("Missing gate source header")
    # All validation before mutating source.
    main.write_text(data)
    shutil.copyfile(guard_header, header_output)
    print("R2A2_HOST_GATE_PATCH_APPLIED")
    print("src/main.cpp + src/platform/bachata/f43dev_identity_gate.h")
    print("R2A core patch preserved")
    return (main, header_output)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--guard", type=Path, default=Path(__file__).with_name("f43dev_identity_gate.h"))
    args = p.parse_args()
    apply(args.source, args.guard)
