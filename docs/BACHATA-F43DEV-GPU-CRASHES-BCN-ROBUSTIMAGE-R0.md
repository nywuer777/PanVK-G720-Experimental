# Bachata F43DEV — GPU crashfix R0: two reproducible core assertions

Date: 2026-10-16 | Branch: `exp/bachata-f43dev-gpu-crashfix-r0`

## Evidence: verified user diagnostic ZIPs

1. `bachata-diagnostic-BS4-20261016-3391886F.zip` SHA256 `89e869953547a8111b01e2d107307703211ae9c316e6fd9bfe20d460aaaa28e1`: game **Outlast CUSA00325**, first frame presented. `image_view.cpp:257 ImageView: Assertion Failed!` followed by the exact cause `GPU BCn decoded image requires a matching sampled BC view`; last preceding GPU BC1/BC3 fallback decoded to R8G8B8A8 UNORM/SRGB. Exit code 139; the report gives terminationKind=UNKNOWN and signalNumber=null.

2. `bachata-diagnostic-BS4-20261016-55D6B9C5.zip` SHA256 `308cfeb7eb73f108e479ec4166eebb6cae5406da143c0643bb8fb141b5efeac0`: game **Minecraft CUSA00265**, first frame presented. `vk_rasterizer.cpp:1940 BindTextures: Assertion Failed!` followed by `Restricted core robust-image compatibility blocker: shader combines guarded mip image fetches with image writes or atomics whose descriptors may alias`. The shader references sampled image id 23 from address `0x2fd81b400`, size `0x200000`, and written image id 24 at **same base address** size `0x280000`. Actual overlapping memory ranges. Exit code 133; terminationKind=UNKNOWN and signalNumber=null.

Both reports unambiguously state **app package** `com.bachatas4.android.f43dev`, **ABI** `linux-glibc-arm64`, **guestBackend** `fex`, **selected driver** `panvk-244793347e1d591f` with `driver.source=glibc`. The shadPS4 native logs show actual Vulkan physical device `GPU_Vendor: panvk`, `GPU_Model: Mali-G720 MC7`, `GPU_Vulkan_Driver: panvk 26.2.99`. These incidents **do not implicate our F4.3 Android/Bionic binary**.

## Engineering corrections required — no assertion suppression

**BCn decoded view mismatch:** ensure decoded host RGBA image view is compatible with descriptor's Vulkan sampled format, sRGB/UNORM, guest/view mip levels, layer ranges and host image dimensions. Correct the descriptor/view creation and fallback transformation; validate BC1 UNORM, BC1 SRGB, BC3 SRGB and 6/10 mips. Never just force the assertion to return or reinterpret compressed data as uncompressed without decoding.

**Robust storage alias:** solve simultaneous guarded LOD reads and writes/atomics referring to overlapping image memory under `restricted core`. Preserve access ordering, barriers and image view/format compatibility; implement correct robust bounds semantics. Never claim `robustImageAccess2` or another extension without actual driver support; do not bypass the fail-closed assertion while the memory hazard persists.

Source binary revision: `433c7f30a66c205dff5c3261431e550957f5d447` — referenced repository `JICA98/Bachata-S4-Dev` returned 404 from GitHub API. The public `zenithblue-oss/shadps4-arm64` core has analogous files but differs in exact functionality and line numbers. Swapping or patching its source blindly **cannot** be represented as a fix for this particular binary. A patched GLIBC executable requires the matching core source/build pipeline or a controlled migration and device validation.

## Material validation performed

Produced locally: `Bachata-F43DEV-BCn-RobustImage-R0-DIAGNOSTICO-REGRESSOES.zip`, SHA256 `f0d43019aa4a2af701dbca7e215aa6bc012ebb82fffb527019dbee7b475dff1d`. Includes `analyze_two_crashes.py`, `test_analyzer.py`, exact original diagnostic derivations in `RESULTADOS.json`, reproduction requirements, reports and SHA256SUMS. **10/10 local regression-test assertions PASS**, including negative tests for altered manifest hashes, wrong ABI and non-overlapping memory. The original diagnostic ZIPs, APK binaries and signing secrets are **not** pushed to GitHub.

### Status/acceptance gate

- [x] Both incident signatures unambiguously identified and differentiated.
- [x] Runtime/actual Vulkan GPU vendor isolated to GLIBC PanVK 26.2.99, not F4.3 Bionic.
- [x] Source revision fingerprint and source availability checked.
- [x] Read-only regression analyzer and adversarial tests built.
- [ ] Obtain matching core source or implement controlled public source port.
- [ ] Rebuild shadPS4 GLIBC/FEX with two real code-level compatibility fixes.
- [ ] Repackage F43DEV with new runtime manifest/checksum and same approved experimental certificate.
- [ ] Confirm Outlast and Minecraft can pass former crash points without rendering regressions on actual G720.

Preserve the user-validated F43DEV Host Identity V2 APK and stable PanVK F3 commit `3cacc2f0bcbb`; do not induce crashes or modify game content. **R0 is DIAGNOSTIC/REGRESSION PREPARATION, NOT A FIXED APK.**
