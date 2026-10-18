# P50 — Real P49 ELF / F43DEV host compatibility

**Status: ABI verification complete on the exact P49 binary; Android host compatibility remains NOT PROVEN.**

This is not another build of the public candidate: P50 tests the **actual** compiled P49 AArch64/GLIBC ELF downloaded from approved run [#39089770038](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39089770038), artifact 12123278265.

## Checked evidence

- Exact P49 ELF SHA-256: `272024fe15b7785be819f7fe3eb403c0543b070da2a6525d10580e24876dadaa`.
- AArch64 ELF64 little-endian, interpreter `/lib/ld-linux-aarch64.so.1`.
- Direct NEEDED dependency set: `libuuid.so.1`, `libm.so.6`, `libudev.so.1`, `libstdc++.so.6`, `libgcc_s.so.1`, `libc.so.6`, `ld-linux-aarch64.so.1`.
- Maximum referenced glibc symbol version: **GLIBC_2.38**. Maximum referenced libstdc++ symbol version: **GLIBCXX_3.4.32**. These are system prerequisites, not proof that the F43DEV private runtime supplies them.
- ELF contains Host V2 HELLO line format and negative-rejection messages, but **strings do not establish control-flow behavior**.
- Public reconstructed source enforces package path `com.bachatas4.android.f43dev` and same-UID `SO_PEERCRED`; actual P42 package/root identity is **not validated** here.
- QEMU ARM64 user-space rejection smoke is isolated to Linux, uses synthetic arguments, and must reject invalid contract and missing managed-host socket. It cannot validate Android Bionic signing or game launch.

## Blockers — do not promote this ELF into an APK

1. Original private P42 ELF reference hash `5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002` is known, but the original bytes and original matching private source were not accessible as trusted container inputs during P50. Project Library APK metadata alone does not confer raw byte access.
2. Existing P42 APK v2 signing, Bionic + 11 GLIBC signer references, 397 runtime manifest entries, JNI/loader command-line construction, private FEX runtime layout and certificate checks have not been reconciled with the public candidate.
3. Full actual Android GLIBC dependency closure, managed AF_UNIX socket handshake, SAF/BFS1 broker, Vulkan renderer loading, and Outlast BC3 sRGB 1024x1024 11-mip execution have not been exercised.
4. This P50 workflow **never signs, repacks, rewrites or replaces** P42, and never attempts to spoof Bionic identities. It remains research-only.

## Artifacts / reproducibility

- `tools/bachata-p50/audit_p49_guest_abi.py` — read-only native ELF/ABI checker, strict SHA and prereq/source gate, JSON with explicit no-go.
- `tools/bachata-p50/test_audit.py` — synthetic negative tests (bad SHA, symlink, symbols, claims).
- `.github/workflows/bachata-f43dev-p50-host-compat.yml` — checks **real P49 artifact** from immutable run, then QEMU negative host gate.
- GitHub Actions P50 output artifacts are small **audit results only**, not duplicate original binaries or installable APKs.

Fase 3 of PanVK and P42 signed application remain unchanged. Successful Linux/QEMU negative tests are narrower than successful Android host/Outlast tests.
