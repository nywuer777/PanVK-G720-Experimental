# PanVK G720 — Fase 4: CSF Submission Diagnostic (measurement only)

## Baseline and scope
Base branch: `exp/uma-inteligente-fase3`. It remains the **best experimental driver** based on the user’s device reports. This branch **does not promote itself** as the best driver and does not replace F3.

The F4 source is F1 + F2 allocated-range flush + F3 sorted idle BO cache, followed by a single diagnostic patch in `csf/panvk_vX_gpu_queue.c`. Preserve E20’s 1 MiB CSF ring, 5 ms CQS wait slice, 256-submit tiler-heap renewal interval, and all graphics settings.

## Read-only audit (source-level)
The kbase queue submission path contains: (1) incoming CPU waits or native GPU wait collection; (2) `pan_kmod_flush_bo_map_syncs`; (3) per-subqueue CSF emission, potentially blocking if the 1 MiB ring is full; (4) publication; (5) optional forced completion wait; (6) periodic tiler-heap graphics drain + renewal.

Important: `CS_EXTRACT` tracks firmware fetching, not completion. Sequence cells and GPU synchronization are necessary. No wait or fence is removed and no firmware commands are changed in F4-DIAG.

## Measurements
The driver logs one `PANVK-F4` record for every **256 successful kbase submissions per CPU thread**, with summed host CPU nanoseconds and counters:

- `cpu_wait_ns`: incoming waits/collection (may include `vk_sync_wait_many`)
- `map_sync_ns`: flush of mapped-buffer synchronization requests
- `emit_ns`: CPU-side ring emission (includes possible ring-space waits)
- `publish_ns`: publication to USER_IO + scheduler kicks
- `forced_wait_ns`: completion wait when `force_sync` is requested
- `renew_wait_ns` / `renew_ns`: tiler-heap graphics drain and heap renewal
- `ring_wait_ns`: **nested within `emit_ns`**; never add it to total again
- `max_submit_ns` and `max_ring_wait_ns`: CPU wall-time peaks within the window
- `ring_stalls`, `cpu_wait_submits`, `gpu_wait_submits`, `forced_submits`, `heap_renewals`

Only CPU wall time is measured. These are **not** GPU occupancy, frame times, FPS or detailed timeline traces. The optional instrumentation adds CPU clock reads and logging; its overhead can itself slightly change FPS.

`PANVK_G720_F4_PROFILE=0` disables the diagnostics when the app environment makes this possible. It defaults to on **only in this F4 diagnostics build**. With disabled profiling it avoids clock reads.

## Testing without a PC
1. Preserve F3 and its downloaded ZIP. Import F4-DIAG **only through Bachata**, never globally.
2. In the same graphics settings, run a known problematic scene for about 5 minutes, then export the app’s diagnostic ZIP.
3. Upload that ZIP in this conversation. We will check **whether it actually includes `PANVK-F4` lines**. The app may not export system Vulkan log messages; absence of records is a collection limitation, not evidence of zero CPU overhead.
4. Analyze logs using `python tools/analyze-uma-f4.py bachata-diagnostic.zip` (optional `--csv windows.csv`).
5. Compare the same scene against F3 for startup, visual correctness, hangs and FPS. A diagnostic build is not expected to increase FPS. Do **not** promote it based on diagnostics alone.

## Exit criteria
Only after valid on-device timing records exist can we isolate one measured bottleneck for F4-OPT. If the diagnostic ZIP contains no matching records, first fix log collection rather than guessing optimizations. F3 remains the project performance baseline regardless of the diagnostic build outcome.
