# Bachata F43DEV — R2A.6/P3: Android SAF broker proof gate

**Date:** 2026-10-17. **Status:** completed **offline/static preparation and CI**, **blocked** on live Android host integration.

Branch: `exp/bachata-f43dev-r2a6p3-android-proof-gate`. CI: [#39004210461](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39004210461) — **SUCCESS** (one job). Latest proven R2A6/P2 full FEX compilation: [#39000550880](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39000550880) — **SUCCESS**.

## New P3 implementation

- `tools/bachata-r2a6p3/device_evidence.py`: rejects noncanonical, duplicated, out-of-order or private event records. It allows only narrowly curated static codes: host gate, BACHATA/1 control messages, BSF1 probe outcome and terminal exit code. Never echo arbitrary input, files, game paths, token, nonce or socket name. **Even a perfect text report sets `source_authenticated=false`, `apk_signature_verified=false`, `real_broker_verified=false`.**
- `tools/bachata-r2a6p3/test_device_evidence.py`: **22 passing tests** in CI and repeated locally, including forged/different exit status, missing host, duplicated events, invalid paths and secret leakage.
- `.github/workflows/bachata-f43dev-r2a6p3-android-proof-gate.yml`: deterministic no-network test corpus, publication of synthetic-only non-installable audit artifact [#12089864825](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39004210461/artifacts/12089864825).
- Standalone verified local kit `Bachata-F43DEV-R2A6P3-ANDROID-SAF-PROOF-GATE-KIT.zip` SHA256 **`e8da090bfe625f9ebfa6686d7702f3bf9b9da145d9bc31a0b793de18dbbfe2f5`**, with source, local tests, a portable read-only ELF audit script and its signed-baseline vs. candidate comparison. No ELF or APK binaries shipped inside this kit.

## Original ELF versus GLIBC R2A6/P2 candidate (read-only audit)

Actual signed F43DEV Host Identity V2 APK SHA256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`; nested `host/shadps4-arm64-fex` SHA256 `b1cd025306b1dbd7b07d3bc228a0f18392d4f32fdeb934c9676e75ed0090abb4`, 75,323,616 bytes.

R2A6/P2 ELF candidate SHA256 `33fdacf7529e85613e866bc41c4179dcaf62d920c1e52bf508caefd79a2c6914`, 99,332,584 bytes (not stripped, debug info). ZIP CRC passed, internal GitHub SHA256 manifest matched extracted ELF.

Both binaries are ELF64 AArch64 PIE, use `/lib/ld-linux-aarch64.so.1`, have the same seven DT_NEEDED shared-library names, and reference GLIBC up to 2.38. **ABI consistency is necessary but insufficient** for runtime contract and identity.

Original ELF contains text references `libbachata_host_loader.so` and `host identity check failed`; the public candidate lacks them, instead containing `BACHATA_F43DEV_R2A2_HOST_GATE_OK` and the new `BSF1_LAB_PROBE_FILE_OK` markers. These are static string-presence facts, not proof of actual control flow. This divergence **blocks replacing the original GLIBC binary** until original host-loader interface, app signing and behavior are verified.

## Hard blocker: Android application source and same-UID broker

The available `PanVK-G720-Experimental` branch contains core/patches, but not the Android host's complete Java/Kotlin/Gradle source. Available files include the signed APK and diagnostic archives. This is insufficient to generate a safe, authorized host-side diagnostic integration.

The original Android app-private socket and transient token belong to its process and Linux UID. A newly signed side-by-side package does not have the original UID or signing identity. `SO_PEERCRED` same-UID verification is **not** the cryptographic certificate check originally enforced by the Bionic host. Neither re-signing the V2 package nor overriding UID checks is permitted for this laboratory effort.

### Hardware acceptance test — NOT RUN

Requires a maintainer-authorized Android host debug interface/source plus an **isolated** lab environment. The real host must spawn a matching, correctly authenticated GLIBC core in `--bachata-saf-probe-only` mode with ephemeral secret fields never printed to logs. Test one authorized non-sensitive file (`Stat` + `OpenRead` read-only FD without file content reads) and one directory (`Stat` + `List`). Negative test missing/wrong token, unauthenticated peer, invalid path, malformed packet, denied access and missing descriptor.

Collect only static codes plus exit status; do not export original tokens, any Android app-private pathname, document URI, full `logcat`, game content or signing keys. Treat the curated text file as **untrusted evidence until bound to a trusted test session**. A successful `device_evidence.py` run alone never proves real Android interoperability.

## Next

Obtain the complete F43DEV Android host source or an officially supported authorized broker diagnostic channel, define an independent signed lab identity and comparable broker trust gates, then perform the above on-device test with user approval. Do **not** mutate the working V2, PanVK F4.3 or Fase 3. Outlast BCn view mismatch and Minecraft texture alias remain GPU issues unverified here.

No APK was built or installed in P3, and **no real Android broker handshake was executed**.
