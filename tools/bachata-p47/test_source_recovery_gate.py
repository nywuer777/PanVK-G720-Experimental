#!/usr/bin/env python3
"""Portable positive/negative source-inventory regression tests (synthetic only)."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from source_recovery_gate import (
    gate, SCHEMA, P42_ELF_SHA256, P42_TEXT_SHA256, REFERENCE_PRIVATE_COMMIT,
    KNOWN_PUBLIC_SOURCE_COMMIT,
)

class SourceRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "private-src"
        self.root.mkdir()
        roles = ["private_host_identity", "bcn_graphics", "runtime_protocol", "build_recipe"]
        self.entries = []
        for role in roles:
            name = role + (".sh" if role == "build_recipe" else ".cpp")
            data = ("synthetic stub: " + role + "\n").encode()
            (self.root / name).write_bytes(data)
            self.entries.append({"path": name, "role": role,
                                 "sha256": hashlib.sha256(data).hexdigest()})
        self.manifest = Path(self.tmp.name) / "manifest.json"
        self.att = {
            "schema": SCHEMA,
            "p42_private_elf_sha256": P42_ELF_SHA256,
            "p42_private_text_sha256": P42_TEXT_SHA256,
            "reference_private_commit": REFERENCE_PRIVATE_COMMIT,
            "source_revision": REFERENCE_PRIVATE_COMMIT,
            "lineage": "recovered-original-private",
            "files": self.entries,
        }
        self.flush()

    def flush(self):
        self.manifest.write_text(json.dumps(self.att), encoding="utf-8")

    def check_blocked(self, code):
        self.flush()
        status, report = gate(self.root, self.manifest)
        self.assertEqual(status, 2)
        self.assertEqual(report["status"], "BLOCKED_SOURCE_ATTESTATION_FAILED")
        self.assertEqual(report["reason"], code)
        self.assertFalse(report["apk_built"])

    def test_missing_inputs_are_blocked(self):
        code, result = gate(None, None)
        self.assertEqual(code, 2)
        self.assertEqual(result["status"], "BLOCKED_PRIVATE_SOURCE_UNAVAILABLE")

    def test_synthetic_inventory_is_not_binary_equivalence(self):
        code, result = gate(self.root, self.manifest)
        self.assertEqual(code, 0)
        self.assertEqual(result["status"], "SOURCE_INVENTORY_CONFIRMED_EQUIVALENCE_PENDING")
        self.assertFalse(result["host_identity_binary_equivalence"])
        self.assertFalse(result["p45_private_bcn_integration_proven"])
        self.assertFalse(result["outlast_fixed"])
        self.assertFalse(result["apk_built"])

    def test_wrong_p42_binary(self):
        self.att["p42_private_elf_sha256"] = "0" * 64
        self.check_blocked("P42_ELF_IDENTITY_MISMATCH")

    def test_wrong_text_digest(self):
        self.att["p42_private_text_sha256"] = "0" * 64
        self.check_blocked("P42_TEXT_IDENTITY_MISMATCH")

    def test_public_source_substitution(self):
        self.att["source_revision"] = KNOWN_PUBLIC_SOURCE_COMMIT
        self.check_blocked("KNOWN_PUBLIC_P31_SUBSTITUTION")

    def test_missing_private_lineage(self):
        self.att["reference_private_commit"] = "0" * 40
        self.check_blocked("PRIVATE_LINEAGE_UNVERIFIED")

    def test_missing_role(self):
        self.att["files"].pop()
        self.check_blocked("SOURCE_INVENTORY_INCOMPLETE")

    def test_tampered_file(self):
        path = self.root / self.entries[0]["path"]
        path.write_text("tampered", encoding="utf-8")
        self.check_blocked("SOURCE_FILE_HASH_MISMATCH")

    def test_path_traversal(self):
        self.att["files"][0]["path"] = "../escape.cpp"
        self.check_blocked("SOURCE_PATH_ESCAPE")

    def test_symlink_rejected(self):
        path = self.root / self.entries[0]["path"]
        path.unlink()
        path.symlink_to(self.root / self.entries[1]["path"])
        self.check_blocked("SYMLINK_SOURCE_REJECTED")

    def test_duplicate_role(self):
        self.att["files"][1]["role"] = "private_host_identity"
        self.check_blocked("SOURCE_DUPLICATE_ROLE")

    def test_empty_source(self):
        path = self.root / self.entries[2]["path"]
        path.write_bytes(b"")
        self.att["files"][2]["sha256"] = hashlib.sha256(b"").hexdigest()
        self.check_blocked("EMPTY_SOURCE_FILE")

if __name__ == "__main__":
    unittest.main()
