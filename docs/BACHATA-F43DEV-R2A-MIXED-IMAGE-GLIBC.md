# Bachata F43DEV — R2A: sampled/storage Vulkan image accesses

Date: 2026-10-16 | branch `exp/bachata-core-glibc-r2a-mixed-image` | baseline F43DEV Host Identity V2 **unchanged**

## Scope and incident provenance

User reported two GPU core asserts from F43DEV with GLIBC PanVK 26.2.99 on G720 MC7:

- **Outlast CUSA00325:** `image_view.cpp:257` says `GPU BCn decoded image requires a matching sampled BC view`; original private runtime binary `433c7f30...`.
- **Minecraft CUSA00265:** `vk_rasterizer.cpp:1940` says `Restricted core robust-image compatibility blocker`. Shader reads `0x2fd81b400` size `0x200000` and writes overlapping `0x2fd81b400` size `0x280000`.

The matching private JICA98/Bachata-S4-Dev revision is unavailable. Public candidate `zenithblue-oss/shadps4-arm64` commit `be6bc2e9c60799e071dd2fafa6216e8d80ec619c` compiled as R1.1; **it is not a drop-in compatible binary** and its `image_view.cpp` / `vk_rasterizer.cpp` differ materially from the original.

## Material R2A implementation

Within the public source candidate only, patched:

1. `src/video_core/texture_cache/image.h`: add per-binding-batch `has_storage` bit.
2. `src/video_core/renderer_vulkan/vk_rasterizer.cpp`: first-pass mixing of sampled and storage descriptors becomes independent of their iteration order, setting `force_general`; second-pass transitions include `ShaderWrite` if storage is present, while color attachment accesses are included **only** when a render target actually exists. Disable attachment feedback layout when storage access is present.

Changes are applied with `tools/bachata-r2/apply_r2a.py`, failing closed on revision, Git blob or source anchor drift. They do **not** bypass asserções / assert guards, fake driver features, or modify PanVK.

**Narrow claim:** fixes order-dependent `GENERAL` transition / omitted ShaderWrite access mask for the *same backing image instance* in the public candidate. It does **not** yet prove a solution to the real Minecraft issue involving two possibly different image handles with overlapping guest memory and robust mip bounds/atomics. Do not claim real-game fix without additional implementation and validation.

## Tests and CI

- [x] 18 source model/negative tests in `tools/bachata-r2/test_r2a.py` passed on GitHub.
- [x] GitHub pinned-source preflight applied patch to 2 expected upstream files, `git diff --check` passed.
- [x] Source patch published: [GitHub artifact #12069986042](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38953746578/artifacts/12069986042).
- [ ] **ARM64/GLIBC/FEX rebuild ongoing** on [GitHub Actions #38953746578](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38953746578). The job needs Debian Trixie toolchain, cross-build and ELF evidence; report status only after confirmation.
- [ ] Outlast BCn real fix: absent from R2A; original private decoder code doesn't match the public candidate. Need migration with actual decoded RGBA image data, source→view correspondence, sRGB/UNORM and mip/layer preservation.
- [ ] Minecraft partially-overlapping-range hazard, robust bounds and image atomics: **not yet solved** by per-image layout fix.
- [ ] APK integration, device installation and game validation: **not performed**.

Local reproducible kit `Bachata-F43DEV-R2A-MIXED-IMAGE-SOURCE-KIT.zip` SHA-256 `df82ccda70e1017efcdee5663d26b7831a838699445a11a90927e82b969e3521` (scripts, local 17-test suite, Outlast migration gate, checksums). Local 17/17 tests PASS. GitHub versioned CI has 18/18.

Functional F43DEV V2 APK SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded` **re-verified** from filesystem, unchanged. Stable PanVK F3 `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb` remains untouched.

## Next engineering gates

1. Wait for ABI-valid executable artifact from R2A CI. Compare disassembly/source diff/hashes with R1.1 candidate and verify basic emulator startup separately without replacing V2.
2. R2B: solve *cross-image* guest range overlap robust sampling/write/atomics in public candidate, preserving memory ordering and bounds.
3. R2C: port the private BCn fallback only with verified decoded-data ownership and view correspondence, or reproduce semantics with an audited equivalent.
4. Integration APK variant: strictly independent and reversible; user must not uninstall V2 or official Bachata. Validation on G720 of Outlast/Minecraft and gameplay in God of War III before declaring regression fixed.
