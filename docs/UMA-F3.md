# PanVK G720 — UMA Inteligente Fase 3 (Sorted BO Cache)

## Goal

Speed up internal memory recycling without changing Vulkan heap sizes, shaders, resolution, CSF scheduling, or GPU/CPU synchronization. Baseline: **UMA Fase 2** (Bachata starts and is reported slightly smoother; no substantive FPS gain).

## Isolated code change

Apply `patches/uma-f3-sorted-idle-big-bo.patch` **after** the unchanged F2 cache-flush patch. This affects only `panvk_mempool.c`.

- Keep *idle, internal, big buffer objects* ordered by increasing capacity.
- Recycle the first idle large BO satisfying the requested capacity, preserving the F1 best-fit semantics and avoiding extra scans after the first matching candidate.
- Return BOs to the sorted idle list **only when the existing pool reset path relinquishes them**. Do not move active or imported Vulkan memory into the cache.
- Evict the largest cached idle BO from the list tail in constant time, instead of re-scanning the entire list.
- Keep F1's available-RAM budget and 256-reset sampling cadence.
- Keep F2's allocated-prefix flush, full invalidate, and previous synchronization.
- Keep the 1 MiB CSF ring, heap renewal interval 256, and other E20 source settings.

## Validation

The F3 patch applies cleanly on top of the F2 patch on the existing source archive. The host-side C policy test `tests/uma-f3-cache-test.c` passed locally with AddressSanitizer and UBSan. This test mocks BO size/ownership and uses Mesa's actual intrusive list implementation; it does **not** test GPU fence completion or the MediaTek driver.

The F3 GitHub workflow runs archive/hash validation, F2 and F3 patch guards, the policy test, Android ARM64 build, ELF dependency checks, and ZIP packaging.

## Risk & comparison

Sorting incurs insertion work when the pool resets; it may fail to increase FPS or even regress in workloads with many returned buffers and limited reuse. Do not use for a system-wide Vulkan driver. Preserve UMA F2 as rollback.

Compare exactly the same scenes with original Bachata settings. Evaluate load success, typical FPS, worst frame times/stutter, memory growth, and rendering correctness. A successful CI build does **not** mean validated on device.

## Project baseline decision — 2026-10-15

**Selected baseline: UMA Fase 3** (best experimental version so far, by user report). Future performance work must branch from this version unless the user explicitly changes the baseline.

Device test report:
- Bachata loads/starts with the experimental UMA driver.
- F1: noticeably more responsive, no major FPS increase.
- F2: small improvement in stability, no major FPS increase.
- F3: small FPS gain; selected as current best experimental reference.
- Graphics glitches and game hangs were already present in the E20 baseline. This rules out their first appearance in UMA, but does **not** exclude changes in their frequency/severity; no controlled regression comparison has been completed.

**Keep existing F3 code and build intact.** Avoid speculative changes or promotion to production. Preserve E20 and F2 artifacts as rollback paths. No full hardware/Vulkan conformance or quantitative frame-time benchmarking has been completed. Investigate command-submission bottlenecks as a *separate* next cycle, with measurements before changing synchronization.

