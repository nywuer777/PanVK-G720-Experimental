"""P59 strict source-anchored patch tests, no game files."""
import unittest
from patch_p59 import patched_main

PREREQ = """BACHATA_F43DEV_R2A2_HOST_GATE_OK
BACHATA_P53_EBOOT_ROOT_UNAVAILABLE
#include "platform/bachata/p54_bsf1_eboot.h"
    std::optional<Bachata::Saf::BSF1::ReadFd> p54_eboot_fd;
            p54_eboot_fd.emplace(std::move(p54_probe.fd));
            ebootPath = std::move(p54_probe.proc_fd_path);
"""

class P59SourceTests(unittest.TestCase):
    def test_replaces_proc_reopen_with_private_staging(self):
        modified=patched_main(PREREQ)
        self.assertIn('BACHATA::SAF::P59',modified.upper())
        self.assertIn('P59::StageAuthenticatedFd(',modified)
        self.assertIn('p59_eboot_stage.emplace(std::move(staged))',modified)
        self.assertIn('ebootPath = p59_eboot_stage->path',modified)
        self.assertNotIn('ebootPath = std::move(p54_probe.proc_fd_path)',modified)
        self.assertIn('p54_eboot_fd.emplace(std::move(p54_probe.fd))',modified)

    def test_duplicate_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"ANCHOR"):
            patched_main(patched_main(PREREQ))

    def test_missing_auth_fd_is_rejected(self):
        with self.assertRaisesRegex(ValueError,"MISSING"):
            patched_main(PREREQ.replace('p54_eboot_fd.emplace(std::move(p54_probe.fd));',''))

if __name__=='__main__':
    unittest.main()
