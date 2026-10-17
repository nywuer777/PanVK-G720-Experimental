#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
import struct
import unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location("host_audit",Path(__file__).with_name("audit_host_contract.py"))
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

def synthetic_dex(strings):
    b=bytearray(256)
    b[:8]=b"dex\n039\0"
    string_ids_off=112
    p=string_ids_off+len(strings)*4
    for i,val in enumerate(strings):
        raw=val.encode("utf-8")
        assert len(raw)<128
        struct.pack_into("<I",b,string_ids_off+i*4,p)
        fragment=bytes([len(raw)])+raw+b"\0"
        b[p:p+len(fragment)]=fragment
        p+=len(fragment)
    struct.pack_into("<I",b,32,len(b))
    struct.pack_into("<II",b,0x38,len(strings),string_ids_off)
    return bytes(b)

class DexStringParserTests(unittest.TestCase):
    def test_known_protocol2_hello(self):
        self.assertIn("BACHATA/1 HELLO version=2 contract=",mod.extract_dex_strings(
            synthetic_dex(["BACHATA/1 HELLO version=2 contract="])))
    def test_known_compatibility_requirement(self):
        self.assertIn("Runtime contract mismatch (app requires protocol 2)",mod.extract_dex_strings(
            synthetic_dex(["Runtime contract mismatch (app requires protocol 2)"])))
    def test_saf_cli_pair(self):
        entries=mod.extract_dex_strings(
            synthetic_dex(["--bachata-saf-socket","--bachata-saf-token"]))
        self.assertIn("--bachata-saf-socket",entries)
        self.assertIn("--bachata-saf-token",entries)
    def test_empty_string_table(self):
        self.assertEqual(mod.extract_dex_strings(synthetic_dex([])),set())
    def test_invalid_signature(self):
        with self.assertRaisesRegex(ValueError,"invalid_dex_header"):
            mod.extract_dex_strings(b"not dex")
    def test_bad_file_length(self):
        b=bytearray(synthetic_dex(["A"]))
        struct.pack_into("<I",b,32,99)
        with self.assertRaisesRegex(ValueError,"invalid_dex_size"):
            mod.extract_dex_strings(b)
    def test_excess_string_index(self):
        b=bytearray(synthetic_dex(["A"]))
        struct.pack_into("<I",b,0x38,1234567)
        with self.assertRaisesRegex(ValueError,"invalid_dex_string_index"):
            mod.extract_dex_strings(b)
    def test_bad_string_offset(self):
        b=bytearray(synthetic_dex(["A"]))
        struct.pack_into("<I",b,112,0xffffffff)
        with self.assertRaisesRegex(ValueError,"invalid_dex_string_offset"):
            mod.extract_dex_strings(b)
    def test_no_null_terminator(self):
        b=bytearray(synthetic_dex(["A"]))
        b[118:]=b"A"*(len(b)-118)
        with self.assertRaisesRegex(ValueError,"invalid_dex_termination"):
            mod.extract_dex_strings(b)
    def test_hex_checksum(self):
        self.assertEqual(mod.sha(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    def test_empty_fingerprint_not_baseline(self):
        self.assertNotEqual(mod.sha(b"fake"),mod.EXPECTED_APK_SHA)
    def test_contract_marker_is_not_real_attestation(self):
        self.assertTrue("contract=" in "BACHATA/1 HELLO version=2 contract=")
        # Syntax strings do not prove peer UID, Android signing or token authentication.

if __name__ == "__main__":
    unittest.main()
