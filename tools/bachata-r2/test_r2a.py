#!/usr/bin/env python3
import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from apply_r2a import (
    HEADER_OLD, HEADER_NEW, FIRST_OLD, FIRST_NEW, SECOND_OLD, SECOND_NEW,
    PATCHES, transform, PIN, HASHES,
)

def analyze_order(sequence):
    bound, storage, general = False, False, False
    for is_written in sequence:
        if bound and (storage or is_written):
            general = True
        storage |= is_written
        bound = True
    return (general, storage)

class R2AMixedImageTests(unittest.TestCase):
    def test_header_added(self):
        self.assertIn("u32 has_storage : 1;", transform(HEADER_OLD, [(HEADER_OLD, HEADER_NEW)]))
    def test_first_pass_tracks_storage(self):
        self.assertIn("image->binding.has_storage |= image_desc.is_written;", FIRST_NEW)
    def test_second_pass_includes_shader_write(self):
        self.assertIn("access |= vk::AccessFlagBits2::eShaderWrite;", SECOND_NEW)
    def test_mixed_read_write(self):
        self.assertEqual(analyze_order([False, True]), (True, True))
    def test_mixed_write_read(self):
        self.assertEqual(analyze_order([True, False]), (True, True))
    def test_only_read(self):
        self.assertEqual(analyze_order([False]), (False, False))
    def test_only_write(self):
        self.assertEqual(analyze_order([True]), (False, True))
    def test_duplicate_reads(self):
        self.assertEqual(analyze_order([False, False]), (False, False))
    def test_duplicate_writes(self):
        self.assertEqual(analyze_order([True, True]), (True, True))
    def test_storage_disallows_feedback_layout(self):
        self.assertIn("!image.binding.has_storage &&", SECOND_NEW)
    def test_real_targets_keep_attachment_access(self):
        self.assertIn("vk::AccessFlagBits2::eColorAttachmentWrite |", SECOND_NEW)
    def test_storage_keeps_general_layout(self):
        self.assertIn("vk::ImageLayout::eGeneral", SECOND_NEW)
    def test_no_assert_bypass(self):
        self.assertNotIn("ASSERT(", FIRST_NEW + SECOND_NEW)
        self.assertNotIn("UNREACHABLE", FIRST_NEW + SECOND_NEW)
    def test_pinned_sha(self):
        self.assertEqual(PIN, "be6bc2e9c60799e071dd2fafa6216e8d80ec619c")
        self.assertEqual(len(HASHES), 2)
    def test_wrong_anchor_fail_closed(self):
        with self.assertRaises(ValueError):
            transform(HEADER_OLD.replace("is_bound", "oops"), [(HEADER_OLD, HEADER_NEW)])
    def test_duplicate_anchor_fail_closed(self):
        with self.assertRaises(ValueError):
            transform(HEADER_OLD + HEADER_OLD, [(HEADER_OLD, HEADER_NEW)])
    def test_repeat_patch_fail_closed(self):
        with self.assertRaises(ValueError):
            transform(HEADER_NEW, [(HEADER_OLD, HEADER_NEW)])
    def test_exactly_two_files_touched(self):
        self.assertEqual(set(PATCHES), set(HASHES))

if __name__ == "__main__":
    unittest.main()
