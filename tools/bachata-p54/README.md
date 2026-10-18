# P54 / phase 1 — authenticated BSF1 read-only eboot descriptor (LAB ONLY)

## Exact objective

P53 Android diagnostic `bachata-diagnostic-BS4-20261018-13BFA848.zip`
returned:

- Android content validator: `validated game root and eboot.bin`.
- Linux FEX backend: `BACHATA_F43DEV_R2A2_HOST_GATE_OK`.
- Physical path resolver: `BACHATA_P53_EBOOT_ROOT_UNAVAILABLE`.
- Runtime still states `BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED`.
- Runtime error `CONTENT_INVALID`, within approximately 15 ms of process start.

**This is a storage handoff failure, NOT evidence of GPU BCn or PanVK
incompatibility.** Original P42 (working reference), experimental P53 clone,
and PanVK Fase 3 must remain unchanged.

## Material implementation

- `tools/bachata-p54/p54_bsf1_eboot.h`: after the Host V2
  same-UID HELLO, when Android launches `-g eboot.bin` and the
  physical `--override-root` lacks it, asks the already-available BSF1
  client for exactly `OpenRead("eboot.bin")`.
- Checks that the host-supplied root is an absolute, lexically normalized,
  non-symlink directory and accepts **only** a same-UID broker's verified,
  read-only regular-file SCM_RIGHTS FD (the R2A5 client itself checks the
  peer credentials, token and descriptor). No guessed CUSA paths or directory
  enumeration.
- On success, holds the file descriptor until `Emulator::Run()` returns and
  supplies `/proc/self/fd/<N>` to the early `Core::Loader::Elf::Open` and
  `std::filesystem::exists` checks. Does not copy game content, alter
  permissions, open private Android files or leak session secrets.
- On failure, the old fail-closed `CONTENT_INVALID` path remains. The only
  added diagnostics are a single fixed marker:
  `BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY`,
  `..._ROOT_INVALID`, `..._BROKER_UNAVAILABLE`,
  `..._BROKER_DENIED`, `..._BROKER_PROTOCOL_MISMATCH`,
  or `..._FD_INVALID`. No path, user data, token or socket is logged.
- `tools/bachata-p54/patch_p54.py` applies to the exact source pin
  `zenithblue-oss/shadps4-arm64@be6bc2e9c60799e071dd2fafa6216e8d80ec619c`
  **after** the reviewed P49 Host V2+BCn patch chain and P53 path
  fix. Rejects missing prerequisite trust gates and altered source anchors.
- `.github/workflows/bachata-f43dev-p54-bsf1-preflight.yml` performs actual
  same-UID AF_UNIX/BSF1 `SCM_RIGHTS` mock tests with the existing R2A5
  client, plus source-regression tests.
- `.github/workflows/bachata-f43dev-p54-bsf1-arm64.yml` rebuilds the
  Linux ARM64/GLIBC public core and proves the P54 source/markers are in the
  linked ELF. No APK/Android signature is manufactured by CI.

## What P54 stage 1 explicitly does NOT prove or fix

1. **Actual Android SAF broker interoperability** has not been tested.
   The reconstructed wire framing is based on earlier static analysis and
   validated only with test servers. If the private host expects another
   framing or a different session-relative path, P54 reports the appropriate
   failure code; it does not alter authentication or brute-force paths.
2. A successful initial `eboot.bin` FD is **not the same as a mounted PS4
   /app0 tree**. The public emulator still needs the real game root for
   `sce_sys/param.sfo`, `Emulator::Run()`, textures, DLC, directories,
   saves and all PS4 guest filesystem syscalls. P54 stage 1 does not
   activate the optional R2A6/P1 SAF VFS or guess a broker root.
3. `/proc/self/fd/N` is a restricted read-only entry path for this
   early proof, not a full FEX/PS4 filesystem mapping. Some launch
   paths may still reject it, and an actual game boot is **not promised**.
4. A successful Linux arm64 CI build and a signed experimental clone
   do not prove original private P42 signer parity. Never overwrite,
   uninstall or re-sign the working P42.
5. GPU BCn fixes from P45/P49 are preserved as source, but Outlast first
   frame, texture correctness and FPS remain **NOT VERIFIED**.

## Next experiment

Test in a separately identified lab app and submit its privacy-redacted
diagnostic. If the marker indicates `..._AUTHENTICATED_FD_READY`, the
broker is answering `OpenRead("eboot.bin")` through the user-approved host
and the next stage can focus on direct game root + `/app0` mount.
If `..._BROKER_...` appears, correct the *actual* host/broker
contract using authorized Android source/JNI/Bionic evidence rather than
faking an FD or weakening SO_PEERCRED/UID/token restrictions.

**Do not describe this as P54 complete-game SAF integration or
Outlast fixed.**
