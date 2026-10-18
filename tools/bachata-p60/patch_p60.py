#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P60 exact-stage integration after pinned Host V2 + BCn + P53..P59.

Only the authorized sce_module/libc.prx is probed. No broad /app0 mount or
game-data disclosure. Stage lifetime spans Emulator::Run.
"""
import argparse
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
def one(source, before, after, label):
    n = source.count(before)
    if n != 1:
        raise ValueError(f"P60_{label}_EXPECTED_1_ANCHOR_GOT_{n}")
    return source.replace(before, after, 1)

def patched_main(main: str) -> str:
    for gate in (
        "BACHATA_F43DEV_R2A2_HOST_GATE_OK",
        "BACHATA_P53_EBOOT_ROOT_UNAVAILABLE",
        "P59::StageAuthenticatedFd(",
        "p59_eboot_stage.emplace(std::move(staged));",
    ):
        if gate not in main:
            raise ValueError(f"P60_MISSING_{gate}")
    main = one(
        main,
        '#include "platform/bachata/p59_private_stage.h"',
        '#include "platform/bachata/p59_private_stage.h"\n'
        '#include "platform/bachata/p60_saf_libc_stage.h"',
        "HEADER",
    )
    main = one(
        main,
        '    std::optional<Bachata::Saf::P59::PrivateStage> p59_eboot_stage;',
        '''    std::optional<Bachata::Saf::P59::PrivateStage> p59_eboot_stage;
    // Keep the borrowed SAF module private stage alive until Run returns.
    // It may be removed on orderly process exit; no /app0-wide disclosure.
    std::optional<Bachata::Saf::P60::Stage> p60_libc_stage;''',
        "PERSISTENT_MODULE_STATE",
    )
    main = one(
        main,
        '''            if (staged) {
                p59_eboot_stage.emplace(std::move(staged));
                ebootPath = p59_eboot_stage->path;
            }''',
        '''            if (staged) {
                p59_eboot_stage.emplace(std::move(staged));
                ebootPath = p59_eboot_stage->path;
                // The emulator will mount ebootPath.parent_path() as /app0.
                // Stage only this missing module; a broker rejection is not
                // evidence of a missing file and MUST NOT be bypassed.
                auto libc = Bachata::Saf::P60::ProbeAndStageLibc(
                    saf_broker, *overrideRoot);
                std::cerr << Bachata::Saf::P60::Marker(libc.status) << '\\n';
                if (libc) p60_libc_stage.emplace(std::move(libc));
            }''',
        "MODULE_STAGE_HOOK",
    )
    if "std::move(p54_probe.proc_fd_path)" in main:
        raise ValueError("P60_P59_PROCFS_REOPEN_REGRESSION")
    return main

def apply(root: Path, header: Path) -> None:
    root = root.resolve()
    if not (root / ".git").is_dir():
        raise ValueError("P60_PINNED_GIT_CHECKOUT_REQUIRED")
    rev = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if rev != PIN:
        raise ValueError("P60_SOURCE_PIN_CHANGED")
    main = root / "src/main.cpp"
    target = root / "src/platform/bachata/p60_saf_libc_stage.h"
    current = root / "src/platform/bachata/p59_private_stage.h"
    broker = root / "src/platform/bachata/saf_bsf1_client.cpp"
    if target.exists() or not header.is_file() or not current.is_file() or not broker.is_file():
        raise ValueError("P60_PREREQUISITES_MISSING")
    if "BACHATA_P59_EBOOT_PRIVATE_STAGE_READY" not in current.read_text():
        raise ValueError("P60_P59_STAGING_NOT_VERIFIED")
    if "AppendBe16(packet, static_cast<uint16_t>(config_.token.size()))" not in broker.read_text():
        raise ValueError("P60_P58_ANDROID_BSF1_WIRE_NOT_VERIFIED")
    updated = patched_main(main.read_text())
    main.write_text(updated, encoding="utf-8", newline="")
    target.write_bytes(header.read_bytes())
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("P60_EXACT_LIBC_SAF_PREFLIGHT_AND_STAGE=APPLIED")
    print("P60_APP0_FULL_VFS=NOT_IMPLEMENTED")
    print("P60_DID_NOT_SYNTHESIZE_MISSING_PRX=YES")
    print("P60_PRIVATE_P42_OR_PANVK=UNMODIFIED")
    print("P60_ANDROID_DEVICE=NOT_TESTED")

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--header", type=Path, required=True)
    a=p.parse_args()
    apply(a.source_root, a.header)
