#include "p44_bcn_imageview_contract.hpp"
#include <array>
#include <cassert>
#include <iostream>
using namespace BachataP44;
static Request Good(Format g,Format backing,CompletedUpload* ups,size_t n){
  return {.guest=g,.allocated_backing=backing,.sampled=true,.storage=false,.depth=false,
  .color_aspect=true,.sampled_feature=true,.view_format_feature=true,
  .width=8,.height=8,.allocated_mips=2,.allocated_layers=2,.samples=1,
  .base_mip=0,.mip_count=2,.base_layer=0,.layer_count=2,
  .generation=5,.current_content_epoch=90,.uploads=ups,.upload_count=n};
}
static std::array<CompletedUpload,4> Full(Format f){
 std::array<CompletedUpload,4> a{};
 for(unsigned l=0;l<2;++l)for(unsigned m=0;m<2;++m){
 auto& p=a[l*2+m];p.mip=m;p.layer=l;p.width=8>>m;p.height=8>>m;
 p.generation=5;p.completion_generation=5;p.content_epoch=90;p.decoded_format=f;
 p.decoder_succeeded=p.guest_layout_verified=p.gpu_copy_submitted=
 p.gpu_fence_completed=p.color_aspect_verified=true;
 }
 return a;
}
int main(){
 size_t passed=0;
 const std::array<Format,6> bc={Format::Bc1RgbUnorm,Format::Bc1RgbSrgb,
 Format::Bc1RgbaUnorm,Format::Bc1RgbaSrgb,Format::Bc3Unorm,Format::Bc3Srgb};
 for(auto f:bc){auto up=Full(DesiredRgba(f));auto req=Good(f,DesiredRgba(f),up.data(),up.size());
 auto ok=Resolve(req);assert(ok.permitted&&ok.verdict==Verdict::VerifiedDecodedRgbaView&&ok.view_format==DesiredRgba(f));++passed;
 req.guest_is_tiled=true;assert(Resolve(req).permitted);++passed;req.guest_is_tiled=false;
 req.storage=true;assert(!Resolve(req).permitted);++passed;req.storage=false;
 req.depth=true;assert(!Resolve(req).permitted);++passed;req.depth=false;
 req.sampled_feature=false;assert(!Resolve(req).permitted);++passed;req.sampled_feature=true;
 req.view_format_feature=false;assert(!Resolve(req).permitted);++passed;req.view_format_feature=true;
 req.samples=4;assert(!Resolve(req).permitted);++passed;req.samples=1;
 req.base_mip=2;assert(!Resolve(req).permitted);++passed;req.base_mip=0;
 req.base_layer=2;assert(!Resolve(req).permitted);++passed;req.base_layer=0;
 req.mip_count=3;assert(!Resolve(req).permitted);++passed;req.mip_count=2;
 req.upload_count=3;assert(!Resolve(req).permitted);++passed;req.upload_count=4;
 req.current_content_epoch=91;assert(!Resolve(req).permitted);++passed;req.current_content_epoch=90;
 req.generation=6;assert(!Resolve(req).permitted);++passed;req.generation=5;
 up[0].gpu_fence_completed=false;assert(!Resolve(req).permitted);++passed;up[0].gpu_fence_completed=true;
 up[0].decoder_succeeded=false;assert(!Resolve(req).permitted);++passed;up[0].decoder_succeeded=true;
 up[0].width=9;assert(!Resolve(req).permitted);++passed;up[0].width=8;
 up[0].decoded_format=IsSrgb(f)?Format::Rgba8Unorm:Format::Rgba8Srgb;
 assert(!Resolve(req).permitted);++passed;up[0].decoded_format=DesiredRgba(f);
 up[0].content_epoch=89;assert(!Resolve(req).permitted);++passed;up[0].content_epoch=90;
 auto dup=up;dup[3]=dup[0];req.uploads=dup.data();assert(!Resolve(req).permitted);++passed;req.uploads=up.data();
 req.uploads=nullptr;assert(!Resolve(req).permitted);++passed;req.uploads=up.data();
 req.allocated_backing=f;auto native=Resolve(req);assert(native.permitted&&native.verdict==Verdict::NativeCompressedView);++passed;
 req.allocated_backing=IsSrgb(f)?Format::Rgba8Unorm:Format::Rgba8Srgb;
 assert(!Resolve(req).permitted);++passed;req.mutable_format=true;req.compatible_mutation=true;
 assert(Resolve(req).permitted);++passed;
 }
 std::cout<<"P44_BCN_VIEW_CONTRACT_PASS checks="<<passed<<"\n";
}