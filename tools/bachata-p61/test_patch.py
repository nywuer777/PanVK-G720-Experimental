"""P61 strict integration anchors; source-independent tests only."""
import unittest
from patch_p61 import patched_main
FIXTURE = '''BACHATA_P53_EBOOT_ROOT_UNAVAILABLE
#include "platform/bachata/p60_saf_libc_stage.h"
    std::optional<Bachata::Saf::P60::Stage> p60_libc_stage;
P60::ProbeAndStageLibc(
                if (libc) p60_libc_stage.emplace(std::move(libc));
'''
class Tests(unittest.TestCase):
    def test_integration(self):
        out=patched_main(FIXTURE)
        for fragment in ('P61::ProbeAndStageParamSfo(', 'CONTENT_METADATA_UNAVAILABLE',
                         'p61_psf_stage.emplace(std::move(psf));',
                         'std::optional<Bachata::Saf::P61::Stage> p61_psf_stage;'):
            self.assertIn(fragment,out)
    def test_repeat_rejected(self):
        with self.assertRaisesRegex(ValueError,'ANCHOR'):
            patched_main(patched_main(FIXTURE))
    def test_requires_p60(self):
        with self.assertRaisesRegex(ValueError,'MISSING'):
            patched_main(FIXTURE.replace('#include "platform/bachata/p60_saf_libc_stage.h"',''))
if __name__=='__main__':unittest.main()
