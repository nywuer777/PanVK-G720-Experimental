# Bachata S4 v0.2.5 APK — PanVK G720 F4.2 static loader audit

Date: 2026-10-16. READ-ONLY. APK SHA-256 `1df49463f396df8b6f042230bdc1bb9f948b8e69894c378915920875c40ab0ee`; equals release `SHA256SUMS.txt` and passes ZIP CRC check. F4.2 library SHA-256 `3ebb24d8d3a7fd03f17c78cf04f57bd6b65bc45dda17141bb2c499ece5f600aa`.

## Proven runtime split from the packaged APK

- `assets/runtime/native-runtime.json`: `android-bionic-arm64` linked to APK `lib/arm64-v8a/libbachata_native_runtime.so`.
- `assets/runtime/runtime.zip`: separate Debian/glibc runtime with `host/shadps4-arm64-fex`, `host/ld-linux-aarch64.so.1` and Linux `libvulkan.so.1`.
- Decompiled-by-index DEX string references in method `Ltt0;->s`: `abi=android-bionic-arm64 host=libbachata_native_runtime.so` and `abi=linux-glibc-arm64 host=libbachata_host_loader.so`. DEX profiles store `runtimeHost` and explicitly distinguish `ANDROID_BIONIC` / `LINUX_GLIBC`. Obfuscated identifiers are valid for this **exact APK only**; no entire-control-flow decompilation was claimed.
- Previous `panvk-f42-all.txt` executions at **10:10:43 PID 5036** and **10:14:05 PID 6168** visibly execute `.../runtime-b7db79837e56/host/shadps4-arm64-fex`, which is **the GLIBC process path**, not the Bionic direct runtime. The more recent **10:54** filtered Logcat lacks enough process records to classify its runtime. The Drivers/Native Bionic tab is per-runtime driver configuration, not proof of launch-runtime choice.
- Bundled `assets/drivers/Bachata-PanVK-V3-glibc.zip` contains `meta.json` with `abi=linux-aarch64-glibc` and binary DT_NEEDED entries `libc.so.6` and `libstdc++.so.6`; F4.2 is Android-NDK/Bionic with `libc.so`, `liblog.so` etc. These are not binary interchangeable.

## Independent interface/export blocker

The APK `classes.dex` has, in `Lv84;->a`, the keys `BACHATA_VULKAN_LOAD_MECHANISM`, `BACHATA_VULKAN_LIBRARY_SHA256`, `BACHATA_VULKAN_DRIVER_NAME` and value `direct-icd`. Native `libbachata_native_runtime.so` reports `Vulkan provider: missing ICD negotiation entry point`, `Vulkan provider: ICD negotiation failed (`, `Vulkan provider: library SHA-256 mismatch`, `Vulkan provider: dlopen failed:`, and success `[Bachata.Vulkan] <Info> backend=panvk-kbase mechanism=direct-icd loaded=%s sha256=%s interface=%u loaderLayers=false`.

**Actual F4.2 ELF dynamic symbol table**:
```
$ nm -D --defined-only libvulkan_panfrost.so
000000000111ea08 D HMI
```
`readelf -Ws -W` shows `vk_icdGetInstanceProcAddr`, `vk_icdNegotiateLoaderICDInterfaceVersion` and `vk_icdGetPhysicalDeviceProcAddr` are **LOCAL**, not exported in `.dynsym`. `dlsym` cannot resolve them for a direct-ICD mechanism. F4.1.1 likewise exports only `HMI` (not an F4.2 logging regression). The official app's Bionic Turnip libraries also export `HMI`, appropriate to their Android HAL integration; it is not the direct ICD API. Conversely, bundled GLIBC PanVK V3 exports the three ICD entrypoints as GLOBAL dynamic symbols.

**Conditional result:** If the app routes F4.2 via `direct-icd`, its current ELF is not compatible with the loader entrypoint contract. If it routes via Android HAL `HMI`, that distinct mechanism needs separate proof. Do **not** call the direct-ICD error observed in a live session: the captured run still lacks any such error event.

## Last device test and diagnostic limits

`panvk-f42-check.txt` has `PANVK_CAPTURE BEFORE_GAME` **10:54:43**, `EmulationService` **10:54:52**, `AFTER_GAME` **10:55:34** and zero `PanVK_F42` tags. Preserves test window; does **not** identify runtimeHost or loaded ICD, nor confirm loader negotiation failure. `/proc/<PID>/maps` denied on Android without root. Crash export is only accessible after an actual crash according to user; never induce one to gather diagnostics.

## Controlled next actions

1. Verify actual runtimeHost of a specific launch independently of the Drivers tab (without inventing an unverified UI control). Match reports to the **same** run.
2. On a **new branch, only after explicit authorization**, adapt the Bionic PanVK integration to export the `vk_icd*` symbols with correct ICD semantics while preserving HAL compatibility if necessary. Validate ELF `nm -D`, linker namespace dependencies, dlsym and negotiation version; changing visibility alone does not prove successful Vulkan creation.
3. Confirm the Bachata success fingerprint `direct-icd loaded=%s sha256=%s interface=%u` and independent PanVK F4.x constructor/CSF telemetry. Only then measure FPS.
4. **Keep stable Phase 3 untouched.** No F4.2 driver changes, APK patch, APK resigning, installation or hardware test took place during this read-only audit.

This report is source-derived from the uploaded APK, F4.2 ELF and uploaded Logcats, plus clearly identified inference for loader routing; it does not claim to have recovered private unshipped Bachata source.
