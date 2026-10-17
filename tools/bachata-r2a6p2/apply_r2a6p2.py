#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Source-pinned R2A.6/P2 opt-in broker probe, independent of VFS lab mode."""
import argparse
import subprocess
from pathlib import Path

PIN="be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
COPIES={"saf_probe.h":"src/platform/bachata/saf_probe.h",
        "saf_probe.cpp":"src/platform/bachata/saf_probe.cpp"}

def one(haystack,needle,replacement,label):
    n=haystack.count(needle)
    if n!=1:
        raise ValueError(f"{label}: expected unique source anchor, got {n}")
    return haystack.replace(needle,replacement,1)

def apply(root,own):
    root,own=root.resolve(),own.resolve()
    if not (root/".git").is_dir():raise ValueError("Not a git checkout")
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if rev!=PIN:raise ValueError("Unpinned upstream revision")
    paths=["CMakeLists.txt","src/main.cpp",
           "src/platform/bachata/saf_cli_contract.h"]
    data={p:(root/p).read_text() for p in paths}
    main=data["src/main.cpp"]
    for marker in ("BACHATA_F43DEV_R2A2_HOST_GATE_OK",
                   "BACHATA_F43DEV_R2A6P1_LAB_VFS_OPTIN_REAL_BROKER_UNVERIFIED",
                   "BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED"):
        if marker not in main:raise ValueError("Missing R2A6P1 prerequisite "+marker)
    data["CMakeLists.txt"]=one(data["CMakeLists.txt"],
        "        src/platform/bachata/saf_guest_mount.h\n",
        "        src/platform/bachata/saf_guest_mount.h\n"
        "        src/platform/bachata/saf_probe.cpp\n"
        "        src/platform/bachata/saf_probe.h\n","CMake")

    cli=data["src/platform/bachata/saf_cli_contract.h"]
    cli=one(cli,
        'constexpr std::string_view VfsRootFlag = "--bachata-saf-vfs-root";',
        'constexpr std::string_view VfsRootFlag = "--bachata-saf-vfs-root";\n'
        'constexpr std::string_view ProbePathFlag = "--bachata-saf-probe-path";',
        "redaction flag")
    cli=one(cli,"value == VfsRootFlag;","value == VfsRootFlag || value == ProbePathFlag;",
            "redaction separate value")
    cli=one(cli,
        "for (const auto flag : {ContractFlag, SocketFlag, TokenFlag, VfsRootFlag}) {",
        "for (const auto flag : {ContractFlag, SocketFlag, TokenFlag, VfsRootFlag, ProbePathFlag}) {",
        "redaction assigned value")
    data["src/platform/bachata/saf_cli_contract.h"]=cli

    main=one(main,
        '#include "platform/bachata/saf_vfs_readonly.h"',
        '#include "platform/bachata/saf_vfs_readonly.h"\n'
        '#include "platform/bachata/saf_probe.h"',"include")
    main=one(main,
        '    bool bachataSafVfsLab = false;\n#endif',
        '    bool bachataSafVfsLab = false;\n'
        '    bool bachataSafProbeOnly = false;\n'
        '    std::optional<std::string> bachataSafProbePath;\n#endif',"variables")
    main=one(main,
        '    app.add_flag("--bachata-saf-vfs-lab", bachataSafVfsLab,\n'
        '                 "Enable read-only BSF1 /app0 mount for controlled laboratory tests");',
        '    app.add_flag("--bachata-saf-vfs-lab", bachataSafVfsLab,\n'
        '                 "Enable read-only BSF1 /app0 mount for controlled laboratory tests");\n'
        '    app.add_flag("--bachata-saf-probe-only", bachataSafProbeOnly,\n'
        '                 "Check broker metadata and FD without starting game or GPU");\n'
        '    app.add_option("--bachata-saf-probe-path", bachataSafProbePath,\n'
        '                   "Explicit non-sensitive broker-relative test fixture");',"options")
    check_before = """    if (bachataSafVfsLab && (!bachataSafVfsRoot.has_value() ||
                              !Bachata::Saf::Vfs::ReadOnlyMount::ValidRoot(*bachataSafVfsRoot))) {
        std::cerr << "Invalid/missing broker-relative laboratory root\\n";
        return 1;
    }"""
    check_after = check_before + """
    if (bachataSafProbeOnly && (bachataSafVfsLab ||
        !bachataSafProbePath.has_value() ||
        !Bachata::Saf::BSF1::Client::ValidatePath(*bachataSafProbePath))) {
        std::cerr << "SAF probe path invalid or incompatible with VFS lab mode\\n";
        return 1;
    }
    if (!bachataSafProbeOnly && bachataSafProbePath.has_value()) {
        std::cerr << "SAF probe path requires explicit probe-only mode\\n";
        return 1;
    }"""
    main=one(main,check_before,check_after,"flags validity")
    after_hello = """        // Enable mount only after R2A2 app-path and same-UID host handshake pass.
        if (bachataSafVfsLab &&
            !Bachata::Saf::Guest::EnableExperimental(saf_config, *bachataSafVfsRoot)) {
            std::cerr << "SAF laboratory mount activation rejected\\n";
            return 1;
        }
#endif"""
    after_probe = """        // Enable mount only after R2A2 app-path and same-UID host handshake pass.
        if (bachataSafVfsLab &&
            !Bachata::Saf::Guest::EnableExperimental(saf_config, *bachataSafVfsRoot)) {
            std::cerr << "SAF laboratory mount activation rejected\\n";
            return 1;
        }
        if (bachataSafProbeOnly) {
            // Probe AFTER same-UID host handshake. No eboot loader, SDL or Vulkan.
            Bachata::Saf::BSF1::Client diagnostic_broker(saf_config);
            const auto status = Bachata::Saf::Probe::Run(
                diagnostic_broker, *bachataSafProbePath);
            std::cerr << Bachata::Saf::Probe::SafeDiagnostic(status.outcome) << '\\n';
            if (!status.passed())
                runtime_client.SendError("SAF_PROBE_FAILED");
            runtime_client.SendStopped(status.passed() ? 0 : 1);
            return status.passed() ? 0 : 1;
        }
#endif"""
    main=one(main,after_hello,after_probe,"authenticated probe")
    data["src/main.cpp"]=main
    for source,target in COPIES.items():
        if not (own/source).is_file() or (root/target).exists():
            raise ValueError("Probe source missing or output already exists")
    for p,body in data.items():
        (root/p).write_text(body,encoding="utf-8",newline="")
    for source,target in COPIES.items():
        (root/target).write_bytes((own/source).read_bytes())
    print("R2A6P2_PROBE_PATCH_APPLIED")
    print("SAFE_PROBE=OPT_IN_ONLY_NO_CONTENT_READ")
    print("ANDROID_REAL_BROKER=NOT_TESTED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("upstream",type=Path)
    p.add_argument("--source-dir",type=Path,default=Path(__file__).resolve().parent)
    a=p.parse_args()
    apply(a.upstream,a.source_dir)
