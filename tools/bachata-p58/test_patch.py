"""P58 source-only regression for exact Android request ABI, no private APK."""
import sys
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
for folder in ('tools/bachata-p56','tools/bachata-p57'):
    sys.path.insert(0,str(ROOT/folder))
from patch_p56 import patch as p56
from patch_p57 import patch as p57
from patch_p58 import patch as p58

class FrameTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        source=[
            ROOT/'tools/bachata-r2a5/saf_bsf1_client.h',
            ROOT/'tools/bachata-r2a5/saf_bsf1_client.cpp',
            ROOT/'tools/bachata-p54/p54_bsf1_eboot.h'
        ]
        cls.h,cls.old_client,cls.old_bridge=p57(*p56(*(p.read_text() for p in source)))
        cls.client,cls.bridge=p58(cls.old_client,cls.old_bridge)

    def test_legacy_frame_removed(self):
        self.assertNotIn('AppendBe32(packet, static_cast<uint32_t>(config_.token.size()))',self.client)
        self.assertIn('AppendBe16(packet, static_cast<uint16_t>(config_.token.size()))',self.client)
        self.assertIn('packet.reserve(12 + config_.token.size() + path.size())',self.client)
        self.assertNotIn('packet.reserve(14 + config_.token.size() + path.size())',self.client)

    def test_lengths_before_binary_strings(self):
        c=self.client
        order=[
            'packet.insert(packet.end(), Magic.begin(), Magic.end());',
            'packet.push_back(Version);',
            'packet.push_back(opcode);',
            'AppendBe16(packet, static_cast<uint16_t>(config_.token.size()));',
            'AppendBe32(packet, static_cast<uint32_t>(path.size()));',
            'packet.insert(packet.end(), config_.token.begin(), config_.token.end());',
            'packet.insert(packet.end(), path.begin(), path.end());',
        ]
        positions=[c.index(line) for line in order]
        self.assertEqual(positions,sorted(positions))

    def test_defensive_controls_unchanged(self):
        for required in (
            'SameUidPeer(sock.get())',
            'if (!ValidateConfig(config_))',
            'if (!ValidatePath(path))',
            'MSG_CMSG_CLOEXEC',
            'const int flags = ::fcntl(reply.fd.get(), F_GETFL);',
            'S_ISREG(st.st_mode)',
            'O_RDONLY',
        ):
            self.assertIn(required,self.client)
        self.assertIn('broker.OpenRead("eboot.bin")',self.bridge)

    def test_marker_privacy(self):
        self.assertIn('BACHATA_P58_BSF1_REQUEST_ANDROID_WIRE_BE16_BE32',self.bridge)
        self.assertNotIn('std::cerr << config_',self.bridge)

    def test_double_patch_refused(self):
        with self.assertRaisesRegex(ValueError,'anchor'):
            p58(self.client,self.bridge)

    def test_missing_trust_gate_refused(self):
        with self.assertRaisesRegex(ValueError,'trust'):
            p58(self.old_client.replace('SameUidPeer(sock.get())','true'),self.old_bridge)

    def test_golden_bytes(self):
        import struct
        token=b'a'*32;path=b'eboot.bin'
        frame=b'BSF1'+bytes((1,3))+struct.pack('>H',len(token))+struct.pack('>I',len(path))+token+path
        self.assertEqual(len(frame),53)
        self.assertEqual(frame[:12],bytes.fromhex('425346310103002000000009'))
        self.assertEqual(frame[12:44],token)
        self.assertEqual(frame[44:],path)

if __name__=='__main__':
    unittest.main()
