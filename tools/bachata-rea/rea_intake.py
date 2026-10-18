#!/usr/bin/env python3
"""Read-only intake of the user-supplied REA 6.6.0 GitHub source ZIP.

Not an installer, not a reverse-engineering provider, and not an Android APK
component. Does not extract or execute source code. No device or network access.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
import subprocess
import zipfile
from pathlib import Path, PurePosixPath

ARCHIVE_SHA256 = "17ee3de75a1ab7963ac5948495324cb4b10ad7fca7c15b859b9d5d5ab597e77d"
PREFIX = "rea-rea-agents-6.6.0/"
MAX_ENTRIES = 6000
MAX_UNCOMPRESSED = 90_000_000
MAX_MEMBER = 5_000_000
EXPECTED_NAME = "rea-agents"
EXPECTED_VERSION = "6.6.0"
EXPECTED_LICENSE = "MIT"


class IntakeFailure(ValueError):
    pass


def safe_member(name: str) -> bool:
    if not name.startswith(PREFIX) or "\x00" in name or "\\" in name:
        return False
    # PurePosixPath normalizes repeated separators and /./, so also inspect
    # the original path components before trusting its canonicalized view.
    raw_parts = name.split("/")
    if any(p in ("..", ".") for p in raw_parts):
        return False
    if any(p == "" for p in raw_parts[:-1]):
        return False
    path = PurePosixPath(name)
    if path.is_absolute():
        return False
    return len(path.parts) >= 1


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1_048_576), b""):
            h.update(chunk)
    return h.hexdigest()


def audit_zip(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        raise IntakeFailure("ARCHIVE_NOT_LOCAL_REGULAR_FILE")
    if path.stat().st_size > 30_000_000:
        raise IntakeFailure("ARCHIVE_COMPRESSED_SIZE_EXCEEDED")
    if digest(path) != ARCHIVE_SHA256:
        raise IntakeFailure("ARCHIVE_SHA256_MISMATCH")
    with zipfile.ZipFile(path) as z:
        entries = z.infolist()
        if not entries or len(entries) > MAX_ENTRIES:
            raise IntakeFailure("UNEXPECTED_ENTRY_COUNT")
        total = 0
        seen = set()
        for item in entries:
            if not safe_member(item.filename):
                raise IntakeFailure("UNSAFE_ZIP_ENTRY")
            if item.filename in seen:
                raise IntakeFailure("DUPLICATE_ZIP_ENTRY")
            seen.add(item.filename)
            if item.flag_bits & 1:
                raise IntakeFailure("ENCRYPTED_ZIP_ENTRY")
            mode = (item.external_attr >> 16) & 0o170000
            if mode == stat.S_IFLNK:
                raise IntakeFailure("SYMLINK_ZIP_ENTRY")
            if mode not in (0, stat.S_IFDIR, stat.S_IFREG):
                raise IntakeFailure("UNEXPECTED_ZIP_MODE")
            if item.file_size > MAX_MEMBER:
                raise IntakeFailure("UNEXPECTED_ENTRY_SIZE")
            total += item.file_size
            if total > MAX_UNCOMPRESSED:
                raise IntakeFailure("UNEXPECTED_TOTAL_SIZE")
        required = {PREFIX + s for s in ("LICENSE", "package.json", "README.md",
                   ".agents/skills/reverse-engineer-anything/SKILL.md",
                   ".agents/skills/reverse-engineer-anything/references/android-applications.md")}
        if not required.issubset(seen):
            raise IntakeFailure("REQUIRED_SOURCE_FILES_ABSENT")
        if z.testzip() is not None:
            raise IntakeFailure("ZIP_CRC_FAILURE")
        package = json.loads(z.read(PREFIX + "package.json"))
        license_text = z.read(PREFIX + "LICENSE").decode("utf-8")
        if (package.get("name") != EXPECTED_NAME
                or package.get("version") != EXPECTED_VERSION
                or package.get("license") != EXPECTED_LICENSE
                or not license_text.startswith("MIT License\n")):
            raise IntakeFailure("SOURCE_IDENTITY_OR_LICENSE_MISMATCH")
        return {
            "schema": "BACHATA_MALI_REA_660_INTAKE_V1",
            "archive_sha256": ARCHIVE_SHA256,
            "version": EXPECTED_VERSION,
            "license": EXPECTED_LICENSE,
            "entry_count": len(entries),
            "uncompressed_bytes": total,
            "source_integrity": "PASS_LOCAL_READONLY",
            "native_reverse_engineering_performed": False,
            "android_apk_modified": False,
            "private_artifacts_uploaded": False,
            "next_step": "INSTALL_REA_LOCALLY_WITH_NODE_22_19_OR_NEWER_AND_AUTHORIZED_PROVIDER",
        }


def node_ready(version: str) -> bool:
    match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", version.strip())
    if not match:
        return False
    major, minor, patch = map(int, match.groups())
    return (
        (major == 22 and (minor, patch) >= (19, 0))
        or (major == 24 and (minor, patch) >= (11, 0))
        or major >= 26
    )


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("zip", type=Path, help="Local user-supplied REA 6.6.0 source ZIP")
    p.add_argument("--check-node", action="store_true",
                   help="Read current local Node version; does not install anything")
    p.add_argument("--report", type=Path, help="Write sanitized local JSON")
    a = p.parse_args()
    try:
        result = audit_zip(a.zip)
        code = 0
        if a.check_node:
            try:
                node = subprocess.run(["node", "--version"], capture_output=True,
                                      text=True, check=True, timeout=5)
                ok = node_ready(node.stdout)
            except (OSError, subprocess.TimeoutExpired, subprocess.CalledProcessError):
                ok = False
            result["node_requirement_satisfied"] = ok
            if not ok:
                result["next_step"] = "UPGRADE_NODE_BEFORE_EXECUTING_REA_6_6_0"
                code = 3
    except (OSError, ValueError, zipfile.BadZipFile, json.JSONDecodeError) as exc:
        result = {
            "schema": "BACHATA_MALI_REA_660_INTAKE_V1",
            "source_integrity": "REJECT_FAIL_CLOSED",
            "reason": str(exc) if isinstance(exc, IntakeFailure) else type(exc).__name__,
            "native_reverse_engineering_performed": False,
            "android_apk_modified": False,
            "private_artifacts_uploaded": False,
        }
        code = 2
    output = json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if a.report:
        a.report.parent.mkdir(parents=True, exist_ok=True)
        a.report.write_text(output, encoding="utf-8")
    print(output, end="")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
