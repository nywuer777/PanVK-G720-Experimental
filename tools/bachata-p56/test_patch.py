"""P56 regression: patch original public source in memory; no private APK/ELF."""
from pathlib import Path
import unittest
from patch_p56 import patch

ROOT=Path(__file__).resolve().parents[2]
FILES=[
    ROOT/"tools/bachata-r2a5/saf_bsf1_client.h",
    ROOT/"tools/bachata-r2a5/saf_bsf1_client.cpp",
    ROOT/"tools/bachata-p54/p54_bsf1_eboot.h",
]

class P56PatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs=[p.read_text(encoding="utf-8") for p in FILES]

    def test_public_source_accepts_checked_patch(self):
        header,cpp,bridge=patch(*self.inputs)
        self.assertIn("HeaderClosed",header)
        self.assertIn("PayloadAncillary",header)
        self.assertIn("HeaderBadMagic",cpp)
        self.assertIn("HeaderBadVersion",cpp)
        self.assertIn("Error::PayloadClosed",cpp)
        self.assertIn("BACHATA_P56_BSF1_HEADER_CLOSED",bridge)
        self.assertIn("BACHATA_P56_BSF1_HEADER_BAD_MAGIC",bridge)
        self.assertIn("BACHATA_P56_BSF1_PAYLOAD_CLOSED",bridge)
        self.assertIn('broker.OpenRead("eboot.bin")',bridge)
        self.assertIn("Outcome::EbootFdReady",bridge)

    def test_double_patch_rejected(self):
        first=patch(*self.inputs)
        with self.assertRaisesRegex(ValueError,"anchor"):
            patch(*first)

    def test_broker_magic_and_version_unchanged(self):
        before=self.inputs[1]
        after=patch(*self.inputs)[1]
        for marker in (
            "constexpr uint8_t Version = 1;",
            "constexpr std::array<uint8_t, 4> Magic{'B', 'S', 'F', '1'};",
            "packet.push_back(Version);",
            "packet.push_back(opcode);",
            "AppendBe32(packet, static_cast<uint32_t>(config_.token.size()));",
            "AppendBe32(packet, static_cast<uint32_t>(path.size()));",
            "SameUidPeer(sock.get())",
            "reply.fd = std::move(recv_fd);",
        ):
            self.assertIn(marker,before)
            self.assertIn(marker,after)

    def test_missing_anchor_refused(self):
        bad=self.inputs[1].replace("RecvAllWithFd(", "ReadSilently(",1)
        with self.assertRaisesRegex(ValueError,"anchor"):
            patch(self.inputs[0],bad,self.inputs[2])

    def test_original_header_not_rewritten(self):
        header=patch(*self.inputs)[0]
        self.assertIn("RemoteError",header)
        self.assertIn("InvalidFrame",header)
        self.assertIn("MissingFd",header)
        self.assertIn("UnexpectedFd",header)

if __name__=="__main__":
    unittest.main()
