# P49 — Host V2 + BCn P45 integrated public GLIBC reconstruction candidate

**Experimental source integration only; NOT the original private F43DEV GLIBC build. Not an Android APK.**

## Baselines

- Functional P42 private guest ELF reference SHA-256:
  `5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002`.
- Original private source `JICA98/Bachata-S4-Dev@433c7f30a66c205dff5c3261431e550957f5d447` still unavailable with current access. P48 could not recover or re-hash its ELF.
- Public reconstruction source is **exactly** `zenithblue-oss/shadps4-arm64@be6bc2e9c60799e071dd2fafa6216e8d80ec619c`. It has never been proven equivalent to the private F43DEV P42 runtime.
- The P49 branch derives from P45 to preserve the P36–P45 source kit and the separately developed R2A–R2A6P5 host chain. P47/P48 investigative branches and stable P42 are not modified.

## Actual implementation

`tools/bachata-p49/integrate_public_hostv2_p45.py`:

1. Requires a clean, pinned public upstream checkout and SHA-256-verified P36–P45 kits.
2. Runs the existing R2A, R2A2, R2A4, R2A5, R2A6/P0, /P1, /P2, and /P5 host V2 / read-only SAF laboratory source ports, including peer/UID gate, CLI contract, and strict lowercase 32-hex HELLO.
3. Generates the P45 renderer port *separately* against a second clean checkout, respecting the original `P45_DIRTY_TRACKED_TREE` invariant.
4. Performs **one** explicit semantic rebase for the overlapping P39 shader-write access hunk in `vk_rasterizer.cpp`. It does *not* remove the P39 active `force_general` branch, and it requires R2A's existing `has_storage` tracking, `eShaderWrite` access, and feedback layout protection to be present exactly once.
5. Applies all remaining P45 hunks with strict `git apply --check --whitespace=error`. Unknown overlaps stop the run. There is no `--3way`, fuzzy application, or suppressed assert.
6. Checks host V2 and P45 source markers together. Records all rebase evidence and reports `apk_built=false`, `outlast_fixed_on_device=false`, `host_original_p42_binary_verified=false`.

## Evidence

- P49 source preflight passed: [GitHub Actions #39085558115](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39085558115).
- Independent checks: 10 P49 source tests, 21 P45 port tests, 25 strict V2 HELLO checks, 138 P44 BCn view checks. P36–P45 source kit hashes passed.
- Additional reviewed conflict rebase negative tests passed: [#39085609383](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39085609383). These tests inspect synthetic fixtures and do not prove runtime behavior.
- ARM64/GLIBC build workflow is `.github/workflows/bachata-f43dev-p49-glibc-build.yml`, independent of the source preflight. The build result must be evaluated on its own; no successful binary is assumed from source integration.

## No-go release criteria

- A public-source replacement is **not** the authenticated F43DEV private runtime, regardless of whether it contains the proper V2 HELLO string or compiled peer-path checks.
- APK promotion requires original trusted host/guest identity chain, verified APK signature, **1 Bionic + 11 private GLIBC signer references**, **397** runtime manifest entries, exact host protocol / SAF handshake, and real-device startup.
- Gameplay requires Outlast's BC3 sRGB 1024×1024 11-mipmap upload/fence/view proof in the actual running executable, not the isolated P44/P45 tests. Minecraft shader aliasing remains separate.
- P42 last functioning signed release and PanVK Fase 3 remain unchanged.
- No private signing material, proprietary source, private APK/ELF or game data is included here. A public candidate ELF, if built, remains an **uninstallable research artifact** and is not approved as a replacement.

## Status

**P49 public source integration: tested and passing.**
**P49 full GLIBC executable, private runtime equivalence and hardware correctness: determined exclusively from separate downstream evidence, not claimed here.**
