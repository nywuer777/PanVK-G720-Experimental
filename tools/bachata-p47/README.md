# P47 — Recovery of original F43DEV private GLIBC source (source-only gate)

## Evidence recorded (2026-10-17, America/Sao_Paulo)

- P46 Actions run #39081367066 passed. Its source-only tests do **not** imply private core integration, an APK, or an Outlast fix.
- Exact P42 working private guest ELF: **75,323,616 bytes**, SHA-256: 
  \`5eee7ec0643bcc80addac60b2cb08b203eac0edcaaf2ac1b11219c8630e6e002\`
- P42 private guest ELF .text SHA-256:
  \`f71b3ac83bb350f7de2835e3f4037b9d95d3fc080f1d9781e2271549f7964157\`
- Probable private code lineage from earlier R1 audit: \`JICA98/Bachata-S4-Dev@433c7f30a66c205dff5c3261431e550957f5d447\` — **unavailable and NOT recovered**.
- Public core alternative: \`zenithblue-oss/shadps4-arm64@be6bc2e9c60799e071dd2fafa6216e8d80ec619c\` — **not interchangeable** with P42; original private source and host-side signer protocol are not proved equivalent.
- Public P45 is a delta for per-(mip,layer) BCn upload/fence/view admission, not a patched private GLIBC ELF.
- The source gates cannot substitute for the original F43DEV runtime identity: Android v2 signature, 1 Bionic + 11 GLIBC signer references, 397 runtime manifest entries and actual loader/host checks.

## Deliverable of P47

A **fail-closed, source-only recovery gate** and portable negative tests. It accepts a local, privately obtained source tree plus an independently assembled hash manifest, proves only that named files and hashes are present, and *always* reports binary equivalence, private P45 integration, Outlast and APK as **not established**.

In the branch CI, no private source is provided intentionally: the CLI must return code 2 with \`BLOCKED_PRIVATE_SOURCE_UNAVAILABLE\`. This blocked result is an expected demonstration of correct behavior, not proof that recovery succeeded.

Sample command (run privately, NOT in this repo's CI):
\`\`\`bash
python3 tools/bachata-p47/source_recovery_gate.py \
  --source-root /secure/recovered-f43dev-src \
  --manifest /secure/recovered-f43dev-manifest.json \
  --report /secure/p47-recovery-report.json
\`\`\`

Manifest schema requires: \`schema=bachata-f43dev-p47-source-v1\`, P42 ELF/.text reference digests, original private reference commit \`433c7f...\`, \`source_revision\` and \`lineage\` (recovered-original-private or reconstructed-private), plus distinct SHA-256-checked files with roles \`private_host_identity\`, \`bcn_graphics\`, \`runtime_protocol\`, \`build_recipe\`. The manifest is evidence supplied by an auditor, not a way to manufacture F43DEV identity.

## Criteria for next phase / no-go rules

1. Recover authorized private source and its build recipe (prefer a verified, immutable archive with source provenance). If impossible, reconstruct as a **new, distinct** private-source port; never pretend exact P42 source equivalence.
2. Run inventory gate and audit the relevant host identity code and GPU image-view paths. The current script deliberately **does not prove** build reproducibility or source-to-binary identity.
3. Compile ARM64 GLIBC private runtime with explicit build log and SHA/ELF/ABI evidence; verify loader protocol, P42 signer/host guards and runtime manifest for the *new executable*.
4. Port P45's real decode-upload-GPU fence-per-layer view chain. Rebuild; do not suppress old BCn assertions or hide missing uploads.
5. Only then construct a separately signed lab APK, run the mandatory P42 post-signature identity gate, and test F43DEV startup followed by the Outlast case on hardware.

**Never upload** private signing keys, APKs, ELF binaries, proprietary recovered sources, secrets, user logs, SAF capabilities or game content to this branch. Maintain stable P42 APK and PanVK Fase 3 unchanged.
