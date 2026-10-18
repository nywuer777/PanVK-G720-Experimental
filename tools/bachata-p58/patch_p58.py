#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P58: align public BSF1 request with Android's actual broker wire format.

Evidence: original P42 classes.dex LocalServerSocket handler uses
DataInputStream.readInt/readUnsignedByte/readUnsignedByte/
readUnsignedShort/readInt/readFully(token)/readFully(path).
Independent original P42 native AArch64 client emits a 2-byte BE token
length and 4-byte BE path length BEFORE either byte sequence.

Never changes uid/token checks, socket flags, FD validation or P42.
Apply AFTER pinned P49+P53+P54+P56+P57 source combination.
"""
from pathlib import Path
import argparse
import subprocess

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"

def one(source: str, before: str, after: str, label: str) -> str:
    matches = source.count(before)
    if matches != 1:
        raise ValueError(f"{label}: expected 1 source anchor; got {matches}")
    return source.replace(before, after, 1)

def patch(client: str, bridge: str) -> tuple[str, str]:
    client = one(
        client,
        """void AppendBe32(std::vector<uint8_t>& data, uint32_t value) {""",
        """void AppendBe16(std::vector<uint8_t>& data, uint16_t value) {
    data.push_back(static_cast<uint8_t>(value >> 8));
    data.push_back(static_cast<uint8_t>(value));
}
void AppendBe32(std::vector<uint8_t>& data, uint32_t value) {""",
        "Big-endian 16-bit length serializer")
    old = """    packet.reserve(14 + config_.token.size() + path.size());
    packet.insert(packet.end(), Magic.begin(), Magic.end());
    packet.push_back(Version);
    packet.push_back(opcode);
    AppendBe32(packet, static_cast<uint32_t>(config_.token.size()));
    packet.insert(packet.end(), config_.token.begin(), config_.token.end());
    AppendBe32(packet, static_cast<uint32_t>(path.size()));
    packet.insert(packet.end(), path.begin(), path.end());"""
    new = """    // P58: match the actual Android server DataInputStream contract:
    // BE32('BSF1'), U8(version), U8(opcode), BE16(token_len),
    // BE32(path_len), token UTF-8 bytes, then path UTF-8 bytes.
    // This is 12+token_len+path_len bytes, not the legacy 14+ layout.
    // Critical: length fields MUST both precede the two payload strings.
    packet.reserve(12 + config_.token.size() + path.size());
    packet.insert(packet.end(), Magic.begin(), Magic.end());
    packet.push_back(Version);
    packet.push_back(opcode);
    AppendBe16(packet, static_cast<uint16_t>(config_.token.size()));
    AppendBe32(packet, static_cast<uint32_t>(path.size()));
    packet.insert(packet.end(), config_.token.begin(), config_.token.end());
    packet.insert(packet.end(), path.begin(), path.end());"""
    client = one(client, old, new, "BSF1 request frame shape")
    if "SameUidPeer(sock.get())" not in client or "MSG_CMSG_CLOEXEC" not in client:
        raise ValueError("P57 trust/FD protection guard missing")
    if "if (!ValidateConfig(config_))" not in client or "if (!ValidatePath(path))" not in client:
        raise ValueError("P57 safe request validation missing")
    if "BACHATA_P57_BSF1_HEADER_PEER_RESET" not in bridge:
        raise ValueError("P57 broker error diagnostics missing")
    bridge = one(bridge, "#include <filesystem>", "#include <filesystem>\n#include <iostream>",
                 "Header self-contained logging include")
    bridge = one(
        bridge,
        """    auto supplied = broker.OpenRead("eboot.bin");""",
        """    // P58 reports source-selected wire format only; not broker acceptance.
    // This fixed marker contains no game file, token, path or socket.
    std::cerr << "BACHATA_P58_BSF1_REQUEST_ANDROID_WIRE_BE16_BE32" << '\\n';
    auto supplied = broker.OpenRead("eboot.bin");""",
        "P54 broker first-entry hook")
    return client, bridge

def run(source_root: Path) -> None:
    root = source_root.resolve()
    if not (root / ".git").is_dir():
        raise ValueError("Pinned upstream git checkout required")
    revision = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if revision != PIN:
        raise ValueError("Pinned source revision mismatch")
    paths = [
        root / "src/platform/bachata/saf_bsf1_client.cpp",
        root / "src/platform/bachata/p54_bsf1_eboot.h",
    ]
    if any(not file.is_file() for file in paths):
        raise ValueError("P57 integrated sources missing")
    client, bridge = patch(*(file.read_text(encoding="utf-8") for file in paths))
    for file, contents in zip(paths, (client, bridge)):
        file.write_text(contents, encoding="utf-8", newline="")
    subprocess.run(["git", "-C", str(root), "diff", "--check"], check=True)
    print("P58_BSF1_ACTUAL_ANDROID_REQUEST_FORMAT_APPLIED")
    print("P58_SAME_UID_AND_SESSION_TOKEN_CHECKS=UNCHANGED")
    print("P58_FD_AND_RECVMSG_FLAGS=UNCHANGED")
    print("P58_P42_PRIVATE_APK=UNMODIFIED")
    print("P58_REAL_ANDROID_GAME_BOOT=NOT_VERIFIED")

if __name__ == "__main__":
    cli = argparse.ArgumentParser()
    cli.add_argument("--source-root", type=Path, required=True)
    a = cli.parse_args()
    run(a.source_root)
