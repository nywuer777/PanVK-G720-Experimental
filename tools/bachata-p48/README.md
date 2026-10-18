# P48 — F43DEV private GLIBC source recovery and ELF forensics

**Source-only / read-only stage. No private ELF, APK, certificate, signing key, game data or recovered proprietary source is committed here.**

## Findings and immutable controls

- P46 GitHub Actions run [#39081367066](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39081367066): source-only success. Outlast is **not** fixed in private runtime.
- P47 run [#39083458367](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39083458367): recovery *gate* passed, not recovery of a private tree.
- Original private source indication: `JICA98/Bachata-S4-Dev@433c7f30a66c205dff5c3261431e550957f5d447`. GitHub API for repository/commit returned HTTP 404 with available access at P48 audit. This does not prove deletion; private or inaccessible remains possible.
- Public maintained core is `zenithblue-oss/shadps4-arm64`; P31 is pinned at `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`, **not** the same as P42 original private GLIBC executable.
- P42 private ELF known SHA-256 `5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002`, private .text SHA-256 `f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157`. Historical ELF size 75,323,616 bytes. The ELF was **not read or re-hashed in P48 CI**.
- P45 sources target the **public** core paths `src/video_core/texture_cache/image_view.cpp`, `src/video_core/texture_cache/image.cpp` and `src/video_core/renderer_vulkan/p27_vk_decoded_upload.cpp`; they require explicit porting into the actual private renderer when available. P45 host identity is not established by those changes.

## Material P48 implementation

1. `private_elf_probe.py`: bounded ELF64 little-endian AArch64 parser; enforces GLIBC interpreter and `libc.so.6`, rejects Android Bionic dependencies, calculates full-ELF and .text SHA-256, and identifies incidental protocol/guard string presence (informational ONLY). For `--mode baseline`, accepts only the **exact** reference P42 ELF and .text digests. For `--mode candidate`, reports ABI eligibility but **never** asserts private host equivalence or Outlast fixed. No bytes from the ELF are published. Synthetic fixtures have no real F43DEV identity.
2. `source_role_locator.py`: safe, size-bounded and symlink-avoiding scan of an authorized locally recovered source tree, producing only matching source paths, SHA hashes and signal identifiers for identity, V2 HELLO, BCn view and upload/fence candidates. A match is **not** proof the code compiles or works. Missing roles remain explicit.
3. P48 GitHub Actions: synthetic tests for both scanners, expected fail-closed when real private source/ELF is missing, plus P47/P46 regression gates. Only a machine-readable blocked status may be uploaded.

## Run locally if source / P42 archive become accessible

These commands must be run **locally against authorized private files**. Never upload private files to GitHub Actions:

```bash
python3 tools/bachata-p48/private_elf_probe.py \
  --elf /secure/P42/host/shadps4-arm64-fex \
  --mode baseline \
  --report /secure/report-p48-p42-elf.json

python3 tools/bachata-p48/source_role_locator.py \
  --source-root /secure/recovered-f43dev-src \
  --report /secure/report-p48-source-locations.json

python3 tools/bachata-p47/source_recovery_gate.py \
  --source-root /secure/recovered-f43dev-src \
  --manifest /secure/p47-private-attestation.json \
  --report /secure/report-p47-private-inventory.json
```

## Acceptance rules: no premature APK

- **Current hard blocker:** original private F43DEV C++ source and reproducible build recipe matching the functional P42 identity chain have not been recovered. The currently accessible P42 library package bytes could not be materialized in this session; no claim of a P48 raw ELF comparison.
- Original source recovered or private-source reconstruction is not accepted simply because GitHub Actions is green or SHA values are written in a manifest.
- Before a private rebuild: provenance of the actual source, matching build scripts and dependencies, host identity guards and `BACHATA/1 HELLO version=2 contract=` handling must be verified, then the private BCn upload/fence/view path modified and compiled for ARM64 GLIBC.
- Promotion requires static ELF ABI evidence; final signer and identity checks (the P42 post-signing composite gate), 397 runtime entries, Android startup, actual V2 host handshake, plus Outlast test logs/screenshots on hardware.
- Never remove the old BCn safety assertion just to bypass the crash. The exact baseline signed P42 APK, P23 identity correction and PanVK Fase 3 remain protected.
- If exact original private source cannot be obtained, a *new* reconstructed core must be treated as a distinct implementation with a fully audited integration boundary, **not** represented as matching the P42 private binary.

**P48 limitations:** scanners do not recover code by decompilation and do not certify executable equivalence; tests use synthetic data only. Outcomes `P48_PRIVATE_SOURCE_RECOVERED=NO`, `P48_PRIVATE_ELF_REBUILT=NO`, `P48_APK_BUILT=NO`, `P48_OUTLAST_FIXED=NO`.
