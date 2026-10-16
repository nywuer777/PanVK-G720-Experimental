#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pin and attach vetted BSF1 transport to the R2A+R2A2+R2A4 GLIBC shadPS4 candidate.

Deliberately does not install a SAF VFS mount, send requests on startup or modify
the Android APK. Fail closed on source, hash or patch-anchor mismatches.
"""
import argparse
import hashlib
import shutil
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
CMAKE_BLOB = "e56c54a142c5c1dbee1818574dfaf20ae4724408"
SOURCE_HASHES = {
    "saf_bsf1_client.h": "cc30a3dc5f805a2a008ccbe166e0f032a812157b872d03a9239f8e04dff18795",
    "saf_bsf1_client.cpp": "693520942c8f4bfc4bc3a8726f727a986a144fb3e40721b39a5f10a87f3142cf",
}
CMAKE_OLD = """        src/platform/bachata/audio_transport.cpp
        src/platform/bachata/runtime_client.h
"""
CMAKE_NEW = """        src/platform/bachata/audio_transport.cpp
        src/platform/bachata/saf_bsf1_client.cpp
        src/platform/bachata/saf_bsf1_client.h
        src/platform/bachata/runtime_client.h
"""
INCLUDE_OLD = '#include "platform/bachata/saf_cli_contract.h"\n'
INCLUDE_NEW = INCLUDE_OLD + '#include "platform/bachata/saf_bsf1_client.h"\n'
MARKER_OLD = '    std::cerr << "BACHATA_F43DEV_R2A4_CLI_SHAPE_OK_SAF_IO_UNIMPLEMENTED\\n";'
MARKER_NEW = """    // R2A5 transport is compiled and its configuration is validated, but the
    // PS4 VFS is intentionally NOT connected to this unverified Android broker.
    const Bachata::Saf::BSF1::Config saf_config{
        *bachataSafSocket, *bachataSafToken, 2000};
    if (!Bachata::Saf::BSF1::Client::ValidateConfig(saf_config)) {
        std::cerr << "Bachata SAF transport configuration rejected\\n";
        return 1;
    }
    const Bachata::Saf::BSF1::Client saf_broker(saf_config);
    (void)saf_broker;
    std::cerr << "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED\\n";"""

def replace_exact(text, before, after):
    count = text.count(before)
    if count != 1:
        raise ValueError(f"Expected one source anchor, saw {count}: {before[:70]!r}")
    return text.replace(before, after, 1)

def apply(root: Path, local: Path):
    root = root.resolve()
    local = local.resolve()
    if not (root / ".git").exists():
        raise ValueError("Not an upstream git checkout")
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != PIN:
        raise ValueError(f"Unexpected source revision {revision}")
    cmake = root / "CMakeLists.txt"
    actual_blob = subprocess.check_output(
        ["git", "-C", str(root), "hash-object", str(cmake)], text=True).strip()
    if actual_blob != CMAKE_BLOB:
        raise ValueError(f"CMake drift: {actual_blob}")
    main = root / "src/main.cpp"
    original = main.read_text(encoding="utf-8")
    for required in ("BACHATA_F43DEV_R2A2_HOST_GATE_OK",
                     "ValidateContractCli", "RedactArgv",
                     "BACHATA_F43DEV_R2A4_CLI_SHAPE_OK_SAF_IO_UNIMPLEMENTED"):
        if required not in original:
            raise ValueError(f"Missing prerequisite R2A2/R2A4 anchor {required}")
    if "image.binding.has_storage" not in (
        root / "src/video_core/renderer_vulkan/vk_rasterizer.cpp"
    ).read_text(encoding="utf-8"):
        raise ValueError("Missing R2A mixed-image fix")

    inputs = {}
    for name, expected in SOURCE_HASHES.items():
        source = local / name
        if not source.is_file():
            raise ValueError(f"Missing R2A5 source {name}")
        data = source.read_bytes()
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError(f"Source SHA-256 mismatch: {name}")
        target = root / "src/platform/bachata" / name
        if target.exists():
            raise ValueError(f"Output already exists: {target}")
        inputs[target] = data
    cmake_new = replace_exact(cmake.read_text(encoding="utf-8"), CMAKE_OLD, CMAKE_NEW)
    main_new = replace_exact(replace_exact(original, INCLUDE_OLD, INCLUDE_NEW),
                             MARKER_OLD, MARKER_NEW)
    # All preconditions checked before first write; no changes to other branches.
    cmake.write_text(cmake_new, encoding="utf-8", newline="")
    main.write_text(main_new, encoding="utf-8", newline="")
    for target, data in inputs.items():
        target.write_bytes(data)
    print("R2A5_TRANSPORT_ATTACHED_TO_CMAKE_AND_MAIN")
    print("R2A5_SAF_VFS_MOUNT=DISABLED")
    print("R2A5_APK_BUILT=NO")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("source", type=Path)
    p.add_argument("--client-dir", type=Path, default=Path(__file__).resolve().parent)
    args = p.parse_args()
    apply(args.source, args.client_dir)
