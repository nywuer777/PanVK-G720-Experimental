// SPDX-License-Identifier: GPL-2.0-or-later
// P63: ensure unknown PSF format telemetry is numeric, bounded and fail-closed.
#include "platform/bachata/p61_saf_psf_stage.h"
#include <array>
#include <cassert>
#include <filesystem>
#include <fstream>
#include <utility>
#include <fcntl.h>
#include <unistd.h>
namespace fs=std::filesystem;
using namespace Bachata::Saf::P61;
static std::array<unsigned char,58> Fixture(unsigned hi,unsigned lo) {
    std::array<unsigned char,58> b{};
    b[1]='P';b[2]='S';b[3]='F';b[4]=1;b[5]=1;b[8]=36;b[12]=45;b[16]=1;
    b[22]=hi;b[23]=lo;b[24]=10;b[28]=10;
    for(std::size_t i=0;i<9;++i)b[36+i]="TITLE_ID"[i];
    for(std::size_t i=0;i<10;++i)b[45+i]="CUSA00325"[i];
    return b;
}
int main() {
    auto unknown=Fixture(0x12,0x34);FormatEvidence observed{};
    assert(ValidatePsf(unknown,"CUSA00325",&observed)==Status::InvalidPsfFormat);
    assert(observed.available && observed.entry_index==0 && observed.raw_format==0x1234);
    auto accepted=Fixture(2,4);observed={};
    assert(ValidatePsf(accepted,"CUSA00325",&observed)==Status::Ready && !observed.available);
    const auto folder=fs::temp_directory_path()/("p63-forensics-"+std::to_string(getpid()));
    assert(fs::create_directory(folder));fs::permissions(folder,fs::perms::owner_all);
    const auto file=folder/"original.sfo";
    {std::ofstream f(file,std::ios::binary);
     f.write(reinterpret_cast<const char*>(unknown.data()),unknown.size());}
    const int fd=::open(file.c_str(),O_RDONLY|O_CLOEXEC);assert(fd>=0);
    {
        auto failed=StageAuthorizedPsf(fd,folder,"CUSA00325");
        assert(failed.status==Status::InvalidPsfFormat);
        assert(failed.format_evidence.available);
        assert(failed.format_evidence.entry_index==0 && failed.format_evidence.raw_format==0x1234);
        auto moved=std::move(failed);
        assert(moved.format_evidence.available && !failed.format_evidence.available);
    }
    assert(!fs::exists(folder/"sce_sys") && ::fcntl(fd,F_GETFD)>=0);
    ::close(fd);fs::remove_all(folder);
}
