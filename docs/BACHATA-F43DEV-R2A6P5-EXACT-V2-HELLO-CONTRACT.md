# Bachata F43DEV — R2A.6/P5: exact Android Host Identity V2 HELLO contract

**Date:** 2026-10-17. **Experimental branch:** `exp/bachata-f43dev-r2a6p5-host-contract-v2-fix`. Source pin for public GLIBC/FEX candidate: `zenithblue-oss/shadps4-arm64@be6bc2e9c60799e071dd2fafa6216e8d80ec619c`. Baseline signed APK **unchanged** SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`.

## Material binary finding: this is no longer only a string guess

Read-only analysis of `classes.dex` from the pinned **functional F43DEV V2 APK** proves the sequence below (the identifiers are obfuscated and apply only to this exact APK):

1. `Lyy2;.<clinit>`: loads regexp `[0-9a-f]{32}` and compiles its matcher.
2. `Lyy2;.a()`: instantiates `java.security.SecureRandom`, allocates a **16-byte** array, calls `SecureRandom.nextBytes` and encodes a 32-digit lowercase hexadecimal nonce.
3. `Lyy2;.b(String,String)`: rejects an invalid nonce; constructs the literal `BACHATA/1 HELLO version=2 contract=` concatenated with the nonce, then compares the **entire received line** using `String.equals`. On an invalid nonce, returns/throws via a message with `Invalid runtime contract nonce`.
4. `Ltt0;.s`, the service's runtime initialization coroutine: invokes `Lyy2;.a()` before building `Ltz2;`'s runtime process request (which holds a field named `contract`), and invokes `Lyy2;.b()` before continuing backend startup; mismatch path reports `runtime contract mismatch; stopping backend`.
5. Original bundled GLIBC core has `BACHATA/1 HELLO version=` and ` contract=` strings. The public upstream runtime `RuntimeClient::SendHello(unsigned)` emits a v1 line without contract, explaining an actual source-level gap.

The proof is **static binary/source evidence**. It does not prove that an arbitrary replacement GLIBC ELF passes developer-signature validation or communicates with the private Android SAF broker.

## Executed change: source-pinned candidate only

- `tools/bachata-r2a6p5/f43dev_contract_v2.h`: `ValidNonce` accepts **only** exactly 32 ASCII lowercase hex characters (no uppercase, NUL, slash, whitespace or newline); `BuildHello` returns exactly `BACHATA/1 HELLO version=2 contract=<nonce>\n` or rejects malformed input. The nonce is not logged.
- `tools/bachata-r2a6p5/apply_r2a6p5.py`: requires exact upstream commit and prerequisite patch chain R2A, R2A2, R2A4, R2A5, R2A6/P0, R2A6/P1, R2A6/P2. Adds a dedicated `RuntimeClient::SendHelloV2(std::string_view)` sending the validated frame on the **existing managed control socket**.
- On **Linux AArch64/F43DEV**, startup validates the lowercase hex contract *before* connecting sockets, verifies the R2A2 app-private root and same-UID peer, and only then calls `SendHelloV2(*bachataContract)`. Other development/platform paths keep their existing SendHello behavior.
- The identity gate, `--bachata-saf-socket` and `--bachata-saf-token` checks, CLI redaction and SAF probe flag remain intact. This patch does **not** disable or imitate signing/UID checks.

## Evidence gates

GitHub Actions [#39005515816](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39005515816):
- `host-v2-protocol-and-source` **SUCCESS**: 25/25 synthetic V2 nonce/frame checks under both standard C++ and ASan/UBSan, upstream patch chain applies, `git diff --check` passes, R2A6/P4 synthetic DEX tests and R2A6/P3 sanitized-evidence tests pass.
- `glibc-arm64-hello-object` **SUCCESS**: a Linux AArch64/GLIBC test ELF built with strict flags and ELF architecture verification.
- `full-glibc-fex-candidate` **IN PROGRESS** when this report was prepared. Its final result **must not be inferred from earlier jobs**. A successful build remains non-installable until the original Bionic host-loader trust chain is reconciled.

The locally run extra DEX trace `audit_nonce_flow.py` validates all nine structural facts above against the pinned signed APK; only boolean evidence and SHA are emitted, no nonce.

## Explicit limitations and remaining blockers

1. No complete Android Gradle/Java/Kotlin F43DEV host project was provided, so there is **no authorized integration path to run this candidate under the host's signing/UID identity**.
2. The original GLIBC executable and public reconstructed candidate differ beyond the HELLO: the original contains references to `libbachata_host_loader.so` and an additional private identity check. Matching the v2 line does not supply that missing native integration.
3. The Android SAF broker's actual `BSF1` handshake and a real file/directory descriptor were **not** tested on the target device. The probe-only mode still needs correct host launch arguments and a trusted socket.
4. This release does not modify or replace the signed functional F43DEV V2 APK; no substitute APK, no certificate spoofing, no bypass of Android private data or host UID.
5. PanVK Fase 3 and F4.3 remain unchanged. No claim is made of Outlast BCn or Minecraft mip-alias bug fixes.

## Next release gate

Obtain authorized host project source or supported in-app broker diagnostics; verify its package signing and original native host loader contract; then test the V2 HELLO on the device with an ephemeral nonce injected only by the trusted host and redact all secret material from test outputs. If the authorized host approves, run the existing R2A6/P2 `Stat/List/OpenRead` probe against **non-sensitive test fixtures**; never expose game data or user files in reports.
