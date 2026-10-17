# P32 — active-path gate

The public AArch64 GLIBC core compiled in P30, but Outlast BCn and Minecraft robust aliasing are **not fixed**. The P27 decoder and P28 async adapter have zero external calls in the P30 render/texture patch, and `TextureCache::RefreshImage` is unchanged. Minecraft alias checks are behind an opt-in diagnostic macro and do not alter memory ordering. Release gate: BLOCKED.

Run the Python script with the P29 source kit ZIP, P30 patch diff, and P30 compiled result JSON, as specified by `--help`. `--require-ready` returns exit status 8 while blocked. This is source audit, not live GPU testing. P23 remains installed and unmodified.

P30 successful CI: https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39045725323
P31 ELF export job: https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/39049368620
