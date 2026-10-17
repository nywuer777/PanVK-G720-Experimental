# Bachata F43DEV R2A.6/P2 — broker BSF1 proof, separate from game boot

Date 2026-10-17. Branch `exp/bachata-f43dev-r2a6p2-saf-probe`. Source pinned `zenithblue-oss/shadps4-arm64` at `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`. GitHub Actions [#39000437946](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39000437946).

## Problem solved at this stage

The R2A.6/P1 experimental `/app0` mount compiled but the original `--game <absolute-eboot>` loading gate still invokes `Core::Loader::Elf::Open()` on a **local Linux path**. For games accessed only via an Android DocumentsProvider, this early check cannot demonstrate broker interoperability. Also, a successful glibc ARM64 compilation never demonstrates a functioning same-UID Android broker.

R2A.6/P2 introduces an independent *metadata-only* lab diagnostic in the existing pinned GLIBC/FEX candidate. It runs **after** the R2A2 host-control socket identity checks and `BACHATA/1` `SendStarting()` but **before** early ELF loader validation, game loading, SDL, Vulkan, or the guest filesystem. The Android host must supply both the existing managed launch arguments and explicit opt-in:

- `--bachata-saf-probe-only`
- `--bachata-saf-probe-path` followed by an explicitly selected, non-sensitive broker-relative test fixture (never guess the path or put user secrets into examples).
- `--bachata-saf-vfs-lab` **cannot** coexist with probe mode.
- Probe paths are redacted in both CLI11 separate-value and `--flag=value` forms. Existing nonce, token, broker socket and VFS-root redaction stays in place.

`tools/bachata-r2a6p2/saf_probe.cpp/.h` dispatches `BSF1::Stat`, then `BSF1::List` for a directory or `BSF1::OpenRead` + `fstat`/read-only FD validation for a regular file. **No `read`, `pread`, file copy, logging of returned filenames, token, document path or content**. Only static outcome codes like `BSF1_LAB_PROBE_FILE_OK`, `...DIRECTORY_OK`, `...STAT_FAILED` are emitted. Runtime signals `Stopped(0)` or `Error/Stopped(1)` to the host. No game starts in probe-only mode.

`tools/bachata-r2a6p2/apply_r2a6p2.py` applies the two source files to the pinned chain of R2A, R2A2, R2A4, R2A5, R2A6/P0 and R2A6/P1, updates CMake and the executable's flags, validates unique anchors, and changes nothing in installed APKs.

## Verified tests and evidence

- Original workflow upload had a YAML validation error in its sanitizer step label (no jobs ran). Corrected in commit `987f03706ab9d61650f6b4d682b13b7bf2b9bc8e` and triggered [#39000437946](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39000437946).
- `source-preflight` **SUCCESS**: 14 checks with deterministic synthetic local socket server (success on Stat+OpenRead, Stat+List, malformed paths, bad wire magic, remote status, missing FD, result data leak checks); the same 14 checks pass AddressSanitizer/UndefinedBehaviorSanitizer. No real tokens, games, or Android system contacted.
- Patch chain applies to pinned upstream source, `git diff --check` passes, CLI redaction and post-host-handshake probe entry are statically verified.
- `aarch64-glibc-probe` and `full-core-elf` jobs are independent compile gates; their results must be checked separately. Do **not** claim full-core compilation unless the run reports success.

## Blockers and non-goals

1. **No on-device broker test yet.** Neither mock server success nor static Bionic disassembly verifies the live Android broker protocol, package signature, session token, or actual broker-relative file-root.
2. R2A2 host gate is bound to existing package `com.bachatas4.android.f43dev`. A new side-by-side APK would need an intentionally distinct, valid signer/package trust chain. The functional F43DEV V2 app must not be overwritten, resigned or patched to spoof the original identity.
3. Without controlled access to the host application's code/development build **or an officially supported diagnostic command path**, there is no safe means to invoke the probe within the original app's UID. A separately installed Android app runs under another UID and cannot meaningfully authenticate to that broker.
4. Probe covers only metadata and read-only descriptor transfer, not complete game loading, `--game` path handling, patch system, save data, full VFS isolation or GPU.
5. Outlast's BCn view mismatch and Minecraft's robust aliased-image behavior remain unresolved.
6. A pass must be accompanied by complete **redacted** evidence: static success code, process exit, host control-socket lifecycle and basic ABI. Never capture/send a real nonce, session token or filesystem content.

## Suggested next gate

Audit full-core ELF. Obtain a *user-authorized Android host integration path* (source or supported test harness, not spoofing signature). Add one safe non-game fixture through DocumentsProvider and request the probe using controlled host-side flags. Verify `BSF1_LAB_PROBE_FILE_OK` / `...DIRECTORY_OK` and an intentional failing request, with no secrets or personal files logged. Only then advance to a separately signed lab app. PanVK Fase3 and F4.3 and F43DEV V2 remain unchanged.
