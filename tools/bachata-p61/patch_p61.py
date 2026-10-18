#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P61 metadata SAF preflight; apply after P60 on pinned shadps4 source."""
import argparse
import subprocess
from pathlib import Path
PIN='be6bc2e9c60799e071dd2fafa6216e8d80ec619c'

def one(source,old,new,label):
    n=source.count(old)
    if n!=1: raise ValueError(f'P61_{label}_EXPECTED_1_ANCHOR_GOT_{n}')
    return source.replace(old,new,1)

def patched_main(main):
    for guard in ('BACHATA_P53_EBOOT_ROOT_UNAVAILABLE',
                  '#include "platform/bachata/p60_saf_libc_stage.h"',
                  'P60::ProbeAndStageLibc(', 'p60_libc_stage.emplace(std::move(libc))'):
        if guard not in main: raise ValueError(f'P61_MISSING_{guard}')
    if '#include "platform/bachata/p61_saf_psf_stage.h"' in main:
        raise ValueError('P61_HEADER_ALREADY_APPLIED_ANCHOR')
    main=one(main,'#include "platform/bachata/p60_saf_libc_stage.h"',
             '#include "platform/bachata/p60_saf_libc_stage.h"\n'
             '#include "platform/bachata/p61_saf_psf_stage.h"','HEADER')
    main=one(main,'    std::optional<Bachata::Saf::P60::Stage> p60_libc_stage;',
             '    std::optional<Bachata::Saf::P60::Stage> p60_libc_stage;\n'
             '    std::optional<Bachata::Saf::P61::Stage> p61_psf_stage;','STATE')
    main=one(main,'                if (libc) p60_libc_stage.emplace(std::move(libc));',
'''                if (libc) p60_libc_stage.emplace(std::move(libc));
                // Upstream Emulator::Run reads /app0/sce_sys/param.sfo
                // before game initialization. Never invent TITLE_ID.
                auto psf = Bachata::Saf::P61::ProbeAndStageParamSfo(
                    saf_broker, *overrideRoot);
                std::cerr << Bachata::Saf::P61::Marker(psf.status) << '\\n';
                if (!psf) {
                    runtime_client.SendError("CONTENT_METADATA_UNAVAILABLE");
                    runtime_client.SendStopped(1);
                    return 1;
                }
                p61_psf_stage.emplace(std::move(psf));''','PSF_STAGE_HOOK')
    if 'std::move(p54_probe.proc_fd_path)' in main:
        raise ValueError('P61_PROCFS_REOPEN_REGRESSION')
    return main

def apply(root,header):
    root=root.resolve()
    if not (root/'.git').is_dir():raise ValueError('P61_PINNED_GIT_CHECKOUT_REQUIRED')
    sha=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip()
    if sha!=PIN:raise ValueError('P61_SOURCE_PIN_CHANGED')
    p=root/'src/main.cpp'
    target=root/'src/platform/bachata/p61_saf_psf_stage.h'
    if not p.is_file() or not (root/'src/platform/bachata/p60_saf_libc_stage.h').is_file() \
       or target.exists() or not header.is_file():
        raise ValueError('P61_MISSING_P60_PREREQUISITES')
    p.write_text(patched_main(p.read_text()),encoding='utf-8',newline='')
    target.write_bytes(header.read_bytes())
    subprocess.run(['git','-C',str(root),'diff','--check'],check=True)
    print('P61_PSF_BROKER_EXACT_PATH=INTEGRATED')
    print('P61_TITLE_ID_SYNTHESIZED=NO')
    print('P61_ANDROID_HARDWARE=NOT_TESTED')
    print('P61_PRIVATE_P42_PANVK=UNMODIFIED')
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--header',type=Path,required=True)
    args=parser.parse_args()
    apply(args.source_root,args.header)
