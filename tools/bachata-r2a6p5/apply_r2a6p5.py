#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pin-locked additive Bachata F43DEV host V2 handshake.
Requires R2A2 host gate through R2A6/P2 SAF probe chain already applied.
No APK modification, certificate spoofing, or native-host replacement.
"""
import argparse
import hashlib
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
FILES = ["src/main.cpp", "src/platform/bachata/runtime_client.h",
         "src/platform/bachata/runtime_client.cpp"]
HEADER_NAME = "src/platform/bachata/f43dev_contract_v2.h"

def replace_unique(content, old, new, label):
    count = content.count(old)
    if count != 1:
        raise ValueError(f"{label}: expected exactly 1 source anchor, got {count}")
    return content.replace(old, new, 1)

def apply(root: Path, own: Path):
    root = root.resolve()
    own = own.resolve()
    if not (root / ".git").is_dir():
        raise ValueError("Not a pinned upstream git source")
    rev = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if rev != PIN:
        raise ValueError("Unexpected upstream commit")
    code = {f: (root / f).read_text(encoding="utf-8") for f in FILES}
    m = code["src/main.cpp"]
    for marker in ("BACHATA_F43DEV_R2A2_HOST_GATE_OK",
                   "ValidateContractCli", "bachataContract",
                   "bachata-saf-probe-only",
                   "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED"):
        if marker not in m:
            raise ValueError(f"Prior experimental runtime precondition absent: {marker}")
    if "VerifyPeer" not in m:
        raise ValueError("R2A2 host peer gate missing")
    h = code["src/platform/bachata/runtime_client.h"]
    h = replace_unique(
        h,
        "    bool SendHello(unsigned version = RuntimeProtocolVersion);\n",
        "    bool SendHello(unsigned version = RuntimeProtocolVersion);\n"
        "    // Strict F43DEV host V2 protocol: lowercase 32-hex ephemeral nonce.\n"
        "    bool SendHelloV2(std::string_view contract_nonce);\n",
        "runtime_client.h V2 API")
    code["src/platform/bachata/runtime_client.h"] = h

    cpp = code["src/platform/bachata/runtime_client.cpp"]
    cpp = replace_unique(
        cpp,
        '#include "platform/bachata/runtime_client.h"\n',
        '#include "platform/bachata/runtime_client.h"\n'
        '#include "platform/bachata/f43dev_contract_v2.h"\n',
        "runtime_client.cpp include")
    cpp = replace_unique(
        cpp,
        'bool RuntimeClient::SendStarting() {\n',
        'bool RuntimeClient::SendHelloV2(std::string_view nonce) {\n'
        '    // No secret in logs or diagnostics; return only pass/fail.\n'
        '    const auto frame = ContractV2::BuildHello(nonce);\n'
        '    return frame.has_value() && SendLine(*frame);\n'
        '}\n\n'
        'bool RuntimeClient::SendStarting() {\n',
        "runtime_client.cpp V2 HELLO")
    code["src/platform/bachata/runtime_client.cpp"] = cpp

    # Exact R2A2-authenticated control socket location; never suppress UID gate.
    before = '''        if (!connected.has_value() || !connected->SendHello()) {'''
    after = '''#if defined(__linux__) && defined(__aarch64__)
        if (!connected.has_value() || !bachataContract.has_value() ||
            !connected->SendHelloV2(*bachataContract)) {
#else
        if (!connected.has_value() || !connected->SendHello()) {
#endif'''
    m = replace_unique(m,before,after,"core main post-auth hello")
    m = replace_unique(
        m, '#include "platform/bachata/saf_probe.h"',
        '#include "platform/bachata/saf_probe.h"\n'
        '#include "platform/bachata/f43dev_contract_v2.h"',
        "main include strict contract")
    m = replace_unique(
        m, '    if (!Platform::Bachata::R2A4::ValidateContractCli(',
        '    // Host DEX enforces [0-9a-f]{32}; reject bad nonce before socket I/O.\n'
        '    if (!bachataContract || !Platform::Bachata::ContractV2::ValidNonce(*bachataContract)) {\n'
        '        std::cerr << "F43DEV host V2 contract syntax rejected\\n";\n'
        '        return 1;\n'
        '    }\n'
        '    if (!Platform::Bachata::R2A4::ValidateContractCli(',
        "main early lowercase-hex validation")
    code["src/main.cpp"] = m

    header_path = root / HEADER_NAME
    header_input = own / "f43dev_contract_v2.h"
    if not header_input.is_file() or header_path.exists():
        raise ValueError("Missing V2 header or output already exists")
    header_data = header_input.read_bytes()
    expected = "4770d504b77547323a6ec781a74749f8ff3f04e8"
    actual = hashlib.sha1(b"blob " + str(len(header_data)).encode() + bytes([0]) + header_data).hexdigest()
    if actual != expected:
        raise ValueError("Header Git blob SHA mismatch")
    # Mutate only when every anchor and prerequisite has been validated.
    for name, body in code.items():
        (root / name).write_text(body, encoding="utf-8", newline="")
    header_path.write_bytes(header_data)
    print("R2A6P5_HOST_V2_HELLO_PATCH_APPLIED")
    print("BACHATA_V2_NONCE_LOWERCASE_HEX32_REQUIRED")
    print("R2A2_SAME_UID_PEER_GATE=PRESERVED")
    print("REAL_ANDROID_BROKER=NOT_TESTED")
    print("APK_CREATED=NO")

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("upstream", type=Path)
    p.add_argument("--source-dir", type=Path, default=Path(__file__).resolve().parent)
    a=p.parse_args()
    apply(a.upstream,a.source_dir)
