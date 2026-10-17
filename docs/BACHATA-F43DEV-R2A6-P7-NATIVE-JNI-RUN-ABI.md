# Bachata F43DEV — R2A.6/P7: verified NativeRuntimeBridge JNI ABI, before Android SAF broker test

**2026-10-17.** Branch: `exp/bachata-f43dev-r2a6p7-native-jni-abi`. Read-only comparison of the *pinned known-good* F43DEV V2 signed APK and its original Bionic native runtime. **No APK modified, rebuilt, signed or installed.** No live Android device has been contacted. CI [#39013438705](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39013438705).

## Scope

Original APK SHA-256 **`e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`**. Internal Android Bionic native library `lib/arm64-v8a/libbachata_native_runtime.so` SHA-256 **`16bd679a762ee3615bc3deb24e0945964775f267eb2f1dc0f015c2eeb030ef54`**.

The binary DEX method-id/proto-id/class-data tables of the actual V2 APK unambiguously show:

```java
// Lcom/bachatas4/android/runtime/process/NativeRuntimeBridge;
public static native int run(
    android.view.Surface surface,
    boolean option,
    String[] arguments,
    String[] environment,
    String value,
    int numericParameter
);
public static native void stop();
```

Canonical JNI DEX descriptors:

- `run: (Landroid/view/Surface;Z[Ljava/lang/String;[Ljava/lang/String;Ljava/lang/String;I)I`
- `stop: ()V`

Both are flagged **`ACC_PUBLIC | ACC_STATIC | ACC_NATIVE`**, with **zero DEX code offset**. These are structural observations from the DEX class data, *not* conjectural Java declarations. The names `option`, `arguments`, `environment`, `value`, and `numericParameter` are **neutral placeholders**: no semantics have been proven for those parameter positions.

The Bionic ELF dynamic symbol table (`readelf --dyn-syms`) contains exactly one nonzero-size, defined global function export for each:

- `Java_com_bachatas4_android_runtime_process_NativeRuntimeBridge_run`;
- `Java_com_bachatas4_android_runtime_process_NativeRuntimeBridge_stop`;
- `JNI_OnLoad`.

These exports are consistent with the DEX methods' static JNI entrypoints; **they are not proof that a real Android process can invoke them in this experimental runtime**, that native memory is safe, or that the broker is reachable.

## R2A.6/P6 reconciliation

P6 already established byte-equality of `libbachata_host_loader.so` and `host/ld-linux-aarch64.so.1`: the renamed file is **GLIBC `ld.so`**, not the JNI runtime bridge. The JNI entrypoints above belong instead to the distinct Bionic `libbachata_native_runtime.so`. The original runtime manifest declares **protocol version 2**; the P5 candidate has a compiled **`BACHATA/1 HELLO version=2 contract=<32 lowercase hex nonce>`** path. These facts do not replace runtime authorization, signature, or actual filesystem mapping.

## Material implementation and validation

- `tools/bachata-r2a6p7/audit_native_bridge.py`: strict pinned APK/native SHA verification; parses DEX string/type/prototype/method/class-data tables; checks native and static flags and zero bytecode; compares the exact descriptors with expected JNI interface; validates native exports using `readelf -W --dyn-syms`; outputs a *fixed-schema, sanitized JSON report*, never raw argument values.
- `tools/bachata-r2a6p7/test_audit_native_bridge.py`: **24 synthetic tests**, including mutated method signatures, broken DEX offsets, native/static flags and fake/undefined/missing/duplicated JNI exports. No proprietary binaries in the GitHub repository or CI.
- CI [#39013438705](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39013438705) **SUCCESS**, artifact [#12093772279](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39013438705/artifacts/12093772279), SHA manifests pass.
- Independently reexecuted the *published CI script* locally against the original pinned APK: method/prototype flags and all three native exports **PASS**. All 24 synthetic tests pass locally; local sanitized JSON matches the original independent extraction audit.

## Critical blockers for P8 / real Android SAF broker

1. **Android host Java/Kotlin/Gradle source is absent.** DEX and ELF reverse-inspection establishes declarations, but not a maintainable, authorized integration or internal launch semantics.
2. **The JNI run parameter semantics remain unresolved.** The exact purpose and allowed values of the `Surface`, boolean, two arrays, String and integer must be established from authorized host code/diagnostics. Do not guess or fabricate an `env` array or a GLIBC root.
3. **Signature/identity:** static class data and exported JNI symbols do not verify APK signer or broker access. The original Bionic host's certificate/UID contract must remain intact. A new side-by-side package has another Android UID and cannot transparently access the original broker. Do **not** replace, re-sign or patch the functional F43DEV V2.
4. **GLIBC loader path:** P6 confirmed `PT_INTERP=/lib/ld-linux-aarch64.so.1` in original and P5; actual Android FEX/GLIBC root staging and loader lookup are not verified without a live, authorized Android debug session.
5. **SAF BSF1:** previous P2 tests used mocks. The same-UID broker handshake, read-only FD transfer, and `Stat/List/OpenRead` on user-selected harmless test fixtures remain **NOT TESTED on Android hardware**.
6. **GPU issues:** Outlast BCn view mismatch and Minecraft alias/robustImageAccess2 errors are separate. No claim of correction or FPS improvement.

## Next authorized action

For P8, supply the **original F43DEV Android host Gradle project** (especially `NativeRuntimeBridge`, native runtime launch logic, SAF broker service, runtime manifest/install extraction and signer verification) or an officially supported diagnostic entry point. We can then implement a **read-only, opt-in same-UID probe in a maintainer-authorized host debug build** using a disposable file/directory, without logging tokens, actual paths, game content or sensitive identifiers. Only after that hardware test can the BSF1 success state advance.

**Stable installations preserved:** F43DEV Host Identity V2, PanVK Fase 3 and PanVK F4.3. P7 produces no installable APK.
