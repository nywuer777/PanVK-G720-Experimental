#!/usr/bin/env python3
"""P63 source-pinned bounded PSF format evidence (read-only forensic change).

Run AFTER exact P61->P62 chain. Preserve validation failure and Android
broker trust; only emit (index, unsigned 16-bit field), no private PSF data.
"""
import argparse, hashlib, subprocess
from pathlib import Path
PIN="be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
P62_HEADER_SHA256="f014c676d7782a26113e978c1f2d9d48d031e434190730d1004704a248731e1a"
MAIN_OLD="""                std::cerr << Bachata::Saf::P61::Marker(psf.status) << '\\n';"""
MAIN_NEW="""                std::cerr << Bachata::Saf::P61::Marker(psf.status) << '\\n';
                if (psf.status == Bachata::Saf::P61::Status::InvalidPsfFormat &&
                    psf.format_evidence.available) {
                    // Only bounded numeric entry index and raw PSF format;
                    // no key name, path, title, SAF token or original file bytes.
                    std::cerr << "BACHATA_P63_PSF_FORMAT_EVIDENCE"
                              << " index=" << psf.format_evidence.entry_index
                              << " raw_u16=" << psf.format_evidence.raw_format
                              << '\\n';
                }"""
def patched_main(source):
    if source.count(MAIN_OLD)!=1 or "BACHATA_P63_PSF_FORMAT_EVIDENCE" in source:
        raise ValueError("P63_MAIN_ANCHOR_INVALID_OR_ALREADY_APPLIED")
    if "BACHATA_F43DEV_R2A2_HOST_GATE_OK" not in source or "CONTENT_METADATA_UNAVAILABLE" not in source:
        raise ValueError("P63_TRUST_OR_ERROR_HOOK_MISSING")
    return source.replace(MAIN_OLD,MAIN_NEW,1)
def run(root:Path,forensic_header:Path):
    root=root.resolve()
    if not (root/".git").is_dir() or subprocess.check_output(
       ["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
       raise ValueError("P63_PINNED_UPSTREAM_MISSING")
    target=root/"src/platform/bachata/p61_saf_psf_stage.h"
    main=root/"src/main.cpp"
    if not target.is_file() or not main.is_file() or not forensic_header.is_file():
        raise ValueError("P63_SOURCE_PREREQUISITES_MISSING")
    if hashlib.sha256(target.read_bytes()).hexdigest()!=P62_HEADER_SHA256:
        raise ValueError("P63_P62_HEADER_HASH_MISMATCH")
    hdr=forensic_header.read_text()
    if ("BACHATA_P62_PSF_FORMAT" not in hdr or
        "FormatEvidence detail{};" not in hdr or
        "if(evidence) *evidence=" not in hdr):
        raise ValueError("P63_EVIDENCE_HEADER_INCOMPLETE")
    updated=patched_main(main.read_text())
    target.write_text(hdr,encoding="utf-8",newline="")
    main.write_text(updated,encoding="utf-8",newline="")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("BACHATA_P63_PSF_UNKNOWN_FORMAT_TELEMETRY=ENABLED")
    print("BACHATA_P63_UNSUPPORTED_FORMAT_ACCEPTED=NO")
    print("BACHATA_P63_TRUST_GATES_DISABLED=NO")
    print("BACHATA_P63_GAMEPLAY=NOT_TESTED")
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--source-root",type=Path,required=True)
    p.add_argument("--header",type=Path,required=True);a=p.parse_args()
    run(a.source_root,a.header)
