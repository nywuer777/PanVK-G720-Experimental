# P51 — P42 identity compatibility decision vs public P49 GLIBC

## Result

**P51 reproducible verdict: `REJECT_PUBLIC_P49_AS_DROP_IN_P42_CORE`.**

This is a **successful negative release gate**, not failure of the P49 AArch64/GLIBC compilation or Vulkan improvements.

- Tested exact real public P49 ELF (CI run 39089770038): SHA-256 `272024fe15b7785be819f7fe3eb403c0543b070da2a6525d10580e24876dadaa`.
- Inspected real P49 `.text`: SHA-256 `bfa4914b56a6246219a13666045b0bf89e778a24f295373a6fbc02a9d44b66dd`.
- Previously independently audited private P42 `.text`: SHA-256 `f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157` (NOT re-read from P42 here).
- P42 private runtime prior ELF SHA-256 reference: `5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002`.
- Public P49 has Host V2 HELLO and managed same-UID rejection indicators. It does **not** contain the known original private `host identity check failed` literal or `GPU BCn fallback admitted` literal. The known release gate in `tools/bachata-hostid/host_identity_release_gate.py` on the separate P46 gate branch requires the original identity/obfuscated signer chain for both Android Bionic and private GLIBC.
- P49 is **not** a drop-in replacement and does not prove Bionic linker / private signer / runtime contents identity. A distinct code hash does not by itself explain an on-device failure, but releasing it into the signed private APK without matching authorized host integration would bypass necessary evidence.

## Important distinction

The original known-good signed experimental F43DEV V2 APK reference is `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. This is **not** the same object as the nested P42 guest ELF or the P49 public ELF.

The P42 APK bytes and private ELF original are currently **not authorized as raw-byte inputs** in this Project's execution container (the existing Library file could not be materialized). P51 does **not** claim to have independently re-hashed the P42 core, certificate or all 397 runtime entries. Prior audited reference values are clearly distinguished from data inspected in this execution.

## Implemented

`tools/bachata-p51/p42_p49_identity_parity.py` is a read-only fail-closed ELF64 little-endian AArch64 analyzer with bounded section/program headers, exact SHA-256 and `.text` pinning, PT_INTERP verification and precise original/public marker comparison. Optional `--private-p42-elf` uses original trusted private bytes locally when available, verifies exact original full ELF and `.text` hashes, and never promotes the public build to an APK.

`tools/bachata-p51/test_identity_parity.py` contains 19 regression tests for hash substitutions, missing peer/identity markers, mismatched baseline references, bounds and symlinks.

`.github/workflows/bachata-f43dev-p51-p42-identity-parity.yml` downloads the actual successful P49 ELF from the approved immutable build run, executes the real audit and requires **rejection** of the drop-in replacement. A green CI result means the safety guard works; it never means F43DEV acceptance or Outlast repair.

## Correct next engineering route

1. Obtain the exact maintainer-authorized P42 private GLIBC source and Android host project, or a supported in-app same-UID diagnostics/probe interface. The complete private source was not recovered by P47/P48.
2. Port the P45 BCn upload/fence/image-view fixes **into the authorized private runtime**, or implement a genuinely interoperable host-approved replacement with complete authentication and SAF.
3. Rebuild and package with the **original signature/identity policies intact**, reconcile the Bionic signer and all 11 private GLIBC references, then validate all 397 manifest files. Never spoof the signature or disable the checks.
4. Only after an authorized signed APK and in-device host/SAF proof test Outlast BC3 sRGB 1024x1024 mip=11 graphics and measure FPS.

**P42 working APK, PanVK Fase 3 and associated driver files are unchanged. No APK is distributed by P51.**
