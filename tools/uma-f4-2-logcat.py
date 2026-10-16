#!/usr/bin/env python3
"""F4.2: Logcat mirror for diagnostics only; apply after F4.1.1."""
import argparse
import difflib
from pathlib import Path
SRC="src/panfrost/vulkan/csf/panvk_vX_gpu_queue.c"
PRELUDE=r"""
/* F4.2-only diagnostic relay: does not alter Vulkan/CSF/UMA operations. */
#define PANVK_F42_BUILD_ID "G720-UMA-F4.2-LOGCAT-20261016"
static void panvk_f42_emit(const char *fmt, ...)
{
   char line[1024];
   va_list args;
   va_start(args, fmt);
   int result = vsnprintf(line, sizeof(line), fmt, args);
   va_end(args);
   if (result < 0)
      return;
   fputs(line, stderr);
#if defined(__ANDROID__)
   size_t length = strlen(line);
   if (length > 0 && line[length - 1] == '\n')
      line[length - 1] = '\0';
   __android_log_write(ANDROID_LOG_INFO, "PanVK_F42", line);
#endif
}
__attribute__((constructor)) static void
panvk_f42_on_load(void)
{
   panvk_f42_emit("PANVK-F4.2 LIB_LOADED build=%s\n", PANVK_F42_BUILD_ID);
   fflush(stderr);
}
"""
def once(s,old,new):
    n=s.count(old)
    if n!=1: raise ValueError("F4.2 guarded anchor failed: %d %s" % (n,old[:80]))
    return s.replace(old,new,1)
def apply(s):
    assert s.count("PANVK-F4.1.1")==4
    assert s.count('fprintf(stderr, "PANVK-')==5
    assert s.count("fflush(stderr);")==5
    assert "PANVK-F4.2 LIB_LOADED" not in s
    s=once(s,"#include <stdio.h>\n","#include <stdio.h>\n#include <stdarg.h>\n#include <string.h>\n#if defined(__ANDROID__)\n#include <android/log.h>\n#endif\n")
    s=once(s,"/* UMA F4-DIAG:",PRELUDE+"/* UMA F4-DIAG:")
    s=s.replace('fprintf(stderr, "PANVK-','panvk_f42_emit("PANVK-')
    assert s.count('panvk_f42_emit("PANVK-F4.1.1')==4
    assert s.count('panvk_f42_emit("PANVK-F4 submits=')==1
    assert s.count('fprintf(stderr, "PANVK-')==0
    assert s.count("fflush(stderr);")==6
    return s
def test():
    src=("#include <stdio.h>\n/* UMA F4-DIAG: test */\n"+
         "".join('fprintf(stderr, "PANVK-F4.1.1 E%d\\n", 1);\n'%i for i in range(4))+
         'fprintf(stderr, "PANVK-F4 submits=1\\n");\n'+"fflush(stderr);\n"*5)
    out=apply(src)
    assert 'PANVK-F4.2 LIB_LOADED' in out
    assert '__android_log_write(ANDROID_LOG_INFO, "PanVK_F42", line)' in out
    try: apply(out)
    except (AssertionError,ValueError): pass
    else: raise AssertionError("Double application must fail")
    print("F4.2 relay self-test OK")
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--self-test",action="store_true")
    p.add_argument("--source",type=Path,default=Path(SRC))
    p.add_argument("--diff",type=Path)
    a=p.parse_args()
    if a.self_test: test();return
    old=a.source.read_text()
    new=apply(old)
    if a.diff:
        a.diff.parent.mkdir(exist_ok=True,parents=True)
        a.diff.write_text("".join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile="a/"+SRC,tofile="b/"+SRC)))
    a.source.write_text(new)
if __name__=="__main__":main()
