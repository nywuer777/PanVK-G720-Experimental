#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P59: replace non-reopenable /proc/self/fd/N ELF loader path with a bounded
private 0600 temporary file copied directly via pread(authenticated fd).

Apply only after pinned P49->P53->P54->P56->P57->P58 integration.
"""
import argparse
import subprocess
from pathlib import Path
PIN="be6bc2e9c60799e071dd2fafa6216e8d80ec619c"

def one(s,a,b,reason):
    count=s.count(a)
    if count!=1:raise ValueError(f"P59_{reason}_ANCHOR_EXPECTED_1_GOT_{count}")
    return s.replace(a,b,1)

def patched_main(main):
    guards=("BACHATA_F43DEV_R2A2_HOST_GATE_OK",
            "BACHATA_P53_EBOOT_ROOT_UNAVAILABLE",
            "p54_eboot_fd.emplace(std::move(p54_probe.fd));",
            "BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY")
    # The final gate is in p54 header, checked separately, not in main.
    for label in guards[:-1]:
        if label not in main:raise ValueError(f"P59_MISSING_{label}")
    main=one(main,
        '#include "platform/bachata/p54_bsf1_eboot.h"',
        '#include "platform/bachata/p54_bsf1_eboot.h"\n#include "platform/bachata/p59_private_stage.h"',
        "HEADER")
    main=one(main,
        '    std::optional<Bachata::Saf::BSF1::ReadFd> p54_eboot_fd;',
        '''    std::optional<Bachata::Saf::BSF1::ReadFd> p54_eboot_fd;
    // Must outlive Core::Loader::Elf and Emulator::Run. The 0600 copy
    // is removed on normal return, but not on abrupt process death.
    std::optional<Bachata::Saf::P59::PrivateStage> p59_eboot_stage;''',
        "STATE")
    main=one(main,
        '''            p54_eboot_fd.emplace(std::move(p54_probe.fd));
            ebootPath = std::move(p54_probe.proc_fd_path);''',
        '''            p54_eboot_fd.emplace(std::move(p54_probe.fd));
            auto staged = Bachata::Saf::P59::StageAuthenticatedFd(
                p54_eboot_fd->get(), *overrideRoot);
            std::cerr << Bachata::Saf::P59::Marker(staged.status) << '\\n';
            if (staged) {
                p59_eboot_stage.emplace(std::move(staged));
                ebootPath = p59_eboot_stage->path;
            }''',
        "EARLY_LOADER")
    if 'ebootPath = std::move(p54_probe.proc_fd_path)' in main:
        raise ValueError("P59_PROC_REOPEN_PATH_STILL_ACTIVE")
    return main

def apply(root,header):
    root=root.resolve()
    if not (root/'.git').is_dir():raise ValueError("P59_PINNED_GIT_CHECKOUT_REQUIRED")
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],
                                text=True).strip()
    if rev!=PIN:raise ValueError("P59_PIN_MISMATCH")
    main_file=root/'src/main.cpp'
    target=root/'src/platform/bachata/p59_private_stage.h'
    prev=root/'src/platform/bachata/p54_bsf1_eboot.h'
    if target.exists() or not header.is_file() or not prev.is_file():
        raise ValueError("P59_STAGE_PRECONDITIONS_MISSING")
    if 'BACHATA_P58_BSF1_REQUEST_ANDROID_WIRE_BE16_BE32' not in prev.read_text():
        raise ValueError("P59_P58_WIRE_FIX_MISSING")
    modified=patched_main(main_file.read_text())
    if 'BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY' not in prev.read_text():
        raise ValueError("P59_P54_AUTHENTICATED_FD_MISSING")
    main_file.write_text(modified,encoding='utf8',newline='')
    target.write_bytes(header.read_bytes())
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("P59_PRIVATE_STAGE_FROM_AUTHENTICATED_FD_APPLIED")
    print("P59_REOPEN_PROC_SELF_FD=DISABLED_FOR_INITIAL_EBOOT")
    print("P59_0600_OWNED_PRIVATE_ROOT_BOUNDED_RAII=ENABLED")
    print("P59_GAME_APP0_VFS=NOT_IMPLEMENTED")
    print("P59_ANDROID_DEVICE_EXECUTION=NOT_TESTED")

if __name__=='__main__':
    cli=argparse.ArgumentParser()
    cli.add_argument('--source-root',type=Path,required=True)
    cli.add_argument('--header',type=Path,required=True)
    args=cli.parse_args()
    apply(args.source_root,args.header)
