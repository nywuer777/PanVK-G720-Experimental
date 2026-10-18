#!/usr/bin/env python3
"""Synthetic ELF fixtures only. No private binaries in GitHub CI."""
import hashlib
import struct
import tempfile
import unittest
from pathlib import Path
from private_elf_probe import (
    ELF_HEADER, PROGRAM_HEADER, SECTION_HEADER, DYNAMIC,
    audit, fingerprint, ProbeError,
)

def build_fixture(machine=183, loader=b"/lib/ld-linux-aarch64.so.1\x00",
                  needed=("libc.so.6",), marker=True) -> bytes:
    blob = bytearray(2048)
    ident = b"\x7fELF" + bytes([2, 1, 1]) + bytes(9)
    ELF_HEADER.pack_into(blob, 0, ident, 3, machine, 1, 0, 64, 1024,
                         0, 64, PROGRAM_HEADER.size, 1, SECTION_HEADER.size, 5, 2)
    PROGRAM_HEADER.pack_into(blob, 64, 3, 4, 0x180, 0, 0, len(loader), len(loader), 1)
    blob[0x180:0x180 + len(loader)] = loader
    payload = b"Q" * 40
    if marker:
        payload += b"BACHATA/1 HELLO version=2 " + b"host identity check failed"
    blob[0x200:0x200 + len(payload)] = payload
    shstr = b"\x00.text\x00.shstrtab\x00.dynstr\x00.dynamic\x00"
    blob[0x300:0x300 + len(shstr)] = shstr
    dynstr = b"\x00" + b"".join(name.encode("ascii") + b"\x00" for name in needed)
    blob[0x340:0x340 + len(dynstr)] = dynstr
    d = b"".join(DYNAMIC.pack(1, dynstr.index(name.encode("ascii")))
                 for name in needed) + DYNAMIC.pack(0, 0)
    blob[0x380:0x380 + len(d)] = d
    def section(i, name, typ, off, size):
        SECTION_HEADER.pack_into(blob, 1024 + SECTION_HEADER.size*i,
                                 shstr.index(name.encode("ascii")), typ, 0, 0,
                                 off, size, 0, 0, 1, 0)
    section(1, ".text", 1, 0x200, len(payload))
    section(2, ".shstrtab", 3, 0x300, len(shstr))
    section(3, ".dynstr", 3, 0x340, len(dynstr))
    section(4, ".dynamic", 6, 0x380, len(d))
    return bytes(blob)

class P48ProbeTest(unittest.TestCase):
    def test_candidate_glibc_is_not_certified_private(self):
        report = fingerprint(build_fixture())
        self.assertEqual(report["machine"], "AArch64")
        self.assertEqual(report["interpreter"], "/lib/ld-linux-aarch64.so.1")
        self.assertEqual(report["needed"], ["libc.so.6"])
        self.assertTrue(report["private_host_guard_string_present"])
        self.assertFalse(report["matches_exact_p42_elf_and_text"])
        self.assertFalse(report["outlast_fixed"])
        self.assertFalse(report["p45_private_integration_proven"])

    def test_reference_must_have_exact_sha(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "core"
            p.write_bytes(build_fixture())
            code, report = audit(p, "baseline")
            self.assertEqual(code, 2)
            self.assertEqual(report["reason"], "REFERENCE_NOT_EXACT_P42")
            self.assertFalse(report["apk_built"])

    def test_candidate_remains_unproven(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "core"
            p.write_bytes(build_fixture())
            code, report = audit(p, "candidate")
            self.assertEqual(code, 0)
            self.assertEqual(report["status"], "CANDIDATE_ABI_VALID_IDENTITY_AND_GAMEPLAY_UNPROVEN")
            self.assertFalse(report["source_reconstructed"])

    def test_no_private_input_blocks(self):
        code, report = audit(None, "baseline")
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "BLOCKED_P42_PRIVATE_ELF_NOT_AVAILABLE")

    def test_x8664_rejected(self):
        with self.assertRaisesRegex(ProbeError, "ELF_NOT_AARCH64"):
            fingerprint(build_fixture(machine=62))

    def test_bionic_interpreter_rejected(self):
        with self.assertRaisesRegex(ProbeError, "GLIBC_INTERPRETER_NOT_PROVEN"):
            fingerprint(build_fixture(loader=b"/system/bin/linker64\x00"))

    def test_android_libc_rejected(self):
        with self.assertRaisesRegex(ProbeError, "GLIBC_LIBC_NOT_FOUND"):
            fingerprint(build_fixture(needed=("libc.so",)))

    def test_mixed_bionic_library_rejected(self):
        with self.assertRaisesRegex(ProbeError, "ANDROID_BIONIC_DEPENDENCY_FOUND"):
            fingerprint(build_fixture(needed=("libc.so.6", "liblog.so")))

    def test_missing_protocol_strings_do_not_change_identity(self):
        report = fingerprint(build_fixture(marker=False))
        self.assertFalse(report["protocol_string_present"])
        self.assertFalse(report["private_host_guard_string_present"])
        self.assertFalse(report["matches_exact_p42_elf_and_text"])

    def test_truncated_file_rejected(self):
        with self.assertRaisesRegex(ProbeError, "ELF_TOO_SHORT"):
            fingerprint(b"\x7fELF")

    def test_wrong_elf_class_rejected(self):
        b = bytearray(build_fixture())
        b[4] = 1
        with self.assertRaisesRegex(ProbeError, "NOT_ELF64_LITTLE_ENDIAN"):
            fingerprint(bytes(b))

    def test_out_of_bounds_section_table_rejected(self):
        b = bytearray(build_fixture())
        struct.pack_into("<Q", b, 40, len(b) + 100)
        with self.assertRaisesRegex(ProbeError, "ELF_REGION_OUT_OF_BOUNDS"):
            fingerprint(bytes(b))

    def test_missing_text_section_rejected(self):
        b = bytearray(build_fixture())
        struct.pack_into("<I", b, 1024 + SECTION_HEADER.size, 0)
        with self.assertRaisesRegex(ProbeError, "ESSENTIAL_ELF_SECTIONS_MISSING"):
            fingerprint(bytes(b))

    def test_wrong_sha_does_not_consume_private_content(self):
        b = build_fixture()
        report = fingerprint(b)
        self.assertEqual(report["elf_sha256"], hashlib.sha256(b).hexdigest())
        self.assertIn("text_sha256", report)
        self.assertNotIn("raw_data", report)

    def test_dynamic_table_must_terminate(self):
        b = bytearray(build_fixture())
        struct.pack_into("<qQ", b, 0x380 + DYNAMIC.size, 1, 1)
        with self.assertRaisesRegex(ProbeError, "DYNAMIC_TABLE_UNTERMINATED"):
            fingerprint(bytes(b))

if __name__ == "__main__":
    unittest.main()
