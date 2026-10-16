# Bachata F43DEV — R2A.2: fail-closed host gate and runtime integration

Date 2026-10-16; isolated branch `exp/bachata-f43dev-r2a2-host-gate`. **Lab preparation; not a final patched APK.**

## Technical blocker from R2A.1

The current user-verified signed APK `Bachata-S4-F43DEV-HOST-IDENTITY-V2-SIGNED.apk` has SHA-256 `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`. Its nested `host/shadps4-arm64-fex` ELF had hash `b1cd025306b1dbd7b07d3bc228a0f18392d4f32fdeb934c9676e75ed0090abb4`, uses GLIBC ARM64, and carries `host identity check failed` / host-loader markers. The source-built R2A ELF `333e7f0c0dc79be4f007958f2018710f91ffd4245ef3b5e475621d33d4eb7584` has the same ELF/ABI/DT_NEEDED but not the same built-in host-identity mechanism.

Both binaries have `BACHATA/1` runtime-control protocol strings; the original APK manifest `protocolVersion=2` relates to the distribution packaging, not a different observed runtime socket frame version.

The Bionic library `libbachata_native_runtime.so` is preserved from the signed V2, SHA `16bd679a762ee3615bc3deb24e0945964775f267eb2f1dc0f015c2eeb030ef54`, and matches `assets/runtime/native-runtime.json`.

## Implementation actually committed

1. `tools/bachata-r2a2/f43dev_identity_gate.h`: dedicated Linux host-side security gate. Require **exact** app-private directory `com.bachatas4.android.f43dev` (with component boundary), canonical parent of the AF_UNIX socket beneath its private storage root, correct file types, app UID ownership; reject symlinked socket; authenticate server using `SO_PEERCRED` and matching `geteuid()`. Fails closed on missing peer API or mismatches.
2. `tools/bachata-r2a2/apply_r2a2.py`: source-pin and blob SHA guard against drift; inserts check before `RuntimeClient::Connect`/HELLO in `src/main.cpp`, applies only to `ENABLE_BACHATA_RUNTIME` Linux ARM64, retains the previous R2A image access patch and aborts if it is absent. Distinct success diagnostic: `BACHATA_F43DEV_R2A2_HOST_GATE_OK`.
3. `tools/bachata-r2a2/test_host_gate.cpp`: positive/negative tests for exact app name, sibling prefix spoofing, root boundary, peer UID and invalid descriptors.
4. `.github/workflows/bachata-f43dev-r2a2-host-gate.yml`: source preflight, host unit tests, 18 R2A regressions, pinned checkout + patch, ARM64/FEX Debian Trixie build, ABI/ELF and distinct marker validation, publish ELF candidate **only** if successful. [CI run #38963049803](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38963049803). First checked status: host-security-preflight **SUCCESS**, full ARM64 cross-build ongoing.

Source patch artifact [GitHub artifact #12072789663](https://github.com/nywuer777/PanVK-G720-Experimental/actions/runs/38963049803/artifacts/12072789663); locally downloaded ZIP SHA-256 `32f1e9f5ba6a31b364ed0a8a2383c6122dccccfcd63a0d698f86c5fec1acb763`. It contains exact diff, new header, hashes. Independent native host C++ test compiled with g++14 `-std=c++23 -Wall -Wextra -Werror -pthread` and passed.

## Runtime-only rehearsal (local kit)

Locally created `Bachata-F43DEV-R2A2-HOST-GATE-INTEGRATION-KIT.zip`, SHA-256 `8f4da81f6c6a7027203744b85f200b035b72f718147806e0757f8a4a2241c697`, containing source patch artifact, a fail-closed `stage_runtime_assets.py` staging tool and seven local regression tests (**7/7 PASS**).

The runtime preparer validates known baseline APK SHA and all **397** nested runtime entries against `assets/runtime/manifest.json`, checks future R2A.2 ELF SHA, package and identity marker, protocol marker, then can generate only `runtime.zip`, `manifest.json`, and staging status (not an APK). **It explicitly rejects the unguarded R2A ELF**, demonstrated in local negative tests. The R2A2 ELF artifact has not been produced at time of the kit creation. It does not patch/sign/install anything automatically.

## Security boundary and remaining gate

These checks establish app UID/root/socket-peer matching, **not a cryptographic verifier for the APK signer inside the GLIBC process**. The existing Bionic signature verification is preserved unchanged, but the equivalence to the old guest's full validation remains unproven without real device handshake tests. User should **NOT** replace the V2 core until a reversible *signed* lab build is independently verified and tested. Native runtime cert check and APK v2 signature must be reverified after any repack.

The two user crashes are NOT fixed or validated: Outlast BCn fallback and Minecraft overlapping guarded-mip writes/atomics. R2A's per-image mixed ShaderWrite/layout fix is only one subset of the problem. Don't confuse host gate success with GPU stability, and don't claim PanVK F4.3 Bionic is used by GLIBC.

## Preserved stable baselines

- F43DEV Host Identity V2 user-validated APK: SHA `e4ec95a1ffcb33f1bf7d8e9d9587cc0af0f839de226b8ed74fb03f08e3444ded`.
- PanVK F3 `3cacc2f0bcbb2333bb7742d37a3e471fd8305acb`, untouched.
- PanVK F4.3 Bionic remains separate, no GLIBC loading claim.

**Promotion to signed lab APK requires:** R2A2 CI PASS + exact SHA/ABI audit; runtime staging checks; APP/Bionic signer verification preserved; boot and control socket handshake confirmation on hardware; separate Outlast/Minecraft case reproduction. Static success is not game compatibility.
