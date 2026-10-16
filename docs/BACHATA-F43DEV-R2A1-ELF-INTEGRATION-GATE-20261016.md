# Bachata F43DEV — R2A.1: ELF integration gate (read-only)

Date: 2026-10-16. Branch: `exp/bachata-f43dev-r2a1-integration-gate`.

## Inputs and provenance

- User-validated **F43DEV Host Identity V2** APK, expected SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. **This copy was not complete in the active container session** (about 120 MB and ZIP invalid); do not attempt to install, repackage, or extract it.
- ABI and runtime comparison instead used intact **F43DEV V2 Vulkan Proof Debug** APK SHA-256 `85d07bf7b81eac9335c7830bb045eda0f1af6bf3eeb689fb843519c154aa70b8`. Its prior creation audit verified that only AndroidManifest.xml differs from the original V2 and 429 other ZIP entries, including `assets/runtime/runtime.zip`, are identical. **No APK was re-signed or modified during this audit.**
- R2A artifact: [GitHub Actions #38953746578 artifact 12072665288](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38953746578/artifacts/12072665288), source `zenithblue-oss/shadps4-arm64` commit `be6bc2e9c60799e071dd2fafa6216e8d80ec619c` with R2A source patch. GitHub CI completed successfully.

## Independently extracted ELF identity

| Field | F43DEV installed-equivalent GLIBC host | Public R2A candidate |
|---|---|---|
| Path | `host/shadps4-arm64-fex` | `shadps4-arm64-glibc-R2A-CANDIDATE` |
| SHA-256 | `b1cd025306b1dbd7b07d3bc228a0f18392d4f32fdeb934c9676e75ed0090abb4` | `333e7f0c0dc79be4f007958f2018710f91ffd4245ef3b5e475621d33d4eb7584` |
| Size | 75,323,616 bytes | 99,320,424 bytes |
| Build ID | `b505e6d4f2dbf557e2d9577ca9029281d685fb96` | `3eff62b26ad906c8b01485495d13f92bdee60134` |
| ELF / interpreter | ELF64 AArch64; `/lib/ld-linux-aarch64.so.1` | Same |
| DT_NEEDED | 7 entries | Same 7 entries |
| Required GLIBC, GLIBCXX and CXXABI version set | Baseline set | Exact same set |
| `host identity check failed` literal | Present | Not found |
| `libbachata_host_loader.so` literal | Present | Not found |

Both archive ZIP CRC validations PASS; R2A artifact `SHA256SUMS.txt` matches extracted ELF; F43DEV `assets/runtime/manifest.json` and `usr/share/bachata/guest-runtime.json` host SHA-256 agree with baseline ELF and all seven host libraries are present.

**Important nuance:** strings differing do not prove the candidate lacks every equivalent security check. But **identity parity and loader handshake are not proven**, so a binary swap is **blocked** until a demonstrably equivalent trusted host identity flow is implemented and tested. The baseline native core was built from a different unavailable Bachata revision; public R2A is not a verified drop-in replacement.

## Executed safety gate and evidence

Built locally `audit_r2a_integration.py` (read-only, fail-closed) and `test_audit_r2a_integration.py`. The scanner verifies ZIP integrity, source pin and patch in provenance, core hashes/manifests, interpreter, library dependencies, version requirements and identity markers.

- **18/18 local unit tests PASS.**
- Static ELF/dependencies gate **PASS**.
- Runtime host identity and Android-GLIBC handshake **NOT PROVEN**.
- Actual Outlast BCn and Minecraft aliasing crashes **NOT FIXED/NOT RETESTED**.
- PanVK F4.3 Bionic **NOT CONFIRMED in GLIBC**.
- Result: `BLOCKED_PENDING_HOST_IDENTITY_AND_RUNTIME_MIGRATION`; `safe_to_replace_baseline=false`.
- User-facing source/report-only kit SHA-256 `55163a857a2af39717f52cecf9b44c72252237ac91c7a58cc9e2e7a657964803`. **No signing keys, full binaries, game data or APK inside kit.**

## Next safe engineering cycle

1. Recover or reimplement equivalent validation of exact Android host package, signing certificate and GLIBC loader handshake **without bypassing identity verification**; require a trustworthy runtime-to-app test.
2. Stage an isolated laboratory runtime with the R2A ELF in `host/shadps4-arm64-fex`, regenerate `usr/share/bachata/guest-runtime.json`, outer runtime `manifest.json` per-file checksum and runtimeVersion. This is **not authorized to replace the functional APK** until step 1 passes.
3. Ensure original host runtime safety/features are accounted for: private BCn decoded-view fallback absent in public source and Minecraft cross-image robust alias guard not replaced by R2A.
4. Only then produce an isolated signed APK and validate startup, game render, Outlast, Minecraft, PanVK ICD provenance and rollback in hardware.

Stable PanVK Phase 3 commit `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb`, F43DEV V2 and PanVK F4.3 are unchanged.
