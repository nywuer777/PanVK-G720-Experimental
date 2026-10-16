# Bachata F43DEV — R1: GLIBC/FEX core rebuild foundation

Date: 2026-10-16. Branch: `exp/bachata-core-glibc-r1`; parent: `exp/bachata-f43dev-gpu-crashfix-r0`.

## Baseline provenance, fail-closed

- **Known functional F43DEV Host Identity V2 APK SHA-256:** `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. This APK was re-hashed locally on 2026-10-16 and was not modified.
- Installed native shadPS4 ELF identifies `JICA98/Bachata-S4-Dev` commit `433c7f30a66c205dff5c3261431e550957f5d447` — GitHub API returns 404; source access missing. Official public `JICA98/Bachata-S4` repository current tree contains 24 records mostly compatibility-site/docs and **does not provide C++ sources**.
- **Alternate source candidate (not the installed code):** public `zenithblue-oss/shadps4-arm64`, pinned to `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`. Contains source, FEX guest backend, `runtime/scripts/build-runtime-debian.sh`, `build-shadps4-arm64.sh`, `build-fexcore-smoke-aarch64.sh`, lockfiles. License GPL-2.0-or-later.
- Divergence **verified:** installed BCn crash references `image_view.cpp:257`, candidate source file has 133 lines; Minecraft refs `vk_rasterizer.cpp:1940`, candidate file has 1475 lines. Therefore the candidate core cannot be treated as a drop-in runtime without an explicit migration and ABI/integration tests.

## Locally executed prep (12/12 tests PASS)

Delivered **Bachata-F43DEV-CORE-GLIBC-R1-SOURCE-BUILD-KIT.zip** with source pin, `scripts/source_preflight.py`, `scripts/checkout_and_build.sh`, `scripts/validate_candidate_elf.py`, 12 local unittest cases, negative tests against wrong SHA/uninitialized git submodules/x86_64/invalid ELF, SHA256SUMS, GitHub Actions cross-build recipe and docs. Standalone source lock preflight gives `LOCK_ONLY`; no source checkout or ARM64 binary build can occur locally because container DNS cannot resolve github.com. Docker/Podman and ARM64 toolchain are absent in that environment.

## CI source + Linux/GLIBC cross-build

Workflow `.github/workflows/bachata-core-glibc-r1.yml` on R1 branch should:
1. Check out pinned source commit and verify actual sha and required C++/FEX build scripts.
2. In disposable `debian:trixie` Docker Action job install upstream pinned multiarch ARM64 dependencies and submodules.
3. Execute upstream `runtime/scripts/build-runtime-debian.sh`, which invokes FEXCore and shadPS4 cross builds.
4. Verify that output ELF is ELF64 **AArch64** with `/lib/ld-linux-aarch64.so.1` and `libc.so.6` (GLIBC, not Bionic).
5. Upload **only** candidate ELF, build metadata, checksums — no modified APK or device auto-update. CI run result must be checked before claiming build success.

## Follow-on, explicitly pending

Outlast CUSA00325: BCn fallback sampled image view correctness for BC1 UNORM/sRGB and BC3 sRGB, mips/layers. Minecraft CUSA00265: correct robust mip image reads + image writes/atomics over aliased backing and synchronization; no disabling assert or falsely advertising robustness extensions. Apply source changes only once compiler/build path works and matching code has been audited; do not claim the 2 crashes fixed by this R1.

**PanVK stable Fase 3** commit `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb` and F4.3 Bionic both unchanged. R1 is source-build groundwork, not GLIBC PanVK port or fixed game APK.

## CI R1 first attempt failure and R1.1 correction

- First execution [38938884730](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38938884730): `source-preflight=success`, `arm64-glibc-candidate=failure`, 51m45s as seen on user screenshot. shadPS4/FEXCore compiled and staged its `needed.txt` before a later `runtime/scripts/build-vortek-client.sh` preflight raised `Vulkan headers (vulkan/vulkan.h and vulkan/vk_icd.h) not found`. Root cause is the *Vortek client packaging* script's search under `/usr/include`, `runtime/sources/mesa/include`, `/usr/aarch64-linux-gnu/include`. It is not an observed compiler failure in the Vulkan renderer or the driver.
- Required fix for future **full-runtime** packaging: add suitable Vulkan development headers (e.g. Debian `libvulkan-dev`) and prove both required files exist before invoking `build-vortek-client.sh`. That full packaging path is not the R1 acceptance criterion and remains separately pending.
- CI correction commit `bfe5fce8bddc50c2b1db33c6bbffbf50e1b57047`: run only `runtime/scripts/build-shadps4-arm64.sh` for this **core-only** gate. This upstream script itself invokes FEXCore and produces `runtime/build/shadps4-arm64-stage/bin/shadps4-arm64`. The workflow separately checks `ELF64`, `AArch64`, `ld-linux-aarch64.so.1`, `libc.so.6` and rejects `liblog.so` Bionic; it stages the executable and ELF inspection reports if valid. No bypass of the *core acceptance checks*.
- Follow-up execution [38945784489](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38945784489) started. At first checked, preflight success; candidate job fetching pinned submodules. **No success claimed before terminal CI result and verified artifact.**
- Existing scheduled alert retargeted from failed first run to follow-up corrected run #38945784489.
