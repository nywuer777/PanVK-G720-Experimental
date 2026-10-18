"""P63 exactly anchored source-patch regression (no live game metadata)."""
import unittest
from patch_p63 import MAIN_OLD,patched_main
FIXTURE = ("BACHATA_F43DEV_R2A2_HOST_GATE_OK\n"
           "CONTENT_METADATA_UNAVAILABLE\n"
           + MAIN_OLD+"\n")
class P63(unittest.TestCase):
    def test_single_target_and_no_unrelated_changes(self):
        patched=patched_main(FIXTURE)
        self.assertIn("BACHATA_P63_PSF_FORMAT_EVIDENCE",patched)
        self.assertIn("psf.format_evidence.raw_format",patched)
        self.assertEqual(patched.count("CONTENT_METADATA_UNAVAILABLE"),1)
        self.assertEqual(patched.count("BACHATA_F43DEV_R2A2_HOST_GATE_OK"),1)
    def test_second_application_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"ANCHOR"):
            patched_main(patched_main(FIXTURE))
    def test_host_guard_required(self):
        with self.assertRaisesRegex(ValueError,"TRUST"):
            patched_main(FIXTURE.replace("BACHATA_F43DEV_R2A2_HOST_GATE_OK",""))
    def test_missing_error_flow_rejected(self):
        with self.assertRaisesRegex(ValueError,"TRUST"):
            patched_main(FIXTURE.replace("CONTENT_METADATA_UNAVAILABLE",""))
if __name__=="__main__": unittest.main()
