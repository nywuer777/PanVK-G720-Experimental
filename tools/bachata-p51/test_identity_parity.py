#!/usr/bin/env python3
"""P51 synthetic failure-mode regressions; actual ELF is checked in CI job."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from p42_p49_identity_parity import (
    P49_SHA,P49_TEXT_SHA,P42_SHA,P42_TEXT_SHA,LOADER,MAX_BYTES,
    bounded_slice,section_inventory,identify,compare,
)

def fake_public():
    return {
        "sha256":P49_SHA,"text_sha256":P49_TEXT_SHA,
        "host_v2_hello_format_literal":True,
        "public_peer_reject_literal":True,
        "private_v2_identity_guard_literal":False,
        "private_bcn_fallback_literal":False,
        "public_bcn_sample_reject_literal":True,
    }

def fake_private():
    return {
        "sha256":P42_SHA,"text_sha256":P42_TEXT_SHA,
        "private_v2_identity_guard_literal":True,
        "private_bcn_fallback_literal":True,
    }

class TestParity(unittest.TestCase):
    def test_reference_hashes_are_different(self):
        self.assertNotEqual(P42_SHA,P49_SHA)
        self.assertNotEqual(P42_TEXT_SHA,P49_TEXT_SHA)
    def test_public_v2_strings_do_not_approve_android(self):
        out=compare(fake_public(),None)
        self.assertEqual(out["verdict"],"REJECT_PUBLIC_P49_AS_DROP_IN_P42_CORE")
        self.assertFalse(out["apk_promotion_authorized"])
        self.assertFalse(out["private_core_raw_bytes_verified"])
    def test_both_real_references_still_do_not_approve_drop_in(self):
        out=compare(fake_public(),fake_private())
        self.assertTrue(out["private_core_raw_bytes_verified"])
        self.assertFalse(out["private_core_text_equal_to_public"])
        self.assertFalse(out["signed_apk_v2_signature_reverified_in_p51"])
    def test_false_hello_rejected(self):
        p=fake_public();p["host_v2_hello_format_literal"]=False
        with self.assertRaisesRegex(ValueError,"HOST_V2_SYMBOLS"):
            compare(p,None)
    def test_missing_peer_reject_string_rejected(self):
        p=fake_public();p["public_peer_reject_literal"]=False
        with self.assertRaisesRegex(ValueError,"HOST_V2_SYMBOLS"):
            compare(p,None)
    def test_swapped_public_binary_hash_rejected(self):
        p=fake_public();p["sha256"]=P42_SHA
        with self.assertRaisesRegex(ValueError,"PUBLIC_P49_CODE_PIN"):
            compare(p,None)
    def test_forged_text_rejected(self):
        p=fake_public();p["text_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"PUBLIC_P49_CODE_PIN"):
            compare(p,None)
    def test_unexpected_private_sha_rejected(self):
        p=fake_private();p["sha256"]=P49_SHA
        with self.assertRaisesRegex(ValueError,"PRIVATE_P42_CODE_PIN"):
            compare(fake_public(),p)
    def test_unexpected_private_text_rejected(self):
        p=fake_private();p["text_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"PRIVATE_P42_CODE_PIN"):
            compare(fake_public(),p)
    def test_missing_private_identity_guard_rejected(self):
        p=fake_private();p["private_v2_identity_guard_literal"]=False
        with self.assertRaisesRegex(ValueError,"PRIVATE_P42_CONTRACT_INCONSISTENT"):
            compare(fake_public(),p)
    def test_missing_private_bcn_fallback_rejected(self):
        p=fake_private();p["private_bcn_fallback_literal"]=False
        with self.assertRaisesRegex(ValueError,"PRIVATE_P42_CONTRACT_INCONSISTENT"):
            compare(fake_public(),p)
    def test_bounded_slice_rejects_negative_offset(self):
        with self.assertRaisesRegex(ValueError,"ELF_SECTION_OUT_OF_BOUNDS"):
            bounded_slice(b"abc",-1,1)
    def test_bounded_slice_rejects_end_overflow(self):
        with self.assertRaisesRegex(ValueError,"ELF_SECTION_OUT_OF_BOUNDS"):
            bounded_slice(b"abc",1,3)
    def test_non_elf_rejected(self):
        with self.assertRaisesRegex(ValueError,"NOT_ELF64_LE"):
            section_inventory(b"\x00"*128)
    def test_missing_binary_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError,"SOURCE_BINARY_NOT_AVAILABLE"):
                identify(Path(t)/"missing",P49_SHA)
    def test_symlink_binary_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"elf";p.write_bytes(b"wrong")
            link=Path(t)/"link";link.symlink_to(p)
            with self.assertRaisesRegex(ValueError,"SOURCE_BINARY_NOT_AVAILABLE"):
                identify(link,P49_SHA)
    def test_wrong_sha_bails_before_elf_parse(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"elf";p.write_bytes(b"random"+b"\0"*128)
            with patch("p42_p49_identity_parity.section_inventory") as parser:
                with self.assertRaisesRegex(ValueError,"BINARY_HASH_DOES_NOT_MATCH"):
                    identify(p,P49_SHA)
                parser.assert_not_called()
    def test_loader_known_path(self):
        self.assertEqual(LOADER,"/lib/ld-linux-aarch64.so.1")
    def test_binary_maximum_bounded(self):
        self.assertLess(MAX_BYTES,200_000_000)

if __name__=="__main__":
    unittest.main()
