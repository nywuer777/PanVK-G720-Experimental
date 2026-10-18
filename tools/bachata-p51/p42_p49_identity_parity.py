#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P51: compare real public P49 ELF to private F43DEV P42 identity invariants.

A verified Linux build is not a signed private Android host. This tool rejects
unsafe promotion and can compare an authorized P42 guest ELF read-only if present.
No APK/ELF is modified or uploaded. No signer, token, nonce or game data emitted.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

P49_SHA = "272024fe15b7785be819f7fe3eb403c0543b070da2a6525d10580e24876dadaa"
P42_SHA = "5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002"
P42_TEXT_SHA = "f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157"
P49_TEXT_SHA = "bfa4914b56a6246219a13666045b0bf89e778a24f295373a6fbc02a9d44b66dd"
APK_V2_REFERENCE = "e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded"
PKG = "com.bachatas4.android.f43dev"
LOADER = "/lib/ld-linux-aarch64.so.1"
MAX_BYTES = 140_000_000
H = struct.Struct("<16sHHIQQQIHHHHHH")
SH = struct.Struct("<IIQQQQIIQQ")
PH = struct.Struct("<IIQQQQQQ")
PRIVATE_GUARD = b"host identity check failed"
PRIVATE_BCN = b"GPU BCn fallback admitted"
P49_HELLO = b"BACHATA/1 HELLO version=2 contract="
P49_PEER = b"F43DEV host gate: untrusted app-private root or socket"
P49_SAMPLE_BCN = b"P25 decoded BCn sampled view blocked"

def file_digest(p: Path) -> str:
    d=hashlib.sha256()
    with p.open("rb") as file:
        for chunk in iter(lambda: file.read(1024*1024), b""):
            d.update(chunk)
    return d.hexdigest()

def bounded_slice(blob:bytes,off:int,size:int)->bytes:
    if off<0 or size<0 or off>len(blob) or size>len(blob)-off:
        raise ValueError("ELF_SECTION_OUT_OF_BOUNDS")
    return blob[off:off+size]

def section_inventory(blob:bytes)->dict:
    if len(blob)<H.size or blob[:7]!=b"\x7fELF\x02\x01\x01":
        raise ValueError("NOT_ELF64_LE")
    (_,elf_type,machine,_,_,phoff,shoff,_,_,phentsize,phnum,shentsize,shnum,shstr)=H.unpack_from(blob)
    if elf_type not in (2,3) or machine!=183:
        raise ValueError("NOT_AARCH64_EXECUTABLE")
    if not (0<shnum<4096 and 0<=shstr<shnum and shentsize==SH.size):
        raise ValueError("INVALID_SECTION_TABLE")
    if not (0<phnum<128 and phentsize==PH.size):
        raise ValueError("INVALID_PROGRAM_TABLE")
    bounded_slice(blob,shoff,shnum*shentsize)
    bounded_slice(blob,phoff,phnum*phentsize)
    rows=[SH.unpack_from(blob,shoff+i*SH.size) for i in range(shnum)]
    index=rows[shstr]
    names=bounded_slice(blob,index[4],index[5])
    result={}
    for row in rows:
        nameidx=row[0]
        if nameidx>=len(names):raise ValueError("INVALID_SECTION_NAME_INDEX")
        stop=names.find(b"\0",nameidx)
        if stop<0:raise ValueError("UNTERMINATED_SECTION_NAME")
        name=names[nameidx:stop].decode("utf-8","strict")
        if name in (".text",".rodata"):
            if name in result:raise ValueError("DUPLICATE_TARGET_SECTION")
            result[name]=bounded_slice(blob,row[4],row[5])
    if set(result)!={".text",".rodata"}:raise ValueError("CODE_OR_RODATA_MISSING")
    interpreters=[]
    for i in range(phnum):
        ph=PH.unpack_from(blob,phoff+i*PH.size)
        if ph[0]==3:
            interpreters.append(bounded_slice(blob,ph[2],ph[5]).rstrip(b"\0").decode("ascii"))
    if interpreters!=[LOADER]:
        raise ValueError("WRONG_GLIBC_INTERPRETER")
    return result

