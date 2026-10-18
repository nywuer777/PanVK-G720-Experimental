"""Regression tests for local REA ZIP intake. No downloaded/private artifacts."""
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

from rea_intake import (
    ARCHIVE_SHA256, PREFIX, IntakeFailure, audit_zip, node_ready, safe_member,
)


def build_zip(path: Path, version="6.6.0", license_id="MIT", extra=None):
    entries = {
        "LICENSE": b"MIT License\nCopyright (c) 2026 morluto\n",
        "package.json": json.dumps({
            "name": "rea-agents",
            "version": version,
            "license": license_id,
        }).encode(),
        "README.md": b"# REA\n",
        ".agents/skills/reverse-engineer-anything/SKILL.md": b"# Skill\n",
        ".agents/skills/reverse-engineer-anything/references/android-applications.md": b"# Android\n",
    }
    if extra:
        entries.update(extra)
    with zipfile.ZipFile(path, "w") as f:
        for rel, data in entries.items():
            f.writestr(PREFIX + rel, data)


class TestREAIntake(unittest.TestCase):
    def test_supported_node_versions(self):
        for s in ("v22.19.0", "v22.20.1", "v24.11.0", "v26.0.0", "v30.1.1"):
            self.assertTrue(node_ready(s), s)

    def test_unsupported_node_versions(self):
        for s in ("v22.16.0", "v22.18.99", "v24.10.9",
                  "v23.0.0", "v25.0.0", "v20.19.0", "v99", "garbage"):
            self.assertFalse(node_ready(s), s)

    def test_paths_reject_unsafe_strings(self):
        for name in ("../../etc/passwd", PREFIX + "../evil", "/" + PREFIX + "LICENSE",
                     PREFIX + r"a\..\file", PREFIX + "a\x00b",
                     PREFIX + "a//b", PREFIX + "./LICENSE",
                     PREFIX + "a/./b"):
            self.assertFalse(safe_member(name), repr(name))

    def test_paths_allow_expected_source(self):
        for name in (PREFIX, PREFIX + "LICENSE",
                     PREFIX + ".agents/skills/reverse-engineer-anything/SKILL.md"):
            self.assertTrue(safe_member(name))

    def test_missing_file(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(IntakeFailure, "NOT_LOCAL"):
                audit_zip(Path(d) / "missing.zip")

    def test_archive_checksum_rejected_before_zip_parse(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.zip"
            build_zip(p)
            with self.assertRaisesRegex(IntakeFailure, "SHA256_MISMATCH"):
                audit_zip(p)

    def test_valid_shape_pinned_zip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.zip"
            build_zip(p)
            with patch("rea_intake.digest", return_value=ARCHIVE_SHA256):
                report = audit_zip(p)
            self.assertEqual(report["version"], "6.6.0")
            self.assertEqual(report["source_integrity"], "PASS_LOCAL_READONLY")
            self.assertFalse(report["private_artifacts_uploaded"])

    def test_version_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.zip"
            build_zip(p, version="6.6.1")
            with patch("rea_intake.digest", return_value=ARCHIVE_SHA256):
                with self.assertRaisesRegex(IntakeFailure, "IDENTITY_OR_LICENSE"):
                    audit_zip(p)

    def test_license_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.zip"
            build_zip(p, license_id="GPL-3.0")
            with patch("rea_intake.digest", return_value=ARCHIVE_SHA256):
                with self.assertRaisesRegex(IntakeFailure, "IDENTITY_OR_LICENSE"):
                    audit_zip(p)

    def test_zip_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.zip"
            build_zip(p, extra={"../escape": b"x"})
            with patch("rea_intake.digest", return_value=ARCHIVE_SHA256):
                with self.assertRaisesRegex(IntakeFailure, "UNSAFE"):
                    audit_zip(p)

    def test_symlink_source_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "test.zip"
            build_zip(p)
            s = Path(d) / "link.zip"
            s.symlink_to(p)
            with self.assertRaisesRegex(IntakeFailure, "NOT_LOCAL"):
                audit_zip(s)


if __name__ == "__main__":
    unittest.main()
