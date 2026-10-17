import importlib.util, tempfile, unittest, zipfile, json
from pathlib import Path

p=Path(__file__).with_name('p32_reachability.py')
spec=importlib.util.spec_from_file_location('gate',p)
gate=importlib.util.module_from_spec(spec);spec.loader.exec_module(gate)
ROOT=Path(__file__).resolve().parent
KIT=ROOT/'inputs/P29_SOURCE_KIT.zip'
PATCH=ROOT/'inputs/P30_APPLIED_PATCH.diff'
RESULT=ROOT/'inputs/P30_COMPILED_RESULT.json'

class GateTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.real=gate.analyze(KIT,PATCH,RESULT)
    def test_compiler_executed(self):self.assertTrue(self.real['glibc_aarch64_compiled'])
    def test_bcn_adapter_present(self):self.assertTrue(self.real['p27_decoder_present_in_build'])
    def test_async_adapter_present(self):self.assertTrue(self.real['p28_async_adapter_present_in_build'])
    def test_missing_main_callsite(self):self.assertEqual(self.real['bcn_external_callsite_count'],0)
    def test_texture_refresh_unchanged(self):self.assertFalse(self.real['texture_cache_refresh_path_modified'])
    def test_alias_diagnostic_only(self):self.assertTrue(self.real['alias_policy_diagnostic_only'])
    def test_alias_classifier_reached_when_enabled(self):self.assertGreater(self.real['alias_classifier_calls_in_patch'],0)
    def test_outlast_not_fixed(self):self.assertFalse(self.real['outlast_fixed'])
    def test_minecraft_not_fixed(self):self.assertFalse(self.real['minecraft_fixed'])
    def test_apk_not_released(self):self.assertFalse(self.real['candidate_approved_for_apk'])
    def test_release_gate_blocks(self):self.assertEqual(self.real['release_gate'],'BLOCKED')
    def test_patch_parser(self):
        result=gate.diff_added_lines('+++ b/a.cpp\n@@ -1 +1 @@\n+  BachataP28::RecordDecodedUpload();\n')
        self.assertEqual(result,{'a.cpp':['  BachataP28::RecordDecodedUpload();']})
    def test_changed_file_parser(self):
        parsed=gate.diff_added_lines('--- a/a\n+++ b/b\n+x\n--- a/b\n+++ b/c\n+y')
        self.assertEqual(parsed,{'b':['x'],'c':['y']})
    def test_reject_tampered_elf_hash(self):
        with tempfile.TemporaryDirectory() as temp:
            data=json.loads(RESULT.read_text());data['elf']['sha256']='0'*64
            q=Path(temp)/'result.json';q.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError,'UNRECOGNIZED_COMPILER_RESULT'):gate.analyze(KIT,PATCH,q)
    def test_reject_unproven_build(self):
        with tempfile.TemporaryDirectory() as temp:
            data=json.loads(RESULT.read_text());data['full_core_compile_passed']=False
            q=Path(temp)/'result.json';q.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError,'P30_BUILD_NOT_PROVEN'):gate.analyze(KIT,PATCH,q)
    def test_reject_wrong_source_revision(self):
        with tempfile.TemporaryDirectory() as temp:
            data=json.loads(RESULT.read_text());data['source_revision']='wrong'
            q=Path(temp)/'result.json';q.write_text(json.dumps(data))
            with self.assertRaisesRegex(RuntimeError,'WRONG_SOURCE_PIN'):gate.analyze(KIT,PATCH,q)
    def test_reject_bad_kit(self):
        with tempfile.TemporaryDirectory() as temp:
            with zipfile.ZipFile(Path(temp)/'kit.zip','w') as z:z.writestr('foo','bar')
            with self.assertRaisesRegex(RuntimeError,'MISSING_KIT_MEMBER'):gate.analyze(Path(temp)/'kit.zip',PATCH,RESULT)
    def test_missing_caller_although_symbol_defined(self):
        parsed=gate.diff_added_lines('+++ b/new.cpp\n+UploadResult RecordDecodedUpload(const Plan&) { return {}; }')
        self.assertNotIn('src/video_core/texture_cache/texture_cache.cpp',parsed)
    def test_regex_recognizes_real_call(self):
        self.assertTrue(gate.BCN_RE.search('  BachataP28::RecordDecodedUpload(plan,image);'))
    def test_no_bcn_marker_leak(self):self.assertNotIn('guest_address',json.dumps(self.real))

if __name__=='__main__':unittest.main()