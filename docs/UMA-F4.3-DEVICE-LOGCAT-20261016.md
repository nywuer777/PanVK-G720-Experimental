# F4.3 — device logcat review (2026-10-16)

Source: user-provided panvk-f43-completo.txt, 45,256 lines (~5.9 MB), SHA256 79357fdf0abaff0d2722dcdfbc2e100173437a7159676e782293fc79968c7363.

Window: main buffer 10-16 11:35:58.982 through 11:37:08.771.
Control markers: BEFORE_F43 at 11:35:59.103, AFTER_F43 at 11:36:05.443, TESTE_F43 at 11:36:56.140. Effective bracketed window **6.34 s**, not a full cold launch.
Zero PanVK_F43, PANVK-F4.3, F4.2 diagnostic tag entries; zero EmulationService, Vulkan provider, direct-icd or libvulkan_panfrost.so messages in this main buffer.

At 11:36:02.379, HyperSentinel monitors PID 13101 with process path containing libbachata_host_loa and RSS 2,751,852 KB -> 3,051,100 KB. This shows the host loader process already present in the window, NOT that this specific runtime launched within the window nor which Vulkan ICD was mapped. This is not evidence of a memory leak due to F4.3.
The system APK nativeLibs list at 11:35:59.095 contains both libbachata_host_loader.so and libbachata_native_runtime.so, which is just package inventory and does not show which one was selected.

**Disposition**: Logcat main capture works, but the F4.3 constructor cannot be proven absent from an earlier loader initialization; no launch event captured between before/after controls. Hardware load validation remains INCONCLUSIVE, not FAIL. The prior ELF export / Android cross-build validation remains PASS; F3 unaffected.

**Safe next protocol**: Fully stop the game through Bachata UI (do not provoke crash); before launching check `ps -A | grep -Ei 'shadps4|libbachata_host'` for lingering game host process, and wait for it to exit. Only then run `logcat -c; log -p i -t PANVK_CAPTURE BEFORE_F43`, launch the game for 20–30 seconds, optionally inspect the live process with `ps -A | grep -Ei 'shadps4|libbachata_host|libbachata_native'`, then write AFTER_F43 and export a filtered log via `logcat -d -b main -v threadtime -s PANVK_CAPTURE:I PanVK_F43:V EmulationService:V '*:S' > /sdcard/Download/panvk-f43-session.txt`. Do not clear logs after starting the game. Confirm BEFORE and AFTER and an actual new EmulationService process before interpreting missing driver tag.

Do not modify the CSF scheduler, cache UMA, Phase 3, or APK until launch runtime and loaded ICD are proven.
## Process observation after logcat review — user LADB ps -A

While the game was open, the user ran `ps -A | grep -Ei 'shadps4|libbachata_host|libbachata_native'` and captured:

```text
u0_a448      19569 18482  373198288 1982484 0                  0 S libbachata_host_loader.so
```

This confirms a child process (PID 19569; PPID 18482) with name `libbachata_host_loader.so` exists in that session. The static APK associates that host-loader name with the Linux/glibc backend, while the Android/Bionic runtime uses `libbachata_native_runtime.so`. Accordingly, the process observation supports — but does not conclusively prove — the GLIBC-route hypothesis. Process name alone does not prove the process' mapped libc or Vulkan ICD, and the listing does not show a matching Bionic runtime process.

**Action**: hold additional PanVK builds and GPU/CSF changes. Resolve the Bachata selected runtime and driver slot first. The Android/Bionic F4.3 binary is not a drop-in GLIBC ICD. No deliberate crash or root-dependent /proc/maps instructions.
