#!/usr/bin/env python3
"""P49 explicitly reviewed rebase of ONE known overlapping P39 Vulkan access hunk.

P45 P39 flag adds ShaderWrite on mixed same-ImageId force_general; R2A already
provides ShaderWrite when a storage binding exists for the same Image.
Only the single exact additive patch hunk may be omitted, after validating the
R2A implementation and P39 active code. No blanket fuzzy patching allowed.
"""
from __future__ import annotations
import hashlib
import re
from pathlib import Path

TARGET = "diff --git a/src/video_core/renderer_vulkan/vk_rasterizer.cpp b/src/video_core/renderer_vulkan/vk_rasterizer.cpp"
HUNK = re.compile(r"(?m)^@@ [^\n]+\n")
R2A_GUARDS = (
    "image->binding.has_storage |= image_desc.is_written;",
    "if (image.binding.has_storage) {",
    "access |= vk::AccessFlagBits2::eShaderWrite;",
    "const bool use_feedback_layout = image.binding.is_target &&",
    "!image.binding.has_storage &&",
)

def prepare(patch: bytes, host_rasterizer: Path) -> tuple[bytes, dict]:
    text = patch.decode("utf-8", errors="strict")
    host = host_rasterizer.read_text(encoding="utf-8")
    for marker in R2A_GUARDS:
        if host.count(marker) != 1:
            raise ValueError(f"R2A_SHADERWRITE_SEMANTICS_NOT_PROVEN: {marker}")
    if text.count(TARGET) != 1:
        raise ValueError("P45_RASTERIZER_PATCH_NOT_UNIQUE")

    before, tail = text.split(TARGET, 1)
    next_diff = tail.find("\ndiff --git ")
    part = tail if next_diff == -1 else tail[:next_diff + 1]
    after = "" if next_diff == -1 else tail[next_diff + 1:]
    matches = list(HUNK.finditer(part))
    if not matches:
        raise ValueError("P45_RASTERIZER_HUNKS_MISSING")

    prefix = part[:matches[0].start()]
    hunks = [
        part[m.start() : (matches[i + 1].start() if i + 1 < len(matches) else len(part))]
        for i, m in enumerate(matches)
    ]
    overlaps = [h for h in hunks if "((BachataP39::Enabled() && image.binding.force_general &&" in h]
    if len(overlaps) != 1:
        raise ValueError("P39_KNOWN_OVERLAP_NOT_UNIQUE")
    overlap = overlaps[0]
    if not overlap.startswith("@@ -842,6 +1130,13 @@"):
        raise ValueError("P39_OVERLAP_HUNK_CHANGED")
    additions = [l[1:] for l in overlap.splitlines()[1:] if l.startswith("+") and not l.startswith("+++")]
    deletions = [l for l in overlap.splitlines()[1:] if l.startswith("-") and not l.startswith("---")]
    if len(additions) != 7 or deletions or not all(
        needle in overlap for needle in (
            "vk::AccessFlagBits2::eShaderRead |",
            "BachataP39::Enabled()",
            "image.binding.force_general",
            "vk::AccessFlagBits2::eShaderWrite",
            ": vk::AccessFlagBits2::eNone) |",
        )
    ):
        raise ValueError("P39_OVERLAP_SEMANTICS_CHANGED")
    other_hunks = [h for h in hunks if h != overlap]
    if not any("P39_EXACT_IMAGE_ID_SAMPLED_STORAGE" in h and
               "p39_image.binding.force_general = 1u;" in h for h in other_hunks):
        raise ValueError("P39_ACTIVE_FORCE_GENERAL_CODE_MISSING")

    edited = before + TARGET + prefix + "".join(other_hunks) + after
    info = {
        "status": "P39_WRITE_ACCESS_HUNK_EXPLICITLY_REBASED",
        "known_overlap_sha256": hashlib.sha256(overlap.encode("utf-8")).hexdigest(),
        "retained_other_p45_hunks": len(hunks)-1,
        "r2a_storage_write_access_statically_verified": True,
        "verified_host_p42_identity": False,
        "outlast_fixed": False,
        "apk_built": False,
    }
    return edited.encode("utf-8"), info
