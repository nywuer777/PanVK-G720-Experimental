#!/usr/bin/env python3
"""F4.3: preserve Android HAL HMI while exporting Vulkan direct-ICD entrypoints.

Run after F4.2 and before Meson configure. Fail closed if upstream source
changes: never mutate CSF scheduling, submit, heap, or synchronization.
"""
from __future__ import annotations

import argparse
import difflib
from pathlib import Path

MAP = "src/vulkan/vulkan-android.sym"
SYMBOLS = "src/vulkan/vulkan-icd-android-symbols.txt"
QUEUE = "src/panfrost/vulkan/csf/panvk_vX_gpu_queue.c"
ICD = (
    "vk_icdGetInstanceProcAddr",
    "vk_icdGetPhysicalDeviceProcAddr",
    "vk_icdNegotiateLoaderICDInterfaceVersion",
)
BUILD_ID = "G720-UMA-F4.3-ICD-DUAL-20261016"


def unique(s: str, old: str, new: str) -> str:
    count = s.count(old)
    if count != 1:
        raise ValueError(f"F4.3 anchor expected exactly once; got {count}: {old!r}")
    return s.replace(old, new, 1)


def transform(android_map: str, symbols: str, queue: str) -> tuple[str, str, str]:
    # Upstream Mesa Android symbol map must export HMI, demoting all others.
    assert "local:" in android_map and "*;" in android_map
    assert not any(x + ";" in android_map for x in ICD), "ICD already in map"
    new_map = unique(
        android_map, "HMI;",
        "HMI;\n\n"
        "\t\t/* F4.3: Bionic direct-ICD alongside Android HAL. */\n"
        + "".join("\t\t" + name + ";\n" for name in ICD).rstrip("\n")
    )
    assert new_map.index("HMI;") < new_map.index(ICD[0])
    assert new_map.index(ICD[-1] + ";") < new_map.index("local:")
    assert new_map.count("HMI;") == 1
    assert all(new_map.count(x + ";") == 1 for x in ICD)

    # Mesa's optional symbol-check target otherwise expects HMI alone.
    assert not any(x in symbols for x in ICD), "ICD already in allowed symbols"
    new_symbols = unique(
        symbols,
        "HMI\n",
        "HMI\n" + "".join(name + "\n" for name in ICD)
    )
    assert new_symbols.count("\nHMI\n") == 1
    assert all(new_symbols.count(name + "\n") == 1 for name in ICD)

    # Distinguishable runtime fingerprint; keep diagnostic logic and CSF intact.
    assert "PANVK-F4.2 LIB_LOADED" in queue
    assert "PANVK-F4.1.1" in queue
    assert "kbase_subqueue_wait_seqno(" in queue
    assert "kbase_renew_tiler_heap(" in queue
    assert "G720-UMA-F4.2-LOGCAT-20261016" in queue
    assert '"PanVK_F42"' in queue
    new_queue = unique(queue, "PANVK-F4.2 LIB_LOADED", "PANVK-F4.3 LIB_LOADED")
    new_queue = unique(
        new_queue,
        "G720-UMA-F4.2-LOGCAT-20261016",
        BUILD_ID
    )
    new_queue = unique(new_queue, '"PanVK_F42"', '"PanVK_F43"')
    assert new_queue.count("PANVK-F4.1.1") == queue.count("PANVK-F4.1.1")
    assert new_queue.count("kbase_subqueue_wait_seqno(") == queue.count("kbase_subqueue_wait_seqno(")
    assert new_queue.count("kbase_renew_tiler_heap(") == queue.count("kbase_renew_tiler_heap(")
    return new_map, new_symbols, new_queue


def self_test() -> None:
    am = "{\n\tglobal:\n\t\tHMI;\n\tlocal:\n\t\t*;\n};\n"
    sy = "# Android HAL\nHMI\n"
    qu = ('#define PANVK_F42_BUILD_ID "G720-UMA-F4.2-LOGCAT-20261016"\n'
          '__android_log_write(ANDROID_LOG_INFO, "PanVK_F42", line);\n'
          'panvk_f42_emit("PANVK-F4.2 LIB_LOADED build=%s\\n", PANVK_F42_BUILD_ID);\n'
          '/* PANVK-F4.1.1 */\n'
          'kbase_subqueue_wait_seqno(x);\nkbase_renew_tiler_heap(y);\n')
    a, b, c = transform(am, sy, qu)
    assert "HMI;" in a and all(x + ";" in a for x in ICD)
    assert all(x + "\n" in b for x in ICD)
    assert "PANVK-F4.3 LIB_LOADED" in c and '"PanVK_F43"' in c
    assert c.count("kbase_subqueue_wait_seqno(") == 1
    for wrong in ((am.replace("HMI;", ""), sy, qu), (am, sy, c), (a, b, qu)):
        try:
            transform(*wrong)
        except (ValueError, AssertionError):
            pass
        else:
            raise AssertionError("Guard must reject mutated or duplicate inputs")
    print("F4.3 self-test PASS: HMI + direct ICD, CSF unchanged, guarded anchors")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--diff", type=Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    paths = [args.root / x for x in (MAP, SYMBOLS, QUEUE)]
    before = [path.read_text(encoding="utf-8") for path in paths]
    after = transform(*before)
    # Only after *all* guards pass, write the transformed sources.
    if args.diff:
        chunks = []
        for name, old, new in zip((MAP, SYMBOLS, QUEUE), before, after):
            chunks.extend(difflib.unified_diff(
                old.splitlines(True), new.splitlines(True),
                fromfile="a/" + name, tofile="b/" + name
            ))
        args.diff.parent.mkdir(parents=True, exist_ok=True)
        args.diff.write_text("".join(chunks), encoding="utf-8")
    for path, updated in zip(paths, after):
        path.write_text(updated, encoding="utf-8")
    print("F4.3 patched Android ICD exports, symbol-check list, and diagnostic fingerprint")


if __name__ == "__main__":
    main()
