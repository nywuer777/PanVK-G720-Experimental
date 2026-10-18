// SPDX-License-Identifier: GPL-2.0-or-later
#include "platform/bachata/p61_saf_psf_stage.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>
#include <fcntl.h>
#include <unistd.h>
namespace fs=std::filesystem;
using Bachata::Saf::P61::StageAuthorizedPsf;
using Bachata::Saf::P61::Status;
static void Put32(std::vector<unsigned char>& b,std::size_t off,std::uint32_t v) {
    for(int i=0;i<4;++i)b[off+i]=static_cast<unsigned char>(v>>(8*i));
}
static std::vector<unsigned char> Psf(const std::string& id="CUSA00325") {
    std::vector<unsigned char>b(36+9+id.size()+1,0);
    b[1]='P';b[2]='S';b[3]='F';Put32(b,4,0x101);
    Put32(b,8,36);Put32(b,12,45);Put32(b,16,1);
    b[22]=2;b[23]=4;Put32(b,24,static_cast<unsigned>(id.size()+1));
    Put32(b,28,static_cast<unsigned>(id.size()+1));
    const char key[]="TITLE_ID";
    std::copy(key,key+9,b.begin()+36);
    std::copy(id.begin(),id.end(),b.begin()+45);
    return b;
}
static int File(const fs::path& p,const std::vector<unsigned char>& bytes) {
    std::ofstream f(p,std::ios::binary);
    f.write(reinterpret_cast<const char*>(bytes.data()),bytes.size());
    f.close();
    return ::open(p.c_str(),O_RDONLY|O_CLOEXEC);
}
int main() {
    const auto root=fs::temp_directory_path()/ ("p61-private-"+std::to_string(::getpid()));
    assert(fs::create_directory(root));fs::permissions(root,fs::perms::owner_all);
    const auto fixture=root/"source.bin";
    int fd=File(fixture,Psf());assert(fd>=0);
    {
        auto stage=StageAuthorizedPsf(fd,root,"CUSA00325");
        assert(stage.status==Status::Ready && stage);
        assert(fs::file_size(stage.path)==Psf().size());
        assert(StageAuthorizedPsf(fd,root,"CUSA00325").status==Status::ExistingFile);
        auto moved=std::move(stage);assert(moved && !stage);
    }
    assert(!fs::exists(root/"sce_sys"));
    assert(::fcntl(fd,F_GETFD)>=0);::close(fd);
    auto check=[&](std::vector<unsigned char> bytes,Status expected,std::string id="CUSA00325"){
        int f=File(fixture,bytes);assert(f>=0);
        assert(StageAuthorizedPsf(f,root,id).status==expected);
        ::close(f);assert(!fs::exists(root/"sce_sys"));
    };
    check(Psf("CUSA12345"),Status::TitleIdMismatch);
    check(Psf(),Status::InvalidPsf,"CUSA-NOTVALID");
    auto malformed=Psf();malformed[1]='Q';check(malformed,Status::InvalidPsf);
    malformed=Psf();Put32(malformed,12,999999);check(malformed,Status::InvalidPsf);
    malformed=Psf();Put32(malformed,24,5000);check(malformed,Status::InvalidPsf);
    malformed=Psf();malformed[36]='Z';check(malformed,Status::MissingTitleId);
    malformed=Psf();malformed.back()='X';check(malformed,Status::InvalidPsf);
    check({},Status::InvalidPsf);
    check(std::vector<unsigned char>(Bachata::Saf::P61::kMaxPsfSize+1),Status::TooLarge);
    {
        const auto external=root.parent_path()/("p61-external-"+std::to_string(::getpid()));
        assert(fs::create_directory(external));
        fs::create_directory_symlink(external,root/"sce_sys");
        int f=File(fixture,Psf());assert(f>=0);
        assert(StageAuthorizedPsf(f,root,"CUSA00325").status==Status::UnsafeDirectory);
        ::close(f);fs::remove(root/"sce_sys");fs::remove(external);
    }
    {
        fs::create_directory(root/"sce_sys");
        fs::permissions(root/"sce_sys",fs::perms::owner_all|fs::perms::group_write);
        int f=File(fixture,Psf());assert(f>=0);
        assert(StageAuthorizedPsf(f,root,"CUSA00325").status==Status::UnsafeDirectory);
        ::close(f);fs::remove(root/"sce_sys");
    }
    {
        fs::create_directory(root/"sce_sys");
        {std::ofstream f(root/"sce_sys"/"param.sfo");f<<"original";}
        int f=File(fixture,Psf());assert(f>=0);
        assert(StageAuthorizedPsf(f,root,"CUSA00325").status==Status::ExistingFile);
        assert(fs::file_size(root/"sce_sys"/"param.sfo")==8);
        ::close(f);fs::remove_all(root/"sce_sys");
    }
    assert(StageAuthorizedPsf(-1,root,"CUSA00325").status==Status::InvalidFd);
    fs::remove_all(root);
}
