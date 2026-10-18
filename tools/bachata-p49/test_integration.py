#!/usr/bin/env python3
"""No real private code; these tests exercise negative and synthetic gates."""
import tempfile
import unittest
from pathlib import Path
from integrate_public_hostv2_p45 import verify_markers, NEEDED, PIN, CHAIN

class P49Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
    def fill(self):
        for file, needles in NEEDED.items():
            path = self.root / file
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("\n".join(needles) + "\n", encoding="utf-8")
    def test_empty_is_rejected(self):
        result = verify_markers(self.root)
        self.assertFalse(result["markers_pass"])
        self.assertEqual(len(result["missing"]), len(NEEDED))
    def test_combined_synthetic_markers_only(self):
        self.fill()
        result = verify_markers(self.root)
        self.assertTrue(result["markers_pass"])
        for key in ("host_original_p42_binary_verified", "host_signer_verified",
                    "private_runtime_reconstructed", "outlast_fixed_on_device",
                    "apk_built"):
            self.assertFalse(result[key])
    def test_missing_host_peer_gate_rejected(self):
        self.fill()
        p = self.root / "src/main.cpp"
        p.write_text(p.read_text().replace("VerifyPeer", "MISSING"))
        self.assertIn("VerifyPeer", verify_markers(self.root)["missing"]["src/main.cpp"])
    def test_missing_v2_hello_rejected(self):
        self.fill()
        p = self.root / "src/platform/bachata/runtime_client.cpp"
        p.write_text("")
        self.assertFalse(verify_markers(self.root)["markers_pass"])
    def test_missing_p45_proof_rejected(self):
        self.fill()
        p = self.root / "src/video_core/texture_cache/image_view.cpp"
        p.write_text("P25 decoded BCn sampled view blocked")
        self.assertIn("P45_BCN_PER_LAYER_VIEW_PROOF",
                      verify_markers(self.root)["missing"]["src/video_core/texture_cache/image_view.cpp"])
    def test_missing_gpu_upload_marker_rejected(self):
        self.fill()
        p = self.root / "src/video_core/renderer_vulkan/p27_vk_decoded_upload.cpp"
        p.unlink()
        self.assertIn("MISSING_FILE", verify_markers(self.root)["missing"]
                      ["src/video_core/renderer_vulkan/p27_vk_decoded_upload.cpp"])
    def test_absent_p39_marker_rejected(self):
        self.fill()
        p = self.root / "src/video_core/renderer_vulkan/vk_rasterizer.cpp"
        p.write_text("BACHATA_F43DEV_R2A2_HOST_GATE_OK")
        self.assertFalse(verify_markers(self.root)["markers_pass"])
    def test_symlinked_source_rejected(self):
        self.fill()
        p = self.root / "src/main.cpp"
        p.unlink()
        p.symlink_to(self.root / "src/platform/bachata/runtime_client.cpp")
        self.assertIn("MISSING_FILE", verify_markers(self.root)["missing"]["src/main.cpp"])
    def test_pin_does_not_claim_p42(self):
        self.assertEqual(PIN, "be6bc2e9c60799e071dd2fafa6216e8d80ec619c")
    def test_chain_order_preserved(self):
        self.assertEqual(CHAIN[0][0], "tools/bachata-r2/apply_r2a.py")
        self.assertEqual(CHAIN[-1][0], "tools/bachata-r2a6p5/apply_r2a6p5.py")

if __name__ == "__main__":
    unittest.main()
