#!/usr/bin/env python3
"""F4.1.1: sparse, flushed CSF breadcrumbs for truncated Bachata logs.

Run ONLY after F2, F3, F4 timing and F4.1 stderr-relay transformations.
The output is observational: no firmware ring, queue waits, or heap policy edits.
"""
import argparse
import difflib
from pathlib import Path

SRC = "src/panfrost/vulkan/csf/panvk_vX_gpu_queue.c"

def unique_replace(text, before, after):
    n = text.count(before)
    if n != 1:
        raise ValueError("F4.1.1 expected exactly one anchor, found "
                         + str(n) + ": " + repr(before[:90]))
    return text.replace(before, after, 1)

def add_markers(text):
    # Queue construction provides an early diagnostic identifier even if the
    # per-thread profiler never reaches its 256-submission reporting threshold.
    text = unique_replace(text,
        "   queue->vk.driver_submit = panvk_per_arch(gpu_queue_submit);\n"
        "   *out_queue = &queue->vk;",
        '   queue->vk.driver_submit = panvk_per_arch(gpu_queue_submit);\n'
        '   fprintf(stderr, "PANVK-F4.1.1 READY queue_created kbase=%d\\n",\n'
        '           (int)uses_kbase);\n'
        '   fflush(stderr);\n'
        "   *out_queue = &queue->vk;")
    # Show that the common Vulkan queue-dispatch path was reached, once per
    # thread, before it can return for bind submissions or a lost device.
    text = unique_replace(text,
        "   VkResult result = VK_SUCCESS;\n\n"
        "   if (vk_queue_is_lost(vk_queue))",
        "   VkResult result = VK_SUCCESS;\n"
        "   static _Thread_local bool f4111_first_submit;\n"
        "   if (!f4111_first_submit) {\n"
        "      f4111_first_submit = true;\n"
        '      fprintf(stderr, "PANVK-F4.1.1 QUEUE_SUBMIT_ENTRY\\n");\n'
        "      fflush(stderr);\n"
        "   }\n\n"
        "   if (vk_queue_is_lost(vk_queue))")
    # Also show that the kbase-specific (Mali G720) path was chosen.
    text = unique_replace(text,
        "   if (gpu_queue_uses_kbase(submit.dev)) {\n"
        "      result = panvk_queue_submit_ioctl_kbase(&submit, vk_submit);",
        "   if (gpu_queue_uses_kbase(submit.dev)) {\n"
        "      static _Thread_local bool f4111_first_kbase;\n"
        "      if (!f4111_first_kbase) {\n"
        "         f4111_first_kbase = true;\n"
        '         fprintf(stderr, "PANVK-F4.1.1 KBASE_SUBMIT_ENTER\\n");\n'
        "         fflush(stderr);\n"
        "      }\n"
        "      result = panvk_queue_submit_ioctl_kbase(&submit, vk_submit);")
    # Small milestones in every 256-submission aggregate window make a short
    # session useful and distinguish "not enough successful submits" from
    # "stderr not captured". Markers have their own explicit version string.
    text = unique_replace(text,
        "      p->max_submit_ns = MAX2(p->max_submit_ns, wall_ns);\n"
        "      p->cpu_wait_ns += f4_cpu_wait_ns;",
        "      p->max_submit_ns = MAX2(p->max_submit_ns, wall_ns);\n"
        "      if (p->submits == 1 || p->submits == 32 || p->submits == 128) {\n"
        '         fprintf(stderr, "PANVK-F4.1.1 PROGRESS submits=%" PRIu64\n'
        '                 " total_ns=%" PRIu64 "\\n", p->submits, p->total_ns);\n'
        "         fflush(stderr);\n"
        "      }\n"
        "      p->cpu_wait_ns += f4_cpu_wait_ns;")
    assert text.count('PANVK-F4.1.1') == 4
    assert text.count("fflush(stderr);") == 5, "Four new + F4.1 flush"
    assert text.count('fprintf(stderr, "PANVK-F4 submits=') == 1
    return text

def self_test():
    example = (
        "   queue->vk.driver_submit = panvk_per_arch(gpu_queue_submit);\n"
        "   *out_queue = &queue->vk;\n"
        "   VkResult result = VK_SUCCESS;\n\n"
        "   if (vk_queue_is_lost(vk_queue))\n"
        "   if (gpu_queue_uses_kbase(submit.dev)) {\n"
        "      result = panvk_queue_submit_ioctl_kbase(&submit, vk_submit);\n"
        "      p->max_submit_ns = MAX2(p->max_submit_ns, wall_ns);\n"
        "      p->cpu_wait_ns += f4_cpu_wait_ns;\n"
        '      fprintf(stderr, "PANVK-F4 submits=payload");\n'
        '      fflush(stderr);\n'
    )
    changed = add_markers(example)
    assert 'PANVK-F4.1.1 READY' in changed
    assert 'PANVK-F4.1.1 KBASE_SUBMIT_ENTER' in changed
    assert 'PANVK-F4.1.1 PROGRESS' in changed
    try:
        add_markers(changed)
    except ValueError:
        pass
    else:
        raise AssertionError("Double application should be rejected")
    print("F4.1.1 source marker self-tests passed")

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", type=Path, default=Path(SRC))
    ap.add_argument("--diff", type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return 0
    before = args.source.read_text()
    after = add_markers(before)
    if args.diff:
        args.diff.parent.mkdir(exist_ok=True, parents=True)
        args.diff.write_text("".join(difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile="a/" + SRC, tofile="b/" + SRC)))
    args.source.write_text(after)
    print("F4.1.1 markers added without touching CSF scheduling or sync")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
