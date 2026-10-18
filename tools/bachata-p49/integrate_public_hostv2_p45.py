#!/usr/bin/env python3
"""P49: lab-only public-core integration of host V2 path and BCn view logic.

No P42 private identity claim, signing, Android install, or gameplay validation.
The original P42 runtime is never patched or used as a substitution target.
"""
from __future__ import annotations
import argparse
import json
import subprocess
from pathlib import Path
from rebase_p39_shaderwrite import prepare

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
NEEDED = {
    "src/main.cpp": (
        "VerifyPeer", "SendHelloV2", "ContractV2::ValidNonce",
        "BACHATA_F43DEV_R2A2_HOST_GATE_OK",
    ),
    "src/platform/bachata/runtime_client.cpp": ("SendHelloV2",),
    "src/platform/bachata/f43dev_contract_v2.h": ("BACHATA/1 HELLO version=2 contract=",),
    "src/video_core/texture_cache/image_view.cpp": (
        "P45_BCN_PER_LAYER_VIEW_PROOF", "P25 decoded BCn sampled view blocked",
        "BachataP44::Resolve(p45_request)",
    ),
    "src/video_core/renderer_vulkan/p27_vk_decoded_upload.cpp": (
        "P45_BCN_LAYER_UPLOAD_COMPLETE",
    ),
    "src/video_core/texture_cache/image.cpp": (
        "p45_completed_bc_uploads.clear()",
    ),
    "src/video_core/renderer_vulkan/vk_rasterizer.cpp": (
        "P39_EXACT_IMAGE_ID_SAMPLED_STORAGE",
    ),
}
CHAIN = (
    ("tools/bachata-r2/apply_r2a.py", ()),
    ("tools/bachata-r2a2/apply_r2a2.py", ("--guard", "tools/bachata-r2a2/f43dev_identity_gate.h")),
    ("tools/bachata-r2a4/apply_r2a4.py", ("--header", "tools/bachata-r2a4/saf_cli_contract.h")),
    ("tools/bachata-r2a5/apply_r2a5.py", ()),
    ("tools/bachata-r2a6/apply_r2a6.py", ()),
    ("tools/bachata-r2a6p1/apply_r2a6p1.py", ()),
    ("tools/bachata-r2a6p2/apply_r2a6p2.py", ()),
    ("tools/bachata-r2a6p5/apply_r2a6p5.py", ()),
)

def run(argv: list[str], cwd: Path) -> None:
    subprocess.run(argv, cwd=cwd, check=True)

def verify_markers(source: Path) -> dict:
    missing = {}
    for relative, markers in NEEDED.items():
        path = source / relative
        if not path.is_file() or path.is_symlink():
            missing[relative] = ["MISSING_FILE"]
            continue
        value = path.read_text(encoding="utf-8")
        misses = [marker for marker in markers if marker not in value]
        if misses:
            missing[relative] = misses
    return {
        "markers_pass": not missing,
        "missing": missing,
        "host_original_p42_binary_verified": False,
        "host_signer_verified": False,
        "private_runtime_reconstructed": False,
        "outlast_fixed_on_device": False,
        "apk_built": False,
    }

