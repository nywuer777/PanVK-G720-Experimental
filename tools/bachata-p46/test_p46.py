import struct
import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from p46_private_glibc_gate import inspect_elf, audit, InvalidELF

def fake_elf(text=b'\x00'*64, rodata=b'--bachata-contract\x00GPU BCn fallback admitted\x00GPU BCn decoded image requires a matching sampled BC view\x00bachata-s4\x00', machine=183):
    buf=bytearray(0xc00)
    interp=b'/lib/ld-linux-aarch64.so.1\x00'
    buf[0x200:0x200+len(interp)]=interp
    buf[0x400:0x400+len(text)] = text
    buf[0x500:0x500+len(rodata)] = rodata
    note=struct.pack('<III', 4, 20, 3)+b'GNU\x00'+b'\x01'*20
    buf[0x800:0x800+len(note)] = note
    names=b'\x00.text\x00.rodata\x00.note.gnu.build-id\x00.shstrtab\x00'
    buf[0x900:0x900+len(names)] = names
    hdr=struct.pack('<16sHHIQQQIHHHHHH',b'\x7fELF\x02\x01\x01'+b'\x00'*9,3,machine,1,0,0x40,0xa00,0,64,56,1,64,5,4)
    buf[:len(hdr)] = hdr
    ph=struct.pack('<IIQQQQQQ',3,4,0x200,0,0,len(interp),len(interp),1)
    buf[0x40:0x40+len(ph)] = ph
    idx={'':0,'.text':1,'.rodata':7,'.note.gnu.build-id':15,'.shstrtab':34}
    entries=[(0,0,0,0,0,0,0,0,0,0),(idx['.text'],1,6,0,0x400,len(text),0,0,4,0),(idx['.rodata'],1,2,0,0x500,len(rodata),0,0,1,0),(idx['.note.gnu.build-id'],7,2,0,0x800,len(note),0,0,4,0),(idx['.shstrtab'],3,0,0,0x900,len(names),0,0,1,0)]
    for i, tup in enumerate(entries):
        sh=struct.pack('<IIQQQQIIQQ',*tup)
        buf[0xa00+i*64:0xa00+(i+1)*64]=sh
    return bytes(buf)

class HostIdentity(unittest.TestCase):
    def setUp(self):
        self.baseline=fake_elf()
    def test_known_f43dev_baseline_rejected_as_fix(self):
        self.assertEqual(audit(self.baseline,self.baseline)['verdict'],'REJECT_BCN_FIX_NOT_IN_PRIVATE_EXECUTABLE_CODE')
    def test_new_text_not_automatically_approved(self):
        changed=fake_elf(text=b'\x10'+b'\0'*63)
        self.assertEqual(audit(changed,self.baseline)['verdict'],'BLOCK_PRIVATE_BCN_INTEGRATION_UNPROVEN')
    def test_marker_in_rodata_not_proof(self):
        changed=fake_elf(text=b'\x10'+b'\0'*63,rodata=b'--bachata-contract\0GPU BCn fallback admitted\0P45_BCN_PER_LAYER_VIEW_PROOF')
        report=audit(changed,self.baseline)
        self.assertTrue(report['candidate']['p45_marker_in_rodata'])
        self.assertFalse(report['outlast_fixed'])
    def test_shared_path_not_private_identity(self):
        changed=fake_elf(rodata=b'bachata-s4\0GPU BCn fallback admitted')
        self.assertEqual(audit(changed,self.baseline)['verdict'],'REJECT_PUBLIC_OR_INCOMPATIBLE_HOST')
    def test_fex_contract_without_fallback_not_enough(self):
        changed=fake_elf(rodata=b'--bachata-contract\0bachata-s4')
        self.assertEqual(audit(changed,self.baseline)['verdict'],'REJECT_PUBLIC_OR_INCOMPATIBLE_HOST')
    def test_marker_only_in_text_rejected(self):
        changed=fake_elf(text=b'--bachata-contract\0GPU BCn fallback admitted')
        self.assertEqual(audit(changed,self.baseline)['verdict'],'BLOCK_PRIVATE_BCN_INTEGRATION_UNPROVEN')
    def test_bad_architecture(self):
        with self.assertRaises(InvalidELF): inspect_elf(fake_elf(machine=62))
    def test_not_elf(self):
        with self.assertRaises(InvalidELF): inspect_elf(b'NOT_ELF')
    def test_missing_section_outside_range(self):
        broken=bytearray(self.baseline)
        struct.pack_into('<Q',broken,0xa00+64+24,0xf000000)
        with self.assertRaises(InvalidELF): inspect_elf(bytes(broken))
    def test_wrong_interpreter(self):
        broken=bytearray(self.baseline)
        broken[0x200:0x200+len(b'/lib/ld-linux-aarch64.so.1')]=b'/bin/no-ld-linux-aarch64.so'
        with self.assertRaises(InvalidELF): inspect_elf(bytes(broken))
    def test_both_markers_in_public_code_text_not_sufficient(self):
        wrong=fake_elf(text=b'P45_BCN_PER_LAYER_VIEW_PROOF',rodata=b'bachata-s4\0')
        self.assertEqual(audit(wrong,self.baseline)['verdict'],'REJECT_PUBLIC_OR_INCOMPATIBLE_HOST')
    def test_invalid_baseline_rejected(self):
        with self.assertRaises(InvalidELF): audit(self.baseline,fake_elf(rodata=b'bachata-s4'))

if __name__ == '__main__':
    unittest.main()