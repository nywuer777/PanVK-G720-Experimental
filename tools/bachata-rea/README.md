# Bachata Mali — REA 6.6.0 development integration

This is an **opt-in analysis tool**, not code embedded in the Android APK or the
GLIBC/FEX emulator. The app remains usable without Node.js, MCP, JADX or Ghidra.

## Provenance of the supplied archive

User-supplied `rea-rea-agents-6.6.0.zip` (analysed read-only, never committed):
- SHA-256: `17ee3de75a1ab7963ac5948495324cb4b10ad7fca7c15b859b9d5d5ab597e77d`
- `package.json` identifies `rea-agents` version `6.6.0`.
- Top-level `LICENSE` is MIT, copyright 2026 morluto.
- 4,705 ZIP members; approximately 56.4 MB uncompressed.
- REA documentation names official upstream [morluto/rea](https://github.com/morluto/rea).
- Third-party providers and libraries have **their own** license and runtime requirements.

`rea_intake.py` checks the provided archive's original digest, member paths,
duplicate entries, symlinks, encrypted members, ZIP CRC, manifest, version and
license **without extracting or executing it**:

```bash
python3 tools/bachata-rea/rea_intake.py /path/to/rea-rea-agents-6.6.0.zip \
  --check-node --report /private/reports/rea-intake.json
```

Readiness is separate from archive integrity. The REA CLI requires Node.js
**22.19+**, **24.11+**, or **26+**. Only install an authorized REA release and its
providers in a controlled development environment after reviewing origin,
dependencies, and permissions. `rea setup` changes agent configurations: do
not run it automatically in CI.

## Useful research tasks

1. Investigate the **Android host** JNI `NativeRuntimeBridge.run`, the two
   String arrays, launcher paths and trusted SAF grants using the documented
   Android analysis MCP provider. Requires Java 17+ / full JDK and the separate
   compatible **headless JADX MCP JAR 0.7.1**. Static decompilation is
   **not** proof that a runtime command executes or passes Android permissions.
2. Analyze the **AArch64 GLIBC P42/P53 guests** with Ghidra or another
   authorized REA provider. Correlate imports, control flow and call sites of
   `eboot.bin`, `--override-root`, `--bachata-saf-socket` and
   `BACHATA/1 HELLO version=2 contract=`. Preserve actual source/ELF hashes.
3. Identify whether the **game content** was physically staged under the
   app-private direct-runtime root, or was available only through
   Android SAF/BSF1. Do not treat a fixed relative-path check as proof the
   broker is implemented.
4. Perform **P53 vs P42 diff** and independently investigate Vulkan BC3 sRGB
   mip/layer upload and view creation. Never infer runtime success from strings,
   decompiled pseudocode or a compiled source tree.

Example local *after* REA installation and provider setup:

```bash
rea providers --json
rea doctor --provider ghidra --json
rea analyze /ABSOLUTE/LOCAL/PATH/TO/AUTHORIZED_ARM64_ELF --provider ghidra --json \
  > /PRIVATE/LOCAL/PATH/rea-elf-evidence.json
```

This example only analyzes a file explicitly supplied locally; it does not
download the private P42 APK or interact with the user's device. Only share
redacted, minimum-necessary evidence with the project.

## Security and release boundaries

- **No** private P42 signed APK, nested ELF, signing key, actual nonce/token,
  device identifiers, game content or raw crash logs in this public repo or CI.
- No `npm install` or `rea setup` during public CI; preflight only tests our
  wrapper and policy.
- Never disable Android host identity, signature or same-UID broker checks.
- Keep P42 working and PanVK Phase 3 unchanged. Do not assert P53 works in
  Outlast until a full authenticated on-device session proves it.
- REA license applies to **REA**, not to a private Bachata binary under analysis.
  Decompilation does not create an unrestricted distribution right.

## Open source versus publication control

The project may use a publicly visible source repository and grant merge and
official-release authority only to maintainers. The **official project name,
logo, signing keys and verified release channels** can be controlled separately.

However, **MIT permits redistribution** of REA itself. The GPL-2.0-or-later
shadPS4 code also gives eligible recipients redistribution rights under the GPL.
Do not append a no-redistribution clause to these components or describe a
closed-redistribution license as "open source". If certain original components
are source-available with separate restrictions, split them clearly and check
GPL license compatibility before any combined distribution.

The P53 source branch is an experimental parent, not a released Android app.
