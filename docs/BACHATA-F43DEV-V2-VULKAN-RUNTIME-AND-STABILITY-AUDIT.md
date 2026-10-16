# Bachata F43DEV Host Identity V2 — ABI/ICD and stability audit

Date: 2026-10-16. **Read-only**, no driver, APK or device mutations.

## Current hardware gate

User confirmed “Sim, inicia normalmente” and provided screenshot of **God of War III Remastered** rendered in the F43DEV V2 main menu, with on-screen 37 FPS (menu snapshot), 17% CPU, 70% RAM, 35.8 C. These readings are not gameplay benchmarks, and control functionality / long-session stability are pending independent test.

Running-process evidence from F43DEV V2: `u0_a454 32055 29111 ... S libbachata_host_loader.so`. This is compatible with the Linux/GLIBC host path, but does not alone prove the actual mapped Vulkan ICD.

## Reproducible archive inspection

Analyzed the exact signed F43DEV Host Identity V2 APK, SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. APK ZIP CRC and native-runtime manifest SHA-256 match.

The package includes **two distinct driver ABIs**:

- `assets/drivers/Bachata-PanVK-V3-glibc.zip` — `meta.json: abi=linux-aarch64-glibc`, version `3.2.0`, profile `g615-v11-csf`, ELF `DT_NEEDED libc.so.6`, `libstdc++.so.6`, X11/Wayland-related libraries. The shipped metadata says G615/v11 even though the vendor's distribution description claims compiler support for other arches; it is not proof of G720 gameplay qualification.
- `assets/drivers/PanVK-G720-UMA-F4.3-ICD-DUAL-Android-ARM64.zip` — Bionic ARM64 with Android `DT_NEEDED libc.so`, `liblog.so`, `libhardware.so`; `meta.json` fingerprint `G720-UMA-F4.3-ICD-DUAL-20261016`, `logcatTag=PanVK_F43`; SHA-256 hashes of ELF and packages match embedded metadata/sidecars.

**GLIBC and Bionic binaries are not interchangeable.** Mere inclusion of Bionic F4.3 in an APK does not mean the GLIBC-emulated game's GPU calls use it.

## Historical native evidence (NOT current F43DEV)

Previously provided official APK diagnostics:

- `bachata-diagnostic-BS4-20261016-627CABD7.zip`: game CUSA00325, `abi=linux-glibc-arm64`, `guestBackend=fex`, `driver.source=glibc`, `driver=panvk-244793347e1d591f`, first frame presented.
- `bachata-diagnostic-BS4-20261016-8B4F1AA7.zip`: game CUSA01623, same GLIBC/FEX and driver ID. These diagnostics are from **official** `com.bachatas4.android.github`, not `com.bachatas4.android.f43dev` and do not prove the F4.3 was used now.

## Material deliverables / tests

Generated read-only `analyze_f43_runtime.py` analyzer, `test_runtime_audit.py` tests, `TESTE-LADB.md` controlled gameplay protocol, JSON static/historical evidence and technical report. **8/8 tests PASS** (including ABI separation, both ELF/package checksums, correct historical session provenance and ZIP CRC rejection). Evidence ZIP SHA-256 `8c91c06a500089759c63371b5b5f7a67b9041b8437dfc1a77cc3f3f09561896d`. No signing keys or copyrighted APK payload in audit ZIP.

## Next hardware verification

Use one natural 3–5 minute **New Game** session on God of War III Remastered; record gameplay FPS, visual artifacts, controls, stability; delimit with `PANVK_CAPTURE` Logcat tag before/after launch; export a narrow Logcat text. A native diagnostic ZIP should be supplied **only if available without inducing a crash**. Absence of `PanVK_F43` in Android Logcat does NOT alone establish the driver was not used.

**Gate for GLIBC F4.3 port or CSF changes:** current-session native log explicitly confirming ABI and loaded ICD. Preserve stable PanVK F3 `3cacc2f0bcbb`, F43DEV V2 functional APK and official Bachata.

## Feedback de gameplay — primeira missão (2026-10-16)

O usuário informou FPS em jogo entre **15 e 22**, e depois confirmou **alguns travamentos ocasionais** na primeira missão de **God of War III Remastered**. Não observou problemas gráficos **até o momento**, mas ressalvou que ainda pode encontrá-los posteriormente e enviará screenshot se necessário.

**Interpretação delimitada:** inicialização e renderização de menu verificadas, gameplay alcançado conforme relato; estabilidade não aprovada por conta dos travamentos. A ausência atual de artefatos gráficos não constitui teste de compatibilidade visual completo. Não atribuir a causa a shader compilation, CSF, PanVK UMA, memória ou FEX sem telemetria correlacionada. FPS de 15–22 é intervalo relatado, não benchmark controlado.

**Próximo gate:** identificar driver efetivamente carregado pela sessão GLIBC e caracterizar travamentos (intervalos, primeira aparição vs repetição, temperatura/memória se disponíveis). Preservar Bachata F43DEV V2 funcional e PanVK Fase 3 estável.
