#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P54 stage 1: wire authenticated BSF1 OpenRead to the first ELF loader only.

Applies after P49 HostV2+BCn and P53 gamepath patches at the upstream source pin.
No whole-game /app0 mount is activated: param.sfo, DLC and game resources still
require a verified broker-root mapping in a later independent stage.
"""
import argparse
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
INCLUDE = '#include "platform/bachata/relative_eboot.h"'
INCLUDE_NEW = INCLUDE + '\n#include "platform/bachata/p54_bsf1_eboot.h"'
ANCHOR = '    if (!std::filesystem::exists(ebootPath)) {'
NEW = r'''#ifdef ENABLE_BACHATA_RUNTIME
    // P54: the original Android app has validated the game tree using SAF;
    // P53 alone can only resolve already-materialized physical files.
    // Probe one exact document through the authenticated, same-UID BSF1
    // broker, after Host V2 verification; do not enumerate guessed paths.
    std::optional<Bachata::Saf::BSF1::ReadFd> p54_eboot_fd;
    if (*gamePath == "eboot.bin" && !std::filesystem::exists(ebootPath)) {
        auto p54_probe = Bachata::Saf::P54::TryOpenInitialEboot(
            saf_broker, *gamePath, overrideRoot);
        std::cerr << Bachata::Saf::P54::Marker(p54_probe.outcome) << '\n';
        if (p54_probe) {
            // /proc/self/fd/N remains valid until Emulator::Run returns,
            // because the owning descriptor is held in p54_eboot_fd.
            p54_eboot_fd.emplace(std::move(p54_probe.fd));
            ebootPath = std::move(p54_probe.proc_fd_path);
        }
    }
#endif
    if (!std::filesystem::exists(ebootPath)) {'''

def patched(source: str) -> str:
    for marker in ("BACHATA_P53_EBOOT_OVERRIDE_ROOT_RESOLVED",
                   "BACHATA_P53_EBOOT_ROOT_UNAVAILABLE",
                   "BACHATA_F43DEV_R2A2_HOST_GATE_OK",
                   "SendHelloV2",
                   "const Bachata::Saf::BSF1::Client saf_broker(saf_config);"):
        if marker not in source:
            raise ValueError("P54_HOST_V2_P53_BSF1_PREREQUISITE_MISSING")
    if source.count(INCLUDE) != 1 or source.count(ANCHOR) != 1:
        raise ValueError("P54_UNEXPECTED_MAIN_GAMEPATH_ANCHOR")
    if "p54_eboot_fd.emplace" in source:
        raise ValueError("P54_ALREADY_PATCHED")
    return source.replace(INCLUDE, INCLUDE_NEW, 1).replace(ANCHOR, NEW, 1)

def apply(source_root: Path, header: Path) -> None:
    src = source_root.resolve()
    if not (src / ".git").is_dir():
        raise ValueError("UPSTREAM_GIT_CHECKOUT_REQUIRED")
    revision = subprocess.check_output(
        ["git", "-C", str(src), "rev-parse", "HEAD"], text=True).strip()
    if revision != PIN:
        raise ValueError("UNEXPECTED_UPSTREAM_COMMIT")
    main = src / "src/main.cpp"
    target = src / "src/platform/bachata/p54_bsf1_eboot.h"
    if target.exists() or not header.is_file():
        raise ValueError("P54_FILE_PRECONDITION_FAILED")
    change = patched(main.read_text(encoding="utf-8"))
    if "BachataP44::Resolve(p45_request)" not in (
            src / "src/video_core/texture_cache/image_view.cpp").read_text(encoding="utf-8"):
        raise ValueError("P45_RENDERER_PREREQUISITE_MISSING")
    # All source checks passed before first write.
    main.write_text(change, encoding="utf-8", newline="")
    target.write_bytes(header.read_bytes())
    subprocess.run(["git", "-C", str(src), "diff", "--check"], check=True)
    print("P54_AUTHENTICATED_EBOOT_DESCRIPTOR_PATH_STAGED")
    print("P54_FULL_GUEST_APP0_VFS=NOT_YET_ENABLED")
    print("P54_REAL_ANDROID_BROKER_SESSION=NOT_TESTED")
    print("P54_OUTLAST_GAMEPLAY=NOT_TESTED")

if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--source-root", required=True, type=Path)
    cli.add_argument("--header", required=True, type=Path)
    args = cli.parse_args()
    apply(args.source_root, args.header)
