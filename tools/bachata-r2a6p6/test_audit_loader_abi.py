#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic-only audit utility tests. Never load or upload private APK in CI."""
import importlib.util
import pathlib
import unittest

path=pathlib.Path(__file__).with_name("audit_loader_abi.py")
spec=importlib.util.spec_from_file_location("a6p6_audit",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class LoaderVerifier(unittest.TestCase):
    def test_01_sha(self):
        self.assertEqual(mod.sha256(b"abc"),"ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad")
    def test_02_aarch64_machine(self):
        raw=bytearray(64);raw[:6]=b"\x7fELF\x02\x01";raw[18:20]=(183).to_bytes(2,"little")
        self.assertEqual(mod.parse_elf_machine(raw),183)
    def test_03_x86_machine_distinct(self):
        raw=bytearray(64);raw[:6]=b"\x7fELF\x02\x01";raw[18:20]=(62).to_bytes(2,"little")
        self.assertEqual(mod.parse_elf_machine(raw),62)
    def test_04_invalid_arch(self):
        with self.assertRaisesRegex(ValueError,"INVALID_ELF"):
            mod.parse_elf_machine(b"not an ELF")
    def test_05_wrong_class(self):
        raw=bytearray(64);raw[:6]=b"\x7fELF\x01\x01"
        with self.assertRaisesRegex(ValueError,"INVALID_ELF"):
            mod.parse_elf_machine(raw)
    def test_06_soname(self):
        self.assertEqual(mod.parse_soname("0x000000000000000e (SONAME) Library soname: [ld-linux-aarch64.so.1]"),"ld-linux-aarch64.so.1")
    def test_07_missing_soname(self):
        with self.assertRaisesRegex(ValueError,"SONAME_NOT_UNIQUE"):
            mod.parse_soname("nothing here")
    def test_08_two_sonames(self):
        with self.assertRaisesRegex(ValueError,"SONAME_NOT_UNIQUE"):
            mod.parse_soname("Library soname: [A]\nLibrary soname: [B]")
    def test_09_needed(self):
        x="Shared library: [libm.so.6]\nShared library: [libc.so.6]"
        self.assertEqual(mod.parse_needed(x),["libc.so.6","libm.so.6"])
    def test_10_no_dependencies(self):
        self.assertEqual(mod.parse_needed("nothing"),[])
    def test_11_interp(self):
        self.assertEqual(mod.parse_interp("INTERP\n[Requesting program interpreter: /lib/ld-linux-aarch64.so.1]"),mod.INTERP)
    def test_12_missing_interp(self):
        with self.assertRaisesRegex(ValueError,"INTERPRETER_NOT_UNIQUE"):
            mod.parse_interp("No program interpreter")
    def test_13_manifest_size_and_hash(self):
        data=b"synthetic-rtld"
        manifest={"files":[{"path":"host/ld-linux-aarch64.so.1","size":len(data),"sha256":mod.sha256(data)}]}
        self.assertTrue(mod.check_manifest(manifest,"host/ld-linux-aarch64.so.1",data))
    def test_14_manifest_reject_tamper(self):
        manifest={"files":[{"path":"host/ld-linux-aarch64.so.1","size":1,"sha256":mod.sha256(b"synthetic")}]}
        self.assertFalse(mod.check_manifest(manifest,"host/ld-linux-aarch64.so.1",b"tampered"))
    def test_15_manifest_reject_wrong_path(self):
        manifest={"files":[{"path":"host/foo","size":1,"sha256":mod.sha256(b"x")}]}
        self.assertFalse(mod.check_manifest(manifest,"host/ld-linux-aarch64.so.1",b"x"))
    def test_16_manifest_reject_duplicate(self):
        data=b"x"; item={"path":"host/ld-linux-aarch64.so.1","size":1,"sha256":mod.sha256(data)}
        self.assertFalse(mod.check_manifest({"files":[item,item]},"host/ld-linux-aarch64.so.1",data))
    def test_17_manifest_reject_missing_files(self):
        self.assertFalse(mod.check_manifest({},"host/ld-linux-aarch64.so.1",b"x"))
    def test_18_expected_pins_distinct(self):
        self.assertNotEqual(mod.LOADER_SHA,mod.NATIVE_SHA)
        self.assertNotEqual(mod.NATIVE_SHA,mod.BASELINE_SHA)
        self.assertNotEqual(mod.APK_SHA,mod.BASELINE_SHA)
    def test_19_interpreter_explicit(self):
        self.assertEqual(mod.INTERP,"/lib/ld-linux-aarch64.so.1")
    def test_20_loader_soname_not_bionic(self):
        self.assertNotEqual("ld-linux-aarch64.so.1","libbachata_native_runtime.so")

if __name__=="__main__":
    unittest.main()
