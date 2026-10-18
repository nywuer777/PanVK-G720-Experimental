#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
from source_role_locator import scan, MAX_FILE_BYTES

class SourceRoleLocatorTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / "source"
        self.root.mkdir()

    def seed(self):
        p = self.root / "src"
        p.mkdir()
        (p / "identity.cpp").write_text("host identity check failed")
        (p / "runtime.cpp").write_text("BACHATA/1 HELLO version=2 contract=")
        (p / "image_view.cpp").write_text("P45_BCN_PER_LAYER_VIEW_PROOF")
        (p / "upload.cpp").write_text("P45_BCN_LAYER_UPLOAD_COMPLETE")

    def test_all_synthetic_roles_are_only_candidates(self):
        self.seed()
        code, report = scan(self.root)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "SOURCE_ROLE_LOCATIONS_IDENTIFIED_NOT_PROVEN")
        self.assertEqual(len(report["matched_roles"]), 4)
        self.assertEqual(len(report["candidate_locations"]), 4)
        self.assertFalse(report["source_equivalence_proven"])
        self.assertFalse(report["p45_private_integration_proven"])
        self.assertFalse(report["apk_built"])

    def test_source_root_missing(self):
        code, report = scan(None)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "BLOCKED_AUTHORIZED_SOURCE_TREE_UNAVAILABLE")

    def test_empty_directory_blocks(self):
        code, report = scan(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(report["status"], "BLOCKED_NO_SOURCE_ROLE_CANDIDATES")

    def test_partial_source_remains_unproven(self):
        (self.root / "image.cpp").write_text("VK_FORMAT_BC3")
        code, report = scan(self.root)
        self.assertEqual(code, 0)
        self.assertEqual(report["status"], "SOURCE_ROLE_LOCATIONS_PARTIAL_NOT_PROVEN")
        self.assertIn("host_identity", report["missing_roles"])

    def test_symlinks_never_followed(self):
        self.seed()
        (self.root / "evil.cpp").symlink_to(self.root / "src" / "identity.cpp")
        (self.root / "external").symlink_to(self.root / "src", target_is_directory=True)
        code, report = scan(self.root)
        self.assertEqual(code, 0)
        paths = [x["relative_path"] for x in report["candidate_locations"]]
        self.assertNotIn("evil.cpp", paths)
        self.assertEqual(len(paths), 4)

    def test_hidden_repositories_and_other_files_skipped(self):
        dotgit = self.root / ".git"
        dotgit.mkdir()
        (dotgit / "spoof.cpp").write_text("BACHATA/1 HELLO")
        (self.root / "README.md").write_text("host identity check failed")
        (self.root / "host.bin").write_bytes(b"host identity check failed")
        code, report = scan(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(report["candidate_locations"], [])

    def test_binary_cpp_with_nul_not_reported(self):
        (self.root / "odd.cpp").write_bytes(b"host identity check failed\x00")
        code, report = scan(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(report["candidate_locations"], [])

    def test_oversized_file_not_reported(self):
        (self.root / "huge.cpp").write_bytes(b"BACHATA/1 HELLO " + b"A" * MAX_FILE_BYTES)
        code, report = scan(self.root)
        self.assertEqual(code, 2)
        self.assertEqual(report["files_skipped"], 1)

    def test_report_contains_no_source_contents(self):
        self.seed()
        code, report = scan(self.root)
        self.assertEqual(code, 0)
        serialized = str(report)
        self.assertNotIn("host identity check failed", serialized)
        self.assertNotIn("BACHATA/1 HELLO version=2 contract=", serialized)
        self.assertTrue(all("sha256" in row for row in report["candidate_locations"]))

if __name__ == "__main__":
    unittest.main()
