#!/usr/bin/env python3
"""F4.1: relay aggregated PanVK CSF profiling to stderr for Bachata diagnostics.

Run after UMA F2, F3 and F4 diagnostic patches; never modify the F3 baseline.
Bachata's shadps4.log already captures Mesa's vk_warn_non_conformant...
fprintf(stderr, ...) warning, so reuse that stderr stream instead of opening
Android-scoped files or needing ADB/Logcat permissions.
"""
from __future__ import annotations

import argparse
import difflib
from pathlib import Path

SRC = "src/panfrost/vulkan/csf/panvk_vX_gpu_queue.c"


def one_replace(text: str, old: str, new: str) -> str:
    count = text.count(old)
    if count != 1:
        raise ValueError(f"Expected one exact F4 diagnostic anchor, got {count}: {old!r}")
    return text.replace(old, new, 1)


def relay(source: str) -> str:
    # Add the header explicitly rather than depending on transitive includes.
    updated = one_replace(
        source,
        "#include <stdint.h>\n",
        "#include <stdint.h>\n#include <stdio.h>\n",
    )
    updated = one_replace(
        updated,
        'mesa_logi("PANVK-F4 submits=',
        'fprintf(stderr, "PANVK-F4 submits=',
    )
    # Complete each profiling line before the flush. Keep field names and values.
    updated = one_replace(
        updated,
        '" heap_renewals=%" PRIu64,',
        '" heap_renewals=%" PRIu64 "\\n",',
    )
    updated = one_replace(
        updated,
        "p->gpu_wait_submits, p->forced_submits, p->heap_renewals);\n"
        "   *p = (struct panvk_f4_profile){0};",
        "p->gpu_wait_submits, p->forced_submits, p->heap_renewals);\n"
        "   fflush(stderr);\n"
        "   *p = (struct panvk_f4_profile){0};",
    )
    assert updated.count('fprintf(stderr, "PANVK-F4 submits=') == 1
    assert updated.count("fflush(stderr);") == 1
    assert updated.count("PANVK_G720_F4_PROFILE") >= 1
    return updated


def self_test() -> None:
    # Test the exact transformed C shape independently from the Mesa source.
    base = (
        "#include <stdint.h>\n"
        "static void example(void) {\n"
        '   mesa_logi("PANVK-F4 submits=%" PRIu64 '
        '" heap_renewals=%" PRIu64,\n'
        "p->gpu_wait_submits, p->forced_submits, p->heap_renewals);\n"
        "   *p = (struct panvk_f4_profile){0};\n"
        "}\n"
        "PANVK_G720_F4_PROFILE\n"
    )
    changed = relay(base)
    assert '#include <stdio.h>' in changed
    assert 'fprintf(stderr, "PANVK-F4 submits=' in changed
    assert '" heap_renewals=%" PRIu64 "\\n",' in changed
    assert changed.index("fflush(stderr);") < changed.index("*p =")
    assert 'mesa_logi("PANVK-F4 submits=' not in changed
    try:
        relay(changed)
    except ValueError:
        pass
    else:
        raise AssertionError("Rerunning must fail instead of duplicating output")
    print("F4.1 stderr relay self-test passed")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--self-test", action="store_true")
    p.add_argument("--source", type=Path, default=Path(SRC))
    p.add_argument("--diff", type=Path, help="Save a reviewable unified diff")
    a = p.parse_args()
    if a.self_test:
        self_test()
        return 0
    before = a.source.read_text(encoding="utf-8")
    after = relay(before)
    if a.diff:
        a.diff.parent.mkdir(parents=True, exist_ok=True)
        a.diff.write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True), after.splitlines(keepends=True),
            fromfile="a/" + SRC, tofile="b/" + SRC)), encoding="utf-8")
    a.source.write_text(after, encoding="utf-8")
    print("F4.1 stderr relay enabled; C source modified only at four guarded anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
