"""Negative patch regression tests; no APK or host token."""
import unittest
from patch_p54 import patched, ANCHOR, INCLUDE

SAMPLE = '\n'.join([
    "BACHATA_P53_EBOOT_OVERRIDE_ROOT_RESOLVED",
    "BACHATA_P53_EBOOT_ROOT_UNAVAILABLE",
    "BACHATA_F43DEV_R2A2_HOST_GATE_OK",
    "SendHelloV2",
    "const Bachata::Saf::BSF1::Client saf_broker(saf_config);",
    INCLUDE,ANCHOR,"return 0;",
])
class TestSource(unittest.TestCase):
    def test_good_patch(self):
        data = patched(SAMPLE)
        self.assertIn('Marker(p54_probe.outcome)', data)
        self.assertIn('p54_eboot_fd.emplace(std::move(p54_probe.fd))', data)
        self.assertIn('TryOpenInitialEboot(', data)
        self.assertIn('std::filesystem::exists(ebootPath)', data)
    def test_preserves_trusted_socket(self):
        data = patched(SAMPLE)
        self.assertIn("BACHATA_F43DEV_R2A2_HOST_GATE_OK",data)
        self.assertIn("const Bachata::Saf::BSF1::Client saf_broker(saf_config);",data)
    def test_not_full_game_vfs(self):
        data = patched(SAMPLE)
        self.assertNotIn("EnableExperimental(",data)
    def test_missing_p53_rejected(self):
        with self.assertRaisesRegex(ValueError,"PREREQUISITE"):
            patched(SAMPLE.replace("BACHATA_P53_EBOOT_ROOT_UNAVAILABLE",""))
    def test_missing_host_v2_rejected(self):
        with self.assertRaisesRegex(ValueError,"PREREQUISITE"):
            patched(SAMPLE.replace("BACHATA_F43DEV_R2A2_HOST_GATE_OK",""))
    def test_missing_client_rejected(self):
        with self.assertRaisesRegex(ValueError,"PREREQUISITE"):
            patched(SAMPLE.replace("const Bachata::Saf::BSF1::Client saf_broker(saf_config);",""))
    def test_double_main_anchor_rejected(self):
        with self.assertRaisesRegex(ValueError,"ANCHOR"):
            patched(SAMPLE+ANCHOR)
    def test_missing_include_rejected(self):
        with self.assertRaisesRegex(ValueError,"ANCHOR"):
            patched(SAMPLE.replace(INCLUDE,""))
    def test_double_apply_rejected(self):
        with self.assertRaisesRegex(ValueError,"(ANCHOR|ALREADY_PATCHED)"):
            patched(patched(SAMPLE))
if __name__ == "__main__":
    unittest.main()
