// SPDX-License-Identifier: GPL-2.0-or-later
// P44: fail-closed image-view admission for *verified* BCn->RGBA uploads.
// This is a standalone C++20 reference contract, NOT a private ELF binary patch.
#pragma once
#include <cstddef>
#include <cstdint>
#include <limits>

namespace BachataP44 {
enum class Format : uint8_t {
    Unknown, Bc1RgbUnorm, Bc1RgbSrgb, Bc1RgbaUnorm, Bc1RgbaSrgb,
    Bc3Unorm, Bc3Srgb, Rgba8Unorm, Rgba8Srgb
};
enum class Verdict : uint8_t {
    NativeCompressedView, VerifiedDecodedRgbaView,
    RejectGuestFormat, RejectStorageOrDepth, RejectExtentOrSamples,
    RejectMipLayerRange, RejectBackingFormat, RejectColorSpace,
    RejectFormatFeatures, RejectMutableFormat, RejectMissingUpload,
    RejectStaleUpload, RejectDirtyAfterUpload, RejectOverflow
};
struct CompletedUpload {
    uint32_t mip{}, layer{}, width{}, height{};
    uint64_t generation{}, completion_generation{}, content_epoch{};
    Format decoded_format{Format::Unknown};
    bool decoder_succeeded{}, guest_layout_verified{}, gpu_copy_submitted{},
         gpu_fence_completed{}, color_aspect_verified{};
};
struct Request {
    Format guest{Format::Unknown}, allocated_backing{Format::Unknown};
    bool sampled{}, storage{}, depth{}, color_aspect{}, sampled_feature{},
         view_format_feature{}, mutable_format{}, compatible_mutation{},
         guest_is_tiled{};
    uint32_t width{}, height{}, allocated_mips{}, allocated_layers{}, samples{1};
    uint32_t base_mip{}, mip_count{}, base_layer{}, layer_count{};
    uint64_t generation{}, current_content_epoch{};
    const CompletedUpload* uploads{};
    size_t upload_count{};
};
struct Result {
    Verdict verdict{Verdict::RejectGuestFormat};
    Format view_format{Format::Unknown};
    bool permitted{};
};
constexpr bool IsBc(Format f) {
    return f==Format::Bc1RgbUnorm||f==Format::Bc1RgbSrgb||
        f==Format::Bc1RgbaUnorm||f==Format::Bc1RgbaSrgb||
        f==Format::Bc3Unorm||f==Format::Bc3Srgb;
}
constexpr bool IsSrgb(Format f) {
    return f==Format::Bc1RgbSrgb||f==Format::Bc1RgbaSrgb||
        f==Format::Bc3Srgb||f==Format::Rgba8Srgb;
}
constexpr bool IsRgba(Format f) {
    return f==Format::Rgba8Unorm||f==Format::Rgba8Srgb;
}
constexpr Format DesiredRgba(Format guest) {
    return IsSrgb(guest)?Format::Rgba8Srgb:Format::Rgba8Unorm;
}
constexpr bool HasRange(uint32_t base,uint32_t count,uint32_t available) {
    return count!=0&&available!=0&&base<available&&count<=available-base;
}
constexpr uint32_t MipDim(uint32_t base,uint32_t mip) {
    return mip>=32?1U:((base>>mip)?(base>>mip):1U);
}
constexpr Result Reject(Verdict why) { return {why, Format::Unknown, false}; }

constexpr Result Resolve(const Request& r) {
    if(!IsBc(r.guest)) return Reject(Verdict::RejectGuestFormat);
    if(!r.sampled||r.storage||r.depth||!r.color_aspect)
        return Reject(Verdict::RejectStorageOrDepth);
    if(!r.width||!r.height||r.samples!=1)
        return Reject(Verdict::RejectExtentOrSamples);
    if(!HasRange(r.base_mip,r.mip_count,r.allocated_mips)||
       !HasRange(r.base_layer,r.layer_count,r.allocated_layers))
        return Reject(Verdict::RejectMipLayerRange);
    if(!r.sampled_feature||!r.view_format_feature)
        return Reject(Verdict::RejectFormatFeatures);
    if(r.allocated_backing==r.guest) {
        // Native BCn views require *no* fallback proof. Never reinterpret native
        // compressed images as RGBA or mixed sRGB/UNORM views implicitly.
        return {Verdict::NativeCompressedView,r.guest,true};
    }
    if(!IsRgba(r.allocated_backing)) return Reject(Verdict::RejectBackingFormat);
    const Format desired=DesiredRgba(r.guest);
    if(r.allocated_backing!=desired) {
        // sRGB reinterpretation requires both mutable image format and a
        // compatibility proof from the actual Vulkan device/format-list.
        if(!r.mutable_format||!r.compatible_mutation)
            return Reject(Verdict::RejectMutableFormat);
    }
    if(r.generation==0||!r.uploads||r.upload_count==0)
        return Reject(Verdict::RejectMissingUpload);
    const uint64_t required=uint64_t(r.mip_count)*r.layer_count;
    if(required>std::numeric_limits<size_t>::max()||required>r.upload_count)
        return Reject(Verdict::RejectMissingUpload);
    if(r.current_content_epoch==0) return Reject(Verdict::RejectDirtyAfterUpload);
    // Every requested (layer,mip) is independently attested; duplicate, stale
    // or incomplete uploads never stand in for a missing subresource.
    for(uint32_t layer=0;layer<r.layer_count;++layer) {
        for(uint32_t mip=0;mip<r.mip_count;++mip) {
            const uint32_t abs_layer=r.base_layer+layer;
            const uint32_t abs_mip=r.base_mip+mip;
            size_t matches=0;
            for(size_t i=0;i<r.upload_count;++i) {
                const auto& p=r.uploads[i];
                if(p.mip!=abs_mip||p.layer!=abs_layer)continue;
                ++matches;
                if(p.generation!=r.generation||p.completion_generation!=r.generation||
                   !p.gpu_fence_completed||!p.gpu_copy_submitted)
                    return Reject(Verdict::RejectStaleUpload);
                if(p.content_epoch!=r.current_content_epoch)
                    return Reject(Verdict::RejectDirtyAfterUpload);
                if(!p.decoder_succeeded||!p.guest_layout_verified||
                   !p.color_aspect_verified||p.decoded_format!=desired||
                   p.width!=MipDim(r.width,abs_mip)||
                   p.height!=MipDim(r.height,abs_mip))
                    return Reject(Verdict::RejectMissingUpload);
            }
            if(matches!=1) return Reject(Verdict::RejectMissingUpload);
        }
    }
    return {Verdict::VerifiedDecodedRgbaView,desired,true};
}
} // namespace BachataP44