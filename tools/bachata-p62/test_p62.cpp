// SPDX-License-Identifier: GPL-2.0-or-later
// P62 real-format PSF negative/positive safety checks (no copyrighted game bytes).
#include "platform/bachata/p61_saf_psf_stage.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <algorithm>
#include <unistd.h>
#include <fcntl.h>
using namespace Bachata::Saf::P61;
namespace fs=std::filesystem;
static void put16(std::vector<unsigned char>& b,size_t p,unsigned v) {b[p]=v&255;b[p+1]=(v>>8)&255;}
static void put32(std::vector<unsigned char>& b,size_t p,unsigned v) {for(int j=0;j<4;++j)b[p+j]=(v>>(j*8))&255;}
// PSF 1.1, TITLE_ID text padded to max 12, FORMAT integer.
static std::vector<unsigned char> fixture(bool padded) {
    const unsigned keys=52,data=72;
    std::vector<unsigned char> b(data+16,0);
    b[0]=0;b[1]='P';b[2]='S';b[3]='F';put32(b,4,0x101);
    put32(b,8,keys);put32(b,12,data);put32(b,16,2);
    // PSFRawEntry declares u16_be param_fmt, unlike u16_le key_offset.
    put16(b,20,0);b[22]=2;b[23]=4;put32(b,24,padded?12:10);
    put32(b,28,12);put32(b,32,0);
    put16(b,36,9);b[38]=4;b[39]=4;put32(b,40,4);put32(b,44,4);put32(b,48,12);
    std::copy_n("TITLE_ID",9,b.begin()+keys);
    std::copy_n("FORMAT",7,b.begin()+keys+9);
    std::copy_n("CUSA00325",10,b.begin()+data);
    return b;
}
static void stage_ok(const std::vector<unsigned char>& b) {
    const auto folder=fs::temp_directory_path()/("p62-stage-"+std::to_string(getpid()));
    fs::create_directory(folder);fs::permissions(folder,fs::perms::owner_all);
    const auto file=folder/"source.sfo";
    {std::ofstream f(file,std::ios::binary);f.write((const char*)b.data(),b.size());}
    int fd=::open(file.c_str(),O_RDONLY|O_CLOEXEC);assert(fd>=0);
    {
        auto stage=StageAuthorizedPsf(fd,folder,"CUSA00325");
        assert(stage.status==Status::Ready);
        assert(fs::file_size(stage.path)==b.size());
    }
    assert(!fs::exists(folder/"sce_sys"));
    assert(::fcntl(fd,F_GETFD)>=0);::close(fd);fs::remove_all(folder);
}
int main() {
    auto b=fixture(false);
    assert(ValidatePsf(b,"CUSA00325")==Status::Ready);
    stage_ok(b);
    b=fixture(true);
    assert(ValidatePsf(b,"CUSA00325")==Status::Ready);
    stage_ok(b);
    assert(ValidatePsf(b,"CUSA00326")==Status::TitleIdMismatch);
    assert(ValidatePsf(b,"INVALID")==Status::InvalidTitleIdFormat);
    b[0]=1;assert(ValidatePsf(b,"CUSA00325")==Status::InvalidPsfMagic);
    b=fixture(true);b[4]=9;assert(ValidatePsf(b,"CUSA00325")==Status::UnsupportedPsfVersion);
    b=fixture(true);put32(b,12,999999);assert(ValidatePsf(b,"CUSA00325")==Status::InvalidPsfLayout);
    b=fixture(true);put32(b,24,1000);assert(ValidatePsf(b,"CUSA00325")==Status::InvalidPsfEntryBounds);
    b=fixture(true);b[52]='Z';assert(ValidatePsf(b,"CUSA00325")==Status::MissingTitleId);
    b=fixture(true);b[22]=4;b[23]=2;assert(ValidatePsf(b,"CUSA00325")==Status::InvalidPsfFormat);
    b=fixture(true);b[72+9]='X';b[72+10]='X';b[72+11]='X';
    assert(ValidatePsf(b,"CUSA00325")==Status::InvalidPsfText);
    b=fixture(true);b[36]=0;b[37]=0;
    assert(ValidatePsf(b,"CUSA00325")==Status::DuplicateTitleId);
    b=fixture(true);b[22]=0;b[23]=4;
    assert(ValidatePsf(b,"CUSA00325")==Status::InvalidTitleIdFormat);
    b=fixture(true);b[52]=0;
    assert(ValidatePsf(b,"CUSA00325")==Status::InvalidPsfKey);
}
