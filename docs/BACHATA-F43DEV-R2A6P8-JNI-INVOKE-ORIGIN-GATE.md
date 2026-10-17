# Bachata F43DEV — R2A.6/P8: Android host JNI invoke-chain and argument provenance

**Date:** 2026-10-17. **Branch:** `exp/bachata-f43dev-r2a6p8-jni-callsite-trace`. Static/read-only analysis **completed**; real Android host integration and SAF broker **blocked** pending authorized source or diagnostic entrypoint. The working F43DEV V2, PanVK Phase 3 and F4.3 remain unchanged.

## Verified original basis

APK pinned SHA-256: `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. Only original `classes.dex` was inspected read-only. Neither APK nor classes.dex nor Bionic native runtime was committed or uploaded to GitHub; no code ran on the Android device.

The scanner uses structural DEX header/string/type/proto/method/field/class-data tables and **instruction-boundary-aware** Dalvik decoding to avoid confusing a method-index constant with an actual invoke. It scanned **21,397 concrete method bodies** and found exactly:

- **One** `invoke-static/range` to `NativeRuntimeBridge.run(Surface, boolean, String[], String[], String, int): int`, from obfuscated `Lp42;.run():void`, with six consecutive Dalvik argument words, starting at register v2.
- **Three** `invoke-static` calls to `NativeRuntimeBridge.stop()`: `NativeRuntimeService.onDestroy()`, `Lh42;.binderDied()` and `Lq42;.a()`.
- The exact `Lp42;<init>` invocation originates at `Lq42;.c(String[],String[],String,Surface,boolean,ParcelFileDescriptor,Lsc1;):long` and carries **ten** parameter words (including the receiver) via `invoke-direct/range`. The constructor receives `ParcelFileDescriptor`, `NativeRuntimeService`, `Surface`, the two string arrays, the string and three collaboration objects.

## JNI run registers — conservative proven observations

At the sole `NativeRuntimeBridge.run` invocation:

| JNI argument | Verified bytecode source | Semantics status |
|---|---|---|
| `Surface` | `Lp42;.f` | Surface value type confirmed; actual rendering use not established |
| `boolean` | Result of `NativeRuntimeService.a():boolean` | Meaning unknown |
| first `String[]` | `Lp42;.g` | Contents and purpose unknown; do **not** label argv from this alone |
| second `String[]` | `Lp42;.h` | Contents and purpose unknown; do **not** label env from this alone |
| `String` | `Lp42;.i` | Contents and purpose unknown; do **not** infer root path or contract |
| `int` | Success branch: `ParcelFileDescriptor.detachFd()`; error branch: **`-1`** | FD handoff **or explicit invalid-FD fallback**; not always a valid FD |

The negative sentinel comes from a Dalvik `const/4 -1` and a branch `move` assigning the sentinel to the register later passed as the sixth argument. The scanner requires the exact pinned sequence and rejects an unsupported register/branch layout. **The prior simpler statement that the int is always a detached FD has been corrected.**

## Material code and reproducibility

- `tools/bachata-r2a6p8/audit_callsite.py`: no native execution; verifies pinned APK SHA, parses DEX tables and method bodies, inspects exact callsites and immediate register provenance, recognizes the negative FD sentinel. Writes **sanitized JSON only**: method/class names and booleans, no argument values, root paths, session token, nonce, user files or signing material.
- `tools/bachata-r2a6p8/test_callsite.py`: **30 synthetic** Dalvik decoding/invoke/bounds/fail-closed tests, no private APK in CI.
- CI [#39014366795](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39014366795) **SUCCESS**. Source-only artifact [#12094242526](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39014366795/artifacts/12094242526).
- The published CI artifact was extracted locally, `SHA256SUMS.txt` validated, all **30 synthetic tests re-run successfully**, and that **identical published audit script** was run read-only against the pinned known-good APK. Results: run=1, stop=3, 21,397 method bodies, constructor chain=true, `VERIFIED_ORIGINS_WITH_FD_OR_MINUS_ONE`. The baseline APK was not modified.

## Remaining release blockers

1. No complete host `NativeRuntimeService` Android Gradle source or trusted supported in-app debug interface has been provided. DEX callsite evidence is not an authorized way to integrate or re-sign the F43DEV V2.
2. We still cannot prove what the boolean, the two arrays or the string represent in the Bionic launcher. Their types/field origins are proven; **contents and invariants remain undetermined**. Do not guess GLIBC rootfs, environment or broker credentials.
3. No real Android test of `NativeRuntimeBridge.run`, loader/rootfs staging, host signing, `HELLO version=2 contract=<nonce>` response, UID authentication or `BSF1` SAF Stat/List/OpenRead FD transfer has run in this cycle.
4. A separate newly signed Android app will have a different Android Linux UID and does not inherit access to the F43DEV broker. Do not bypass UID or signature verification and do not replace the functioning package.
5. No new APK, release or GPU fix; Outlast and Minecraft remain independently unverified and PanVK Phase 3/F4.3 are preserved.

## Next approval / P9

Obtain the maintainer-authorized **F43DEV Android host source** or a supported in-app debug invocation. Use that to resolve JNI array and string semantics and validate the Bionic-to-GLIBC rootfs mapping and `ParcelFileDescriptor` FD ownership. Only after this gate prepare a **lab-only read-only** on-device SAF fixture test with redacted evidence. The next phase must not fabricate a launch wrapper from the static classes alone.
