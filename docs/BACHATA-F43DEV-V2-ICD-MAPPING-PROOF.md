# Bachata F43DEV V2 — Proof of Loaded Vulkan ELF (experiment)

Date 2026-10-16. User reports 15–22 FPS and minor recurring stutters on God of War III Remastered. No confirmed graphical artifacts in first mission. Current F43DEV sessions expose process `libbachata_host_loader.so`, consistent with GLIBC, but neither `PanVK_F43` nor Logcat proves the actual Vulkan ICD.

## Experimental probe, independent of GPU code

Built a temporary `com.bachatas4.android.f43dev` developer APK from the already functional signed **F43DEV Host Identity V2** base by adding only Android `application:debuggable=true` in compiled manifest, preserving all original APK contents (429/430 entries exact-byte-identical including Linux runtime, Bionic runtime, PanVK V3 GLIBC and PanVK F4.3 Bionic). Existing experimental signer reused; signed APK Signature Scheme v2 independently verified and 10/10 static tests passed.

- Baseline APK SHA256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`.
- Debug-only APK SHA256 `85d07bf7b81eac9335c7830bb045eda0f1af6bf3eeb689fb843519c154aa70b8`.
- Evidence kit SHA256 `2e433df2dc5e0b55accb37a21665f90588e62750018ee6e658b767c368a65066` (scripts, report, unit tests, exact hash list; **no private keys**).
- New AXML debug attribute uses resource id `0x0101000f`, Android namespace, boolean TRUE. All original application attributes unchanged.

## Device gate — do not claim victory from static tests

1. Update ONLY the separate F43DEV experimental package. Do not uninstall or replace original Bachata. Keep rollback `Bachata-S4-F43DEV-HOST-IDENTITY-V2-SIGNED.apk`.
2. LADB `run-as com.bachatas4.android.f43dev id` confirms whether debugging shell access works on Android 16. If denied, stop; do not interpret denial as a driver fault.
3. With game running, obtain child PID with `ps -A | grep libbachata_host_loader`, then `run-as com.bachatas4.android.f43dev sh -c 'grep -iE "vulkan|panfrost|vortek|mali|mesa" /proc/PID/maps'`. Capture output and error.
4. Match actual ELF pathname and hash against known GLIBC PanVK V3 versus Bionic F4.3. Mapped library identity is **not** proof of vkQueueSubmit being used. A definitive queue submission attestation requires a uniquely identified loader/ICD log in the same game session.
5. Restore unmodified F43DEV V2 APK as an update to turn OFF debugging; APK is same signer and package, installer acceptance pending device verification.

Android SELinux may block cross-process `/proc/<pid>/maps` even with `run-as`. In such a case this route is inconclusive; next option is instrumenting loader / GLIBC ICD in a separate experiment rather than claiming the driver is active. No induced crashes, root, changes to PanVK code, or APK data wipes.

Status: **Static instrumentation build and cryptographic verification PASS; Android install/physical proof PENDING.** PanVK stable F3 commit `3cacc2f0bcbb` unchanged.