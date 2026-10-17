# Bachata F43DEV — R2A.6/P1: SAF read-only kernel integration

**Date:** 2026-10-16/17 · **Branch:** `exp/bachata-f43dev-r2a6p1-saf-kernel` · [CI #38996567581](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38996567581).

## Scope and provenance

Exact public source `zenithblue-oss/shadps4-arm64` at `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`, with chained R2A (mixed-image layout), R2A2 (host identity), R2A4 (SAF CLI), R2A5 (BSF1 transport), R2A6/P0 (read-only guest-path adapter). This is not the private, original Bachata F43DEV source tree; differences remain. Functional **F43DEV Host Identity V2 signed APK** SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded` unchanged.

## Material implementation

- `tools/bachata-r2a6p1/saf_guest_mount.h/.cpp`: global process-scoped lab mount `/app0`; immutable configuration after initialization. Fails closed if a broker token/socket/root is invalid or activation repeated. Disabled by default.
- `tools/bachata-r2a6p1/saf_directory.h/.cpp`: read-only `BaseDirectory` subclass from actual BSF1 `List` entries. Builds aligned 512-byte Orbis dirent snapshots (fileno, reclen, type, name), no host path `directory_iterator`; rejects malformed names or overflow.
- `tools/bachata-r2a6p1/apply_r2a6p1.py`: source-pinned patch applies CMake, main, `Core::FileSys::MntPoints::GetHostPath`, `kernel/file_system.cpp` and SAF CLI redaction. No APK patch/re-sign.
- Guest `open` uses `BSF1::Stat` to determine directory vs regular, directory snapshot uses `BSF1::List`, regular opens via read-only `BSF1::OpenRead` + `SCM_RIGHTS` duplicated FD into `Common::FS::IOFile::AdoptReadOnlyFd`. No guest modification permitted.
- Guest `stat` uses BSF1 to determine type and a real read-only FD's `fstat` for length/timestamps; directory metadata only uses verified type, rather than guessing ambiguous upstream u64 fields.
- `fstat` uses `::fstat(::fileno(file->f.file))` for SAF-backed regular handles and read-only mode; file read and lseek remain standard `IOFile` paths.
- Guest `getdents` routes through `SafDirectory::getdents` (existing guest `BaseDirectory` dispatch). No fake directory entries if broker unavailable.
- Guest writes blocked: `open` write/create/truncate/append/exclusive flags; SAF `write`, `writev`, `pwritev`, `ftruncate`; scoped guest path `mkdir`, `rmdir`, `rename`, `unlink`. Extra defense: `MntPoints::GetHostPath` returns an empty path rather than silently falling back to host paths for `/app0` when the mount is active.
- `--bachata-saf-vfs-lab` + `--bachata-saf-vfs-root` (explicit broker-relative root) are mandatory for opt-in; root value is masked by the patched R2A4 argv redactor; defaults leave VFS completely disabled.
- Mount activation is placed **after** the R2A2 same-UID verified host control socket handshake. No token is sent to GitHub and no original game content included.

## CI gates (as of initial source preflight)

[Workflow #38996567581](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38996567581):
- `source-and-broker-tests` **SUCCESS**: 16/16 opt-in/invalid-root tests, ASan/UBSan pass, previous 33 broker and 35 guest-path tests, unique-anchor patches and `git diff --check`.
- `arm64-glibc-adapter` **SUCCESS**: cross-compiled Linux AArch64/GLIBC BSF1+VFS guest mount as a standalone shared test library. Not Bionic.
- `full-glibc-fex-core` underway at documentation time. The full shadPS4 ELF must build before it can be described as compiled. **No APK is released.**

## Remaining blockers (release gate)

1. The real Android broker has **not** been exercised. Static reconstruction of `BSF1` frames and mock responses is not Android interoperability or token authentication. Must run sandboxed tests with non-secret user-selected test files on target hardware and validate success + error cases.
2. The **actual broker-relative root for an installed PS4 game has not been established**. The new lab `--bachata-saf-vfs-root` requires an explicit, correctly authorized root. Never infer a game root from CUSA or logs.
3. This P1's guest `/app0` routing does not automatically replace the Android host's initial `--game`/eboot file-selection semantics. A device run must confirm how the executable is mounted and that the F43DEV startup contract remains valid.
4. The R2A2 host gate explicitly binds to the existing F43DEV package `com.bachatas4.android.f43dev`; a distinct side-by-side APK would need separate identity/signature verification design. **Do not overwrite the functional APK.**
5. Outlast BCn decoded-image view failure and Minecraft mip/storage overlapping alias remain unresolved independently of SAF.
6. `getdents`, `stat/fstat` and read-only write guards still need game-level and broker-real tests; passing mocked tests / static source compilation does not demonstrate correct PS4 loader behavior.

**Preserved:** functional F43DEV V2, PanVK Fase3 frozen `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb`, PanVK F4.3 Bionic, and all games/settings.

## Next

After full CI confirms compilation, audit and stage **core-only** ELF, then collect one real Android F43DEV SAF handshake trace with redacted tokens and root, followed by read-only `Stat/List/OpenRead` calls. Do not sign or deliver an installable APK until Android Bionic signer, loader contract and broker contents are validated in a separate lab package.
