# P61 — Outlast PSF TITLE_ID via authenticated SAF broker

**Trigger:** `BS4-20261018-FF85A04C` on P60 laboratory clone. P59 eboot and P60 libc private stages both succeeded. The FEX game entered the `sceAppContentInitialize` HLE handler and exited with code 133 after `UNREACHABLE_MSG("Failed to get TITLE_ID")`. Upstream pinned to `be6bc2e9c60799e071dd2fafa6216e8d80ec619c` loads `/app0/sce_sys/param.sfo` into singleton `PSF` in `src/emulator.cpp` before game execution. P60 deliberately does not stage that file, so absent PSF metadata is the **leading hypothesis**. No guesswork about the missing title string is permitted.

## Scope

- Only `sce_sys/param.sfo` is authorized for `BSF1::Client::Stat` then `OpenRead`.
- No synthetic PSF, synthetic `TITLE_ID`, bypass of `sceAppContentInitialize`, or global `/app0` mount.
- At most 1 MiB. Validate PSF magic, version, table boundaries, every entry length/format and null-terminated strings, plus a unique `TITLE_ID` matching the trusted root basename `CUSAxxxxx`, **before** the file reaches the upstream parser.
- Private copy only (`sce_sys/param.sfo`, `0600`, `O_EXCL`, `O_NOFOLLOW`), under a verified owner-only root and directory. Never overwrite existing data. Delete only files created by the stage, on orderly unwind; abrupt process death may leave an orphan.
- A broker rejection is not interpreted as file absence. Distinct markers report stat/open failure, malformed PSF, missing ID, ID mismatch and successful stage.
- On stage failure, notify the Android runtime using `CONTENT_METADATA_UNAVAILABLE` and stop gracefully instead of proceeding to the known fatal `sceAppContentInitialize` assertion.
- The P42 functional clone, Fase 3 PanVK driver, game assets and private credentials are untouched. No copyrighted game files are distributed.

## Verification gates

1. Python anchor tests and C++ synthetic fixtures with GCC/Clang ASAN+UBSAN, including negative tests for malformed data, mismatched ID, symlink, wrong permissions, preexisting destination and cleanup.
2. BSF1 real client compiled with P56–P58 patch series against an isolated mock socket: `Stat` and `OpenRead` exact path, denial = no open.
3. Rebuild upstream pinned public ARM64/GLIBC with P53–P61 in patch order. CI pass alone is not APK compatibility.
4. LAB CLONE APK signing/integrity audit and Android test; export a fresh ZIP. Expected marker: `BACHATA_P61_PSF_SAF_PRIVATE_STAGE_READY` and upstream `Loader: Game id` log. Frame of game, other missing `/app0` assets, and HLE `ENOSYS` compatibility still unproven.

Do not install over P42, publish user game bytes, or infer a game FPS result from swapchain `present_done` traces.
