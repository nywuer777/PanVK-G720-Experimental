# Stage 2 — BCn-hostfix experimental APK + PanVK F4.3 (READ-ONLY SIGNING GATE)

Date 2026-10-16. User supplied actual `Bachata-S4-0.2.5-BCn-hostfix-EXPERIMENTAL.apk` after stage1.

## Signed experimental base

- APK SHA-256: `acfe40bf44d3384c049b6058059f5312e1e47483a114b692ab76d4a6dfc68d64`.
- APK v2 signed with certificate SHA-256: `82ce012ec936573c5b15447f857c0bc3b8c81a9e396dfe61fdbdeee60b5e7404`, CN Experimental Bachata BCn Compatibility.
- Native runtime SHA-256: `5c2fffb9f42f26e50cf26e60b4d0c1a82b5870af4f1ac0190d18c39fdfa11bf7`.
- Binary comparison with official v0.2.5: exactly 63 modified bytes in native ELF; no changes in other original ZIP entries. One of these changes is the BCn fix from earlier experimental work.
- `assets/runtime/native-runtime.json` still contained OFFICIAL native SHA-256 `147fd32524cbf21c8946c6e93bd6e3d50ed325251aa4acae5a284f456ce6a9f4`, which mismatches the changed binary in the user-supplied experimental APK.

## Generated integration (unsigned; NOT an installable APK)

- Base BCn-hostfix unchanged in source files except `assets/runtime/native-runtime.json` corrected to `5c2fffb9...a11bf7`.
- Added F4.3 Bionic Dual ICD driver `assets/drivers/PanVK-G720-UMA-F4.3-ICD-DUAL-Android-ARM64.zip` and `.sha256` sidecar.
- F4.3 ZIP SHA256 `2bfd4e74314c1c6d7adfc44eb0a8058ac330c707c6726584335c4d3d8df6351c`; embedded driver ELF SHA256 `841f52e574dfea3770ccf25a27286ca1f3da52752f68d004b3d837dd78e64155`.
- Staged ZIP/APK 430 entries; 428 existing unchanged except the single native manifest; 2 additions; all ZIP CRCs correct; all STORED entries correctly aligned.
- Staged unsigned APK SHA256 `8ac73820a077f753ef58d5cecf72541b2aba333726f159084c1ae2374cfff848`, bytes 215151693, **not installable**.
- Executed local automated suite: **10/10 PASS**; initial alignment failure caught and corrected before package delivery.
- Reproducible code + F4.3 driver + log and hashes in `Bachata-S4-BCn-hostfix-F43-INTEGRATION-KIT.zip`, SHA256 `6caedb0c01277897a9d27213935ba7e61ff53441a9bb681155566deae2fc2cf3`.

## Hard signing and functional gates

The **private key** matching the earlier experimental certificate is absent from the uploaded APK, and cannot be recovered from its public certificate. A re-pack requires Android v2/v3 re-signing. If a different key signs, the native allowlist will reject that signer unless the trust policy is amended specifically and verified; cannot treat the signing work as completed. Signing a same-package experimental APK with a different certificate also does not permit an update over the official app. Never uninstall or delete app data without backup and consent.

Simply bundling F4.3 in `assets/drivers/` does not establish UI registration nor force `ANDROID_BIONIC`; the earlier observed `libbachata_host_loader.so` still indicates a GLIBC host path likely in use. Validation of runtimeHost, dlsym and PanVK_F43 constructor remains pending.

Stable F3 unchanged. Official original APK unchanged. No hardware validation or crash induced.
