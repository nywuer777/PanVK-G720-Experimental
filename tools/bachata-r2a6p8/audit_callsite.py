#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Pinned F43DEV V2 DEX callsite inspection. No Android runtime or secrets.

Output: static method invocation counts, anonymized register provenance,
failure sentinel observation. Does NOT prove argument semantics or live JNI.
"""
import argparse
import hashlib
import json
import struct
from pathlib import Path
from zipfile import ZipFile

APK_SHA = "e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded"
CLASS = "Lcom/bachatas4/android/runtime/process/NativeRuntimeBridge;"
RUN = "(Landroid/view/Surface;Z[Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;I)I"

def uleb(data, cursor):
    result = 0
    for shift in range(0, 35, 7):
        if cursor >= len(data): raise ValueError("TRUNCATED_ULEB")
        x = data[cursor]
        cursor += 1
        result |= (x & 127) << shift
        if not x & 128: return result, cursor
    raise ValueError("INVALID_ULEB")

def table(data, position, stride):
    n, start = struct.unpack_from("<II", data, position)
    if n > 1000000 or start + n * stride > len(data):
        raise ValueError("DEX_TABLE_BOUNDS")
    return n, start

def decode(data):
    if not (len(data)>=112 and data.startswith(b"dex\n") and data[7]==0 and
            struct.unpack_from("<I", data, 32)[0]==len(data)):
        raise ValueError("INVALID_DEX")
    n,o = table(data, 0x38, 4)
    strings=[]
    for i in range(n):
        pos=struct.unpack_from("<I",data,o+4*i)[0]
        if pos>=len(data):raise ValueError("STRING_BOUNDS")
        _,pos=uleb(data,pos)
        end=data.find(b"\0",pos)
        if end<0 or end-pos>65535:raise ValueError("STRING_BOUNDS")
        strings.append(data[pos:end].decode("utf-8","replace"))
    n,o=table(data,0x40,4)
    types=[]
    for i in range(n):
        index=struct.unpack_from("<I",data,o+4*i)[0]
        if index>=len(strings):raise ValueError("TYPE_BOUNDS")
        types.append(strings[index])
    n,o=table(data,0x48,12)
    protos=[]
    for i in range(n):
        _,r,params=struct.unpack_from("<III",data,o+12*i)
        if r>=len(types):raise ValueError("PROTO_BOUNDS")
        args=[]
        if params:
            if params+4>len(data):raise ValueError("PARAM_BOUNDS")
            count=struct.unpack_from("<I",data,params)[0]
            if count>256 or params+4+count*2>len(data):raise ValueError("PARAM_BOUNDS")
            for j in range(count):
                idx=struct.unpack_from("<H",data,params+4+j*2)[0]
                if idx>=len(types):raise ValueError("PARAM_BOUNDS")
                args.append(types[idx])
        protos.append("("+"".join(args)+")"+types[r])
    n,o=table(data,0x58,8)
    methods=[]
    for i in range(n):
        c,p,name=struct.unpack_from("<HHI",data,o+8*i)
        if c>=len(types) or p>=len(protos) or name>=len(strings):
            raise ValueError("METHOD_BOUNDS")
        methods.append((types[c],strings[name],protos[p]))
    n,o=table(data,0x50,8)
    fields=[]
    for i in range(n):
        c,t,name=struct.unpack_from("<HHI",data,o+8*i)
        if c>=len(types) or t>=len(types) or name>=len(strings):
            raise ValueError("FIELD_BOUNDS")
        fields.append((types[c],types[t],strings[name]))
    return types,methods,fields

def instructions(words,index):
    op=words[index]&255
    if op==0:
        kind=words[index]>>8
        if kind==0:return 1
        if kind in (1,2):
            if index+2>len(words):raise ValueError("SWITCH_TRUNC")
            return (4+2*words[index+1]) if kind==1 else (2+4*words[index+1])
        if kind==3:
            if index+4>len(words):raise ValueError("ARRAY_TRUNC")
            size=words[index+2]|(words[index+3]<<16)
            width=words[index+1]
            if width>8 or size>50000000:raise ValueError("ARRAY_SIZE")
            return 4+(size*width+1)//2
        raise ValueError("PAYLOAD_INVALID")
    if op==0x18:return 5
    if op in (0xfa,0xfb):return 4
    if op in (0x03,0x06,0x09,0x14,0x17,0x1b,0x24,0x25,0x26,0x2a,0x2b,0x2c,0xfc,0xfd) or (0x6e<=op<=0x72) or (0x74<=op<=0x78):return 3
    if op in (0x02,0x05,0x08,0x13,0x15,0x16,0x19,0x1a,0x1c,0x1f,0x20,0x22,0x23,0x29,0xfe,0xff) or (0x2d<=op<=0x3d) or (0x44<=op<=0x6d) or (0x90<=op<=0xaf) or (0xd0<=op<=0xe2):return 2
    if op==0x73 or 0x3e<=op<=0x43 or 0x79<=op<=0x7a or 0xe3<=op<=0xf9:raise ValueError("RESERVED_OPCODE")
    return 1

def enumerate_bodies(data,types,methods):
    n,o=table(data,0x60,32)
    for i in range(n):
        cid,_,_,_,_,_,pos,_=struct.unpack_from("<IIIIIIII",data,o+i*32)
        if cid>=len(types):raise ValueError("CLASS_BOUNDS")
        if not pos:continue
        if pos>=len(data):raise ValueError("CLASS_OFFSET")
        counts=[]
        for _ in range(4):
            size,pos=uleb(data,pos)
            if size>100000:raise ValueError("CLASS_SIZE")
            counts.append(size)
        for c in counts[:2]:
            for _ in range(c):
                _,pos=uleb(data,pos);_,pos=uleb(data,pos)
        for c in counts[2:]:
            mid=0
            for _ in range(c):
                diff,pos=uleb(data,pos);_,pos=uleb(data,pos);offset,pos=uleb(data,pos)
                mid+=diff
                if mid>=len(methods):raise ValueError("CLASS_METHOD_INDEX")
                if not offset:continue
                if offset+16>len(data):raise ValueError("CODE_BOUNDS")
                size=struct.unpack_from("<I",data,offset+12)[0]
                if size>2000000 or offset+16+2*size>len(data):
                    raise ValueError("CODE_BOUNDS")
                yield methods[mid],struct.unpack_from(f"<{size}H",data,offset+16)

def exact_argument_origin(words,methods,fields,target):
    provenance={}
    last=None
    i=0
    while i<len(words):
        op=words[i]&255
        size=instructions(words,i)
        if size<=0 or i+size>len(words):raise ValueError("INSN_BOUNDS")
        if op in (0x71,0x77) and words[i+1]==target:
            count=(words[i]>>8) if op==0x77 else (words[i]>>12)
            start=words[i+2] if op==0x77 else -1
            if op!=0x77 or count!=6 or start!=2:
                return "UNSUPPORTED_INVOKE_SHAPE"
            expected=[
                ("field","Lp42;","Landroid/view/Surface;","f"),
                ("result","Lcom/bachatas4/android/runtime/process/NativeRuntimeService;","a","()Z"),
                ("field","Lp42;","[Ljava/lang/String;","g"),
                ("field","Lp42;","[Ljava/lang/String;","h"),
                ("field","Lp42;","Ljava/lang/String;","i")]
            # The original run() has an exceptional path forwarding -1 rather
            # than a detached descriptor; linear register dataflow alone
            # CANNOT establish v7, so explicitly verify both path patterns.
            branch=(len(words)>41 and words[28]==0xfe12 and
                words[29]&255==0x38 and words[31]&255==0x6e and
                words[34]&255==0x0a and words[35]==0x0701 and
                words[36]&255==0x28 and words[40]==0xe701 and
                words[32]<len(methods) and
                methods[words[32]]==("Landroid/os/ParcelFileDescriptor;","detachFd","()I"))
            return "VERIFIED_ORIGINS_WITH_FD_OR_MINUS_ONE" if (
                [provenance.get(j) for j in range(2,7)]==expected and branch
                ) else "REGISTER_OR_BRANCH_ORIGIN_UNVERIFIED"
        if op==0x54:
            idx=words[i+1]
            provenance[(words[i]>>8)&15]=("field",*fields[idx]) if idx<len(fields) else None
            last=None
        elif op in (*range(0x6e,0x73),*range(0x74,0x79)):
            idx=words[i+1]
            last=("result",*methods[idx]) if idx<len(methods) else None
        elif op in (0x0a,0x0b,0x0c):
            provenance[(words[i]>>8)&255]=last
            last=None
        elif op==0x01:
            provenance[(words[i]>>8)&15]=provenance.get((words[i]>>12)&15)
            last=None
        else:last=None
        i+=size
    return "NO_MATCH"

def audit_dex(data):
    types,methods,fields=decode(data)
    ids={i:v[1] for i,v in enumerate(methods) if v[0]==CLASS and (
        (v[1]=="run" and v[2]==RUN) or (v[1]=="stop" and v[2]=="()V"))}
    if len(ids)!=2 or set(ids.values())!={"run","stop"}:
        raise ValueError("JNI_METHODS_NOT_UNIQUE")
    constructors={i for i,method in enumerate(methods)
                  if method[0]=="Lp42;" and method[1]=="<init>" and
                  method[2]=="(Landroid/os/ParcelFileDescriptor;Lcom/bachatas4/android/runtime/process/NativeRuntimeService;Landroid/view/Surface;[Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;Lq42;Lsc1;Lh42;)V"}
    if len(constructors)!=1:raise ValueError("JNI_RUNNER_CONSTRUCTOR_NOT_UNIQUE")
    results=[];constructor_sites=[];count=0
    for owner,words in enumerate_bodies(data,types,methods):
        count+=1
        i=0
        while i<len(words):
            op=words[i]&255;size=instructions(words,i)
            if size<=0 or i+size>len(words):raise ValueError("INSN_BOUNDS")
            if op in (0x70,0x76) and words[i+1] in constructors:
                constructor_sites.append({"caller_class":owner[0],
                    "caller_method":owner[1],"caller_descriptor":owner[2],
                    "argument_words":words[i]>>8 if op==0x76 else words[i]>>12,
                    "invoke_range":op==0x76})
            if op in (0x71,0x77) and words[i+1] in ids:
                idx=words[i+1]
                row={"native":ids[idx],"caller_class":owner[0],
                     "caller_method":owner[1],"invoke_opcode":
                     "static/range" if op==0x77 else "static",
                     "argc_words":words[i]>>8 if op==0x77 else words[i]>>12}
                if ids[idx]=="run":
                    row["origins_status"]=exact_argument_origin(words,methods,fields,idx)
                results.append(row)
            i+=size
    return {"schema":"bachata-f43dev-r2a6p8-callsite-v1",
            "run_callsite_count":sum(r["native"]=="run" for r in results),
            "stop_callsite_count":sum(r["native"]=="stop" for r in results),
            "dex_method_bodies_scanned":count,
            "runner_constructor_callsites":constructor_sites,
            "runner_constructor_chain_confirmed":len(constructor_sites)==1 and
                constructor_sites[0]["caller_class"]=="Lq42;" and
                constructor_sites[0]["caller_method"]=="c" and
                constructor_sites[0]["argument_words"]==10 and
                constructor_sites[0]["invoke_range"],
            "callsites":results,"real_device_test":False,
            "jni_parameter_meaning_completely_known":False,
            "apk_signature_verified":False,"saf_broker_verified":False,
            "android_original_host_source_provided":False}

def main():
    ap=argparse.ArgumentParser(description="Read-only pinned F43DEV V2 JNI callsite audit")
    ap.add_argument("--apk",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    h=hashlib.sha256()
    with a.apk.open("rb") as stream:
        for block in iter(lambda:stream.read(1048576),b""):h.update(block)
    if h.hexdigest()!=APK_SHA:raise ValueError("APK_BASELINE_SHA_MISMATCH")
    with ZipFile(a.apk) as apk:r=audit_dex(apk.read("classes.dex"))
    r["apk_pinned_sha256"]=APK_SHA
    encoded=json.dumps(r,sort_keys=True,indent=2)+"\n"
    if a.output:a.output.write_text(encoded,encoding="utf-8")
    else:print(encoded,end="")

if __name__=="__main__":main()