def identify(path:Path, expected_sha:str)->dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("SOURCE_BINARY_NOT_AVAILABLE")
    size=path.stat().st_size
    if size>MAX_BYTES or size<H.size:
        raise ValueError("BINARY_SIZE_OUT_OF_RANGE")
    if file_digest(path)!=expected_sha:
        raise ValueError("BINARY_HASH_DOES_NOT_MATCH_PIN")
    b=path.read_bytes()
    sections=section_inventory(b)
    return {
        "sha256":expected_sha,
        "size_bytes":len(b),
        "text_sha256":hashlib.sha256(sections[".text"]).hexdigest(),
        "private_v2_identity_guard_literal":PRIVATE_GUARD in b,
        "private_bcn_fallback_literal":PRIVATE_BCN in sections[".rodata"],
        "host_v2_hello_format_literal":P49_HELLO in b,
        "public_peer_reject_literal":P49_PEER in b,
        "public_bcn_sample_reject_literal":P49_SAMPLE_BCN in b,
    }

def compare(public:dict, private:dict|None)->dict:
    if public["sha256"]!=P49_SHA or public["text_sha256"]!=P49_TEXT_SHA:
        raise ValueError("PUBLIC_P49_CODE_PIN_MISMATCH")
    if not public["host_v2_hello_format_literal"] or not public["public_peer_reject_literal"]:
        raise ValueError("PUBLIC_P49_HOST_V2_SYMBOLS_MISSING")
    if private is not None:
        if private["sha256"]!=P42_SHA or private["text_sha256"]!=P42_TEXT_SHA:
            raise ValueError("PRIVATE_P42_CODE_PIN_MISMATCH")
        if not private["private_v2_identity_guard_literal"] or not private["private_bcn_fallback_literal"]:
            raise ValueError("PRIVATE_P42_CONTRACT_INCONSISTENT")
    same_private_code = None if private is None else public["text_sha256"]==private["text_sha256"]
    assert same_private_code is not True
    report={
        "schema":"P51_P42_P49_REPLACEMENT_PARITY_V1",
        "tested_real_public_elf_sha256":public["sha256"],
        "tested_public_text_sha256":public["text_sha256"],
        "p42_private_core_reference_sha256":P42_SHA,
        "p42_private_text_reference_sha256":P42_TEXT_SHA,
        "f43dev_signed_apk_original_reference_sha256":APK_V2_REFERENCE,
        "package_identity":PKG,
        "private_core_raw_bytes_verified":private is not None,
        "private_core_text_equal_to_public":same_private_code,
        "public_hello_v2_frame_present":public["host_v2_hello_format_literal"],
        "public_same_uid_peer_rejection_present":public["public_peer_reject_literal"],
        "public_private_v2_identity_guard_literal_present":public["private_v2_identity_guard_literal"],
        "public_private_bcn_fallback_literal_present":public["private_bcn_fallback_literal"],
        "public_bcn_reject_path_present":public["public_bcn_sample_reject_literal"],
        "p42_has_reference_private_guard_from_prior_verified_audit":True,
        "p42_has_reference_private_bcn_fallback_from_prior_verified_audit":True,
        "signed_apk_v2_signature_reverified_in_p51":False,
        "private_bionic_plus_11_glibc_cert_bindings_verified_in_p51":False,
        "all_397_private_runtime_entries_verified_in_p51":False,
        "actual_android_package_uid_and_af_unix_peer_tested":False,
        "saf_broker_and_fex_loader_equivalent_proven":False,
        "outlast_gpu_fix_verified_on_device":False,
        "apk_promotion_authorized":False,
        "verdict":"REJECT_PUBLIC_P49_AS_DROP_IN_P42_CORE",
        "next_required":"AUTHORIZED_PRIVATE_SOURCE_OR_SUPPORTED_SAME_UID_DIAGNOSTIC",
    }
    return report

def main()->int:
    cli=argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--public-elf",type=Path,required=True)
    cli.add_argument("--private-p42-elf",type=Path,default=None,
                     help="Optional authorized private guest ELF, read-only; never uploaded")
    cli.add_argument("--out",type=Path,required=True)
    a=cli.parse_args()
    try:
        public=identify(a.public_elf,P49_SHA)
        private=identify(a.private_p42_elf,P42_SHA) if a.private_p42_elf else None
        result=compare(public,private)
        code=0
    except (ValueError, OSError, UnicodeError) as error:
        # Sanitized: no caller filesystem path, nonce, signer or candidate bytes.
        result={"schema":"P51_P42_P49_REPLACEMENT_PARITY_V1",
                "verdict":"ERROR_FAIL_CLOSED",
                "reason":str(error) if isinstance(error,ValueError) else type(error).__name__,
                "apk_promotion_authorized":False}
        code=2
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("P51_VERDICT="+result["verdict"])
    return code

if __name__=="__main__":
    raise SystemExit(main())
