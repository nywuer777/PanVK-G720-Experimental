# P34 — 1D tiled BCn detile + RGBA Vulkan source integration

Parent: P33. This experimental source-only build gates the 1D-tiled BCn fallback through `TileManager::DetileImage` and a CPU-readable GPU readback. Only exact public upstream `be6bc2e9c60799e071dd2fafa6216e8d80ec619c`, never private F43DEV APK. Source kit SHA256: `d3460d8ffb1b5cf88b4c99de037b0f8e7eddf6c73936db102bf6931c7e2f6885`.

Before shipping: compile ELF AArch64 GLIBC, audit host identity, validate on Mali-G720 with Outlast, remove synchronous GPU waits for perf. Minecraft robust image alias remains blocked; no assert removal and no `robustImageAccess2` assumption. P23 functional APK remains unchanged.
