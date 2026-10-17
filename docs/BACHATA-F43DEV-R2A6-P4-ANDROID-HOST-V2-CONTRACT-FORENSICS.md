# Bachata F43DEV — R2A.6/P4: original Android host contract versus public GLIBC core

**Execution date:** 2026-10-17. **Branch:** `exp/bachata-f43dev-r2a6p4-host-contract-v2-audit`.

## Decision

**Do not install, overwrite, repack or replace the functional F43DEV Host Identity V2 APK.** The R2A6/P2 candidate compiles and its local BSF1 mock probe tests pass, but the original APK host advertises a different control-protocol contract from the public source. A live Android broker test is still **NOT PERFORMED**. Both PanVK Fase 3 and F4.3 are preserved.

## Verified material evidence

A reproducible **read-only** audit ran against the actual signed known-good APK and against the CI artifact containing the GLIBC R2A6/P2 ELF. It validates original APK/core hashes, DEX bytecode string-table layout, embedded runtime ZIP, public header protocol constant, candidate ELF SHA manifest and probe symbols. Findings:

| Source | Grounded observed result |
| --- | --- |
| Functional APK `Bachata-S4-F43DEV-HOST-IDENTITY-V2-SIGNED.apk` | SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded` |
| APK `classes.dex` DEX strings | Contains literal `BACHATA/1 HELLO version=2 contract=` |
| APK `classes.dex` DEX strings | Contains `Runtime contract mismatch (app requires protocol 2)` |
| APK `classes.dex` | Contains `--bachata-saf-socket` and `--bachata-saf-token` |
| Nested `assets/runtime/runtime.zip` original GLIBC `host/shadps4-arm64-fex` | SHA-256 `b1cd025306b1dbd7b07d3bc228a0f18392d4f32fdeb934c9676e75ed0090abb4` |
| Original GLIBC core | Contains `BACHATA/1 HELLO version=` and adjacent ` contract=` strings; values assembled dynamically |
| Public upstream `src/platform/bachata/runtime_client.h` at `be6bc2e9c60799e071dd2fafa6216e8d80ec619c` | `constexpr unsigned RuntimeProtocolVersion = 1;` |
| Public upstream `RuntimeClient::SendHello` | Sends `BACHATA/1 HELLO version=1` via current protocol constant; does **not** attach `contract=` |
| R2A6/P2 candidate | SHA-256 `33fdacf7529e85613e866bc41c4179dcaf62d920c1e52bf508caefd79a2c6914`; has `BSF1_LAB_PROBE_FILE_OK` and `--bachata-saf-probe-only` strings; CI SHA manifest checked |

The static evidence establishes a **version/field divergence**. It does **not** by itself prove every real session fails, because the host may distinguish modes and the complete original native GLIBC control state machine has not been exercised in a live test. Under these circumstances a compatibility claim would be unjustified.

The APK contains both `lib/arm64-v8a/libbachata_native_runtime.so` and `assets/runtime/runtime.zip` with the GLIBC core; it is a compiled Android deliverable, **not the complete editable Java/Kotlin/Gradle source tree**. The project repository and current user-provided file set do not include that host source. Decompiling or patching the signed APK is not a supported way to produce a trusted new Android host.

## Material R2A6/P4 tool

- `tools/bachata-r2a6p4/audit_host_contract.py`: read-only static audit. Pins APK and original GLIBC core SHA-256, parses DEX string offsets, inspects the nested runtime.zip, reads a pinned public protocol header excerpt and verifies the R2A6/P2 candidate CI manifest. The report never contains session tokens, pathnames, game content or decompiled private methods. Explicit booleans `real_android_broker_verified=false`, `apk_signature_verified_cryptographically=false`, `test_executed_on_device=false`.
- `tools/bachata-r2a6p4/test_audit_host_contract.py`: 12 synthetic DEX / input-integrity regression cases. CI [#39004899150](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39004899150): **SUCCESS**. The same 12 tests passed in the local container.
- A local, actual-APK run of the verifier returned `host_dex_explicit_hello_v2_contract=true`, `host_dex_requires_protocol2=true`, `original_glibc_core_baseline_match=true`, `public_runtime_version=1`, `candidate_sha_manifest_match=true`, `real_android_broker_verified=false`. This device-independent evidence is contained in the local handoff ZIP.

## Decision gate for Android implementation

Before turning on a real broker probe, obtain either:

1. The **maintainer-authorized F43DEV Android host source** (Gradle/Kotlin/Java and JNI bridge code), including version-2 host HELLO/contract negotiation, SAF broker lifecycle and native runtime launcher; **without** signing keys, nonces, session tokens, or app-private user data; or
2. A documented, **officially supported diagnostic launch interface** that allows the original signed host, while it is running on the device, to request a safe `BSF1` diagnostic using a non-sensitive fixture without modifying its own APK.

Use an **independently signed experimental package** with a deliberately separate identity only after the package/UID and broker authorization model has been designed and verified. It will not gain the original app's UID by using the same label. Do not disable peer authorization, claim a forged certificate, edit the signed V2, or overwrite the frozen APK.

No assumptions are made about how version 2 nonce/contract fields are computed. **Do not patch `SendHello` to append a guessed string:** implement against the actual host source and test it with a mock host and the real Android host before enabling the guest VFS.

### Future release criteria

- Verify the version-2 handshake contract and expected runtime events with original host code.
- Produce a new versioned CLI/runtime ABI integration with no secret logging, no real token redistribution and no bypass of Android certificate/UID controls.
- Exercise `BSF1::Stat/List/OpenRead` against an opt-in, non-sensitive user-chosen fixture with read-only FD and negative-case tests; capture only sanitized markers.
- Confirm the mounted guest `/app0` root, PS4 `open/stat/fstat/getdents` and write protection without fallback to host paths. **Only then** test loading a game and independently tackle Outlast BCn and Minecraft aliased images.

This step produced **no new APK**, **no new GPU FPS gains** and **no confirmed real Android handshake**.
