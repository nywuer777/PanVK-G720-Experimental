#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Read-only JNI ABI proof from known-good signed F43DEV V2 APK.

Only sanitized JSON is publishable. Never commit the APK, DEX, Bionic library,
original app paths, tokens, JNI raw memory, or signing material to GitHub.
This is static verification, not an Android broker or live launch test.
"""
import argparse
import hashlib
import json
import struct
import subprocess
import tempfile
from pathlib import Path
from zipfile import ZipFile

APK_PIN = "e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded"
NATIVE_PIN = "16bd679a762ee3615bc3deb24e0945964775f267eb2f1dc0f015c2eeb030ef54"
NATIVE_CLASS = "Lcom/bachatas4/android/runtime/process/NativeRuntimeBridge;"
RUN_PROTO = "(Landroid/view/Surface;Z[Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;I)I"
STOP_PROTO = "()V"
RUN_JNI = "Java_com_bachatas4_android_runtime_process_NativeRuntimeBridge_run"
STOP_JNI = "Java_com_bachatas4_android_runtime_process_NativeRuntimeBridge_stop"

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for chunk in iter(lambda:f.read(1_048_576),b""):h.update(chunk)
    return h.hexdigest()

def uleb(data,offset):
    value=0
    for i in range(5):
        if offset>=len(data):raise ValueError("DEX_BAD_ULEB")
        x=data[offset];offset+=1
        value|=(x&127)<<(i*7)
        if not x&128:return value,offset
    raise ValueError("DEX_ULEB_OVERFLOW")

def extract_bridge(data):
    if not data.startswith(b"dex\n") or len(data)<112 or data[7]!=0 or (
        struct.unpack_from("<I",data,32)[0]!=len(data)
    ):raise ValueError("DEX_BAD_HEADER")
    def table(hdr,size):
        n,o=struct.unpack_from("<II",data,hdr)
        if n>1_000_000 or o+n*size>len(data):raise ValueError("DEX_BAD_TABLE")
        return n,o
    sc,so=table(0x38,4)
    strings=[]
    for i in range(sc):
        pos=struct.unpack_from("<I",data,so+i*4)[0]
        if pos>=len(data):raise ValueError("DEX_BAD_STRING_OFFSET")
        _,pos=uleb(data,pos)
        end=data.find(b"\0",pos)
        if end<0 or end-pos>65535:raise ValueError("DEX_BAD_STRING_TERMINATOR")
        strings.append(data[pos:end].decode("utf-8","replace"))
    tc,to=table(0x40,4)
    types=[]
    for i in range(tc):
        k=struct.unpack_from("<I",data,to+i*4)[0]
        if k>=len(strings):raise ValueError("DEX_BAD_TYPE")
        types.append(strings[k])
    pc,po=table(0x48,12)
    protos=[]
    for i in range(pc):
        _,result_idx,params=struct.unpack_from("<III",data,po+i*12)
        if result_idx>=len(types):raise ValueError("DEX_BAD_PROTO")
        arguments=[]
        if params:
            if params+4>len(data):raise ValueError("DEX_BAD_PARAMS")
            n=struct.unpack_from("<I",data,params)[0]
            if n>256 or params+4+2*n>len(data):raise ValueError("DEX_BAD_PARAMS")
            for j in range(n):
                idx=struct.unpack_from("<H",data,params+4+j*2)[0]
                if idx>=len(types):raise ValueError("DEX_BAD_PARAMS")
                arguments.append(types[idx])
        protos.append("("+"".join(arguments)+")"+types[result_idx])
    mc,mo=table(0x58,8)
    methods=[]
    for i in range(mc):
        cl,pr,name=struct.unpack_from("<HHI",data,mo+i*8)
        if cl>=len(types) or pr>=len(protos) or name>=len(strings):
            raise ValueError("DEX_BAD_METHOD")
        methods.append((types[cl],strings[name],protos[pr]))
    cc,co=table(0x60,32)
    found=[]
    for i in range(cc):
        cl,_,_,_,_,_,off,_=struct.unpack_from("<IIIIIIII",data,co+i*32)
        if cl>=len(types):raise ValueError("DEX_BAD_CLASS")
        if types[cl]!=NATIVE_CLASS:continue
        if not 0<off<len(data):raise ValueError("DEX_MISSING_BRIDGE_DATA")
        cursor=off
        counts=[]
        for _ in range(4):
            v,cursor=uleb(data,cursor);counts.append(v)
        if any(v>100_000 for v in counts):raise ValueError("DEX_BAD_CLASS_SIZE")
        for count in counts[:2]:
            for _ in range(count):
                _,cursor=uleb(data,cursor)
                _,cursor=uleb(data,cursor)
        for count in counts[2:]:
            method_index=0
            for _ in range(count):
                diff,cursor=uleb(data,cursor)
                flags,cursor=uleb(data,cursor)
                code,cursor=uleb(data,cursor)
                method_index+=diff
                if method_index>=len(methods):raise ValueError("DEX_BAD_CLASS_METHOD")
                cls,name,proto=methods[method_index]
                if cls==NATIVE_CLASS and name in ("run","stop"):
                    found.append({"method":name,"descriptor":proto,
                        "static":bool(flags&0x8),"native":bool(flags&0x100),
                        "has_bytecode":bool(code)})
    if len(found)!=2 or len({m["method"] for m in found})!=2:
        raise ValueError("DEX_BRIDGE_METHODS_NOT_UNIQUE")
    return {m["method"]:m for m in found}

def check_exports(text):
    selected=[RUN_JNI,STOP_JNI,"JNI_OnLoad"]
    answer={}
    for symbol in selected:
        sizes=[]
        for line in text.splitlines():
            row=line.split()
            if len(row)>=8 and row[-1]==symbol and row[3]=="FUNC" and (
                row[4]=="GLOBAL" and row[6]!="UND"
            ):
                try:sizes.append(int(row[2]))
                except ValueError:pass
        answer[symbol]=len(sizes)==1 and sizes[0]>0
    return answer

def audit(apk):
    if sha256_file(apk)!=APK_PIN:raise ValueError("APK_BASELINE_SHA_MISMATCH")
    with ZipFile(apk) as zipfile:
        bridge=extract_bridge(zipfile.read("classes.dex"))
        with tempfile.TemporaryDirectory(prefix="f43dev-p7-") as temp:
            native=Path(temp)/"native.so"
            with zipfile.open("lib/arm64-v8a/libbachata_native_runtime.so") as inp, native.open("wb") as out:
                for block in iter(lambda:inp.read(1_048_576),b""):out.write(block)
            if sha256_file(native)!=NATIVE_PIN:raise ValueError("NATIVE_RUNTIME_PIN_MISMATCH")
            symbols=subprocess.run(["readelf","-W","--dyn-syms",str(native)],
                capture_output=True,text=True,check=True).stdout
    exports=check_exports(symbols)
    return {
        "schema":"bachata-r2a6p7-jni-abi-static-v1",
        "apk_pinned_sha256":APK_PIN,
        "bionic_runtime_pinned_sha256":NATIVE_PIN,
        "native_bridge_class":NATIVE_CLASS,
        "run_method":bridge["run"],"stop_method":bridge["stop"],
        "expected_run_descriptor_matched":bridge["run"]["descriptor"]==RUN_PROTO,
        "expected_stop_descriptor_matched":bridge["stop"]["descriptor"]==STOP_PROTO,
        "native_export_run_present":exports[RUN_JNI],
        "native_export_stop_present":exports[STOP_JNI],
        "native_export_jni_onload_present":exports["JNI_OnLoad"],
        "android_host_source_available":False,
        "jni_abi_execution_verified_on_device":False,
        "android_broker_auth_verified_on_device":False,
        "fex_rootfs_runtime_mapping_verified_on_device":False,
        "apk_created_or_modified":False,
        "release_gate":"BLOCKED_AUTHORIZED_HOST_INTEGRATION_AND_LIVE_DEVICE"
    }

if __name__=="__main__":
    parser=argparse.ArgumentParser(description="Read-only F43DEV V2 JNI ABI audit")
    parser.add_argument("--apk",required=True,type=Path)
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    report=json.dumps(audit(args.apk),sort_keys=True,indent=2)+"\n"
    if args.output:args.output.write_text(report,encoding="utf-8")
    else:print(report,end="")
