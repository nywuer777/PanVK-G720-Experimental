#!/usr/bin/env python3
"""P47: fail-closed inventory gate for a recovered F43DEV private GLIBC source.

A successful inventory is NOT binary equivalence, a rebuilt ELF, or an Outlast fix.
No APKs, keys, private binaries or game assets are published by this tool.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
from pathlib import Path

P42_ELF_SHA256 = "5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002"
P42_TEXT_SHA256 = "f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157"
REFERENCE_PRIVATE_COMMIT = "433c7f30a66c205dff5c3261431e550957f5d447"
KNOWN_PUBLIC_SOURCE_COMMIT = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
REQUIRED_ROLES = frozenset({"private_host_identity", "bcn_graphics", "runtime_protocol", "build_recipe"})
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
SCHEMA = "bachata-f43dev-p47-source-v1"

class GateError(ValueError):
    pass

def require(cond: bool, problem: str) -> None:
    if not cond:
        raise GateError(problem)

def _safe_file(root: Path, rel: str) -> Path:
    require(isinstance(rel, str) and len(rel) > 0, "INVALID_SOURCE_PATH")
    p = Path(rel)
    require(not p.is_absolute() and ".." not in p.parts and "." not in p.parts, "SOURCE_PATH_ESCAPE")
    require(p.parts[0] not in ("", "~"), "SOURCE_PATH_ESCAPE")
    dest = root
    for segment in p.parts:
        dest = dest / segment
        require(not dest.is_symlink(), "SYMLINK_SOURCE_REJECTED")
    require(dest.is_file(), "SOURCE_FILE_MISSING")
    require(dest.resolve().is_relative_to(root.resolve()), "SOURCE_PATH_ESCAPE")
    return dest

def inspect_source(source_root: Path, manifest_file: Path) -> dict:
    require(source_root.exists() and source_root.is_dir() and not source_root.is_symlink(),
            "PRIVATE_SOURCE_ROOT_MISSING")
    require(manifest_file.is_file() and not manifest_file.is_symlink(), "ATTESTATION_MISSING")
    require(manifest_file.stat().st_size <= 1048576, "ATTESTATION_TOO_LARGE")
    try:
        att = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise GateError("ATTESTATION_INVALID_JSON") from exc
    require(isinstance(att, dict), "ATTESTATION_INVALID_SCHEMA")
    require(att.get("schema") == SCHEMA, "ATTESTATION_INVALID_SCHEMA")
    require(att.get("p42_private_elf_sha256") == P42_ELF_SHA256, "P42_ELF_IDENTITY_MISMATCH")
    require(att.get("p42_private_text_sha256") == P42_TEXT_SHA256, "P42_TEXT_IDENTITY_MISMATCH")
    require(att.get("reference_private_commit") == REFERENCE_PRIVATE_COMMIT, "PRIVATE_LINEAGE_UNVERIFIED")
    require(att.get("lineage") in ("recovered-original-private", "reconstructed-private"),
            "PRIVATE_LINEAGE_UNVERIFIED")
    commit = att.get("source_revision")
    require(isinstance(commit, str) and HEX40.fullmatch(commit) is not None,
            "SOURCE_REVISION_MISSING")
    require(commit != KNOWN_PUBLIC_SOURCE_COMMIT, "KNOWN_PUBLIC_P31_SUBSTITUTION")
    files = att.get("files")
    require(isinstance(files, list) and len(files) >= len(REQUIRED_ROLES), "SOURCE_INVENTORY_INCOMPLETE")
    roles, paths = set(), set()
    checked = []
    for entry in files:
        require(isinstance(entry, dict), "SOURCE_ENTRY_INVALID")
        path, role, expected = entry.get("path"), entry.get("role"), entry.get("sha256")
        require(isinstance(role, str) and role in REQUIRED_ROLES, "SOURCE_ROLE_INVALID")
        require(isinstance(expected, str) and HEX64.fullmatch(expected) is not None,
                "SOURCE_FILE_HASH_MISSING")
        require(isinstance(path, str) and path not in paths, "SOURCE_DUPLICATE_PATH")
        require(role not in roles, "SOURCE_DUPLICATE_ROLE")
        file = _safe_file(source_root, path)
        blob = file.read_bytes()
        require(len(blob) > 0, "EMPTY_SOURCE_FILE")
        actual = hashlib.sha256(blob).hexdigest()
        require(actual == expected, "SOURCE_FILE_HASH_MISMATCH")
        checked.append({"role": role, "path": path, "sha256": actual, "size": len(blob)})
        roles.add(role)
        paths.add(path)
    require(roles == REQUIRED_ROLES, "SOURCE_ROLES_INCOMPLETE")
    return {
        "status": "SOURCE_INVENTORY_CONFIRMED_EQUIVALENCE_PENDING",
        "source_revision": commit,
        "source_files_checked": checked,
        "p42_private_elf_sha256": P42_ELF_SHA256,
        "private_elf_rebuilt": False,
        "host_identity_binary_equivalence": False,
        "p45_private_bcn_integration_proven": False,
        "outlast_fixed": False,
        "apk_built": False
    }

def gate(source_root: Path | None, manifest: Path | None) -> tuple[int, dict]:
    if source_root is None or manifest is None:
        return 2, {"status": "BLOCKED_PRIVATE_SOURCE_UNAVAILABLE",
                   "private_elf_rebuilt": False, "outlast_fixed": False, "apk_built": False}
    try:
        return 0, inspect_source(source_root, manifest)
    except (GateError, OSError) as exc:
        problem = str(exc) if isinstance(exc, GateError) else "SOURCE_READ_ERROR"
        return 2, {"status": "BLOCKED_SOURCE_ATTESTATION_FAILED", "reason": problem,
                   "private_elf_rebuilt": False, "outlast_fixed": False, "apk_built": False}

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    code, result = gate(args.source_root, args.manifest)
    data = json.dumps(result, indent=2, sort_keys=True) + "\n"
    print(data, end="")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(data, encoding="utf-8")
    return code

if __name__ == "__main__":
    raise SystemExit(main())
