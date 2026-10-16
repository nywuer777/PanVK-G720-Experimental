#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""R2A.4 P0 -- pinned additive SAF CLI contract support on R2A+R2A2 host-gated core."""
import argparse
import shutil
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"

PATCHES = [
    (
        '#include "platform/bachata/runtime_client.h"\n',
        '#include "platform/bachata/runtime_client.h"\n'
        '#include "platform/bachata/saf_cli_contract.h"\n',
    ),
    (
        '    std::optional<std::filesystem::path> patchSessionPath;\n#endif',
        '    std::optional<std::filesystem::path> patchSessionPath;\n'
        '    std::optional<std::string> bachataContract;\n'
        '    std::optional<std::string> bachataSafSocket;\n'
        '    std::optional<std::string> bachataSafToken;\n#endif',
    ),
    (
        '    app.add_option("--patch-session", patchSessionPath,\n'
        '                   "Managed patch launch session file (frozen snapshot staged by Android)");\n#endif',
        '    app.add_option("--patch-session", patchSessionPath,\n'
        '                   "Managed patch launch session file (frozen snapshot staged by Android)");\n'
        '    app.add_option("--bachata-contract", bachataContract,\n'
        '                   "Bachata managed session contract nonce (32 hex characters)");\n'
        '    app.add_option("--bachata-saf-socket", bachataSafSocket,\n'
        '                   "Android SAF broker abstract socket name");\n'
        '    app.add_option("--bachata-saf-token", bachataSafToken,\n'
        '                   "Android SAF broker session token (sensitive)");\n#endif',
    ),
    (
        '    auto runtime_client = Platform::Bachata::RuntimeClient::Disabled();\n'
        '#if defined(__linux__) && defined(__aarch64__)',
        '    auto runtime_client = Platform::Bachata::RuntimeClient::Disabled();\n'
        '#if defined(__linux__) && defined(__aarch64__)\n'
        '    // SAF transport is NOT yet implemented: only parse and validate launch syntax.\n'
        '    if (!Platform::Bachata::R2A4::ValidateContractCli(\n'
        '            bachataContract, bachataSafSocket, bachataSafToken)) {\n'
        '        std::cerr << "Bachata contract/SAF launch arguments missing or invalid\\n";\n'
        '        return 1;\n'
        '    }\n'
        '    std::cerr << "BACHATA_F43DEV_R2A4_CLI_SHAPE_OK_SAF_IO_UNIMPLEMENTED\\n";',
    ),
    (
        '    LOG_INFO(Debug, "Run: {}", std::span(argv, argc));',
        '#ifdef ENABLE_BACHATA_RUNTIME\n'
        '    // Never persist managed contract nonces, broker names or session tokens.\n'
        '    const auto safe_argv = Platform::Bachata::R2A4::RedactArgv(argc, argv);\n'
        '    LOG_INFO(Debug, "Run: {}", std::span(safe_argv));\n'
        '#else\n'
        '    LOG_INFO(Debug, "Run: {}", std::span(argv, argc));\n'
        '#endif',
    ),
]


def transform(source):
    for old, new in PATCHES:
        matches = source.count(old)
        if matches != 1:
            raise ValueError(f"Source anchor mismatch {matches}: {old[:65]!r}")
        source = source.replace(old, new, 1)
    return source


def apply(root: Path, header: Path):
    root = root.resolve()
    if not (root / ".git").exists():
        raise ValueError("Not a git checkout")
    sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if sha != PIN:
        raise ValueError(f"Unexpected upstream revision {sha}")
    main = root / "src/main.cpp"
    original = main.read_text(encoding="utf-8")
    if 'BACHATA_F43DEV_R2A2_HOST_GATE_OK' not in original:
        raise ValueError("Missing R2A2 host identity gate")
    if 'image.binding.has_storage' not in (
        root / "src/video_core/renderer_vulkan/vk_rasterizer.cpp"
    ).read_text():
        raise ValueError("Missing R2A mixed access fix")
    dest = root / "src/platform/bachata/saf_cli_contract.h"
    if dest.exists() or not header.is_file():
        raise ValueError("R2A4 header exists or supplied header absent")
    new_main = transform(original)
    # Do not write anything before every preflight requirement passed.
    main.write_text(new_main, encoding="utf-8", newline="")
    shutil.copyfile(header, dest)
    print("R2A4_CLI_PATCH_APPLIED")
    print("SAF_IO_STATUS=UNIMPLEMENTED")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--header", type=Path, default=Path(__file__).with_name("saf_cli_contract.h"))
    args = parser.parse_args()
    apply(args.source, args.header)
