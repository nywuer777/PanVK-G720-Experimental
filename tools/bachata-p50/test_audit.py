import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from audit_p49_guest_abi import (
    INTERP, MARKERS, NEEDED, PACKAGE, P49_SHA256, attest,
    needed_libraries, symbols,
)

DYNS = "\n".join(" (NEEDED) Shared library: [" + lib + "]" for lib in NEEDED)
VERS = """
Name: GLIBC_2.17
Name: GLIBC_2.38
Name: GLIBCXX_3.4.32
Name: GLIBCXX_3.4.29
"""

class P50Test(unittest.TestCase):
    def test_dependency_parser_and_allowlist(self):
        self.assertEqual(set(needed_libraries(DYNS)), NEEDED)
        self.assertNotIn("liblog.so", NEEDED)
    def test_symbol_version_numerical_order(self):
        self.assertEqual(symbols(VERS, "GLIBC"), ["GLIBC_2.17", "GLIBC_2.38"])
        self.assertEqual(symbols(VERS, "GLIBCXX"),
                         ["GLIBCXX_3.4.29", "GLIBCXX_3.4.32"])
    def test_symbol_versions_not_invented_from_other_sections(self):
        self.assertEqual(symbols("Name: GLIBC_PRIVATE", "GLIBC"), [])
    def test_missing_elf_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaisesRegex(ValueError, "MISSING_OR_SYMLINKED"):
                attest(Path(t)/"missing", Path(t)/"gate")
    def test_symlink_elf_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/"file";p.write_bytes(b"elf")
            (root/"link").symlink_to(p)
            with self.assertRaisesRegex(ValueError, "MISSING_OR_SYMLINKED"):
                attest(root/"link", root/"gate")
    def test_bad_checksum_blocks_before_any_readelf(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);p=root/"wrong"
            p.write_bytes(b"not an elf")
            with patch("audit_p49_guest_abi.read_elf_output") as obj:
                with self.assertRaisesRegex(ValueError, "SHA256_MISMATCH"):
                    attest(p, root/"gate")
                obj.assert_not_called()
    def test_reference_p42_distinct(self):
        from audit_p49_guest_abi import P42_SHA256
        self.assertNotEqual(P42_SHA256, P49_SHA256)
    def test_expected_source_package_is_hypothesis_only(self):
        self.assertEqual(PACKAGE, "com.bachatas4.android.f43dev")
    def test_loader_is_glibc_not_bionic(self):
        self.assertEqual(INTERP, "/lib/ld-linux-aarch64.so.1")
    def test_markers_do_not_prove_host_compatibility(self):
        self.assertEqual(len(MARKERS), 4)
        self.assertIn(b"BACHATA/1 HELLO version=2 contract=", MARKERS)

if __name__ == "__main__":
    unittest.main()
