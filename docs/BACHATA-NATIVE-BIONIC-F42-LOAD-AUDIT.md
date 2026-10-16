# Bachata S4 0.2.5 — Native Bionic / PanVK F4.2 loader audit (read-only)
Date: 2026-10-16. Audited branch derives from `exp/uma-inteligente-fase4-2-logcat` and does not change any driver source, binary, workflow or Phase 3 baseline.

## Evidence
- User UI: in game settings, **Drivers** page includes `GLIBC | NATIVE BIONIC | HERDAL`; with Native Bionic selected the `PanVK G720 UMA Fase 4.2 Logcat` card reads **ATIVO**. A *separate sidebar page named "Ambiente"* exists. This driver-list selection has NOT yet been proved to set the runtime that launches the game.
- F4.2 package SHA256: `f3db91f46d4b4a6d415801d579e87339fc634ea341c8b5037fff3894f8476856`. ELF `libvulkan_panfrost.so` SHA256 `3ebb24d8d3a7fd03f17c78cf04f57bd6b65bc45dda17141bb2c499ece5f600aa`, consistent with `meta.json`. ELF64 ARM64; Android `DT_NEEDED` includes `liblog.so`, `libhardware.so`, and `libnativewindow.so`. Binary contains `PANVK-F4.2 LIB_LOADED`, build ID and `PanVK_F42`. Build instrumentation exists; that fact does not prove that it was loaded by the app.
- `panvk-f42-all.txt` 592524 lines, with `main` covering Oct 16 10:10:52.874–10:14:25.742; events around shadPS4 process launches 10:10:43 (PID 5036) and 10:14:05 (PID 6168). Zero strings `PANVK-F4.2 LIB_LOADED`, `PANVK-F4.1.1`, `PanVK_F42`, or `libvulkan_panfrost.so`. This does NOT directly prove ELF was absent from memory. Buffer `main` misses the earliest boot of 10:10:43, but covers boot 10:14:05 for ~20 seconds.
- Device command `/proc/5036/maps` returned `Permission denied` under shell; do not repeat blocked inspection nor mistake it for a driver fault.
- **Separate diagnostic session**, `bachata-diagnostic-BS4-20261016-627CABD7.zip` at 12:19–12:20 UTC (09:19–09:20 UTC−3): `application.log` explicitly reports `abi=linux-glibc-arm64`, `guestBackend=fex`, `driver=panvk-244793347e1d591f`; `report.json` gives `driver.source=glibc`, `driver.packageSha256=null`. It is NOT the logcat's 10:10/10:14 session, so its driver ID must NOT be attributed to that later session. It proves only that GLIBC/FEX was actually used in this earlier session.
- A shadPS4-FEX process loads Linux/glibc libraries (e.g. `libm.so.6`, `libuuid.so.1`), whereas F4.2 is a Bionic Android ELF. That distinction motivates checking the Vulkan bridging/routing mechanism; by itself it is NOT proof of an ABI error.
- Public Bachata-S4 release repository hosts documentation/releases rather than the Android app driver's importer/router source. Core project `zenithblue-oss/shadps4-arm64` does not establish that proprietary APK route. App-level exact code path not directly auditable.

## Prioritized hypotheses
1. The Native Bionic button within the **Drivers** page shows/sets that environment's driver profile, while actual **Ambiente** game runtime remains GLIBC. Check actual environment first.
2. Bionic runtime active but selected F4.2 package not routed into Vulkan loader; need per-session resolved driver path + ELF digest or runtime signature.
3. F4.2 mapped but Android logging unavailable/filtered; capture boot continuously and use positive Logcat control, do not guess.
4. Vulkan host bridge translates Linux/glibc shadPS4 to Bionic driver; cannot infer direct glibc `dlopen` into Bionic ELF.

## Next nondestructive test
For the SAME game: open the left **Ambiente** page and screenshot the actual game execution runtime. Then return to Drivers and confirm active selection for that exact runtime. No root, no forced crashes, no new PanVK build. Optionally run `logcat -c` before launch and `logcat -d -v threadtime -b all > /sdcard/Download/panvk-f42-boot.txt` immediately after. On a naturally occurring crash, correlate `application.log abi=` and `report.json driver.source/name/packageSha256` to the **same** session; do not compare different sessions.

Gates: actual environment confirmed -> loaded ELF fingerprint confirmed -> CSF telemetry confirmed -> only then controlled F3-vs-branch performance comparison.

The best-performing F3 baseline is untouched; F4.2 remains diagnostic pending proof of loaded library.


