# P46 — F43DEV private GLIBC BCn integration gate

Private source readiness audit; **not an Outlast fix, and not a signed APK**.

Checked functional P42 (Android v2 identity 1 Bionic + 11 GLIBC signer references, 397 runtime entries), source-only public P45 and real Outlast diagnostic. Protected findings:

- P42 private ELF AArch64/GLIBC 75,323,616 bytes, SHA-256 `5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002`.
- P42 private `.text` SHA-256 `f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157` — unmodified, old BCn sampled-view assertion still present.
- P31 **public** ELF contains the same `bachata-s4` source path string; never use this as private-host identity evidence.
- Outlast diagnostic's last BC3 sRGB resource: 1024×1024, 11 mipmaps, RGBA8 sRGB selected. GPU fence and per-(mip,layer) upload proof NOT shown.
- Synthetic tests of P44 admission rules do not prove Outlast gameplay and do not replace source-level integration.

**Required for real P46 APK**: compilable F43DEV private GLIBC source matching the functional P42 host; port the BCn decode-upload-fence-view chain into it; preserve private V2 runtime identity and assert; compile ARM64 GLIBC; pass signer/host identity gate on final signed APK; test on device.

SHA256 of this source kit: `676ec08289ad8c0dccc1985054b2e7a294b6cb07a493e6da7bf80b9e6b3ddadf`.

GitHub Actions here intentionally runs **source-only gates**, never includes P42 ELF, signing keys, private data or tokens. The gate is fail-closed when private source or finished hardware proof is missing.
