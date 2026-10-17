# Bachata F43DEV — R2A.6/P6: forensic ABI + loader verification

**Date:** 2026-10-17. **Status:** materially executed read-only **static audit**, not on-device handshake. Branch `exp/bachata-f43dev-r2a6p6-loader-abi-proof`.

## Validated original assets (not uploaded to repository)

Reference APK: `Bachata-S4-F43DEV-HOST-IDENTITY-V2-SIGNED.apk`, SHA256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`.

- APK's `lib/arm64-v8a/libbachata_host_loader.so` (201,208 bytes), SHA256 **`e9d9a01ac27c4369980023a7b20817aa4c158a8bd797c9883bd20386f126e578`**.
- The nested `assets/runtime/runtime.zip` contains `host/ld-linux-aarch64.so.1`, same **201,208 bytes**, **identical bytes** to `libbachata_host_loader.so`. Its SHA matches the `assets/runtime/manifest.json` record.
- `readelf -d` of that loader gives `DT_SONAME: ld-linux-aarch64.so.1`; its exported symbols include `GLIBC_PRIVATE` symbols, and **no JNI bridge exports**. This is a Linux **GLIBC runtime linker** repackaged as an Android-labeled library entry. It is **not** the Android JNI/native launcher.
- APK's `lib/arm64-v8a/libbachata_native_runtime.so` SHA256 `16bd679a762ee3615bc3deb24e0945964775f267eb2f1dc0f015c2eeb030ef54` is a distinct Bionic/Android ARM64 ELF. Its dynamic dependencies include Android's `libc.so` and `liblog.so`. Verified JNI exports: `JNI_OnLoad`, `Java_com_bachatas4_android_runtime_process_NativeRuntimeBridge_run`, and `..._stop`.
- `assets/runtime/manifest.json` declares **`protocolVersion: 2`** and records the original `host/shadps4-arm64-fex` SHA256 **`b1cd025306b1dbd7b07d3bc228a0f18392d4f32fdeb934c9676e75ed0090abb4`**.

## R2A.6/P5 experimental comparison

GitHub Actions [R2A6/P5 #39005515816](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39005515816) fully completed successfully. Artifact [#12092015671](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39005515816/artifacts/12092015671) provides **Linux AArch64 GLIBC ELF only**, not APK.

Checked candidate ELF: SHA256 **`bd495c6085dfd1fb334bd609d2e1fb229f8555ba8d239d5a0ff190c3c6f42f5c`**, matching its published `SHA256SUMS.txt`.

Both original and candidate ELF interpreter declarations are `/lib/ld-linux-aarch64.so.1` and both have the **same list of DT_NEEDED shared library names** (the scripts compare sorted lists, not ABI internals). Candidate includes static string `BACHATA/1 HELLO version=2 contract=`. **That does not establish successful native execution or authorization.** No live process was started.

The earlier interpretation of the filename `libbachata_host_loader.so` as a missing proprietary JNI loader interface is **corrected**: the filename points to the bundled glibc dynamic linker. Host-specific identity and launch code must instead be sought in the Android application's code and `libbachata_native_runtime.so` / JNI bridge. The precise identity checks remain unproven by this static audit.

## New source and CI

- `tools/bachata-r2a6p6/audit_loader_abi.py`: verifies pinned APK/core SHA, bundle manifest consistency, byte-exact rtld alias, ELF AArch64 machine, linker SONAME, JNI bridge dynamic exports, interpreter and DT_NEEDED comparison with P5 core. Output is sanitized JSON of boolean indicators, no tokens, binary blobs, file contents, document URIs, native memory addresses or private paths.
- `tools/bachata-r2a6p6/test_audit_loader_abi.py`: **20 synthetic unit tests** for hash, ELF64 architecture, SONAME, PT_INTERP and runtime manifest.
- CI [R2A6/P6 #39011074702](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39011074702) **SUCCESS**. GitHub artifact [#12093017052](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39011074702/artifacts/12093017052) includes the audit scripts, synthetic tests and expected hashes only.
- Local read-only audit executed against actual original signed APK and R2A6/P5 GitHub artifact, **PASS**. Local unittest 20/20 passed. Static sanitized evidence is preserved separately; original binaries **never uploaded** to GitHub.

## Strict release limits

- APK signature verification **not performed cryptographically by this script**; matching a known SHA256 only identifies the pinned baseline.
- AArch64/GLIBC ABI and bundled loader equality do **not** prove the Android GLIBC root maps the candidate PT_INTERP correctly at runtime. Loader environment, ELF mounting/exec permissions and FEX start-up remain a **hardware test blocker**.
- Bionic JNI bridge symbol presence does **not** prove the exact interface, host ABI, signature enforcement or UID authorization. The original Android Gradle host source, developer-authorized debug interface or a supported diagnostic entrypoint is still needed.
- R2A6/P5 correct HELLO V2 syntax and R2A6/P2 BSF1 mock tests do not prove authentic Android broker connectivity. **No real Android broker handshake executed.**
- No APK rebuilt, resigned, installed or replaced. Functional F43DEV V2, PanVK Fase 3 and PanVK F4.3 preserved; no claims for Outlast/Minecraft fixes or FPS improvement.

## Next gate (P7)

Acquire authorized **host Android source or official diagnostic interface**, trace `NativeRuntimeBridge.run` contract and GLIBC root staging (without bypassing app identity), then test using disposable, non-sensitive SAF fixture and redacted outcome codes on Android. Do not treat the GLIBC ld.so copy as JNI. Keep the known-good V2 unchanged.
