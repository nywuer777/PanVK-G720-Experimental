# Bachata v0.2.5 — host identity check failed: root-cause audit

2026-10-16. Static inspection ONLY of user-provided unmodified `bachatas4-0.2.5-release.apk`, SHA-256 `1df49463f396df8b6f042230bdc1bb9f948b8e69894c378915920875c40ab0ee` (matches release SHA256SUMS.txt).

## Observation

User's actual emulator screen reports `Emulation Error — IllegalStateException: host identity check failed`. This message is NOT evidence of a PanVK GPU crash. The literal `host identity check failed` exists exactly once in the APK's `lib/arm64-v8a/libbachata_native_runtime.so` at file/rodata offset 0xE30E5C, which is referenced by native error handling that prints to stderr and calls `_exit(1)` in some paths; the Java overlay may render the associated session failure.

## Decisive native code

The ELF contains exported native functions:

- `Platform::Bachata::HostIdentityAccepted(string_view)` @ 0x387F10C: calls `PackageNameFromAppPath`, `ApkSigningCertSha256FromFile`, and `IsAllowedOfficialHost`, returning a boolean.
- Its companion no-argument code @ 0x387F2D8 checks `IsAndroidHost` and calls `DiscoverHostApkPath`; rejection emits `host identity check failed` to stderr then exits.
- `DiscoverHostApkPath` @ 0x387ED44 reads `/proc/self/exe` and attempts `FindHostApkFromMaps`; on missing result it parses `/proc/self/maps`. These sources may be environment-dependent and should be instrumented before editing.
- `IsAllowedOfficialHost` @ 0x387E04C checks the length and content of recognized package names. One accepted name decoded from its obfuscated literal is `com.bachatas4.android.github` (28 bytes); another accepted length is 21 (`com.bachatas4.android`). It accepts three 64-hex-character certificate digest strings, obfuscated in rodata.

## Critical signature finding

APK signing block v2 contains certificate DER SHA-256:
`a1d6e9aa7b3ff5ae3354f082b133b4d37b156be8aeaf704b0bfaaaee625761ee`.

Decoded first accepted signer fingerprint in `IsAllowedOfficialHost` **matches this APK's certificate exactly**. Thus this supplied official APK should pass the package-plus-signer *comparison* if the native runtime discovers and opens the correct APK file. The image does not establish whether the device actually runs this exact APK; those remain independent questions.

## Decision: do not blindly repack APK

Editing or resigning an Android APK without the original private signing key changes its signing certificate. A resigned APK cannot normally be installed as an update over the existing package, and the host-identity check would reject the new signer unless the trust policy is intentionally updated. Naively making the check always return true would mask path resolution or runtime selection failures, not repair them.

The public JICA98/Bachata-S4 repository is release/documentation-focused, not the full Android application source (per upstream README). Its maintained emulator core is separately developed at zenithblue-oss/shadps4-arm64, but a tree inspection does not locate this Android host-identity JNI implementation there. No APK source-based fix has yet been implemented or validated.

## Non-root diagnostic gate

With Bachata closed, run from LADB:

```sh
pm path com.bachatas4.android.github
APK_PATH="$(pm path com.bachatas4.android.github | sed -n 's/^package://p' | grep '/base.apk' | head -n 1)"
if [ -n "$APK_PATH" ]; then sha256sum "$APK_PATH"; else echo 'base.apk path not found'; fi
```

Compare installed `base.apk` hash to the supplied release APK SHA-256. A mismatch is evidence the installed bytes differ, not necessarily a signature failure (packaging and signed splits may differ). If a real crash just occurred, export the *native* Bachata diagnostic ZIP and correlate that particular session's runtimeHost and detailed error. Avoid induced crashes and do not delete app data.

## Potential implementation if evidence confirms host path discovery defect

Fork an authorized build of the native runtime and pass Android `ApplicationInfo.sourceDir` / `PackageManager`-verified package path explicitly to the native host validation (with issuer package binding and signature verification retained), instead of depending solely on `/proc/self/maps`. Log which path-resolution step failed; keep rejection on mismatched package or signer. Requires corresponding Android source/build and a separate developer signature (or author-signed release) before a runnable modified APK can be safely tested.

F3 remains preserved; PanVK F4.3 dual-ICD exports unaffected; no APK was modified, resigned or installed in this audit.
