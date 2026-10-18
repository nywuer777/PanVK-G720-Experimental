"""P60 strict source integration regressions; no private APK or PRX."""
import unittest
from patch_p60 import patched_main

FIXTURE = """BACHATA_F43DEV_R2A2_HOST_GATE_OK
BACHATA_P53_EBOOT_ROOT_UNAVAILABLE
#include "platform/bachata/p59_private_stage.h"
    std::optional<Bachata::Saf::P59::PrivateStage> p59_eboot_stage;
P59::StageAuthenticatedFd(
            if (staged) {
                p59_eboot_stage.emplace(std::move(staged));
                ebootPath = p59_eboot_stage->path;
            }
"""
class P60MainPatchTests(unittest.TestCase):
    def test_exact_staging_path_and_scope(self):
        result=patched_main(FIXTURE)
        self.assertIn('P60::ProbeAndStageLibc(',result)
        self.assertIn('p60_libc_stage.emplace(std::move(libc))',result)
        self.assertIn('std::optional<Bachata::Saf::P60::Stage> p60_libc_stage;',result)
        self.assertIn('ebootPath = p59_eboot_stage->path;',result)
        self.assertNotIn('std::move(p54_probe.proc_fd_path)',result)
    def test_repeated_application_rejected(self):
        with self.assertRaisesRegex(ValueError,'ANCHOR'):
            patched_main(patched_main(FIXTURE))
    def test_missing_p59_guard_rejected(self):
        with self.assertRaisesRegex(ValueError,'MISSING'):
            patched_main(FIXTURE.replace('P59::StageAuthenticatedFd(',''))

if __name__=='__main__':
    unittest.main()
