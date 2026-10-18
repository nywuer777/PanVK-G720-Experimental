#include "p44_bcn_imageview_contract.hpp"
#include <array>
#include <cstdlib>
#include <iostream>
#include <vector>

using namespace BachataP44;
static unsigned checks = 0;
static void Check(bool condition, const char* name) {
    if (!condition) { std::cerr << "P46_FAILED " << name << '\n'; std::exit(2); }
    ++checks;
}
static std::array<CompletedUpload, 11> MakeUploads() {
    std::array<CompletedUpload, 11> result{};
    for (unsigned mip = 0; mip < result.size(); ++mip) {
        auto& p = result[mip];
        p.mip = mip; p.layer = 0;
        p.width = MipDim(1024,mip); p.height = MipDim(1024,mip);
        p.generation = 34; p.completion_generation = 34; p.content_epoch = 7;
        p.decoded_format = Format::Rgba8Srgb;
        p.decoder_succeeded = p.guest_layout_verified = p.gpu_copy_submitted =
            p.gpu_fence_completed = p.color_aspect_verified = true;
    }
    return result;
}
static Request MakeRequest(std::array<CompletedUpload, 11>& records) {
    Request r{};
    r.guest = Format::Bc3Srgb;
    r.allocated_backing = Format::Rgba8Srgb;
    r.sampled = true; r.storage = false; r.depth = false; r.color_aspect = true;
    r.sampled_feature = true; r.view_format_feature = true;
    r.width = 1024; r.height = 1024; r.allocated_mips = 11;
    r.allocated_layers = 1; r.samples = 1;
    r.base_mip = 0; r.mip_count = 11; r.base_layer = 0; r.layer_count = 1;
    r.generation = 34; r.current_content_epoch = 7;
    r.uploads = records.data(); r.upload_count = records.size();
    return r;
}
int main() {
    auto p = MakeUploads();
    auto r = MakeRequest(p);
    Check(Resolve(r).permitted && Resolve(r).view_format == Format::Rgba8Srgb,
          "valid_bc3_srgb_1024_11_mips");
    r.guest_is_tiled = true; Check(Resolve(r).permitted, "tiled_layout_verified");
    r.guest_is_tiled = false;
    r.upload_count = 10; Check(!Resolve(r).permitted,"missing_last_mip"); r.upload_count = 11;
    p[10].gpu_fence_completed = false;
    Check(!Resolve(r).permitted,"last_mip_fence_not_completed"); p[10].gpu_fence_completed = true;
    p[9].completion_generation = 33;
    Check(!Resolve(r).permitted,"stale_gpu_completion_generation"); p[9].completion_generation = 34;
    p[0].decoded_format = Format::Rgba8Unorm;
    Check(!Resolve(r).permitted,"wrong_srgb_decode_format"); p[0].decoded_format = Format::Rgba8Srgb;
    p[5].width = 1; Check(!Resolve(r).permitted,"mipmap_dimension_mismatch"); p[5].width = 32;
    r.current_content_epoch = 8; Check(!Resolve(r).permitted,"gpu_written_after_upload"); r.current_content_epoch = 7;
    r.storage = true; Check(!Resolve(r).permitted,"storage_view_not_allowed"); r.storage = false;
    r.view_format_feature = false; Check(!Resolve(r).permitted,"sampled_view_feature_missing"); r.view_format_feature = true;
    r.allocated_backing = Format::Rgba8Unorm;
    Check(!Resolve(r).permitted,"srgb_unorm_reinterpret_without_mutation_proof");
    r.allocated_backing = Format::Rgba8Srgb;
    r.allocated_layers = 2; r.layer_count = 2;
    Check(!Resolve(r).permitted,"second_layer_unproven"); r.allocated_layers = 1; r.layer_count = 1;
    auto dup = p; dup[10] = dup[9]; r.uploads = dup.data();
    Check(!Resolve(r).permitted,"duplicate_mip_and_missing_last_mip"); r.uploads = p.data();
    Check(Resolve(r).permitted,"recovered_evidence_approved");
    std::cout << "P46_OUTLAST_BC3_1024x1024_11MIPS_CONTRACT_PASS checks=" << checks << '\n';
}