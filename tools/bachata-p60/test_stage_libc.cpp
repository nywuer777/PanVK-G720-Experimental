// SPDX-License-Identifier: GPL-2.0-or-later
// Direct private staging regression: not a real game PRX, no private payload.
#include "platform/bachata/p60_saf_libc_stage.h"
#include <cassert>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <iterator>
#include <string>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
namespace fs = std::filesystem;
using Bachata::Saf::P60::StageAuthorizedLibc;
using Bachata::Saf::P60::Status;

static fs::path MakePrivateRoot() {
    const auto root = fs::temp_directory_path() /
       ("p60-private-" + std::to_string(::getpid()));
    assert(fs::create_directory(root));
    fs::permissions(root, fs::perms::owner_all);
    return root;
}
static void MakeFixture(const fs::path& p, unsigned count) {
    std::ofstream f(p, std::ios::binary);
    for(unsigned i=0;i<count;++i) f.put(static_cast<char>((i*19U)&255));
    f.close();
}
int main() {
    const auto root=MakePrivateRoot();
    const auto original=root/"synthetic-original.bin";
    MakeFixture(original,8192);
    int input=::open(original.c_str(),O_RDONLY|O_CLOEXEC);
    assert(input>=0);
    {
        auto stage=StageAuthorizedLibc(input,root);
        assert(stage.status==Status::Ready && stage);
        assert(stage.path==root/"sce_module"/"libc.prx");
        struct stat st{};
        assert(::stat(stage.path.c_str(),&st)==0);
        assert(S_ISREG(st.st_mode) && (st.st_mode&0777)==0600);
        assert(st.st_uid==::geteuid());
        assert(fs::file_size(stage.path)==8192);
        std::ifstream lhs(original,std::ios::binary),rhs(stage.path,std::ios::binary);
        assert(std::equal(std::istreambuf_iterator<char>(lhs),
                          std::istreambuf_iterator<char>(),
                          std::istreambuf_iterator<char>(rhs)));
        // A second stage must fail closed, never replace an existing library.
        assert(StageAuthorizedLibc(input,root).status==Status::ExistingFile);
        auto moved=std::move(stage);
        assert(!stage && moved);
    }
    assert(!fs::exists(root/"sce_module"/"libc.prx"));
    assert(!fs::exists(root/"sce_module"));

    {
        const auto external=root.parent_path()/
               ("p60-external-"+std::to_string(::getpid()));
        assert(fs::create_directory(external));
        const auto link=root/"sce_module";
        fs::create_directory_symlink(external,link);
        assert(StageAuthorizedLibc(input,root).status==Status::UnsafeDirectory);
        fs::remove(link);
        fs::remove(external);
    }
    {
        fs::create_directory(root/"sce_module");
        fs::permissions(root/"sce_module",
            fs::perms::owner_all | fs::perms::group_write);
        assert(StageAuthorizedLibc(input,root).status==Status::UnsafeDirectory);
        fs::remove(root/"sce_module");
    }
    {
        const auto existing=root/"sce_module";
        fs::create_directory(existing);
        MakeFixture(existing/"libc.prx",4096);
        assert(StageAuthorizedLibc(input,root).status==Status::ExistingFile);
        assert(fs::file_size(existing/"libc.prx")==4096); // no overwrite
        fs::remove_all(existing);
    }
    assert(StageAuthorizedLibc(-1,root).status==Status::InvalidFd);
    {
        const auto zero=root/"empty";
        MakeFixture(zero,0);
        int fd=::open(zero.c_str(),O_RDONLY|O_CLOEXEC);
        assert(fd>=0);
        assert(StageAuthorizedLibc(fd,root).status==Status::EmptyFile);
        ::close(fd);fs::remove(zero);
        assert(!fs::exists(root/"sce_module"));
    }
    {
        const auto huge=root/"huge";
        int fd=::open(huge.c_str(),O_RDWR|O_CREAT|O_EXCL|O_CLOEXEC,0600);
        assert(fd>=0);
        assert(::ftruncate(fd, static_cast<off_t>(Bachata::Saf::P60::kMaxModuleSize+1))==0);
        assert(StageAuthorizedLibc(fd,root).status==Status::TooLarge);
        ::close(fd);fs::remove(huge);
    }
    {
        const auto insecure=root/"insecure";
        fs::create_directory(insecure);
        fs::permissions(insecure,fs::perms::owner_all | fs::perms::others_write);
        assert(StageAuthorizedLibc(input,insecure).status==Status::UnsafeRoot);
        fs::remove(insecure);
    }
#ifdef O_PATH
    {
        int fd=::open(original.c_str(),O_PATH|O_CLOEXEC);
        assert(fd>=0);
        assert(StageAuthorizedLibc(fd,root).status==Status::ReadFailed);
        ::close(fd);
        assert(!fs::exists(root/"sce_module"));
    }
#endif
    // The borrowed read-only descriptor remains alive after stage cleanup.
    assert(::fcntl(input,F_GETFD)>=0);
    ::close(input);
    fs::remove_all(root);
}
