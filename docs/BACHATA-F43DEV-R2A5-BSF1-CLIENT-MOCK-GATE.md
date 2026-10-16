# Bachata F43DEV — R2A.5/P1: read-only BSF1 client and mock broker

Date: 2026-10-16. Branch `exp/bachata-f43dev-r2a5-bsf1-client`. Work isolated from PanVK stable Fase 3 and functional signed F43DEV V2.

## Grounded ABI and wire protocol

Original signed F43DEV V2 APK SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`.
Original Bionic `libbachata_native_runtime.so` SHA-256 `16bd679a762ee3615bc3deb24e0945964775f267eb2f1dc0f015c2eeb030ef54`.

Static disassembly of original library, not guessed from public fork:
- request `BSF1 | version:1 | opcode:u8 | token_len:u32 BE | token | path_len:u32 BE | path`.
- response `BSF1 | version:1 | status:u8 | payload_len:u32 BE | payload`; 4 MiB bound.
- opcodes 1=Stat, 2=List, 3=OpenRead.
- Stat successful payload size 17: directory flag byte + two big-endian u64 with **unverified semantics**.
- List success: count:u32 BE, entries of name_length:u16 BE, name, flag:u8, two u64 BE.
- OpenRead expects `SCM_RIGHTS` descriptor. Status zero is success according to Bionic code path; other codes are treated generically as remote error until status semantics are known.

## Local tested implementation, separate downloadable kit

`Bachata-F43DEV-R2A5-BSF1-CLIENT-MOCK-TESTES.zip` SHA-256:
`4084ec75dffbf6b0e4ad13e30d038dad2b3dc438a9b14a6ad5c61826eb45854a`.

This local kit includes:
- `src/saf_bsf1_client.h`, `src/saf_bsf1_client.cpp`: self-contained Linux C++20 client with read-only typed `Stat/List/OpenRead`, bounded connect, socket send/receive timeouts, exact fragmented frame reads, fail-closed 4 MiB payload cap, same-UID `SO_PEERCRED`, `SCM_RIGHTS` FD receipt with ownership and CLOEXEC, read-only regular-file FD validation, relative-path traversal prevention and no token logging.
- `tests/test_bsf1_mock.cpp`: local AF_UNIX abstract socket broker mock with an entirely synthetic token; positive and negative protocol/FD/path cases.
- `logs/mock-run.txt`, `logs/sanitizer-run.txt`, `docs/EVIDENCE.md`, static evidence JSON, `SHA256SUMS.txt`.

**Local results:** 33/33 checks, 21 named mock broker scenarios + 12 direct configuration/path assertions; same harness passed under AddressSanitizer and UndefinedBehaviorSanitizer with no reported errors. The client's header API is also published at `tools/bachata-r2a5/saf_bsf1_client.h` in this branch.

The full implementation and test sources remain in the downloadable local kit; **they have not yet been promoted as a complete GitHub CI C++ project**. Do not report a CI build for R2A.5 without one.

## Explicit blockers (do not conflate with compilable core)

1. Real Android SAF broker wire handshake and token authentication not performed. Same-UID `SO_PEERCRED` is not Android signing verification.
2. Per-entry List and Stat 64-bit fields have not been identified. Strict read-only FD policy may need verified real-broker adjustments.
3. The tested independent client is not yet wired into `Core::FileSys` and no ARM64 GLIBC R2A.5 executable has been produced.
4. F43DEV V2 signed APK and PanVK Fase3/F4.3 remain unmodified.
5. No fixes claimed for Outlast BCn or Minecraft robust-image alias. The legacy private core source still differs from public candidate.

Next: move exact locally-tested source and mock into repo, run GH CI (x86 native ASan, Linux ARM64 cross build), then integrate a read-only VFS adapter and test a broker sandbox with non-sensitive test data. Only after a real Android handshake can a signed separate lab APK be considered.
