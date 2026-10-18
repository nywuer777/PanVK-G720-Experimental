// SPDX-License-Identifier: GPL-2.0-or-later
// P59 synthetic broker-FD private-stage tests; no user game content.
#include "platform/bachata/p59_private_stage.h"
#include <cassert>
#include <array>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>

namespace fs=std::filesystem;
using Bachata::Saf::P59::StageAuthenticatedFd;
using Bachata::Saf::P59::Status;

static void create_test_data(const fs::path& path) {
    int out=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC,0600);
    assert(out>=0);
    constexpr char begin[]="PS4-SELF-FIXTURE-NOT-A-REAL-EXECUTABLE";
    assert(::write(out,begin,sizeof(begin))==sizeof(begin));
    std::array<unsigned char,16384> sequence{};
    for(std::size_t i=0;i<sequence.size();++i)sequence[i]=static_cast<unsigned char>((i*13)&255);
    for(int i=0;i<32;++i)assert(::write(out,sequence.data(),sequence.size())==
                                          static_cast<ssize_t>(sequence.size()));
    assert(::close(out)==0);
}

int main() {
    const auto base=fs::temp_directory_path()/("p59-test-"+std::to_string(::getpid()));
    fs::create_directories(base);
    fs::permissions(base,fs::perms::owner_all);
    const auto fixture=base/"original.fd";
    create_test_data(fixture);
    int input=::open(fixture.c_str(),O_RDONLY|O_CLOEXEC);
    assert(input>=0);
    {
        auto copy=StageAuthenticatedFd(input,base);
        assert(copy.status==Status::Staged);
        assert(copy.path.parent_path()==base);
        assert(copy.path.filename().string().starts_with(".p59-eboot-"));
        assert(fs::exists(copy.path));
        struct stat stat_out{};
        assert(::stat(copy.path.c_str(),&stat_out)==0);
        assert(S_ISREG(stat_out.st_mode) && (stat_out.st_mode & 0777)==0600);
        assert(fs::file_size(copy.path)==fs::file_size(fixture));
        std::ifstream original(fixture,std::ios::binary);
        std::ifstream staged(copy.path,std::ios::binary);
        assert(std::equal(std::istreambuf_iterator<char>(original),
                          std::istreambuf_iterator<char>(),
                          std::istreambuf_iterator<char>(staged)));
        auto moved=std::move(copy);
        assert(!copy);
        assert(moved);
    }
    assert(fs::directory_iterator(base)!=fs::directory_iterator{}); // fixture remains
    {
        std::size_t leftovers=0;
        for(auto& e:fs::directory_iterator(base))
            if(e.path().filename().string().starts_with(".p59-eboot-"))++leftovers;
        assert(leftovers==0);
    }
    assert(StageAuthenticatedFd(-1,base).status==Status::InvalidSource);
    {
        const auto symlink=base.parent_path()/("p59-test-symlink-"+std::to_string(::getpid()));
        fs::create_directory_symlink(base,symlink);
        assert(StageAuthenticatedFd(input,symlink).status==Status::UnsafeRoot);
        fs::remove(symlink);
    }
    {
        const auto dir=base/"untrusted";
        fs::create_directory(dir);
        fs::permissions(dir,fs::perms::owner_all|fs::perms::group_write);
        assert(StageAuthenticatedFd(input,dir).status==Status::UnsafeRoot);
        fs::remove(dir);
    }
    {
        const auto empty=base/"empty.fd";
        std::ofstream f(empty);f.close();
        int fd=::open(empty.c_str(),O_RDONLY|O_CLOEXEC);
        assert(fd>=0);
        assert(StageAuthenticatedFd(fd,base).status==Status::EmptySource);
        ::close(fd);fs::remove(empty);
    }
    {
        const auto huge=base/"oversized.fd";
        int fd=::open(huge.c_str(),O_RDWR|O_CREAT|O_EXCL|O_CLOEXEC,0600);
        assert(fd>=0);
        assert(::ftruncate(fd,static_cast<off_t>(Bachata::Saf::P59::kMaxExecutableBytes+1))==0);
        assert(StageAuthenticatedFd(fd,base).status==Status::TooLarge);
        ::close(fd);fs::remove(huge);
    }
#ifdef O_PATH
    {
        int fd=::open(fixture.c_str(),O_PATH|O_CLOEXEC);
        assert(fd>=0);
        assert(StageAuthenticatedFd(fd,base).status==Status::ReadFailed);
        ::close(fd);
    }
#endif
    assert(::fcntl(input,F_GETFD)!=-1); // borrowed fd still owned by caller
    ::close(input);
    fs::remove_all(base);
}
