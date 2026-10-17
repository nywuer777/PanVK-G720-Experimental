#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("device_evidence", Path(__file__).with_name("device_evidence.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

H, HE, ST = module.HOST, module.HELLO, module.START
OK, BAD = module.STOP_OK, module.STOP_FAIL
ERROR = module.HOST_ERROR
FILE = "BSF1_LAB_PROBE_FILE_OK"
DIRECTORY = "BSF1_LAB_PROBE_DIRECTORY_OK"
FAIL = "BSF1_LAB_PROBE_STAT_FAILED"

def sample(*entries): return "\n".join(entries) + "\n"

class CheckCuratedEvents(unittest.TestCase):
    def assert_safe(self, events, expected):
        result = module.check(events)
        self.assertEqual(result["status"], expected)
        self.assertFalse(result["real_broker_verified"])
        self.assertFalse(result["apk_signature_verified"])
        self.assertFalse(result["source_authenticated"])
        self.assertNotIn("0123456789abcdef0123456789abcdef", str(result))
        return result

    def test_file_ok(self):
        self.assert_safe(sample(H,HE,ST,FILE,OK), "CONSISTENT_UNATTESTED_EVENTS")
    def test_directory_ok(self):
        self.assert_safe(sample(H,HE,ST,DIRECTORY,OK), "CONSISTENT_UNATTESTED_EVENTS")
    def test_failure(self):
        self.assert_safe(sample(H,HE,ST,FAIL,ERROR,BAD), "CONSISTENT_UNATTESTED_EVENTS")
    def test_classified_failure(self):
        self.assert_safe(sample(H,HE,ST,FAIL+" BSF1_DIAG_REMOTE_REJECTED",ERROR,BAD),
                         "CONSISTENT_UNATTESTED_EVENTS")
    def test_classified_success(self):
        self.assert_safe(sample(H,HE,ST,FILE+" BSF1_DIAG_NONE",OK),
                         "CONSISTENT_UNATTESTED_EVENTS")
    def test_fake_success_error_code(self):
        self.assert_safe(sample(H,HE,ST,FILE+" BSF1_DIAG_IO_FAILURE",OK), "REJECTED")
    def test_failure_none(self):
        self.assert_safe(sample(H,HE,ST,FAIL+" BSF1_DIAG_NONE",ERROR,BAD), "REJECTED")
    def test_skips_host(self):
        self.assert_safe(sample(HE,ST,FILE,OK), "REJECTED")
    def test_skips_hello(self):
        self.assert_safe(sample(H,ST,FILE,OK), "REJECTED")
    def test_skips_starting(self):
        self.assert_safe(sample(H,HE,FILE,OK), "REJECTED")
    def test_multiple_probes(self):
        self.assert_safe(sample(H,HE,ST,FILE,DIRECTORY,OK), "REJECTED")
    def test_reversed_order(self):
        self.assert_safe(sample(HE,H,ST,FILE,OK), "REJECTED")
    def test_incorrect_exit_code(self):
        self.assert_safe(sample(H,HE,ST,FILE,BAD), "REJECTED")
    def test_failure_without_error(self):
        self.assert_safe(sample(H,HE,ST,FAIL,BAD), "REJECTED")
    def test_arbitrary_filename_rejected(self):
        self.assert_safe(sample(H,HE,ST,"file=eboot.bin",FILE,OK), "REJECTED")
    def test_token_leak_rejected(self):
        self.assert_safe(sample(H,HE,ST,"--bachata-saf-token 0123456789abcdef0123456789abcdef",FILE,OK),
                         "REJECTED")
    def test_traversal_rejected(self):
        self.assert_safe(sample(H,HE,ST,"../data/user/0",FILE,OK), "REJECTED")
    def test_unsupported_marker(self):
        self.assert_safe(sample(H,HE,ST,"BSF1_LAB_PROBE_FILE_BYPASS",OK), "REJECTED")
    def test_whitespace(self):
        self.assert_safe(sample(H,HE,ST,FILE,OK)+"\n ", "REJECTED")
    def test_duplicate_host(self):
        self.assert_safe(sample(H,H,HE,ST,FILE,OK), "REJECTED")
    def test_large_input(self):
        self.assert_safe(sample(H,HE,ST,FILE,OK)+("A"*4096), "REJECTED")
    def test_secret_must_not_appear_in_safe_report(self):
        secret="0123456789abcdef0123456789abcdef"
        report=self.assert_safe(sample(H,HE,ST,FILE,OK)+"--secret="+secret+"\n","REJECTED")
        self.assertNotIn(secret, str(report))

if __name__ == "__main__":
    unittest.main()
