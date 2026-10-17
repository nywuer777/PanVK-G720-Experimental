#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""24 synthetic DEX/JNI ABI tests. No original private APK in GitHub CI."""
import importlib.util
import pathlib
import struct
import unittest

spec=importlib.util.spec_from_file_location("bridge",pathlib.Path(__file__).with_name("audit_native_bridge.py"))
bridge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)
TYPES=[bridge.NATIVE_CLASS,"Landroid/view/Surface;","Z","[Ljava/lang/String;",
       "Ljava/lang/String;","I","V"]
STRINGS=TYPES+["run","stop"]

def uleb(n):
    out=bytearray()
    while True:
        value=n&127;n>>=7
        out.append(value | (128 if n else 0))
        if not n:return bytes(out)

def synthetic_dex(native=True,static=True,run_int=True,stop_void=True):
    data=bytearray(8192);data[:8]=b"dex\n039\0"
    def pair(index,count,offset):struct.pack_into("<II",data,index,count,offset)
    pair(0x38,len(STRINGS),112)
    t=112+4*len(STRINGS);pair(0x40,len(TYPES),t)
    p=t+4*len(TYPES);pair(0x48,2,p)
    m=p+24;pair(0x58,2,m)
    c=m+16;pair(0x60,1,c)
    cursor=c+32
    params=[1,2,3,3,4,5]
    po=cursor;struct.pack_into("<I",data,po,len(params))
    for i,x in enumerate(params):struct.pack_into("<H",data,po+4+i*2,x)
    cursor+=4+2*len(params)
    struct.pack_into("<III",data,p,0,5 if run_int else 6,po)
    struct.pack_into("<III",data,p+12,0,6 if stop_void else 5,0)
    struct.pack_into("<HHI",data,m,0,0,len(TYPES))
    struct.pack_into("<HHI",data,m+8,0,1,len(TYPES)+1)
    classdata=cursor
    flags=1 | (8 if static else 0) | (256 if native else 0)
    header=uleb(0)+uleb(0)+uleb(2)+uleb(0)
    data[cursor:cursor+len(header)]=header;cursor+=len(header)
    for idx in (0,1):
        record=uleb(idx)+uleb(flags)+uleb(0)
        data[cursor:cursor+len(record)]=record;cursor+=len(record)
    struct.pack_into("<IIIIIIII",data,c,0,1,0,0,0,0,classdata,0)
    for i in range(len(TYPES)):struct.pack_into("<I",data,t+4*i,i)
    for i,s in enumerate(STRINGS):
        raw=s.encode();part=uleb(len(raw))+raw+b"\0"
        struct.pack_into("<I",data,112+4*i,cursor)
        data[cursor:cursor+len(part)]=part;cursor+=len(part)
    data=data[:cursor]
    struct.pack_into("<I",data,32,len(data))
    return bytes(data)

GOOD=synthetic_dex()

class NativeAbiAuditTests(unittest.TestCase):
    def test_01_run_descriptor(self):
        self.assertEqual(bridge.extract_bridge(GOOD)["run"]["descriptor"],bridge.RUN_PROTO)
    def test_02_stop_descriptor(self):
        self.assertEqual(bridge.extract_bridge(GOOD)["stop"]["descriptor"],bridge.STOP_PROTO)
    def test_03_native_run(self):
        self.assertTrue(bridge.extract_bridge(GOOD)["run"]["native"])
    def test_04_native_stop(self):
        self.assertTrue(bridge.extract_bridge(GOOD)["stop"]["native"])
    def test_05_static_run(self):
        self.assertTrue(bridge.extract_bridge(GOOD)["run"]["static"])
    def test_06_static_stop(self):
        self.assertTrue(bridge.extract_bridge(GOOD)["stop"]["static"])
    def test_07_no_code(self):
        self.assertFalse(bridge.extract_bridge(GOOD)["run"]["has_bytecode"])
    def test_08_instance_not_static(self):
        self.assertFalse(bridge.extract_bridge(synthetic_dex(static=False))["run"]["static"])
    def test_09_java_not_native(self):
        self.assertFalse(bridge.extract_bridge(synthetic_dex(native=False))["run"]["native"])
    def test_10_bad_run_return_type(self):
        self.assertNotEqual(bridge.extract_bridge(synthetic_dex(run_int=False))["run"]["descriptor"],bridge.RUN_PROTO)
    def test_11_bad_stop_return_type(self):
        self.assertNotEqual(bridge.extract_bridge(synthetic_dex(stop_void=False))["stop"]["descriptor"],bridge.STOP_PROTO)
    def test_12_bad_magic(self):
        with self.assertRaisesRegex(ValueError,"DEX_BAD_HEADER"):bridge.extract_bridge(b"bad")
    def test_13_bad_length(self):
        b=bytearray(GOOD);struct.pack_into("<I",b,32,7)
        with self.assertRaisesRegex(ValueError,"DEX_BAD_HEADER"):bridge.extract_bridge(bytes(b))
    def test_14_table_out_of_bounds(self):
        b=bytearray(GOOD);struct.pack_into("<I",b,0x44,0xffffffff)
        with self.assertRaisesRegex(ValueError,"DEX_BAD_TABLE"):bridge.extract_bridge(bytes(b))
    def test_15_bad_string_index(self):
        b=bytearray(GOOD);struct.pack_into("<I",b,112,0xfffffffe)
        with self.assertRaisesRegex(ValueError,"DEX_BAD_STRING_OFFSET"):bridge.extract_bridge(bytes(b))
    def test_16_bad_method_index(self):
        b=bytearray(GOOD);mo=struct.unpack_from("<I",b,0x5c)[0]
        struct.pack_into("<H",b,mo,0xffff)
        with self.assertRaisesRegex(ValueError,"DEX_BAD_METHOD"):bridge.extract_bridge(bytes(b))
    def test_17_exports_present(self):
        names=(bridge.RUN_JNI,bridge.STOP_JNI,"JNI_OnLoad")
        rows="\n".join(f"{i}: deadbeef 100 FUNC GLOBAL DEFAULT 15 {name}" for i,name in enumerate(names,1))
        self.assertTrue(all(bridge.check_exports(rows).values()))
    def test_18_undefined_not_exported(self):
        self.assertFalse(bridge.check_exports(f"1: 00000000 0 FUNC GLOBAL DEFAULT UND {bridge.RUN_JNI}")[bridge.RUN_JNI])
    def test_19_duplicate_symbol_rejected(self):
        r=f"1: deadbeef 100 FUNC GLOBAL DEFAULT 15 {bridge.RUN_JNI}"
        self.assertFalse(bridge.check_exports(r+"\n"+r)[bridge.RUN_JNI])
    def test_20_jni_onload_required(self):
        self.assertFalse(bridge.check_exports("")["JNI_OnLoad"])
    def test_21_strict_pin_size(self):
        self.assertEqual(len(bridge.APK_PIN),64)
    def test_22_library_pin_size(self):
        self.assertEqual(len(bridge.NATIVE_PIN),64)
    def test_23_two_string_arrays(self):
        self.assertEqual(bridge.RUN_PROTO.count("[Ljava/lang/String;"),2)
    def test_24_no_single_string_shortcut(self):
        self.assertNotEqual(bridge.RUN_PROTO,"(Ljava/lang/String;)I")

if __name__=="__main__":unittest.main()
