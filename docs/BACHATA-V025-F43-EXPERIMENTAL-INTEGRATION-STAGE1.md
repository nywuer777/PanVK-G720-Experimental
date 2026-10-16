# Bachata S4 v0.2.5 × PanVK F4.3 — integration stage 1 (2026-10-16)

## Scope

User authorized an **experimental modified Bachata**, reusing the previous BCn-hostfix experience from 2026-10-15. This stage is deliberately **NOT an installable APK**; previous `Bachata-S4-0.2.5-BCn-hostfix-EXPERIMENTAL.apk` and its private experimental signing key are NOT available in this conversation workspace.

Inputs, verified:

- Official `bachatas4-0.2.5-release.apk` SHA-256 `1df49463f396df8b6f042230bdc1bb9f948b8e69894c378915920875c40ab0ee`.
- PanVK F4.3 Dual ICD ZIP SHA-256 `2bfd4e74314c1c6d7adfc44eb0a8058ac330c707c6726584335c4d3d8df6351c`.
- `assets/runtime/native-runtime.json` ABI `android-bionic-arm64` contains `libbachata_native_runtime.so` SHA-256 `147fd32524cbf21c8946c6e93bd6e3d50ed325251aa4acae5a284f456ce6a9f4`, matching APK payload.

## Material work

Produced local `bachata_f43_stage.py`: fails closed on unexpected ABI, original native checksum mismatch, missing `classes.dex` / manifest, unexpected F4.3 ID/ELF arch, erroneous driver hash, double insertion, overwrite. Allows *only* explicit `--stage-unsigned` creation.

Added F4.3 untouched ZIP as `assets/drivers/PanVK-G720-UMA-F4.3-ICD-DUAL-Android-ARM64.zip` and `.sha256` sidecar in a staging APK; verified CRC and original native SO + native runtime manifest unchanged. F4.3 ZIP includes ELF + meta.json and all expected ICD function names and F4.3 fingerprint.

Actual local staging APK SHA-256 `ce6f2b15e17bdff0f7738de85572a15f9dc1caf1dd276913993d9036775d22ec` — **not delivered as runnable artifact, invalidated Android v2/v3 signature**. Integration-kit ZIP includes tool, driver, manifest check, five unit tests (all PASS), logs, staged-report and checksums. Integration-kit ZIP SHA-256 `e53eef39032b400791ed298be432974aff4df1c7e364d44c7acb666f3be4806e`.

## Pending before production of experimental APK

1. Inspect actual prior **BCn-hostfix experimental APK** and the prior build provenance; this previous file was not in current runtime. The APK does not contain the prior private signing key.
2. Preserve host package + explicit approved signer identity checks. A new APK signature needs matching controlled host-identity policy; do not bypass all identity checks. Any changed native ELF must also update `assets/runtime/native-runtime.json` digest.
3. Verify how the app chooses `runtimeHost` (`LINUX_GLIBC` vs `ANDROID_BIONIC`) and make Bionic selection explicit/testable for the experimental integration. Simply bundling F4.3 does not load it or prove registration in UI.
4. Isolate developer APK installation from the official app; if same package is used, it cannot install as an update signed by a different key and user data must be backed up before removing official.
5. Only claim runtime success after in-session native loader `direct-icd loaded ... sha256 ... interface ...` and PanVK_F43 markers.

## Preservation

PanVK stable F3 commit `3cacc2f0bcbb` unchanged. F4.3 source and official APK installation unchanged; no device test, root operation or forced crash.

## Gate

Request the missing `Bachata-S4-0.2.5-BCn-hostfix-EXPERIMENTAL.apk` from the earlier chat before applying native runtime identity modifications or claiming a signed installable APK.