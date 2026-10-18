"""P61.1 tests: package specificity, exact three-byte patch and trust marker retention."""
import hashlib, unittest
from verified_lab_package_rebind import (
    patched_lab_core, PUBLIC_NAME, LAB_NAME, GATE_MARKERS, sha,
)

def fixture():
    blob = bytearray(b"\x7fELF" + bytes([2, 1]) + bytes(12) + b"\xb7\x00")
    blob += b"trusted\x00" + PUBLIC_NAME + b"\x00"
    for marker in GATE_MARKERS:
        blob += marker + b"\x00"
    return bytes(blob)

class TestLabPackageBinder(unittest.TestCase):
    def test_positive_exact_byte_diff(self):
        orig = fixture()
        modified, indexes = patched_lab_core(orig, sha(orig))
        self.assertEqual(modified.count(LAB_NAME), 1)
        self.assertNotIn(PUBLIC_NAME, modified)
        self.assertEqual(len(modified), len(orig))
        actual = [i for i, (a, b) in enumerate(zip(orig, modified)) if a != b]
        self.assertEqual(indexes, actual)
        self.assertEqual(len(indexes), 3)
        for marker in GATE_MARKERS:
            self.assertIn(marker, modified)
    def test_pinned_sha_rejected(self):
        with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
            patched_lab_core(fixture())
    def test_duplicate_old_name_rejected(self):
        original = fixture() + PUBLIC_NAME
        with self.assertRaisesRegex(ValueError, "NOT_UNIQUE"):
            patched_lab_core(original, sha(original))
    def test_premature_lab_name_rejected(self):
        original = fixture() + LAB_NAME
        with self.assertRaisesRegex(ValueError, "ALREADY_BOUND"):
            patched_lab_core(original, sha(original))
    def test_missing_protection_rejected(self):
        original = fixture().replace(GATE_MARKERS[1], b"missing")
        with self.assertRaisesRegex(ValueError, "GUARD_OR_STAGE"):
            patched_lab_core(original, sha(original))
    def test_wrong_machine_rejected(self):
        original = fixture().replace(b"\xb7\x00", b"\x3e\x00", 1)
        with self.assertRaisesRegex(ValueError, "NOT_ELF64"):
            patched_lab_core(original, sha(original))
    def test_wrong_package_reference_rejected(self):
        original = fixture().replace(PUBLIC_NAME, b"com.bachatas4.android.f43bad")
        with self.assertRaisesRegex(ValueError, "NOT_UNIQUE"):
            patched_lab_core(original, sha(original))

if __name__ == "__main__":
    unittest.main()
