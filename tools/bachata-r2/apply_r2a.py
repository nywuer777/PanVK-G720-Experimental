#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Fail-closed Bachata R2A source patch for pinned shadPS4 Linux ARM64/GLIBC."""
import argparse
import subprocess
from pathlib import Path

PIN = "be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
HASHES = {
    "src/video_core/texture_cache/image.h": "6af58cbbece05a32aafd1a8a3f93c6b775f9ee9c",
    "src/video_core/renderer_vulkan/vk_rasterizer.cpp": "99db69505bd3b5e34e5e49251a9b94955f51f081",
}
HEADER_OLD = """    struct {
        u32 is_bound : 1;
        u32 is_target : 1;
        u32 needs_rebind : 1;
        u32 force_general : 1;
    } binding{};"""
HEADER_NEW = """    struct {
        u32 is_bound : 1;
        u32 is_target : 1;
        u32 needs_rebind : 1;
        u32 force_general : 1;
        // Per-batch storage-write usage, regardless of descriptor order.
        u32 has_storage : 1;
    } binding{};"""
FIRST_OLD = """            if (image->binding.is_bound) {
                // The image is already bound. In case if it is about to be used as storage we
                // need to force general layout on it.
                image->binding.force_general |= image_desc.is_written;
            }
            image->binding.is_bound = 1u;"""
FIRST_NEW = """            // Sampling and storage must resolve to GENERAL, regardless of descriptor order.
            if (image->binding.is_bound &&
                (image->binding.has_storage || image_desc.is_written)) {
                image->binding.force_general = 1u;
            }
            image->binding.has_storage |= image_desc.is_written;
            image->binding.is_bound = 1u;"""
SECOND_OLD = """            // The image is either bound as storage in a separate descriptor or bound as render
            // target in feedback loop. Depth images are excluded because they can't be bound as
            // storage and feedback loop doesn't make sense for them
            if ((image.binding.force_general || image.binding.is_target) &&
                !image.info.props.is_depth) {
                image.Transit(instance.IsAttachmentFeedbackLoopLayoutSupported() &&
                                      image.binding.is_target
                                  ? vk::ImageLayout::eAttachmentFeedbackLoopOptimalEXT
                                  : vk::ImageLayout::eGeneral,
                              vk::AccessFlagBits2::eShaderRead |
                                  (image.info.props.is_depth
                                       ? vk::AccessFlagBits2::eDepthStencilAttachmentWrite
                                       : vk::AccessFlagBits2::eColorAttachmentWrite |
                                             vk::AccessFlagBits2::eColorAttachmentRead),
                              {});
            } else {"""
SECOND_NEW = """            // Mixed sampled/storage access needs GENERAL and ShaderWrite barriers.
            if ((image.binding.force_general || image.binding.is_target) &&
                !image.info.props.is_depth) {
                vk::AccessFlags2 access = vk::AccessFlagBits2::eShaderRead;
                if (image.binding.has_storage) {
                    access |= vk::AccessFlagBits2::eShaderWrite;
                }
                if (image.binding.is_target) {
                    access |= vk::AccessFlagBits2::eColorAttachmentWrite |
                              vk::AccessFlagBits2::eColorAttachmentRead;
                }
                // Feedback-loop attachment layout is not valid for storage writes.
                const bool use_feedback_layout = image.binding.is_target &&
                                                 !image.binding.has_storage &&
                                                 instance.IsAttachmentFeedbackLoopLayoutSupported();
                image.Transit(use_feedback_layout
                                  ? vk::ImageLayout::eAttachmentFeedbackLoopOptimalEXT
                                  : vk::ImageLayout::eGeneral,
                              access, {});
            } else {"""
PATCHES = {
    "src/video_core/texture_cache/image.h": [(HEADER_OLD, HEADER_NEW)],
    "src/video_core/renderer_vulkan/vk_rasterizer.cpp":
        [(FIRST_OLD, FIRST_NEW), (SECOND_OLD, SECOND_NEW)],
}
def transform(text, patches):
    for old, new in patches:
        count = text.count(old)
        if count != 1:
            raise ValueError(f"Unmodified source anchor expected once, got {count}: {old[:45]}")
        text = text.replace(old, new, 1)
    return text
def run(source):
    source = source.resolve()
    if not (source / ".git").exists():
        raise ValueError("Source must be a pinned Git checkout")
    actual = subprocess.check_output(
        ["git", "-C", str(source), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != PIN:
        raise ValueError(f"Wrong upstream commit {actual}; expected {PIN}")
    updates = {}
    for name, expected in HASHES.items():
        actual_hash = subprocess.check_output(
            ["git", "-C", str(source), "hash-object", name], text=True
        ).strip()
        if actual_hash != expected:
            raise ValueError(f"Blob changed: {name} = {actual_hash}; expected {expected}")
        path = source / name
        data = transform(path.read_text(encoding="utf-8"), PATCHES[name])
        updates[path] = data
    for path, data in updates.items():
        path.write_text(data, encoding="utf-8", newline="")
        print(f"R2A PATCHED {path.relative_to(source)}")
    print("R2A_SOURCE_PATCH_OK")
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    args = parser.parse_args()
    run(args.source)
