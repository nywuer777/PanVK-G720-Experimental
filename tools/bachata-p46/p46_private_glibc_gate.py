#!/usr/bin/env python3
"""P46: fail-closed provenance and code-section preflight for PRIVATE F43DEV V2 GLIBC.

This is not a BCn decoder, private ELF patch, proof of Vulkan completion, or
Android-game validation. Never use this to bypass the original ImageView asserts.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import struct
import zipfile
from pathlib import Path
from typing import Any

MAGIC = b'\x7fELF\x02\x01\x01'
ELF_HEADER = struct.Struct('<16sHHIQQQIHHHHHH')
SH = struct.Struct('<IIQQQQIIQQ')
PH = struct.Struct('<IIQQQQQQ')
SECTIONS = ('.text', '.rodata', '.note.gnu.build-id')
F43_V2 = b'--bachata-contract'
BCN_FALLBACK = b'GPU BCn fallback admitted'
OUTLAST_ASSERT = b'GPU BCn decoded image requires a matching sampled BC view'
PATH_FALSE_POSITIVE = b'bachata-s4'
P45_MARKER = b'P45_BCN_PER_LAYER_VIEW_PROOF'

class InvalidELF(ValueError):
    pass

def checked_slice(binary: bytes, start: int, size: int) -> bytes:
    if start < 0 or size < 0 or start > len(binary) or size > len(binary) - start:
        raise InvalidELF('bad ELF bounds')
    return binary[start:start + size]


def inspect_elf(binary: bytes) -> dict[str, Any]:
    if len(binary) < ELF_HEADER.size or not binary.startswith(MAGIC):
        raise InvalidELF('not ELF64 little-endian')
    header = ELF_HEADER.unpack_from(binary)
    (_, e_type, machine, _, _, phoff, shoff, _, _, phentsize, phnum,
     shentsize, shnum, shstrndx) = header
    if machine != 183 or e_type not in (2, 3):
        raise InvalidELF('not AArch64 executable/PIE')
    if shnum == 0 or shstrndx >= shnum or shentsize != SH.size or shnum > 4096:
        raise InvalidELF('unsupported ELF section table')
    checked_slice(binary, shoff, shentsize * shnum)
    sections = [SH.unpack_from(binary, shoff + i * shentsize) for i in range(shnum)]
    strtab = sections[shstrndx]
    names = checked_slice(binary, strtab[4], strtab[5])
    parsed = {}
    for sh in sections:
        name_off = sh[0]
        if name_off >= len(names):
            raise InvalidELF('invalid section name index')
        end = names.find(b'\x00', name_off)
        if end < 0:
            raise InvalidELF('unterminated section name')
        name = names[name_off:end].decode('utf-8', 'replace')
        if name in parsed:
            raise InvalidELF('duplicate ELF section name')
        if name in SECTIONS:
            parsed[name] = checked_slice(binary, sh[4], sh[5])
    if '.text' not in parsed or '.rodata' not in parsed:
        raise InvalidELF('missing core code or rodata section')
    if phentsize != PH.size or phnum == 0 or phnum > 128:
        raise InvalidELF('unsupported ELF program headers')
    checked_slice(binary, phoff, phentsize * phnum)
    interp = []
    for i in range(phnum):
        pt = PH.unpack_from(binary, phoff + i * phentsize)
        if pt[0] == 3:
            interp.append(checked_slice(binary, pt[2], pt[5]).rstrip(b'\x00').decode('utf-8', 'replace'))
    if interp != ['/lib/ld-linux-aarch64.so.1']:
        raise InvalidELF('unexpected GLIBC interpreter')
    text = parsed['.text']
    rodata = parsed['.rodata']
    buildid = None
    note = parsed.get('.note.gnu.build-id', b'')
    if len(note) >= 12:
        namesz, descsz, typ = struct.unpack_from('<III', note)
        descstart = 12 + ((namesz + 3)//4)*4
        if typ == 3 and note[12:12+namesz].startswith(b'GNU\x00'):
            desc = note[descstart:descstart+descsz]
            if len(desc)==descsz and 0<descsz<128:
                buildid = desc.hex()
    return {
        'size': len(binary),
        'elf_sha256': hashlib.sha256(binary).hexdigest(),
        'text_sha256': hashlib.sha256(text).hexdigest(),
        'text_size': len(text),
        'build_id': buildid,
        'interpreter': interp[0],
        'host_v2_contract_in_rodata': F43_V2 in rodata,
        'bcn_fallback_in_rodata': BCN_FALLBACK in rodata,
        'outlast_assert_in_rodata': OUTLAST_ASSERT in rodata,
        'path_bachata_s4_in_rodata': PATH_FALSE_POSITIVE in rodata,
        'p45_marker_in_rodata': P45_MARKER in rodata,
    }


def audit(candidate: bytes, baseline: bytes) -> dict[str, Any]:
    base = inspect_elf(baseline)
    cand = inspect_elf(candidate)
    # A runtime fix cannot be proved by an arbitrary marker, a changed signing
    # certificate, a different build-ID or the shared bachata-s4 string.
    host = (cand['host_v2_contract_in_rodata'] and cand['bcn_fallback_in_rodata'])
    text_changed = cand['text_sha256'] != base['text_sha256']
    if not (base['host_v2_contract_in_rodata'] and base['bcn_fallback_in_rodata']):
        raise InvalidELF('invalid private F43DEV baseline')
    if not host:
        verdict = 'REJECT_PUBLIC_OR_INCOMPATIBLE_HOST'
    elif not text_changed:
        verdict = 'REJECT_BCN_FIX_NOT_IN_PRIVATE_EXECUTABLE_CODE'
    else:
        verdict = 'BLOCK_PRIVATE_BCN_INTEGRATION_UNPROVEN'
    return {
        'schema': 'bachata-p46-private-glibc-identity-v1',
        'verdict': verdict,
        'candidate': cand,
        'baseline': base,
        'private_host_contract_seen': host,
        'code_text_changed_vs_baseline': text_changed,
        'p45_rodata_marker_not_accepted_as_fix': True,
        'private_bcn_source_and_build_provenance_present': False,
        'bcn_decode_upload_view_fence_compatibility_proved': False,
        'outlast_fixed': False,
        'apk_authorized_to_claim_bcn_fix': False,
    }


def load_binary(path: Path) -> bytes:
    if path.suffix.lower() == '.apk':
        with zipfile.ZipFile(path) as apk:
            with zipfile.ZipFile(__import__('io').BytesIO(apk.read('assets/runtime/runtime.zip'))) as rt:
                return rt.read('host/shadps4-arm64-fex')
    if path.suffix.lower() == '.zip':
        with zipfile.ZipFile(path) as rt:
            return rt.read('host/shadps4-arm64-fex')
    return path.read_bytes()


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument('--baseline', type=Path, required=True)
    cli.add_argument('--candidate', type=Path, required=True)
    cli.add_argument('--report', type=Path)
    opts = cli.parse_args()
    try:
        result = audit(load_binary(opts.candidate), load_binary(opts.baseline))
    except (ValueError, KeyError, zipfile.BadZipFile, OSError) as exc:
        result = {'schema':'bachata-p46-private-glibc-identity-v1', 'verdict': 'REJECT_INVALID_ELF_OR_RUNTIME', 'reason':str(exc), 'outlast_fixed':False, 'apk_authorized_to_claim_bcn_fix':False}
    output = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
    print(output)
    if opts.report:
        opts.report.write_text(output+'\n', encoding='utf-8')
    return 0 if result['verdict']=='PRIVATE_BCN_INTEGRATION_APPROVED' else 3

if __name__ == '__main__':
    raise SystemExit(main())