# P62 — PSF text-slot compatibility + fail-closed reason codes

## Device evidence (P61.1 lab)

Hardware diagnostic `BS4-20261018-6F9C455D` (2026-10-18) on `com.bachatas4.android.f43lab`, Outlast `CUSA00325`: the protected socket passed (`BACHATA_F43DEV_R2A2_HOST_GATE_OK`); exact broker `eboot.bin` and `sce_module/libc.prx` stages both passed; `BACHATA_P61_PSF_INVALID` was emitted before game initialization, with app-facing `CONTENT_METADATA_UNAVAILABLE`. The diagnostic contains **no raw `sce_sys/param.sfo` bytes**, so the precise rejected field cannot yet be established.

## Source audit

Pinned upstream `zenithblue-oss/shadps4-arm64` commit `be6bc2e9c60799e071dd2fafa6216e8d80ec619c` uses a PSF parser that extracts a text field as a C string ending at the **first NUL**; it does not require the declared `param_len` to end exactly at the first NUL. P61 treated the entire declared `TITLE_ID` value (minus only its last NUL) as the identifier. The P62 parser now accepts a well-bounded, correctly NUL-terminated value with extra slot padding while still requiring exactly `CUSAxxxxx` matching the private root.

The byte order is intentional and maintained: the PSF magic is BE, offsets are LE, and upstream `PSFRawEntry::param_fmt` uses **BE** (0x0204 for text).

## New failure diagnostics

`BACHATA_P62_PSF_BAD_MAGIC`, `_UNSUPPORTED_VERSION`, `_LAYOUT`, `_ENTRY_BOUNDS`, `_KEY`, `_FORMAT`, `_TEXT`, `_DUPLICATE_TITLE_ID`, and `_TITLE_ID_FORMAT`. The existing `BACHATA_P61_PSF_TITLE_ID_MISMATCH`, `_TITLE_ID_MISSING`, `_BROKER_*` and `_SAF_PRIVATE_STAGE_READY` markers remain. Do not log PSF strings or private SAF tokens.

## Verification and security

- P62 C++ fixtures model upstream PSF header and entries with a padded text slot and one integer field, including positive staging + negative malformed inputs, duplicate and mismatched IDs.
- GCC, Clang, ASan, UBSan, and authenticated P58 BSF1 broker mock CI: [#39166067347](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39166067347) **PASS**.
- Full P53–P62 public ARM64/GLIBC build: [#39166151135](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39166151135) **started; do not claim finished until verified**.
- Source stays bounded at 1 MiB; rejects malformed layouts, duplicate TITLE_ID, symlink directories, mismatched app UID/socket trust. No fake PSF, no title override, no VFS bypass.
- P42 working clone and PanVK Fase 3 untouched. Device launch, successful P62 PSF stage, first game frame and FPS **not yet verified**.
