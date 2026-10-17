# Bachata F43DEV V2 — permanent host identity release gate

The **P23 host identity fix is an invariant of all future APK candidates**, not a one-off replacement of the private F43DEV core. After packaging and signing, future APK workflows MUST run the composite action:

```yaml
- uses: actions/checkout@v4
- name: Block host-identity regressions before any APK artifact upload
  uses: ./.github/actions/bachata-host-identity-gate
  with:
    apk-path: path/to/Bachata-F43DEV-signed.apk
```

The action fails closed unless: Android APK v2 cryptographic signature and signer digest are valid; exactly **one Bionic** and **11 private GLIBC** obfuscated signer references bind to the **actual APK signer**; both guards and the F43DEV protocol marker are present; the runtime V2 protocol and all **397** runtime entries agree with their SHA-256 and sizes; guest ELF hashes agree with internal metadata. No identity guard, assertion or caller check is disabled.

If the signing certificate changes, apply a checked rebind of **both** ELF identities, update the guest and native manifests, re-sign, and run this gate against the **final signed APK**. A public shadPS4/GLIBC binary that omits the private host protocol must be rejected even if it compiled successfully. Retain the last working signed P23 separately.

Validation of the release policy (2026-10-17): signed P23 **PASS**, signed P42 private-host experimental build **PASS**, public-core P31 compatibility smoke build **REJECT** (`PRIVATE_GLIBC_HOST_IDENTITY_GUARD_MISSING`). Twelve local regression tests passed. This static gate **does not validate gameplay**, SAF session or actual device launch. **P39 gameplay patches are not present in P42** and Minecraft/Outlast remain unverified.

Only source checks are stored in this public repository. **Do not add private signing keys, certificates with private material, game data, SAF tokens, local command-line logs or private ELF binaries.**

The gate MUST be explicitly invoked by every future APK-packaging job; merely having the source CI workflow pass does not gate unrelated workflows. 