## UPDATE — UI corrected; crash diagnostics unavailable on normal exit

User verified: the left-side **Ambiente** screen is NOT a runtime switcher; it contains shadPS4 per-game settings (Audio/Debug/GPU/General). **Jogar** launches the game directly. Therefore, preceding instructions to use the left-side Ambiente page to prove Bionic vs GLIBC runtime were invalid and are **superseded**. The Drivers screen tab `NATIVE BIONIC` indicates per-runtime driver selection only, not the actual launch ABI. User reports export of the Bachata diagnostic ZIP is accessible **only following an actual crash**. Do not induce a crash to generate evidence.

Official Bachata 0.2.2 release notes independently confirm glibc and Bionic runtimes have **separate per-runtime driver-profile selections**; they do not document how this particular 0.2.5 APK chooses runtime at launch: https://github.com/JICA98/Bachata-S4/releases/tag/0.2.2

### Recommended safe capture (ADB/LADB, no crash, no root)

Do not repeat `/proc/<pid>/maps` since Android denies it. To avoid the circular Logcat buffer overwriting the driver constructor emission, start a **live file-backed capture** before tapping Jogar, using app-filtered tag capture and a control marker:

```sh
logcat -c
logcat -v threadtime -b main -f /sdcard/Download/panvk-f42-live.txt -r 2048 -n 2 -s PanVK_F42:V PANVK_CAPTURE:V EmulationService:V linker:V AndroidRuntime:E '*:S' &
echo $! > /sdcard/Download/panvk-f42-logger.pid
log -p i -t PANVK_CAPTURE BEFORE_GAME
```

Start and play the game, then return to LADB and run:

```sh
log -p i -t PANVK_CAPTURE AFTER_GAME
kill "$(cat /sdcard/Download/panvk-f42-logger.pid)"
```

The `logcat` background job can die if its shell process is terminated or the app stops it, so first ensure the `BEFORE_GAME` control record persists; failures are not evidence of a driver problem. Attach `panvk-f42-live.txt` (and rotation siblings if present). Distinguish `PANVK_CAPTURE` markers produced by shell from actual driver tag `PanVK_F42`. A positive control with absent F4.2 tag shows the capture mechanism works, **not** definitive proof that the ELF was never loaded. If background jobs cannot survive LADB task switching, do not persist in repeated uninformative snapshots; request a public source APK or upstream loader logs to audit static driver-selection logic.

No change to PanVK F3, F4.2 CSF, Vulkan render, or build artifacts. Wait for genuine spontaneous crash if app-only `application.log` evidence is required.


## UPDATE — 2026-10-16 10:54:43–10:55:34 UTC−3: captured full test window, no F4.2 tag

User provided `panvk-f42-check.txt`, exactly 7 lines (including buffer header), produced after explicitly clearing `logcat`, writing a `PANVK_CAPTURE BEFORE_GAME` control, launching a game and writing `PANVK_CAPTURE AFTER_GAME` then dumping `main` with tags `PANVK_CAPTURE:I PanVK_F42:V EmulationService:V`.

Verbatim:
```text
--------- beginning of main
10-16 10:54:43.022 25038 25038 I PANVK_CAPTURE: BEFORE_GAME
10-16 10:54:52.007 18482 25123 I EmulationService: Adreno turbo requested: false
10-16 10:54:52.013 18482 25123 I EmulationService: Adreno turbo supported: false
10-16 10:54:52.275 18482 25123 I EmulationService: staging diag env={BACHATA_MALI_GPU_OPT=1, BACHATA_STAGING_TICK_LAG=12}
10-16 10:55:34.956 25338 25338 I PANVK_CAPTURE: AFTER_GAME
```

**Interpretation**: The log window and expected Android logcat capture method were independently verified, yet **no `PanVK_F42` tag** was observed between the bracketing control markers. This makes the prior “buffer window overwritten/filtered incorrectly” explanation less plausible. **It still does not conclusively establish the ELF was not mapped**, nor which library/device was selected. `EmulationService` variable `BACHATA_MALI_GPU_OPT=1` is not proof of a specific Vulkan ICD. A logcat tag emitted by a driver only fires if code executed and logging reached Android logd.

Do not run additional `/proc` dumps, background `logcat -f` loops, or trigger deliberate crashes. Next step should be direct inspection of Bachata's actual loader/driver-routing implementation or an explicit native-loader `dlopen` success/failure path, preferably using upstream source or diagnostic logs. If none is accessible, evidence status is "driver load unconfirmed", not "different driver proven". No modifications to F3/F4.2.