def integrate(repo: Path, source: Path, kit_source: Path, result_path: Path) -> None:
    repo = repo.resolve()
    source = source.resolve()
    kit_source = kit_source.resolve()
    if not (source / ".git").is_dir():
        raise RuntimeError("PINNED_GIT_CHECKOUT_REQUIRED")
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    if head != PIN:
        raise RuntimeError("UPSTREAM_COMMIT_MISMATCH")
    if subprocess.check_output(["git", "status", "--porcelain"], cwd=source, text=True).strip():
        raise RuntimeError("UPSTREAM_WORKTREE_NOT_CLEAN")
    if not (kit_source / "port_renderer_p45.py").is_file():
        raise RuntimeError("P45_PORT_SCRIPT_MISSING")
    for rel, _ in CHAIN:
        if not (repo / rel).is_file():
            raise RuntimeError(f"HOST_SOURCE_PATCH_MISSING: {rel}")

    # P45 must be generated against a clean, exact-PIN checkout. Keeping the
    # public reference independent prevents weakening P45's clean-tree guard.
    # Never use --3way/-C/reject or skip context validation when rebasing.
    result_path.parent.mkdir(parents=True, exist_ok=True)
    p45_clean = source.parent / "p49-p45-clean"
    if p45_clean.exists():
        raise RuntimeError("P45_CLEAN_SANDBOX_ALREADY_EXISTS")
    run(["git", "clone", "--local", "--no-hardlinks", str(source), str(p45_clean)], repo)
    clean_head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=p45_clean, text=True).strip()
    if clean_head != PIN:
        raise RuntimeError("P45_CLEAN_SOURCE_PIN_DRIFT")
    run(["python3", str(kit_source / "port_renderer_p45.py"),
         "--source-root", str(p45_clean), "--out",
         str(result_path.parent / "p49-p45-reference.diff"), "--write"], repo)
    run(["git", "diff", "--check"], p45_clean)
    # New source files are included as intent-to-add, without a fake commit.
    run(["git", "add", "-N", "."], p45_clean)
    patch = subprocess.check_output(["git", "diff", "--binary", "--no-ext-diff"],
                                    cwd=p45_clean)
    require_patch = result_path.parent / "p49-clean-p45.patch"
    if not patch or len(patch) > 8_000_000:
        raise RuntimeError("P45_PATCH_EMPTY_OR_TOO_LARGE")
    require_patch.write_bytes(patch)

    # Preexisting host trust checks must remain; compilation alone does not prove
    # equivalence to the P42 APK.
    for relative, extra in CHAIN:
        args = ["python3", str(repo / relative), str(source)]
        for item in extra:
            args.append(str(repo / item) if item.startswith("tools/") else item)
        run(args, repo)

    # P39 and R2A both change the same ShaderWrite expression. Resolve only
    # the single exact, reviewed hunk and retain R2A's broader has_storage
    # gating. Every other P45 patch hunk is still checked strictly.
    rebased, audit = prepare(require_patch.read_bytes(),
                             source / "src/video_core/renderer_vulkan/vk_rasterizer.cpp")
    rebased_path = result_path.parent / "p49-rebased-p45.patch"
    rebased_path.write_bytes(rebased)
    (result_path.parent / "p49-reviewed-rebase.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True) + "\n")
    run(["git", "apply", "--check", "--whitespace=error",
         str(rebased_path.resolve())], source)
    run(["git", "apply", "--whitespace=error", str(rebased_path.resolve())], source)
    run(["git", "diff", "--check"], source)
    result = verify_markers(source)
    result["source_pin"] = PIN
    result["public_hostv2_plus_bcn_combination"] = result["markers_pass"]
    result["experimental_public_source_only"] = True
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    if not result["markers_pass"]:
        raise RuntimeError(f"INTEGRATION_MARKERS_MISSING: {result['missing']}")
    print("P49_PUBLIC_HOSTV2_BCN_SOURCE_COMBINED_NOT_PRIVATE_NOT_APK")

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", type=Path, required=True)
    p.add_argument("--source-root", type=Path, required=True)
    p.add_argument("--kit-source", type=Path, required=True)
    p.add_argument("--result", type=Path, required=True)
    a = p.parse_args()
    try:
        integrate(a.repo, a.source_root, a.kit_source, a.result)
        return 0
    except (RuntimeError, subprocess.CalledProcessError, FileNotFoundError, OSError) as exc:
        a.result.parent.mkdir(parents=True, exist_ok=True)
        a.result.write_text(json.dumps({
            "status": "BLOCKED_INTEGRATION_NOT_PROVEN",
            "reason": str(exc),
            "host_original_p42_binary_verified": False,
            "outlast_fixed_on_device": False,
            "apk_built": False,
        }, indent=2, sort_keys=True) + "\n")
        print(str(exc))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
