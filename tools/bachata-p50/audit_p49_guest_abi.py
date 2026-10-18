#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P50: read-only ABI and identity-gap audit of the ACTUAL P49 AArch64 GLIBC ELF.

This is a compatibility inventory, not a replacement P42 identity/signature.
Never outputs ephemeral contract/token values, uploads APKs, or modifies binaries.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
from pathlib import Path

P49_SHA256 = "272024fe15b7785be819f7fe3eb403c0543b070da2a6525d10580e24876dadaa"
P42_SHA256 = "5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002"
INTERP = "/lib/ld-linux-aarch64.so.1"
PACKAGE = "com.bachatas4.android.f43dev"
NEEDED = frozenset((
    "libuuid.so.1", "libm.so.6", "libudev.so.1", "libstdc++.so.6",
    "libgcc_s.so.1", "libc.so.6", "ld-linux-aarch64.so.1",
))
MARKERS = (b"BACHATA/1 HELLO version=2 contract=",
           b"BACHATA_F43DEV_R2A2_HOST_GATE_OK",
           b"F43DEV host V2 contract syntax rejected",
           b"P25 decoded BCn sampled view blocked")

def sha256_file(path: Path) -> str:
    hash_obj = hashlib.sha256()
    with path.open("rb") as reader:
        for chunk in iter(lambda: reader.read(1024 * 1024), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def read_elf_output(path: Path, option: str) -> str:
    result = subprocess.run(
        ["readelf", "-W", option, str(path)], capture_output=True, text=True,
        env={**os.environ, "LC_ALL": "C"}, check=True, timeout=25,
    )
    return result.stdout

def symbols(section: str, family: str) -> list[str]:
    escaped = re.escape(family)
    found = set(re.findall(r"\bName: (" + escaped + r"_[0-9]+(?:\.[0-9]+)+)\b", section))
    return sorted(found, key=lambda x: tuple(int(v) for v in x.split("_", 1)[1].split(".")))

def needed_libraries(dynamic: str) -> list[str]:
    return sorted(set(re.findall(r"\(NEEDED\)\s+Shared library: \[([^\]]+)\]", dynamic)))

def attest(elf: Path, gate: Path, p42: Path | None = None) -> dict:
    if not elf.is_file() or elf.is_symlink():
        raise ValueError("MISSING_OR_SYMLINKED_P49_ELF")
    if elf.stat().st_size > 200_000_000:
        raise ValueError("P49_ELF_SIZE_EXCEEDS_LIMIT")
    actual = sha256_file(elf)
    if actual != P49_SHA256:
        raise ValueError("P49_ELF_SHA256_MISMATCH")
    with elf.open("rb") as f:
        header = f.read(64)
    if header[0:5] != b"\x7fELF\x02" or header[5] != 1 or header[18:20] != b"\xb7\x00":
        raise ValueError("NOT_LITTLE_ENDIAN_ELF64_AARCH64")
    if not gate.is_file() or gate.is_symlink():
        raise ValueError("MISSING_PRIVATE_ROOT_SOURCE_GATE")
    source = gate.read_text(encoding="utf-8")
    if source.count('constexpr std::string_view Package = "' + PACKAGE + '";') != 1:
        raise ValueError("PRIVATE_PACKAGE_ROOT_GATE_DRIFT")
    for clause in ("VerifyManagedSocket(", "SO_PEERCRED", "S_ISSOCK", "geteuid()",
                   "std::filesystem::canonical", "AppPrivatePath("):
        if clause not in source:
            raise ValueError("PRIVATE_GATE_CLAUSE_ABSENT")
    head = read_elf_output(elf, "-h")
    ph = read_elf_output(elf, "-l")
    dynamic = read_elf_output(elf, "-d")
    ver = read_elf_output(elf, "--version-info")
    if not re.search(r"Machine:\s+AArch64", head) or not re.search(r"Class:\s+ELF64", head):
        raise ValueError("READ_ELF_TARGET_MISMATCH")
    if INTERP not in ph:
        raise ValueError("GLIBC_AARCH64_LOADER_MISSING")
    libs = needed_libraries(dynamic)
    if set(libs) != NEEDED:
        raise ValueError("P49_DEPENDENCY_SET_DRIFT")
    glibc = symbols(ver, "GLIBC")
    glibcxx = symbols(ver, "GLIBCXX")
    if not glibc or glibc[-1] != "GLIBC_2.38":
        raise ValueError("P49_GLIBC_SYMBOL_BASELINE_DRIFT")
    if not glibcxx or glibcxx[-1] != "GLIBCXX_3.4.32":
        raise ValueError("P49_LIBSTDCXX_SYMBOL_BASELINE_DRIFT")
    # Reading binary strings is NOT evidence the corresponding runtime control
    # path runs. Real-device authenticated host evidence remains mandatory.
    data = elf.read_bytes()
    present = {m.decode(): m in data for m in MARKERS}
    if not all(present.values()):
        raise ValueError("P49_RUNTIME_ERROR_MARKER_MISSING")
    reference = "NOT_ACCESSIBLE"
    if p42 is not None:
        if not p42.is_file() or p42.is_symlink():
            raise ValueError("INVALID_P42_REFERENCE")
        if sha256_file(p42) != P42_SHA256:
            raise ValueError("P42_REFERENCE_SHA256_MISMATCH")
        reference = "EXPECTED_P42_ELF_HASH_VERIFIED_ONLY"
    return {
        "schema": "P50_P49_PUBLIC_ELF_ABI_V1",
        "p49_actual_sha256": actual,
        "p49_size_bytes": elf.stat().st_size,
        "p49_abi": "AArch64 ELF64 Linux GLIBC",
        "loader": INTERP,
        "needed": libs,
        "max_glibc_symbol": glibc[-1],
        "max_glibcxx_symbol": glibcxx[-1],
        "p49_markers_present_not_runtime_proof": present,
        "public_candidate_app_private_gate_package": PACKAGE,
        "private_reference_status": reference,
        "private_p42_apk_signer_verified": False,
        "private_host_accepts_candidate": False,
        "bionic_and_11_glibc_signer_identity_verified": False,
        "p42_397_entry_runtime_manifest_verified": False,
        "real_android_broker_authenticated": False,
        "outlast_bc3_srgb_11_mips_runtime_verified": False,
        "apk_created": False,
        "status": "PUBLIC_ELF_ABI_VERIFIED_PRIVATE_HOST_COMPATIBILITY_BLOCKED",
    }

def main() -> int:
    cli = argparse.ArgumentParser()
    cli.add_argument("--elf", type=Path, required=True)
    cli.add_argument("--gate", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--p42-reference", type=Path)
    args = cli.parse_args()
    try:
        report = attest(args.elf, args.gate, args.p42_reference)
        code = 0
    except (ValueError, OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
        # Never include user-provided paths, file contents, or command stderr.
        report = {"schema": "P50_P49_PUBLIC_ELF_ABI_V1",
                  "status": "ELF_ABI_VERIFICATION_FAILED",
                  "reason": type(exc).__name__ if not isinstance(exc, ValueError) else str(exc),
                  "apk_created": False, "outlast_fixed": False}
        code = 2
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print("P50_STATUS=" + report["status"])
    return code

if __name__ == "__main__":
    raise SystemExit(main())
