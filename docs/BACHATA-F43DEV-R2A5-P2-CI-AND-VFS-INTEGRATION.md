# Bachata F43DEV R2A.5/P2 — source-pinned BSF1 transport and VFS integration boundary

Date: 2026-10-16. Branch: `exp/bachata-f43dev-r2a5-bsf1-client`. Prior user-validated F43DEV Host Identity V2 APK and PanVK Fase3/F4.3 **untouched**.

## Material work

Source code migrated from locally tested and checksum-sealed R2A.5/P1 kit, **without editing the C++ transport or mock harness**:

- `tools/bachata-r2a5/saf_bsf1_client.h` — SHA-256 `cc30a3dc5f805a2a008ccbe166e0f032a812157b872d03a9239f8e04dff18795`
- `tools/bachata-r2a5/saf_bsf1_client.cpp` — SHA-256 `693520942c8f4bfc4bc3a8726f727a986a144fb3e40721b39a5f10a87f3142cf`
- `tools/bachata-r2a5/test_bsf1_mock.cpp` — SHA-256 `14e17fe203e2952e161f9d0f8814298b28e239b4d2bf38344d5c4b2698bc3485`

`tools/bachata-r2a5/apply_r2a5.py` applies source pin `be6bc2e9c60799e071dd2fafa6216e8d80ec619c` **only after** the R2A Vulkan mixed sampled/storage, R2A2 Android host gate and R2A4 SAF CLI redaction patches. It refuses source drift, CMake drift, missing prerequisites, missing/changed BSF1 source hashes or existing destination files.

It copies BSF1 client header/implementation into `src/platform/bachata/`, links the implementation into the `shadps4` executable's `ENABLE_BACHATA_RUNTIME` `target_sources` in upstream `CMakeLists.txt`, and calls `Client::ValidateConfig` at managed startup (thus linking the client object). It **never** makes an SAF network request at startup, never bypasses the Android identity gate, and keeps the guest VFS mount **disabled**. The runtime marker is explicit: `BACHATA_F43DEV_R2A5_BSF1_LINKED_VFS_DISABLED`.

### Test gates

[GitHub Actions #38976282195](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38976282195) consists of:
1. Original source SHA guard, 33 native synthetic broker checks and AddressSanitizer/UndefinedBehaviorSanitizer, guarded source patch and source diff artifact.
2. **Standalone** Linux AArch64 GLIBC client compile and dynamic link (not Android Bionic or real broker test).
3. FEX/shadPS4 **full** Linux ARM64/GLIBC candidate compile, ELF/loader/GLIBC checks, marker and integrity evidence, candidate artifact **not an APK**.

At creation time run active; never infer success from a started build.

## Why the read-only VFS mount is deliberately not activated

Audited public source `zenithblue-oss/shadps4-arm64`:
- `src/core/file_sys/fs.h` tracks open regular handles through `Common::FS::IOFile f` and directories through `std::shared_ptr<Core::Directories::BaseDirectory>`.
- `src/common/io_file.h` offers `IOFile::Open(filesystem::path,...)`, but no safe `AdoptReadOnlyFd(int)`/FILE* factory for an already received `SCM_RIGHTS` descriptor.
- `src/core/file_sys/fs.cpp` resolves guest mounts to **local filesystem paths** via `MntPoints::GetHostPath`.
- `src/core/libraries/kernel/file_system.cpp` `open` resolves `GetHostPath`, `std::filesystem::exists/is_directory`, calls `IOFile::Open`; `getdents` and `fstat` flow through directory implementations.
- `src/core/file_sys/directories/normal_directory.h` is designed for host directories; a broker-provided `List` result needs its own proper `BaseDirectory` implementation.

A mock BSF1 server cannot prove correct semantics for the real SAF app document provider. Pretending the guest paths exist on Linux disk, creating temporary copies, bypassing mount APIs or returning fabricated `Stat/List` data would make game access misleading and could break save behavior.

### P2B functional VFS work — acceptance criteria

1. Obtain **non-secret real** Android broker responses with client handshake after Bionic signer/UID verification. Confirm absolute vs relative broker paths, optional root listings, unknown 64-bit stat fields, error/status mapping, payload/FD semantics.
2. Implement read-only `Common::FS::IOFile::AdoptReadOnlyFd` with explicit fd ownership and `fdopen("rb")`, preserving seek, close and fstat semantics. Ensure any `FILE*`/fd wrapper never writes.
3. Add SAF-aware `Core::FileSys` mount kind with explicitly scoped guest path prefix, separate from `MntPoints::GetHostPath` local fallback; only route `Stat`, `OpenRead`, `List` through broker. Return read-only errors for all create/write/truncate/unlink/rename modes.
4. Implement `Core::Directories::BaseDirectory` backed by BSF1 `List`; only assign stat field semantics verified on device. Enforce traversal, symlink and escaping constraints at every layer.
5. Tests: mock success/negative on guest paths, real device read-only eboot and directory listing, no token logging, full SAF handshake and simulated broker unavailable, no regression in ordinary local game mounts.
6. Only **after** a real Android handshake and verified host identity may an independently signed, side-by-side APK be considered. No mutation of functional F43DEV V2.

## Unchanged regression status

- Outlast CUSA00325: BCn decoded-image view assert still not fixed in the candidate.
- Minecraft CUSA00265: aliased guarded-mip read/write/atomic case still not validated, R2A mixed-image same-instance fix is narrower.
- F43DEV V2 signed stable SHA-256: `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`.
- PanVK Fase3 frozen commit `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb`.
- Bionic PanVK F4.3 remains separate from in-game ARM64/GLIBC FEX stack.
