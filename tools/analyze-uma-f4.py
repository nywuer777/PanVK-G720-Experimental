#!/usr/bin/env python3
"""Analyze UMA F4 host-side CSF timing lines from a Bachata diagnostic log or ZIP."""
import argparse
import csv
import io
import re
import sys
import zipfile
from pathlib import Path

FIELDS = (
    "submits total_ns cpu_wait_ns map_sync_ns emit_ns publish_ns "
    "forced_wait_ns renew_wait_ns renew_ns ring_wait_ns max_submit_ns "
    "max_ring_wait_ns ring_stalls cpu_wait_submits gpu_wait_submits "
    "forced_submits heap_renewals"
).split()
BUCKETS = ["cpu_wait_ns", "map_sync_ns", "emit_ns", "publish_ns",
           "forced_wait_ns", "renew_wait_ns", "renew_ns"]
PATTERN = re.compile(r"\bPANVK-F4\s+(.*)")
PAIR = re.compile(r"([a-z_]+)=([0-9]+)")


def records(text):
    for line in text.splitlines():
        match = PATTERN.search(line)
        if match is None:
            continue
        row = {k: int(v) for k, v in PAIR.findall(match.group(1))}
        if all(k in row for k in FIELDS) and row["submits"] > 0:
            yield row


def read_input(path):
    path = Path(path)
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            for entry in archive.infolist():
                if entry.is_dir() or entry.file_size > 40_000_000:
                    continue
                if entry.filename.lower().endswith(
                    (".log", ".txt", ".json", ".jsonl", ".csv")
                ):
                    yield archive.read(entry).decode("utf-8", errors="replace")
    else:
        yield path.read_text(encoding="utf-8", errors="replace")


def summarize(rows):
    if not rows:
        return None
    sums = {f: sum(row[f] for row in rows) for f in FIELDS}
    samples = sums["submits"]
    pct = lambda value: 100 * value / sums["total_ns"] if sums["total_ns"] else 0
    return {
        "windows": len(rows),
        "submissions": samples,
        "avg_cpu_submit_ms": sums["total_ns"] / samples / 1_000_000,
        "max_cpu_submit_ms": max(r["max_submit_ns"] for r in rows) / 1_000_000,
        "max_ring_wait_ms": max(r["max_ring_wait_ns"] for r in rows) / 1_000_000,
        "ring_stalls": sums["ring_stalls"],
        "heap_renewals": sums["heap_renewals"],
        "cpu_wait_submits": sums["cpu_wait_submits"],
        "gpu_wait_submits": sums["gpu_wait_submits"],
        "forced_submits": sums["forced_submits"],
        "buckets": [
            (bucket, sums[bucket] / samples / 1_000_000, pct(sums[bucket]))
            for bucket in sorted(BUCKETS, key=lambda x: sums[x], reverse=True)
        ],
        # A ring wait is already counted inside emit_ns. Do not add twice.
        "ring_wait_pct_nested": pct(sums["ring_wait_ns"]),
    }


def self_test():
    row = "PANVK-F4 " + " ".join(
        f"{field}={256 if field == 'submits' else 256000000 if field == 'total_ns' else 0}"
        for field in FIELDS
    )
    text = "10-15 21:00:00 I Mesa: " + row + "\n"
    assert len(list(records(text))) == 1
    stat = summarize(list(records(text)))
    assert stat["avg_cpu_submit_ms"] == 1.0
    assert stat["submissions"] == 256
    assert stat["ring_wait_pct_nested"] == 0.0
    assert not list(records("PANVK-F4 broken text"))
    print("F4 profile analyzer: self-tests passed")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("input", nargs="?", help="Bachata diagnostic ZIP or log file")
    ap.add_argument("--csv", type=Path, help="Optional CSV output for each window")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    if not args.input:
        ap.error("input file required unless --self-test is used")
    rows = [row for content in read_input(args.input) for row in records(content)]
    stat = summarize(rows)
    if stat is None:
        print("No valid PANVK-F4 timing lines found. Check the Bachata diagnostic log.", file=sys.stderr)
        return 2
    print(f"UMA F4: {stat['windows']} windows, {stat['submissions']} CPU-side submits")
    print(f"Average CPU submission: {stat['avg_cpu_submit_ms']:.3f} ms")
    print(f"Longest CPU submission: {stat['max_cpu_submit_ms']:.3f} ms")
    print(f"Longest ring-space wait: {stat['max_ring_wait_ms']:.3f} ms")
    print(f"Ring stalls: {stat['ring_stalls']}; renewals: {stat['heap_renewals']}; "
          f"CPU wait submits: {stat['cpu_wait_submits']}; GPU waits: {stat['gpu_wait_submits']}")
    for key, ms, percent in stat["buckets"]:
        print(f"  {key}: {ms:.4f} ms/submit ({percent:.1f}% of CPU submit wall time)")
    print(f"  ring_wait_ns: {stat['ring_wait_pct_nested']:.1f}% (nested in emit_ns)")
    print("NOTE: these are CPU-side timings, NOT GPU utilization or frame times.")
    if args.csv:
        with args.csv.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)
        print("Wrote:", args.csv)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
