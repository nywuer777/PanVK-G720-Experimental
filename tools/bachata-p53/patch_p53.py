#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Apply P53 only after exact P49 HostV2+P45 source integration.

The APK P42 is never an input; no fake success if Android SAF data is not
present in the physical override root.
"""
import argparse
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
IMPORT_OLD = '#include "platform/bachata/runtime_client.h"'
IMPORT_NEW = IMPORT_OLD + '\n#include "platform/bachata/relative_eboot.h"'
GAME_OLD = '    std::filesystem::path ebootPath(*gamePath);\n    if (!std::filesystem::exists(ebootPath)) {'
GAME_NEW = r'''    std::filesystem::path ebootPath(*gamePath);
#ifdef ENABLE_BACHATA_RUNTIME
    // The trusted Android host uses -g eboot.bin plus --override-root,
    // usually pointing at its private direct-runtime game directory.
    // Resolve only the exact entry without allowing path traversal/symlinks.
    if (auto p53_eboot = Platform::Bachata::P53::ResolveEboot(*gamePath, overrideRoot)) {
        ebootPath = *p53_eboot;
        std::cerr << "BACHATA_P53_EBOOT_OVERRIDE_ROOT_RESOLVED\n";
    } else if (*gamePath == "eboot.bin" && overrideRoot) {
        // SAF-only content may not have been materialized as a physical file.
        // No untrusted fallback, and never misreport successful content I/O.
        std::cerr << "BACHATA_P53_EBOOT_ROOT_UNAVAILABLE\n";
    }
#endif
    if (!std::filesystem::exists(ebootPath)) {'''

def patched(source: str) -> str:
    for marker in ("BACHATA_F43DEV_R2A2_HOST_GATE_OK",
                   "SendHelloV2",
                   "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED"):
        if marker not in source:
            raise ValueError("P49_HOST_V2_PREREQUISITE_MISSING")
    if source.count(IMPORT_OLD) != 1 or source.count(GAME_OLD) != 1:
        raise ValueError("P49_GAME_ENTRY_PATCH_ANCHOR_MISMATCH")
    if "BACHATA_P53_EBOOT_OVERRIDE_ROOT_RESOLVED" in source:
        raise ValueError("P53_ALREADY_PATCHED")
    return source.replace(IMPORT_OLD, IMPORT_NEW, 1).replace(GAME_OLD, GAME_NEW, 1)

def run(upstream: Path, header: Path) -> None:
    upstream = upstream.resolve()
    if not (upstream / ".git").is_dir():
        raise ValueError("PINNED_SOURCE_REQUIRED")
    if subprocess.check_output(
        ["git", "-C", str(upstream), "rev-parse", "HEAD"], text=True
    ).strip() != PIN:
        raise ValueError("PINNED_SOURCE_REVISION_CHANGED")
    main = upstream / "src/main.cpp"
    target = upstream / "src/platform/bachata/relative_eboot.h"
    if target.exists() or not header.is_file():
        raise ValueError("SOURCE_PATCH_PRECONDITION_FAILED")
    text = main.read_text()
    new = patched(text)
    if not all(x in (upstream / "src/video_core/texture_cache/image_view.cpp").read_text() for x in
               ("BachataP44::Resolve(p45_request)", "P45_BCN_PER_LAYER_VIEW_PROOF")):
        raise ValueError("P49_BCN_VIEW_PREREQUISITE_MISSING")
    main.write_text(new, encoding="utf8", newline="")
    target.write_bytes(header.read_bytes())
    subprocess.run(["git", "-C", str(upstream), "diff", "--check"], check=True)
    print("P53_EBOOT_RELATIVE_ROOT_SOURCE_APPLIED; SAF_NOT_PROVEN; OUTLAST_NOT_PROVEN")

if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-root", required=True, type=Path)
    p.add_argument("--header", required=True, type=Path)
    a=p.parse_args()
    run(a.source_root,a.header)
