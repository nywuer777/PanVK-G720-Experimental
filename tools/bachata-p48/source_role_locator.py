#!/usr/bin/env python3
"""P48 read-only source locator for authorized local F43DEV source trees.

This performs an indexed triage of likely host/BCn code locations, NOT provenance,
correctness, build equivalence, or a port. Never outputs source contents.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path

ALLOW_EXTENSIONS = {".cpp", ".c", ".cc", ".cxx", ".h", ".hpp", ".inl", ".sh", ".kt", ".java"}
ALLOW_NAMES = {"CMakeLists.txt"}
SKIP_DIRS = {".git", ".gradle", ".idea", ".venv", "node_modules", "build", "dist", "obj"}
MAX_FILES = 50000
MAX_FILE_BYTES = 2 * 1024 * 1024
SIGNALS = {
    "host_identity": (
        b"host identity check failed", b"libbachata_host_loader.so",
        b"BACHATA_F43DEV_R2A2_HOST_GATE_OK", b"f43dev_identity_gate",
    ),
    "runtime_hello": (
        b"BACHATA/1 HELLO", b"SendHelloV2", b"version=2 contract=",
    ),
    "bcn_image_view": (
        b"P45_BCN_PER_LAYER_VIEW_PROOF", b"P25 decoded BCn sampled view blocked",
        b"VK_FORMAT_BC3", b"bc3", b"BCn",
    ),
    "bcn_upload_fence": (
        b"P45_BCN_LAYER_UPLOAD_COMPLETE", b"p45_completed_bc_uploads",
        b"vkWaitForFences", b"vkQueueSubmit",
    ),
}

def scan(root: Path | None) -> tuple[int, dict]:
    if root is None or not root.is_dir() or root.is_symlink():
        return 2, {"status": "BLOCKED_AUTHORIZED_SOURCE_TREE_UNAVAILABLE",
                   "source_equivalence_proven": False, "apk_built": False}
    findings: list[dict] = []
    checked = 0
    skipped = 0
    for parent, dirs, files in os.walk(root, topdown=True, followlinks=False):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")
                         and not (Path(parent) / d).is_symlink())
        for filename in sorted(files):
            if Path(filename).suffix.lower() not in ALLOW_EXTENSIONS and filename not in ALLOW_NAMES:
                continue
            file = Path(parent) / filename
            if file.is_symlink() or not file.is_file():
                skipped += 1
                continue
            checked += 1
            if checked > MAX_FILES:
                return 2, {"status": "BLOCKED_SOURCE_TREE_TOO_LARGE",
                           "source_equivalence_proven": False, "apk_built": False}
            try:
                if file.stat().st_size > MAX_FILE_BYTES:
                    skipped += 1
                    continue
                raw = file.read_bytes()
            except OSError:
                skipped += 1
                continue
            if b"\x00" in raw:
                skipped += 1
                continue
            hits = {role: [i for i, token in enumerate(tokens) if token in raw]
                    for role, tokens in SIGNALS.items()}
            hits = {role: indices for role, indices in hits.items() if indices}
            if hits:
                findings.append({
                    "relative_path": file.relative_to(root).as_posix(),
                    "sha256": hashlib.sha256(raw).hexdigest(),
                    "signal_ids": {role: indices for role, indices in sorted(hits.items())},
                })
    roles = sorted({role for row in findings for role in row["signal_ids"]})
    if not findings:
        state = "BLOCKED_NO_SOURCE_ROLE_CANDIDATES"
        code = 2
    elif len(roles) == len(SIGNALS):
        state = "SOURCE_ROLE_LOCATIONS_IDENTIFIED_NOT_PROVEN"
        code = 0
    else:
        state = "SOURCE_ROLE_LOCATIONS_PARTIAL_NOT_PROVEN"
        code = 0
    return code, {
        "status": state,
        "files_scanned": checked,
        "files_skipped": skipped,
        "matched_roles": roles,
        "missing_roles": sorted(set(SIGNALS) - set(roles)),
        "candidate_locations": findings,
        "source_equivalence_proven": False,
        "private_glibc_rebuilt": False,
        "p45_private_integration_proven": False,
        "outlast_fixed": False,
        "apk_built": False,
    }

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source-root", type=Path)
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    code, result = scan(args.source_root)
    output = json.dumps(result, sort_keys=True, indent=2) + "\n"
    print(output, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(output, encoding="utf-8")
    return code

if __name__ == "__main__":
    raise SystemExit(main())
