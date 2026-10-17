#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Synthetic Dalvik instruction tests; no original DEX or APK in CI."""
import unittest
import audit_callsite as a

TARGET={101:"run",102:"stop"}

def scan(words):
    records=[];i=0
    while i<len(words):
        opcode=words[i]&255
        size=a.instructions(words,i)
        if size<=0 or i+size>len(words):raise ValueError("INSN_BOUNDS")
        if opcode in (0x71,0x77) and words[i+1] in TARGET:
            records.append((TARGET[words[i+1]],opcode,
                words[i]>>8 if opcode==0x77 else words[i]>>12))
        i+=size
    return records

class TestSyntheticDalvik(unittest.TestCase):
    def test_01_static_range(self):self.assertEqual(scan([0x677,101,2]),[("run",0x77,6)])
    def test_02_static(self):self.assertEqual(scan([0x71,102,0]),[("stop",0x71,0)])
    def test_03_ignored_reference(self):self.assertEqual(scan([0x677,5,2]),[])
    def test_04_no_invocation(self):self.assertEqual(scan([0x0e]),[])
    def test_05_multiple(self):self.assertEqual(len(scan([0x677,101,2,0x71,102,0])),2)
    def test_06_value_in_const_not_call(self):self.assertEqual(scan([0x14,0x677,101]),[])
    def test_07_method_id_in_const_not_call(self):self.assertEqual(scan([0x13,101]),[])
    def test_08_nonstatic_call_rejected(self):self.assertEqual(scan([0x676,101,2]),[])
    def test_09_truncated_call(self):
        with self.assertRaisesRegex(ValueError,"INSN_BOUNDS"):scan([0x677,101])
    def test_10_reserved_opcode(self):
        with self.assertRaisesRegex(ValueError,"RESERVED_OPCODE"):scan([0x73])
    def test_11_payload_packed(self):self.assertEqual(a.instructions([0x0100,3],0),10)
    def test_12_payload_sparse(self):self.assertEqual(a.instructions([0x0200,3],0),14)
    def test_13_array_payload(self):self.assertEqual(a.instructions([0x0300,1,5,0],0),7)
    def test_14_array_bad_element_size(self):
        with self.assertRaisesRegex(ValueError,"ARRAY_SIZE"):a.instructions([0x0300,10,1,0],0)
    def test_15_array_truncated(self):
        with self.assertRaisesRegex(ValueError,"ARRAY_TRUNC"):a.instructions([0x0300,1],0)
    def test_16_bad_dex_header(self):
        with self.assertRaisesRegex(ValueError,"INVALID_DEX"):a.decode(b"hello")
    def test_17_uleb_single(self):self.assertEqual(a.uleb(bytes([7]),0),(7,1))
    def test_18_uleb_multibyte(self):self.assertEqual(a.uleb(bytes([0x80,1]),0),(128,2))
    def test_19_uleb_truncated(self):
        with self.assertRaisesRegex(ValueError,"TRUNCATED_ULEB"):a.uleb(bytes([0x80]),0)
    def test_20_no_match(self):self.assertEqual(a.exact_argument_origin([0x0e],[],[],1),"NO_MATCH")
    def test_21_wrong_shape(self):
        self.assertEqual(a.exact_argument_origin([0x71,0,0],[("Lx;","f","()V")],[],0),"UNSUPPORTED_INVOKE_SHAPE")
    def test_22_nonattested_registers(self):
        self.assertEqual(a.exact_argument_origin([0x677,0,2],[("Lx;","f","()V")],[],0),"REGISTER_OR_BRANCH_ORIGIN_UNVERIFIED")
    def test_23_hex_pin(self):self.assertEqual(len(a.APK_SHA),64)
    def test_24_array_parameters(self):self.assertEqual(a.RUN.count("[Ljava/lang/String;"),2)
    def test_25_return_type(self):self.assertTrue(a.RUN.endswith(")I"))
    def test_26_two_register_move(self):self.assertEqual(a.instructions([0x701],0),1)
    def test_27_invoke_width(self):self.assertEqual(a.instructions([0x106e,101,0],0),3)
    def test_28_goto_width(self):self.assertEqual(a.instructions([0x28],0),1)
    def test_29_iget_width(self):self.assertEqual(a.instructions([0x54,44],0),2)
    def test_30_no_token_literal(self):self.assertNotIn("bachata-saf-token",a.RUN)

if __name__=="__main__":unittest.main()
