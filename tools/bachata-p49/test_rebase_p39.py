#!/usr/bin/env python3
import tempfile
import unittest
from pathlib import Path
from rebase_p39_shaderwrite import prepare, R2A_GUARDS

TARGET = "diff --git a/src/video_core/renderer_vulkan/vk_rasterizer.cpp b/src/video_core/renderer_vulkan/vk_rasterizer.cpp"
PATCH = """diff --git a/src/main.cpp b/src/main.cpp
index 0000000..1111111 100644
--- a/src/main.cpp
+++ b/src/main.cpp
@@ -1 +1,2 @@
 context
+preserve
""" + TARGET + """
index 99db6950..828618a0 100644
--- a/src/video_core/renderer_vulkan/vk_rasterizer.cpp
+++ b/src/video_core/renderer_vulkan/vk_rasterizer.cpp
@@ -800,1 +800,4 @@ void Rasterizer::BindTextures()
 existing
+ // P39_EXACT_IMAGE_ID_SAMPLED_STORAGE
+ if (p39_decision.use_general) {
+ p39_image.binding.force_general = 1u;
@@ -842,6 +1130,13 @@ void Rasterizer::BindTextures(const Shader::Info& stage, Shader::Backend::Binding
                                   ? vk::ImageLayout::eAttachmentFeedbackLoopOptimalEXT
                                   : vk::ImageLayout::eGeneral,
                               vk::AccessFlagBits2::eShaderRead |
+                                  // Opt-in: a GENERAL view shared with storage must
+                                  // advertise writes, including when descriptors are
+                                  // encountered storage-first then sampled-second.
+                                  ((BachataP39::Enabled() && image.binding.force_general &&
+                                    !image.binding.is_target)
+                                       ? vk::AccessFlagBits2::eShaderWrite
+                                       : vk::AccessFlagBits2::eNone) |
                                   (image.info.props.is_depth
                                        ? vk::AccessFlagBits2::eDepthStencilAttachmentWrite
                                        : vk::AccessFlagBits2::eColorAttachmentWrite |
diff --git a/another.cpp b/another.cpp
index 0000000..1111111 100644
--- a/another.cpp
+++ b/another.cpp
@@ -1 +1,2 @@
 context
+unrelated
"""

class RebaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.host = Path(self.temp.name) / "vk_rasterizer.cpp"
        self.host.write_text("\n".join(R2A_GUARDS), encoding="utf-8")

    def test_exact_known_overlap_is_rebased_and_other_changes_retained(self):
        body, report = prepare(PATCH.encode(), self.host)
        text = body.decode()
        self.assertEqual(report["status"], "P39_WRITE_ACCESS_HUNK_EXPLICITLY_REBASED")
        self.assertEqual(report["retained_other_p45_hunks"], 1)
        self.assertNotIn("@@ -842,6 +1130,13 @@", text)
        self.assertIn("P39_EXACT_IMAGE_ID_SAMPLED_STORAGE", text)
        self.assertIn("another.cpp", text)
        self.assertFalse(report["verified_host_p42_identity"])
        self.assertFalse(report["outlast_fixed"])

    def test_missing_shaderwrite_guard_blocks(self):
        self.host.write_text("no storage check")
        with self.assertRaisesRegex(ValueError, "R2A_SHADERWRITE_SEMANTICS_NOT_PROVEN"):
            prepare(PATCH.encode(), self.host)

    def test_p45_overlap_moved_blocks(self):
        with self.assertRaisesRegex(ValueError, "P39_OVERLAP_HUNK_CHANGED"):
            prepare(PATCH.replace("@@ -842,6 +1130,13 @@", "@@ -843,6 +1131,13 @@").encode(), self.host)

    def test_p45_overlap_extra_line_blocks(self):
        corrupted = PATCH.replace("+                                       : vk::AccessFlagBits2::eNone) |", "+  malicious\n+                                       : vk::AccessFlagBits2::eNone) |")
        with self.assertRaisesRegex(ValueError, "P39_OVERLAP_SEMANTICS_CHANGED"):
            prepare(corrupted.encode(), self.host)

    def test_must_retain_p39_force_general(self):
        edited = PATCH.replace("p39_image.binding.force_general = 1u;", "something_else;")
        with self.assertRaisesRegex(ValueError, "P39_ACTIVE_FORCE_GENERAL_CODE_MISSING"):
            prepare(edited.encode(), self.host)

    def test_repeated_overlap_rejected(self):
        edited = PATCH.replace("diff --git a/another.cpp", PATCH[PATCH.index("@@ -842,6 +1130,13 @@"):PATCH.index("diff --git a/another.cpp")] + "diff --git a/another.cpp")
        with self.assertRaisesRegex(ValueError, "P39_KNOWN_OVERLAP_NOT_UNIQUE"):
            prepare(edited.encode(), self.host)

    def test_unknown_rasterizer_patch_blocked(self):
        with self.assertRaisesRegex(ValueError, "P45_RASTERIZER_PATCH_NOT_UNIQUE"):
            prepare(b"not a unified diff", self.host)

if __name__ == "__main__":
    unittest.main()
