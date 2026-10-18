#!/usr/bin/env python3
"""P61.1 fail-closed Android laboratory package binding.

A public P61 GLIBC core defaults to the trusted f43dev package. The signed
LAB CLONE is com.bachatas4.android.f43lab. This prepares a lab-only core while
preserving all socket/root/peer checks; it does NOT disable any trust gate.
No APK/private signer/game files are used. If the next public ELF changes,
update its expected digest after review rather than silently patching it.
"""
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

PUBLIC_SHA = "80cd281bf314e12b8e0be936bcc62bf1613ceb98fbc24f7881f280819950c234"
PUBLIC_NAME = b"com.bachatas4.android.f43dev"
LAB_NAME = b"com.bachatas4.android.f43lab"
GATE_MARKERS = (
    b"F43DEV host gate: untrusted app-private root or socket",
    b"BACHATA_F43DEV_R2A2_HOST_GATE_OK",
    b"BACHATA_P59_EBOOT_PRIVATE_STAGE_READY",
    b"BACHATA_P60_LIBC_SAF_PRIVATE_STAGE_READY",
    b"BACHATA_P61_PSF_SAF_PRIVATE_STAGE_READY",
)

def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def patched_lab_core(public: bytes, expected_sha: str = PUBLIC_SHA) -> tuple[bytes, list[int]]:
    if sha(public) != expected_sha:
        raise ValueError("PINNED_PUBLIC_P61_ELF_HASH_MISMATCH")
    if not public.startswith(b"\x7fELF") or public[4] != 2 or public[5] != 1 or public[18:20] != b"\xb7\x00":
        raise ValueError("NOT_ELF64_AARCH64")
    if len(PUBLIC_NAME) != len(LAB_NAME):
        raise ValueError("PACKAGE_LENGTH_MISMATCH")
    if public.count(PUBLIC_NAME) != 1 or LAB_NAME in public:
        raise ValueError("PUBLIC_PACKAGE_NOT_UNIQUE_OR_ALREADY_BOUND")
    if any(marker not in public for marker in GATE_MARKERS):
        raise ValueError("TRUST_GUARD_OR_STAGE_MARKER_MISSING")
    start = public.index(PUBLIC_NAME)
    patched = public[:start] + LAB_NAME + public[start + len(PUBLIC_NAME):]
    differences = [i for i in range(start, start + len(PUBLIC_NAME)) if public[i] != patched[i]]
    if differences != list(range(start + len(PUBLIC_NAME) - 3, start + len(PUBLIC_NAME))):
        raise ValueError("UNEXPECTED_PACKAGE_DIFF")
    if patched.count(PUBLIC_NAME) != 0 or patched.count(LAB_NAME) != 1:
        raise ValueError("LAB_PACKAGE_BINDING_INVALID")
    if any(marker not in patched for marker in GATE_MARKERS):
        raise ValueError("TRUST_GUARD_REMOVED")
    assert len(public) == len(patched)
    # Binary is byte-for-byte unchanged outside the explicitly reviewed literal.
    assert public[:start] == patched[:start]
    assert public[start + len(PUBLIC_NAME):] == patched[start + len(PUBLIC_NAME):]
    return patched, differences

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    opts = parser.parse_args()
    if opts.input.resolve() in (opts.output.resolve(), opts.report.resolve()) or opts.output.resolve() == opts.report.resolve():
        raise ValueError("UNSAFE_OUTPUT")
    if opts.output.exists() or opts.report.exists() or not opts.input.is_file():
        raise ValueError("INPUT_MISSING_OR_OUTPUT_ALREADY_EXISTS")
    payload = opts.input.read_bytes()
    new, differences = patched_lab_core(payload)
    opts.output.parent.mkdir(parents=True, exist_ok=True)
    opts.output.write_bytes(new)
    report = {
        "verdict": "LAB_ROOT_GATE_PACKAGE_REBOUND_BYTE_EXACT",
        "input_sha256": sha(payload),
        "output_sha256": sha(new),
        "input_bytes": len(payload),
        "output_bytes": len(new),
        "changed_byte_offsets": differences,
        "public_package": PUBLIC_NAME.decode(),
        "lab_package": LAB_NAME.decode(),
        "root_socket_uid_and_peer_auth": "PRESERVED_NO_GATE_BYPASS",
        "signed_apk": "NOT_CREATED",
        "android_device_test": "NOT_EXECUTED",
    }
    opts.report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    print(report["verdict"])
    print("P61_LAB_CORE_SHA256=" + report["output_sha256"])

if __name__ == "__main__":
    main()
