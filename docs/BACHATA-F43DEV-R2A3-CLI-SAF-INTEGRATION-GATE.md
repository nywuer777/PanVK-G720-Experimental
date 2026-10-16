# Bachata F43DEV R2A.3 — ABI valid, runtime assets staged, SAF/contract gate BLOCKED

Date: 2026-10-16 | Branch: `exp/bachata-f43dev-r2a3-saf-contract-gate`

## Executed with original user-verified files (read-only)

- Baseline signed APK `Bachata-S4-F43DEV-HOST-IDENTITY-V2-SIGNED.apk`, SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. Verified with independent APK v2 RSA+digest verifier: signer cert SHA-256 `224cc7d30bbcd6ccbceaba9ea373dc6840d600c0be9e47e8e418684138b4c9a3`, expected package `com.bachatas4.android.f43dev`, Bionic native runtime hash and driver ZIP hash unchanged, CRC and stored-data alignment PASS. 430 entries.
- Exact GitHub Actions [R2A.2 #38963049803](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38963049803) finished SUCCESS; ELF artifact [#12075748618](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38963049803/artifacts/12075748618), artifact ZIP SHA-256 `a5bc190589d9deba5f299e8b51fd1e2cdf844df70a1ca5af3006e4dc17963c27`. Inner Linux ARM64/GLIBC candidate ELF is 99,321,872 bytes, SHA-256 `dd74ed1b9aeaa5ade19112c3b42d9eedeb130e33c4c7358856bdcf8be60b6e3b`.
- Old V2 ELF size 75,323,616 bytes; both ELF64 AArch64 PIE, `/lib/ld-linux-aarch64.so.1`. Compared `DT_NEEDED` entries identical and no additional `GLIBC` / `GLIBCXX` / `CXXABI` symbol version requirements in R2A2 candidate. `BACHATA_F43DEV_R2A2_HOST_GATE_OK` appears in new ELF. Original old host's internal `host identity check failed` protection is different, and parity with native signer is NOT established by the new SO_PEERCRED/UID check.
- R2A.2 staging script rechecked all **397** ZIP entries against baseline manifest hashes, rewrote **only 3** nested assets: `host/shadps4-arm64-fex`, `usr/share/bachata/guest-runtime.json`, `usr/share/bachata/guest-runtime.txt`. All **394 other nested runtime files** remain byte-identical. Staged runtime version `runtime-72523e491d27`, ZIP SHA-256 `b9be70b32908f3a72b4925f0755714454a2f644b2b0a30493127835a7dfdd7a9`. Repacked nested manifest SHA/size and CRC validated. **Staging is NOT an installable APK.**
- Executed 10 local test cases for observed CLI contract and secret redaction; 10/10 PASS. Logs `bachata-diagnostic-BS4-20261016-3391886F.zip` (Outlast), `55D6B9C5.zip` (Minecraft) and `8B4F1AA7.zip` (third game) were read locally. Only CLI **option names** were saved; token values and full log lines were **not** published.

## Critical blocker: host SAF/contract API missing

All three tested game sessions pass `--bachata-contract`, `--bachata-saf-socket`, `--bachata-saf-token`, `--bachata-socket`, `--bachata-storage-root`, `--ignore-game-patch`, `--override-root`. Public candidate source at `zenithblue-oss/shadps4-arm64` commit `be6bc2e9c60799e071dd2fafa6216e8d80ec619c` only declares the latter options, and lacks the three SAF/contract options and an equivalent SAF client under `src/platform/bachata`.

Because the candidate uses CLI11 `app.allow_extras()`, unknown flags **might not crash the parser**. This does not implement the SAF transport, token handling, PS4 file access or contract validation. Therefore the previously claimed ABI match and generic `BACHATA/1` control socket compatibility are *necessary but not sufficient* for boot/real game I/O. Explicitly avoid accepting/ignoring arguments without reconstructing semantics. The private original shadPS4 core revision `433c7f30...` is not accessible.

**R2A.3 release gate: BLOCKED.** No signed APK produced, no replacement of installed working F43DEV V2, no demonstrated Android handshake, no Outlast/Minecraft crash resolution. Fase3 PanVK `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb` and F4.3 Bionic untouched.

## Future R2A.4 requirements

1. Recover compatible SAF/contract source from the original core OR design/implement a faithful authorized SAF client in public core. Document message framing, token authentication, path permissions, error handling, input/output consistency, race/replay handling; maintain Bionic APK-signature verification.
2. Rebuild ARM64/GLIBC core with supported CLI and SAF protocol semantics (not a stub/ignored switch); add negative tests for invalid tokens, socket reuse and unauthorized document access.
3. Build **separate and reversible** Android laboratory APK only after full app/core integration passes offline audits; the same package name would **update**, not install side by side with F43DEV V2. Require a genuinely distinct package+identity for coexistence.
4. Test boot, handshake, SAF reads and games on Android hardware. Only then evaluate Outlast BCn and Minecraft read/write aliased image bug; no PanVK F4.3 GLIBC-use assertion without actual loaded-ELF proof.

## Reproducible materials

CI workflow `.github/workflows/bachata-f43dev-r2a3-saf-contract-audit.yml` uses a fresh pinned Git checkout to check real public source and emits a **BLOCKED** report without confidential diagnostic tokens. Local R2A.3 staged runtime (two files and report) and auditor script/tests are distributed separately; neither is a signed APK.
