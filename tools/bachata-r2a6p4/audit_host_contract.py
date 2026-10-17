#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only APK/Dex + nested GLIBC runtime static protocol comparison.

No APK modification, signing, extraction into app storage, runtime execution,
device contact, output of paths/tokens/nonce, or claims of real interoperability.
Use an authorized copy of the *already installed* F43DEV APK.
"""
import argparse
import hashlib
import json
import re
import struct
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

EXPECTED_APK_SHA = "e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded"
ORIGINAL_CORE_SHA = "b1cd025306b1dbd7b07d3bc228a0f18392d4f32fdeb934c9676e75ed0090abb4"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def extract_dex_strings(data):
    if len(data) < 112 or not data.startswith(b"dex\n"):
        raise ValueError("invalid_dex_header")
    size = struct.unpack_from("<I", data, 32)[0]
    if size != len(data):
        raise ValueError("invalid_dex_size")
    count, offset = struct.unpack_from("<II", data, 0x38)
    if count > 1_000_000 or offset + 4 * count > len(data):
        raise ValueError("invalid_dex_string_index")
    results = set()
    for i in range(count):
        address = struct.unpack_from("<I", data, offset + 4 * i)[0]
        if address >= len(data):
            raise ValueError("invalid_dex_string_offset")
        cursor = address
        for _ in range(5):
            if cursor >= len(data):
                raise ValueError("invalid_dex_uleb")
            code = data[cursor]
            cursor += 1
            if not code & 0x80:
                break
        else:
            raise ValueError("invalid_dex_uleb")
        zero = data.find(b"\0", cursor)
        if zero < 0:
            raise ValueError("invalid_dex_termination")
        # UTF-8 failures are not surfaced in evidence output.
        results.add(data[cursor:zero].decode("utf-8", errors="replace"))
    return results

def audit(apk_path, candidate_path=None, public_protocol_header=None):
    apk_bytes = Path(apk_path).read_bytes()
    report = {
        "schema": "f43dev-host-protocol-readonly-v1",
        "analysis_type": "STATIC_ONLY_NO_DEVICE_ACCESS",
        "apk_sha256": sha(apk_bytes),
        "trusted_apk_baseline_match": sha(apk_bytes) == EXPECTED_APK_SHA,
        "host_dex_explicit_hello_v2_contract": False,
        "host_dex_requires_protocol2": False,
        "host_dex_has_saf_args": False,
        "original_glibc_core_sha256": None,
        "original_glibc_core_baseline_match": False,
        "original_glibc_has_dynamic_version_and_contract": False,
        "bionic_native_runtime_sha256": None,
        "public_runtime_version": None,
        "candidate_elf_sha256": None,
        "candidate_sha_manifest_match": None,
        "candidate_contains_probe": None,
        "handshake_compatible": "UNVERIFIED",
        "original_android_host_source_available": False,
        "real_android_broker_verified": False,
        "apk_signature_verified_cryptographically": False,
        "test_executed_on_device": False,
    }
    if not report["trusted_apk_baseline_match"]:
        raise ValueError("Unexpected APK hash: this is not the pinned known-good F43DEV V2")
    with ZipFile(BytesIO(apk_bytes)) as outer:
        dex = extract_dex_strings(outer.read("classes.dex"))
        report["host_dex_explicit_hello_v2_contract"] = (
            "BACHATA/1 HELLO version=2 contract=" in dex
        )
        report["host_dex_requires_protocol2"] = (
            "Runtime contract mismatch (app requires protocol 2)" in dex
        )
        report["host_dex_has_saf_args"] = all(
            x in dex for x in ("--bachata-saf-socket", "--bachata-saf-token")
        )
        native = outer.read("lib/arm64-v8a/libbachata_native_runtime.so")
        report["bionic_native_runtime_sha256"] = sha(native)
        with ZipFile(BytesIO(outer.read("assets/runtime/runtime.zip"))) as archive:
            core = archive.read("host/shadps4-arm64-fex")
            report["original_glibc_core_sha256"] = sha(core)
            report["original_glibc_core_baseline_match"] = sha(core) == ORIGINAL_CORE_SHA
            report["original_glibc_has_dynamic_version_and_contract"] = all(
                x in core for x in (b"BACHATA/1 HELLO version=", b" contract=")
            )

    if public_protocol_header:
        text = Path(public_protocol_header).read_text(encoding="utf-8")
        versions = re.findall(
            r"constexpr\s+unsigned\s+RuntimeProtocolVersion\s*=\s*(\d+)\s*;", text
        )
        if len(versions) != 1:
            raise ValueError("Public header missing unique RuntimeProtocolVersion")
        report["public_runtime_version"] = int(versions[0])
    if candidate_path:
        with ZipFile(candidate_path) as archive:
            binary_names = [x for x in archive.namelist() if x.startswith("shadps4-arm64-glibc-R2A6P2")]
            if len(binary_names) != 1:
                raise ValueError("Candidate CI artifact missing unique core ELF")
            elf = archive.read(binary_names[0])
            report["candidate_elf_sha256"] = sha(elf)
            expected = archive.read("SHA256SUMS.txt").decode("ascii", "replace").split()
            report["candidate_sha_manifest_match"] = len(expected) == 2 and expected[0] == sha(elf)
            report["candidate_contains_probe"] = all(
                tag in elf for tag in (b"BSF1_LAB_PROBE_FILE_OK", b"bachata-saf-probe-only")
            )

    if (report["host_dex_explicit_hello_v2_contract"] and
        report["host_dex_requires_protocol2"] and report["public_runtime_version"] == 1):
        report["handshake_compatible"] = "KNOWN_VERSION_DIVERGENCE_CORE_V1_VS_HOST_V2"
    elif report["public_runtime_version"] is None:
        report["handshake_compatible"] = "NOT_COMPARABLE_PUBLIC_HEADER_MISSING"
    return report

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apk", type=Path, required=True)
    p.add_argument("--candidate-zip", type=Path)
    p.add_argument("--public-protocol-header", type=Path)
    p.add_argument("--output", type=Path)
    args=p.parse_args()
    result=audit(args.apk, args.candidate_zip, args.public_protocol_header)
    text=json.dumps(result,sort_keys=True,indent=2)+"\n"
    if args.output:
        args.output.write_text(text,encoding="utf-8")
    else:
        print(text,end="")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
