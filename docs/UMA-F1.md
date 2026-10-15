# PanVK G720 — UMA Inteligente Fase 1

## Scope
Experimental memory-pool optimization preserving default game settings and the E20 source-level performance settings.

- Reuse large BOs with a best-fit policy rather than first-fit.
- Periodically trim *idle, internal* cached large BOs according to available shared RAM.
- Preserve active allocations, imported objects, Vulkan memory reporting, GPU queues and synchronization.
- Carry source-parity performance settings: 1 MiB CSF ring per queue, tiler-heap renewal interval 256 with estimated-work trigger disabled, 5 ms CQS wait slice, suppressed repetitive SYNC-A3 info logging, and full tile memory budgeting.

## Provenance
Base: PanVK G720 0.1.0-beta.2 custom kbase/CSF development snapshot, as provided by the project owner.

Source archive SHA-256: `c0f343adcfdb6779df5642f4252308baed2c7e8b462181af79864c7471023d4a`.

Source patch application and standalone UMA-policy tests passed locally. **Android NDK compilation and device validation are not yet complete.** The custom trimmed source archive may require source/dependency restoration if CI detects missing files.

## Build and release discipline
1. Keep `main` unchanged; all experiments live on `exp/uma-inteligente-fase1`.
2. Upload the exact supplied source ZIP to `vendor/PanVK-G720-UMA-F1-source.zip` in the experimental branch.
3. GitHub Actions runs `build-uma-f1.yml`, checks SHA-256 and verifies code markers before configuring Meson.
4. If CI succeeds, download the Actions artifact `PanVK-G720-UMA-F1-Android-ARM64` containing the Bachata-importable driver ZIP.
5. Preserve E19/E20 as rollback drivers. Test in the Bachata app only, not as a global Android Vulkan driver.
6. A build pass is not proof of GPU stability, performance benefit or Vulkan conformance.

No Android APK, official signing keys, or edits to Bachata/shadPS4 are part of this cycle.
