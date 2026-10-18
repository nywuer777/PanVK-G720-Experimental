#!/usr/bin/env python3
"""P48: read-only provenance inspection of a LOCAL ELF64/AArch64 GLIBC runtime.

Does not recover source, patch code, assert game compatibility, or create an APK.
The functional P42 reference is accepted only by its exact SHA-256 and .text SHA-256.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import struct

P42_ELF = "5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002"
P42_TEXT = "f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157"
ELF_HEADER = struct.Struct("<16sHHIQQQIHHHHHH")
PROGRAM_HEADER = struct.Struct("<IIQQQQQQ")
SECTION_HEADER = struct.Struct("<IIQQQQIIQQ")
DYNAMIC = struct.Struct("<qQ")

class ProbeError(ValueError):
    pass

def require(test: bool, message: str) -> None:
    if not test:
        raise ProbeError(message)

def region(blob: bytes, offset: int, size: int) -> bytes:
    require(0 <= offset <= len(blob) and 0 <= size <= len(blob) - offset,
            "ELF_REGION_OUT_OF_BOUNDS")
    return blob[offset:offset + size]

def cstring(blob: bytes, start: int) -> str:
    require(0 <= start < len(blob), "INVALID_STRING_OFFSET")
    end = blob.find(b"\x00", start)
    require(end >= start and end - start <= 4096, "UNTERMINATED_STRING")
    try:
        return blob[start:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ProbeError("INVALID_STRING_ENCODING") from exc

def fingerprint(elf: bytes) -> dict:
    require(len(elf) >= ELF_HEADER.size, "ELF_TOO_SHORT")
    ident, kind, machine, version, entry, phoff, shoff, flags, hsize, phentsize, phnum, shentsize, shnum, stridx = ELF_HEADER.unpack_from(elf)
    require(ident[:4] == b"\x7fELF" and ident[4] == 2 and ident[5] == 1 and ident[6] == 1,
            "NOT_ELF64_LITTLE_ENDIAN")
    require(hsize == ELF_HEADER.size and version == 1 and kind in (2, 3), "ELF_HEADER_INVALID")
    require(machine == 183, "ELF_NOT_AARCH64")
    require(phentsize == PROGRAM_HEADER.size and 1 <= phnum <= 512, "ELF_PROGRAM_TABLE_INVALID")
    require(shentsize == SECTION_HEADER.size and 1 <= shnum <= 8192 and 0 < stridx < shnum,
            "ELF_SECTION_TABLE_INVALID")
    region(elf, phoff, phnum * phentsize)
    region(elf, shoff, shnum * shentsize)

    interp = None
    for i in range(phnum):
        typ, pflags, off, vaddr, paddr, size, memsz, align = PROGRAM_HEADER.unpack_from(elf, phoff + i * phentsize)
        if typ == 3:
            require(interp is None, "DUPLICATE_PT_INTERP")
            raw = region(elf, off, size)
            require(bool(raw) and raw.endswith(b"\x00"), "INVALID_PT_INTERP")
            interp = cstring(raw, 0)
    require(interp == "/lib/ld-linux-aarch64.so.1", "GLIBC_INTERPRETER_NOT_PROVEN")

    sh = [SECTION_HEADER.unpack_from(elf, shoff + i * shentsize) for i in range(shnum)]
    names_blob = region(elf, sh[stridx][4], sh[stridx][5])
    sections = {}
    for row in sh[1:]:
        name = cstring(names_blob, row[0])
        if name:
            require(name not in sections, "DUPLICATE_SECTION_NAME")
            sections[name] = row
    require(".text" in sections and ".dynamic" in sections and ".dynstr" in sections,
            "ESSENTIAL_ELF_SECTIONS_MISSING")
    text = region(elf, sections[".text"][4], sections[".text"][5])
    require(len(text) >= 16, "EMPTY_TEXT_SECTION")
    dynstr = region(elf, sections[".dynstr"][4], sections[".dynstr"][5])
    dynamic = region(elf, sections[".dynamic"][4], sections[".dynamic"][5])
    require(len(dynamic) % DYNAMIC.size == 0, "INVALID_DYNAMIC_TABLE")
    require(len(dynamic) <= 1024 * 1024, "DYNAMIC_TABLE_TOO_LARGE")

    needed = []
    ended = False
    for j in range(0, len(dynamic), DYNAMIC.size):
        tag, offset = DYNAMIC.unpack_from(dynamic, j)
        if tag == 0:
            ended = True
            break
        if tag == 1:
            needed.append(cstring(dynstr, offset))
    require(ended, "DYNAMIC_TABLE_UNTERMINATED")
    require("libc.so.6" in needed, "GLIBC_LIBC_NOT_FOUND")
    require("libc.so" not in needed and "liblog.so" not in needed,
            "ANDROID_BIONIC_DEPENDENCY_FOUND")
    sha = hashlib.sha256(elf).hexdigest()
    text_sha = hashlib.sha256(text).hexdigest()
    is_p42 = sha == P42_ELF and text_sha == P42_TEXT
    require(not (sha == P42_ELF and text_sha != P42_TEXT), "P42_TEXT_PROVENANCE_CONTRADICTION")
    return {
        "elf_sha256": sha,
        "text_sha256": text_sha,
        "elf_bytes": len(elf),
        "machine": "AArch64",
        "abi": "Linux ARM64 GLIBC",
        "interpreter": interp,
        "needed": needed,
        "protocol_string_present": b"BACHATA/1 HELLO version=" in elf,
        "private_host_guard_string_present": b"host identity check failed" in elf,
        "matches_exact_p42_elf_and_text": is_p42,
        "source_reconstructed": False,
        "p45_private_integration_proven": False,
        "apk_built": False,
        "outlast_fixed": False,
    }

def audit(path: Path | None, mode: str) -> tuple[int, dict]:
    if path is None:
        return 2, {"status": "BLOCKED_P42_PRIVATE_ELF_NOT_AVAILABLE",
                   "outlast_fixed": False, "apk_built": False}
    try:
        require(path.is_file() and not path.is_symlink(), "INVALID_ELF_PATH")
        require(path.stat().st_size <= 250 * 1024 * 1024, "ELF_TOO_LARGE")
        result = fingerprint(path.read_bytes())
        if mode == "baseline":
            require(result["matches_exact_p42_elf_and_text"], "REFERENCE_NOT_EXACT_P42")
            result["status"] = "P42_BASELINE_FINGERPRINT_MATCH"
        else:
            result["status"] = "CANDIDATE_ABI_VALID_IDENTITY_AND_GAMEPLAY_UNPROVEN"
        return 0, result
    except (ProbeError, OSError) as exc:
        reason = str(exc) if isinstance(exc, ProbeError) else "ELF_READ_ERROR"
        return 2, {"status": "BLOCKED_ELF_PROVENANCE_FAILURE", "reason": reason,
                   "outlast_fixed": False, "apk_built": False}

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--elf", type=Path)
    ap.add_argument("--mode", choices=("baseline", "candidate"), default="baseline")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args()
    status, result = audit(args.elf, args.mode)
    report = json.dumps(result, sort_keys=True, indent=2) + "\n"
    print(report, end="")
    if args.report is not None:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(report, encoding="utf-8")
    return status

if __name__ == "__main__":
    raise SystemExit(main())
