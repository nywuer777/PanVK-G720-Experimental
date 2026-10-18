import unittest
from patch_p53 import patched, GAME_OLD, IMPORT_OLD

PREREQS=(
    "BACHATA_F43DEV_R2A2_HOST_GATE_OK",
    "SendHelloV2",
    "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED",
)
MINIMAL='\n'.join(PREREQS)+'\n'+IMPORT_OLD+'\n'+GAME_OLD+'\n'
class P53PatchTests(unittest.TestCase):
    def test_preserves_host_v2_and_game_fallback(self):
        value=patched(MINIMAL)
        for marker in PREREQS:self.assertIn(marker,value)
        self.assertIn("std::filesystem::exists(ebootPath)",value)
    def test_only_target_eboot(self):
        value=patched(MINIMAL)
        self.assertIn('ResolveEboot(*gamePath, overrideRoot)',value)
        self.assertIn('else if (*gamePath == "eboot.bin" && overrideRoot)',value)
    def test_error_is_not_faked(self):
        value=patched(MINIMAL)
        self.assertIn("BACHATA_P53_EBOOT_ROOT_UNAVAILABLE",value)
        self.assertIn("BACHATA_P53_EBOOT_OVERRIDE_ROOT_RESOLVED",value)
    def test_fails_if_no_override_root_support(self):
        with self.assertRaisesRegex(ValueError,"ANCHOR_MISMATCH"):
            patched(MINIMAL.replace(GAME_OLD,""))
    def test_fails_if_no_import_anchor(self):
        with self.assertRaisesRegex(ValueError,"ANCHOR_MISMATCH"):
            patched(MINIMAL.replace(IMPORT_OLD,""))
    def test_fails_if_absent_host_guard(self):
        with self.assertRaisesRegex(ValueError,"PREREQUISITE"):
            patched(MINIMAL.replace(PREREQS[0],""))
    def test_fails_if_absent_hello(self):
        with self.assertRaisesRegex(ValueError,"PREREQUISITE"):
            patched(MINIMAL.replace(PREREQS[1],""))
    def test_fails_if_bsf1_missing(self):
        with self.assertRaisesRegex(ValueError,"PREREQUISITE"):
            patched(MINIMAL.replace(PREREQS[2],""))
    def test_fails_double_game_anchor(self):
        with self.assertRaisesRegex(ValueError,"ANCHOR_MISMATCH"):
            patched(MINIMAL+GAME_OLD)
    def test_fails_double_apply(self):
        with self.assertRaisesRegex(ValueError,"(PREREQUISITE|ANCHOR_MISMATCH|ALREADY_PATCHED)"):
            patched(patched(MINIMAL))
if __name__ == "__main__":
    unittest.main()
