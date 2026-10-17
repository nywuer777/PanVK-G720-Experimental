#!/usr/bin/env python3
"""P32: fail-closed audit of whether P25-P28 code is ACTIVE in the GLIBC texture path.

No APK mutation, binary patch or Android game testing. This is a release-gate audit,
not a proof of runtime graphics correctness. Input source patch and kit are pinned.
"""
from __future__ import annotations
import argparse, hashlib, json, re, sys, zipfile
from pathlib import Path

EXPECTED_P23 = '2806f93e9f4346dda5c796462c3d916fb021e2dc942fa2e7366dc78c265c62b6'
EXPECTED_P30_ELF = 'ab6bebe0930b14e96d999c64aa686f9f051979ec7d0790ed6c64b0d66a78f758'
BCN_RE = re.compile(r'\b(?:BachataP27::)?(?:DecodeAndUploadBcn|RecordDecodedUpload)\s*\(')
ALIAS_RE = re.compile(r'\b(?:BachataP26::)?(?:DecideDispatch)\s*\(')


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(4*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def diff_added_lines(patch: str) -> dict[str, list[str]]:
    changed: dict[str, list[str]] = {}
    path = None
    for line in patch.splitlines():
        if line.startswith('+++ b/'):
            path = line[6:]
            changed.setdefault(path, [])
        elif line.startswith('+++ /dev/null'):
            path = None
        elif line.startswith('+') and not line.startswith('+++') and path:
            changed[path].append(line[1:])
    return changed


def analyze(kit: Path, patch: Path, result: Path, p23_apk: Path | None = None) -> dict:
    with zipfile.ZipFile(kit) as z:
        members = set(z.namelist())
        def read(name: str) -> str:
            if name not in members: raise RuntimeError(f'MISSING_KIT_MEMBER:{name}')
            return z.read(name).decode('utf8')
        p27 = read('source/p27_vk_decoded_upload.cpp')
        p28 = read('source/p28_vk_async_upload.cpp')
        p26 = read('source/p26_alias_dispatch_gate.hpp')
        p29_gate = read('source/p29_build_gate.py')
    p30 = json.loads(result.read_text())
    if p30.get('elf',{}).get('sha256') != EXPECTED_P30_ELF:
        raise RuntimeError('UNRECOGNIZED_COMPILER_RESULT')
    if not p30.get('full_core_compile_passed') or not p30.get('p28_port_applied'):
        raise RuntimeError('P30_BUILD_NOT_PROVEN')
    if p30.get('source_revision')!='be6bc2e9c60799e071dd2fafa6216e8d80ec619c':
        raise RuntimeError('WRONG_SOURCE_PIN')
    if p23_apk and sha_file(p23_apk) != EXPECTED_P23:
        raise RuntimeError('WRONG_P23_APK')
    diff = patch.read_text()
    added = diff_added_lines(diff)
    all_added = '\n'.join('\n'.join(v) for v in added.values())
    # New translation units implement P27/P28, but they must have a caller in
    # the main renderer. Do not mistake their own definitions for a dispatch.
    cpps = {k:v for k,v in added.items() if k.endswith('.cpp')}
    bcmain = [line for name, lines in cpps.items() if 'p27_vk_decoded_upload.cpp' not in name
              and 'p28_vk_async_upload.cpp' not in name for line in lines if BCN_RE.search(line)]
    alias = [line for name, lines in cpps.items() if ('vk_rasterizer.cpp' in name or 'texture_cache.cpp' in name)
             for line in lines if ALIAS_RE.search(line)]
    # Explicitly check the source units aren't just stubs; P30 is a real compile.
    if 'UploadDecodedToRgba' not in p27 or 'RecordDecodedUpload' not in p28:
        raise RuntimeError('CANDIDATE_ADAPTER_MISSING')
    if 'DecideDispatch' not in p26 or 'PUBLIC_CORE_GLIBC_COMPILED_NOT_F43DEV' not in p29_gate:
        raise RuntimeError('SOURCE_CHAIN_MISMATCH')
    # A classifer without resource rewrites is not a fix: inspect the exact
    # changes in the rasterizer, not function names alone.
    raster = '\n'.join(added.get('src/video_core/renderer_vulkan/vk_rasterizer.cpp', []))
    diagnostic_only = ('BACHATA_P25_GPU_AUDIT' in raster and
                       'gpu_rewrite=0' in raster and 'classification-only' in raster)
    # A decoded view proof is not useful until the main texture path connects
    # to the decoder and produces an RGBA backing.
    active_bcn = bool(bcmain)
    active_alias_repair = False  # Explicit unsupported feature; do not auto-infer from logs.
    reasons = []
    if not active_bcn: reasons.append('BCN_NO_MAIN_RENDERER_CALLSITE')
    if 'src/video_core/texture_cache/texture_cache.cpp' not in added:
        reasons.append('TEXTURE_REFRESH_PATH_UNCHANGED')
    if diagnostic_only: reasons.append('ALIAS_POLICY_DIAGNOSTIC_ONLY')
    if not active_alias_repair: reasons.append('ALIAS_SHADER_ORDERING_NOT_IMPLEMENTED')
    reasons.append('F43DEV_PRIVATE_RUNTIME_SOURCE_NOT_MATCHED')
    return {
        'schema':'bachata-p32-active-path-gate-v1',
        'baseline_p23_sha256_expected':EXPECTED_P23,
        'p30_public_elf_sha256':EXPECTED_P30_ELF,
        'source_revision':p30['source_revision'],
        'glibc_aarch64_compiled':True,
        'p27_decoder_present_in_build':True,
        'p28_async_adapter_present_in_build':True,
        'bcn_external_calls_in_p30_patch':bcmain,
        'bcn_external_callsite_count':len(bcmain),
        'bcn_renderer_integration_eligible':active_bcn,
        'texture_cache_refresh_path_modified': 'src/video_core/texture_cache/texture_cache.cpp' in added,
        'alias_classifier_calls_in_patch':len(alias),
        'alias_policy_diagnostic_only':diagnostic_only,
        'alias_memory_order_fix_present':active_alias_repair,
        'outlast_fixed':False,'minecraft_fixed':False,
        'f43dev_apk_untouched':True,
        'candidate_approved_for_apk':False,
        'release_gate':'BLOCKED', 'reasons':reasons,
    }


def main(argv=None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--kit',type=Path,required=True)
    p.add_argument('--patch',type=Path,required=True)
    p.add_argument('--result',type=Path,required=True)
    p.add_argument('--p23',type=Path)
    p.add_argument('--output',type=Path)
    p.add_argument('--require-ready',action='store_true')
    args=p.parse_args(argv)
    report=analyze(args.kit,args.patch,args.result,args.p23)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'gate':report['release_gate'],'reasons':report['reasons'], 'bcn_callsite_count':report['bcn_external_callsite_count']}))
    return 8 if args.require_ready and report['release_gate']!='READY' else 0

if __name__=='__main__':sys.exit(main())