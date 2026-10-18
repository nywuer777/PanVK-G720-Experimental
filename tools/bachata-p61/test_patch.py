"""P61 source anchor tests: preserve all P60 hooks, never synthesize PSF."""
import unittest
from patch_p61 import patched_main
P60='''BACHATA_P53_EBOOT_ROOT_UNAVAILABLE
#include "platform/bachata/p60_saf_libc_stage.h"
    std::optional<Bachata::Saf::P60::Stage> p60_libc_stage;
P60::ProbeAndStageLibc(
p60_libc_stage.emplace(std::move(libc))
                if (libc) p60_libc_stage.emplace(std::move(libc));
'''
class Tests(unittest.TestCase):
    def test_stage_and_error_report(self):
        t=patched_main(P60)
        self.assertIn('P61::ProbeAndStageParamSfo(',t)
        self.assertIn('Bachata::Saf::P61::Marker(psf.status)',t)
        self.assertIn('CONTENT_METADATA_UNAVAILABLE',t)
        self.assertIn('p61_psf_stage.emplace(std::move(psf));',t)
        self.assertNotIn('std::move(p54_probe.proc_fd_path)',t)
    def test_repatch_fails(self):
        with self.assertRaisesRegex(ValueError,'MISSING|ANCHOR'):
            patched_main(patched_main(P60))
    def test_p60_guard(self):
        with self.assertRaisesRegex(ValueError,'MISSING'):
            patched_main(P60.replace('P60::ProbeAndStageLibc(', ''))
if __name__=='__main__':
    unittest.main()
