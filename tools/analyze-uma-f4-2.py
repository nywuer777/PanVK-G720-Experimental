#!/usr/bin/env python3
"""Inspect F4.2 Logcat and Bachata diagnostic text/ZIP."""
import argparse
import zipfile
from pathlib import Path
MARKERS={"loaded":"PANVK-F4.2 LIB_LOADED build=G720-UMA-F4.2-LOGCAT-20261016","ready":"PANVK-F4.1.1 READY","submit":"PANVK-F4.1.1 QUEUE_SUBMIT_ENTRY","kbase":"PANVK-F4.1.1 KBASE_SUBMIT_ENTER","progress":"PANVK-F4.1.1 PROGRESS","profile":"PANVK-F4 submits="}
def contents(file):
    if zipfile.is_zipfile(file):
        with zipfile.ZipFile(file) as z:
            for i in z.infolist():
                if not i.is_dir() and i.file_size<40000000 and i.filename.endswith((".txt",".log")):
                    yield z.read(i).decode("utf-8","replace")
    else: yield Path(file).read_text(errors="replace")
def counts(texts):
    out={x:0 for x in MARKERS}
    for t in texts:
        for line in t.splitlines():
            for key,val in MARKERS.items():
                if val in line:out[key]+=1
    return out
def main():
    p=argparse.ArgumentParser()
    p.add_argument("file",nargs="?")
    p.add_argument("--self-test",action="store_true")
    a=p.parse_args()
    if a.self_test:
        r=counts(["\n".join(MARKERS.values())])
        assert all(v==1 for v in r.values())
        print("F4.2 analyzer self-test OK");return
    if not a.file:p.error("Provide Logcat TXT or Bachata ZIP")
    r=counts(contents(Path(a.file)))
    for k,v in r.items():print(k,v)
    print("BUILD_SEEN" if r["loaded"] else "NOT_VERIFIED")
if __name__=="__main__":main()
