#!/usr/bin/env python3
"""Fail-closed F43DEV V2 APK release gate. Does not patch APKs or waive identity security.

Usage: python host_identity_release_gate.py /path/to/candidate.apk [--report result.json]
A candidate must have a valid Android APK v2 signature, the F43DEV V2 GLIBC
host contract, the correct signer bound in 1 Bionic and 11 GLIBC reference
slots, and coherent native/guest manifests. This is a static gate, not a
substitute for device launch tests. Key material is neither required nor read.
"""
from __future__ import annotations
import argparse, hashlib, io, json, sys, zipfile
from pathlib import Path

try:
 from apk_identity_p15 import verify_apk
except ImportError:
 from .apk_identity_p15 import verify_apk

NATIVE='lib/arm64-v8a/libbachata_native_runtime.so'
RUNTIME='assets/runtime/runtime.zip'
CORE='host/shadps4-arm64-fex'
NATIVE_OFFSETS=(0x23d8665,)
CORE_OFFSETS=(0x2a63535,0x2a63d3d,0x2a63e31,0x2a63f25,0x2a64019,0x2a6410d,0x2a64201,0x2a642f5,0x2a643e9,0x2a644dd,0x3d10875)
GUEST_JSON='usr/share/bachata/guest-runtime.json'
GUEST_TEXT='usr/share/bachata/guest-runtime.txt'


def sha(data:bytes)->str:return hashlib.sha256(data).hexdigest()

def check_code(data:bytes, offsets:tuple[int,...], signer:str, label:str):
    if not data.startswith(b'\x7fELF'):raise ValueError(f'{label}_NOT_ELF')
    if b'host identity check failed' not in data:raise ValueError(f'{label}_HOST_IDENTITY_GUARD_MISSING')
    if b'BACHATA/1' not in data:raise ValueError(f'{label}_F43DEV_PROTOCOL_MISSING')
    if len(signer)!=64:raise ValueError('SIGNER_DIGEST_INVALID')
    for off in offsets:
        data64=data[off:off+64]
        if len(data64)!=64:raise ValueError(f'{label}_CERT_SLOT_TRUNCATED')
        seed=bytes(data64[i]^ord(signer[i])^((0x5b+0x25*i)&255) for i in range(64))
        if not all(seed[i]==seed[i%4] for i in range(64)):
            raise ValueError(f'{label}_CERTIFICATE_MISMATCH_AT_{off:x}')
    return len(offsets)


def assert_manifest(rows,identifier,name,blob):
    hits=[x for x in rows if x[identifier]==name]
    if len(hits)!=1 or hits[0]['sha256']!=sha(blob):raise ValueError('MANIFEST_SHA256_MISMATCH_'+name)
    if 'size' in hits[0] and hits[0]['size']!=len(blob):raise ValueError('MANIFEST_SIZE_MISMATCH_'+name)


def gate(apk:Path)->dict:
    sig=verify_apk(apk)
    if not sig['v2_signature_verified'] or not sig['v2_file_integrity_verified']:
        raise ValueError('APK_V2_SIGNATURE_OR_CONTENT_INVALID')
    signers=sig['signers']
    if len(signers)!=1:raise ValueError('EXPECTED_ONE_SIGNER')
    cert=signers[0]['certificate_sha256']
    with zipfile.ZipFile(apk) as z:
        if z.testzip() is not None:raise ValueError('APK_ZIP_CRC_ERROR')
        required={NATIVE,RUNTIME,'assets/runtime/manifest.json','assets/runtime/native-runtime.json','AndroidManifest.xml','classes.dex'}
        if not required.issubset(z.namelist()):raise ValueError('MISSING_REQUIRED_APK_MEMBERS')
        native=z.read(NATIVE)
        native_ok=check_code(native,NATIVE_OFFSETS,cert,'BIONIC')
        native_manifest=json.loads(z.read('assets/runtime/native-runtime.json'))
        assert_manifest(native_manifest['files'],'name',NATIVE.split('/')[-1],native)
        runtime_manifest=json.loads(z.read('assets/runtime/manifest.json'))
        if runtime_manifest.get('protocolVersion')!=2 or not str(runtime_manifest.get('runtimeVersion','')).startswith('runtime-f43dev'):
            raise ValueError('RUNTIME_HOST_PROTOCOL_VERSION_MISMATCH')
        entries=runtime_manifest['files']
        if len(entries)!=397:raise ValueError('RUNTIME_FILE_COUNT_MISMATCH')
        with zipfile.ZipFile(io.BytesIO(z.read(RUNTIME))) as rt:
            if rt.testzip() is not None:raise ValueError('RUNTIME_ZIP_CRC_ERROR')
            if len(rt.namelist())!=397 or set(rt.namelist())!={row['path'] for row in entries}:
                raise ValueError('RUNTIME_FILE_PATHS_MISMATCH')
            for row in entries:
                assert_manifest(entries,'path',row['path'],rt.read(row['path']))
            core=rt.read(CORE)
            core_ok=check_code(core,CORE_OFFSETS,cert,'PRIVATE_GLIBC')
            guest_json=json.loads(rt.read(GUEST_JSON))
            if guest_json.get('sha256')!=sha(core):raise ValueError('GUEST_JSON_ELF_SHA256_MISMATCH')
            if rt.read(GUEST_TEXT).count(sha(core).encode())!=1:raise ValueError('GUEST_TEXT_ELF_SHA256_MISMATCH')
        report={
         'verdict':'PASS_HOST_IDENTITY_STATIC_RELEASE_GATE',
         'apk_sha256':hashlib.sha256(apk.read_bytes()).hexdigest(),
         'apk_bytes':apk.stat().st_size,'signer_certificate_sha256':cert,
         'android_signature_v2_verified':True,'bionic_cert_slots':native_ok,
         'glibc_cert_slots':core_ok,'private_f43dev_v2_hello_present':True,
         'runtime_manifest_members':len(entries),'native_manifest_sha256_match':True,
         'guest_runtime_sha256_match':True,
         'android_launch_test':'NOT_EXECUTED','gameplay_fixed':'NOT_CLAIMED'
        }
        return report


def main():
    parser=argparse.ArgumentParser();parser.add_argument('apk',type=Path);parser.add_argument('--report',type=Path)
    a=parser.parse_args()
    try:
        result=gate(a.apk);code=0
    except Exception as exc:
        result={'verdict':'REJECT_HOST_IDENTITY_RELEASE','reason':str(exc),'apk_name':a.apk.name};code=2
    if a.report:a.report.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))
    return code
if __name__=='__main__':raise SystemExit(main())
