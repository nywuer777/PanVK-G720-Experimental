#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only F43DEV V2 Android Bionic vs GLIBC ld.so chain audit.

Only the generated *sanitized JSON* may be published. Do not upload original
APK, DEX, Bionic libbachata_native_runtime.so, GLIBC loader, or other binaries
to the repository. Static ELF parsing cannot prove a live Android loader works.
"""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

APK_SHA = "e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded"
LOADER_SHA = "e9d9a01ac27c4369980023a7b20817aa4c158a8bd797c9883bd20386f126e578"
NATIVE_SHA = "16bd679a762ee3615bc3deb24e0945964775f267eb2f1dc0f015c2eeb030ef54"
BASELINE_SHA = "b1cd025306b1dbd7b07d3bc228a0f18392d4f32fdeb934c9676e75ed0090abb4"
INTERP = "/lib/ld-linux-aarch64.so.1"

def sha256(raw):
    return hashlib.sha256(raw).hexdigest()

def file_sha256(path):
    d = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            d.update(chunk)
    return d.hexdigest()

def parse_elf_machine(raw):
    if len(raw) < 20 or raw[:4] != b"\x7fELF" or raw[4] != 2 or raw[5] != 1:
        raise ValueError("INVALID_ELF64_LITTLE_ENDIAN")
    return int.from_bytes(raw[18:20], "little")

def parse_soname(readelf_dynamic):
    found = re.findall(r"Library soname: \[([^\]]+)\]", readelf_dynamic)
    if len(found) != 1:
        raise ValueError("SONAME_NOT_UNIQUE")
    return found[0]

def parse_needed(readelf_dynamic):
    return sorted(re.findall(r"Shared library: \[([^\]]+)\]", readelf_dynamic))

def parse_interp(readelf_program):
    found = re.findall(r"\[Requesting program interpreter: ([^\]]+)\]", readelf_program)
    if len(found) != 1:
        raise ValueError("INTERPRETER_NOT_UNIQUE")
    return found[0]

def check_manifest(manifest, path, data):
    matches = [item for item in manifest.get("files", [])
               if item.get("path") == path]
    return (len(matches) == 1 and
            matches[0].get("size") == len(data) and
            matches[0].get("sha256") == sha256(data))

def static_elf(path, *args):
    cmd = ["readelf", "-W", *args, str(path)]
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

def audit(apk_path, candidate_zip=None):
    if file_sha256(apk_path) != APK_SHA:
        raise ValueError("APK_BASELINE_MISMATCH")
    result = {
        "schema": "bachata-r2a6p6-elf-loader-audit-v1",
        "source": "READ_ONLY_PINNED_APK_AND_OPTIONAL_CI_ELF",
        "apk_sha256": APK_SHA,
        "apk_cryptographic_signature_verified": False,
        "apk_original_untouched": True,
        "original_loader_sha256": LOADER_SHA,
        "original_bionic_runtime_sha256": NATIVE_SHA,
        "original_glibc_core_sha256": BASELINE_SHA,
        "manifest_protocol_version": None,
        "host_loader_equal_bundled_glibc_ld_so": False,
        "host_loader_declared_soname": None,
        "host_loader_contains_glibc_private_symbols": False,
        "host_loader_contains_jni_bridge_symbols": False,
        "native_runtime_contains_jni_onload": False,
        "native_runtime_contains_bridge_run": False,
        "native_runtime_contains_bridge_stop": False,
        "native_runtime_links_android_bionic_libc": False,
        "baseline_glibc_core_interpreter": None,
        "candidate_core_sha256": None,
        "candidate_manifest_sha256_matches": None,
        "candidate_interpreter": None,
        "candidate_needed_matches_original_core": None,
        "candidate_contains_v2_hello_marker": None,
        "loader_available_in_packaged_glibc_tree": False,
        "runtime_path_resolution_verified_on_android": False,
        "host_signature_verification_verified_live": False,
        "android_broker_handshake_verified_live": False,
        "apk_installable_candidate": False,
        "next_gate": "AUTHORIZED_HOST_SOURCE_OR_IN_APP_DIAGNOSTIC_REQUIRED",
    }
    with tempfile.TemporaryDirectory(prefix="r2a6p6-audit-") as tmp:
        t = Path(tmp)
        with ZipFile(apk_path) as apk:
            host_loader = apk.read("lib/arm64-v8a/libbachata_host_loader.so")
            if sha256(host_loader) != LOADER_SHA:
                raise ValueError("APK_LOADER_HASH_MISMATCH")
            (t/"loader.so").write_bytes(host_loader)
            with apk.open("lib/arm64-v8a/libbachata_native_runtime.so") as source:
                with (t/"native-runtime.so").open("wb") as dest:
                    for data in iter(lambda: source.read(1_048_576), b""):
                        dest.write(data)
            if file_sha256(t/"native-runtime.so") != NATIVE_SHA:
                raise ValueError("APK_NATIVE_RUNTIME_HASH_MISMATCH")
            manifest = json.loads(apk.read("assets/runtime/manifest.json"))
            result["manifest_protocol_version"] = manifest.get("protocolVersion")
            if result["manifest_protocol_version"] != 2:
                raise ValueError("APK_RUNTIME_MANIFEST_NOT_V2")
            with ZipFile(BytesIO(apk.read("assets/runtime/runtime.zip"))) as runtime:
                ldso = runtime.read("host/ld-linux-aarch64.so.1")
                if not check_manifest(manifest, "host/ld-linux-aarch64.so.1", ldso):
                    raise ValueError("GLIBC_RTLD_MANIFEST_MISMATCH")
                result["host_loader_equal_bundled_glibc_ld_so"] = host_loader == ldso
                result["loader_available_in_packaged_glibc_tree"] = True
                if not result["host_loader_equal_bundled_glibc_ld_so"]:
                    raise ValueError("APK_HOST_LOADER_NOT_BUNDLED_LDSO")
                with runtime.open("host/shadps4-arm64-fex") as source:
                    with (t/"original-core").open("wb") as dest:
                        for data in iter(lambda: source.read(1_048_576), b""):
                            dest.write(data)
                if file_sha256(t/"original-core") != BASELINE_SHA:
                    raise ValueError("APK_CORE_BASELINE_MISMATCH")
                if not check_manifest(manifest, "host/shadps4-arm64-fex", (t/"original-core").read_bytes()):
                    raise ValueError("APK_CORE_MANIFEST_MISMATCH")
        for name in ["loader.so", "native-runtime.so", "original-core"]:
            if parse_elf_machine((t/name).read_bytes()[:64]) != 183:
                raise ValueError("NOT_AARCH64")
        ld_dyn = static_elf(t/"loader.so","-d")
        ld_syms = static_elf(t/"loader.so","--dyn-syms")
        native_dyn = static_elf(t/"native-runtime.so","-d")
        native_syms = static_elf(t/"native-runtime.so","--dyn-syms")
        original_dyn = static_elf(t/"original-core","-d")
        result["host_loader_declared_soname"] = parse_soname(ld_dyn)
        result["host_loader_contains_glibc_private_symbols"] = "GLIBC_PRIVATE" in ld_syms
        result["host_loader_contains_jni_bridge_symbols"] = "JNI_OnLoad" in ld_syms or "Java_com_bachatas4_" in ld_syms
        result["native_runtime_contains_jni_onload"] = "JNI_OnLoad" in native_syms
        result["native_runtime_contains_bridge_run"] = "Java_com_bachatas4_android_runtime_process_NativeRuntimeBridge_run" in native_syms
        result["native_runtime_contains_bridge_stop"] = "Java_com_bachatas4_android_runtime_process_NativeRuntimeBridge_stop" in native_syms
        result["native_runtime_links_android_bionic_libc"] = ("libc.so" in parse_needed(native_dyn) and
                                                              "liblog.so" in parse_needed(native_dyn))
        result["baseline_glibc_core_interpreter"] = parse_interp(static_elf(t/"original-core","-l"))
        if result["host_loader_declared_soname"] != "ld-linux-aarch64.so.1":
            raise ValueError("NOT_GLIBC_RTLD")
        if candidate_zip:
            with ZipFile(candidate_zip) as z:
                names = [s for s in z.namelist()
                         if s.startswith("shadps4-arm64-glibc-R2A6P5") and not s.endswith("/")]
                if len(names) != 1:
                    raise ValueError("BAD_CANDIDATE_CONTENTS")
                with z.open(names[0]) as source:
                    with (t/"candidate-core").open("wb") as dest:
                        for data in iter(lambda: source.read(1_048_576), b""):
                            dest.write(data)
                binary_sha = file_sha256(t/"candidate-core")
                result["candidate_core_sha256"] = binary_sha
                checksum = z.read("SHA256SUMS.txt").decode("ascii", "strict").strip().split()
                result["candidate_manifest_sha256_matches"] = (
                    len(checksum) == 2 and checksum == [binary_sha, names[0]])
                if not result["candidate_manifest_sha256_matches"]:
                    raise ValueError("CANDIDATE_SHA_MANIFEST_MISMATCH")
            if parse_elf_machine((t/"candidate-core").read_bytes()[:64]) != 183:
                raise ValueError("CANDIDATE_NOT_AARCH64")
            result["candidate_interpreter"] = parse_interp(static_elf(t/"candidate-core","-l"))
            candidate_needed = parse_needed(static_elf(t/"candidate-core","-d"))
            result["candidate_needed_matches_original_core"] = (
                candidate_needed == parse_needed(original_dyn))
            # Use byte-presence evidence ONLY; do not claim handshake execution.
            with (t/"candidate-core").open("rb") as binary:
                result["candidate_contains_v2_hello_marker"] = (
                    b"BACHATA/1 HELLO version=2 contract=" in binary.read())
    return result

def main():
    p = argparse.ArgumentParser(description="Static ELF/ZIP loader audit, no device access")
    p.add_argument("--apk", type=Path, required=True)
    p.add_argument("--candidate-zip", type=Path)
    p.add_argument("--output", type=Path)
    args=p.parse_args()
    result=audit(args.apk,args.candidate_zip)
    encoded=json.dumps(result,sort_keys=True,indent=2)+"\n"
    if args.output:
        args.output.write_text(encoded,encoding="utf-8")
    else:
        print(encoded,end="")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
