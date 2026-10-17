#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""R2A6/P3 local, fail-closed checker for deliberately REDACTED Android test events.

INPUT is NOT logcat. Manually select ONLY the whitelisted markers, no paths,
device IDs, signing material, package data, nonce, token or socket labels.
Successful syntax verification DOES NOT authenticate the handset or its APK.
"""
import argparse
import json
from pathlib import Path

HOST = "BACHATA_F43DEV_R2A2_HOST_GATE_OK"
HELLO = "BACHATA/1 HELLO version=1"
START = "BACHATA/1 EVENT Starting"
STOP_OK = "BACHATA/1 EVENT Stopped exit_code=0"
STOP_FAIL = "BACHATA/1 EVENT Stopped exit_code=1"
HOST_ERROR = "BACHATA/1 ERROR code=SAF_PROBE_FAILED"
PROBE_RESULTS = {
    "BSF1_LAB_PROBE_FILE_OK", "BSF1_LAB_PROBE_DIRECTORY_OK",
    "BSF1_LAB_PROBE_INVALID_PATH", "BSF1_LAB_PROBE_STAT_FAILED",
    "BSF1_LAB_PROBE_LIST_FAILED", "BSF1_LAB_PROBE_OPEN_FAILED",
    "BSF1_LAB_PROBE_FD_REJECTED",
}
TRANSPORT_CODES = {
    "BSF1_DIAG_NONE", "BSF1_DIAG_CONFIG_INVALID",
    "BSF1_DIAG_PATH_INVALID", "BSF1_DIAG_SOCKET_UNAVAILABLE",
    "BSF1_DIAG_UID_MISMATCH", "BSF1_DIAG_IO_FAILURE",
    "BSF1_DIAG_FRAME_INVALID", "BSF1_DIAG_REMOTE_REJECTED",
    "BSF1_DIAG_FD_MISSING", "BSF1_DIAG_FD_INVALID",
    "BSF1_DIAG_PAYLOAD_INVALID",
}
SUCCESS = {"BSF1_LAB_PROBE_FILE_OK", "BSF1_LAB_PROBE_DIRECTORY_OK"}
ALLOWED = {HOST, HELLO, START, STOP_OK, STOP_FAIL, HOST_ERROR, *PROBE_RESULTS}
ALLOWED_PAIRS = {
    *(f"{outcome} {transport}" for outcome in PROBE_RESULTS for transport in TRANSPORT_CODES),
}

def check(text: str) -> dict:
    # Never echo input or any unknown line; it may contain private user data.
    lines = text.splitlines()
    safe = {"schema": "r2a6p3-safe-events-v1",
            "source_authenticated": False,
            "apk_signature_verified": False,
            "real_broker_verified": False,
            "status": "REJECTED",
            "reason_code": "UNVERIFIED_EVENTS"}
    if not lines or len(lines) > 16 or len(text.encode("utf-8")) > 4096:
        safe["reason_code"] = "SIZE_OR_COUNT_INVALID"
        return safe
    if any(line != line.strip() or not line for line in lines):
        safe["reason_code"] = "NON_CANONICAL_EVENT"
        return safe

    result_entries = []
    normalized = []
    for line in lines:
        if line in ALLOWED:
            if line in PROBE_RESULTS:
                result_entries.append((line, None))
            normalized.append(line)
        elif line in ALLOWED_PAIRS:
            kind, subtype = line.split(" ", 1)
            result_entries.append((kind, subtype))
            normalized.append(kind)
        else:
            safe["reason_code"] = "UNRECOGNIZED_OR_PRIVATE_INPUT"
            return safe

    if (normalized.count(HOST) != 1 or normalized.count(HELLO) != 1 or
        normalized.count(START) != 1 or len(result_entries) != 1 or
        (normalized.count(STOP_OK) + normalized.count(STOP_FAIL)) != 1):
        safe["reason_code"] = "INCOMPLETE_OR_DUPLICATE_EVENTS"
        return safe
    outcome, transport = result_entries[0]
    expected_success = outcome in SUCCESS
    if expected_success and transport not in (None, "BSF1_DIAG_NONE"):
        safe["reason_code"] = "INCONSISTENT_TRANSPORT"
        return safe
    if not expected_success and transport == "BSF1_DIAG_NONE":
        safe["reason_code"] = "INCONSISTENT_TRANSPORT"
        return safe
    expected = ([HOST, HELLO, START, outcome, STOP_OK] if expected_success
                else [HOST, HELLO, START, outcome, HOST_ERROR, STOP_FAIL])
    if normalized != expected:
        safe["reason_code"] = "ORDER_OR_EXIT_MISMATCH"
        return safe

    safe["status"] = "CONSISTENT_UNATTESTED_EVENTS"
    safe["reason_code"] = "SUCCESS_MARKERS_PRESENT" if expected_success else "FAILURE_MARKERS_PRESENT"
    safe["probe_result"] = outcome
    safe["test_passed_on_observer_report"] = expected_success
    # This field stays false even for successful markers: text is forgeable.
    safe["real_broker_verified"] = False
    return safe

def main() -> int:
    parser = argparse.ArgumentParser(description="R2A6/P3 sanitized event proof checker, no real attestation")
    parser.add_argument("marker_file", type=Path,
                        help="ONLY curated, sanitized event lines (not logcat)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write a small JSON report; never embeds input text")
    args = parser.parse_args()
    if args.marker_file.stat().st_size > 4096:
        report = check("")
    else:
        report = check(args.marker_file.read_text(encoding="utf-8"))
    result = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(result, end="")
    else:
        args.output.write_text(result, encoding="utf-8")
    return 0 if report["status"] == "CONSISTENT_UNATTESTED_EVENTS" else 2

if __name__ == "__main__":
    raise SystemExit(main())
