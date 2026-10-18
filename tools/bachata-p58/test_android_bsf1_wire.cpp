// SPDX-License-Identifier: GPL-2.0-or-later
// P58: mock actual Android DataInputStream BE16/BE32 request contract.
#include "platform/bachata/p54_bsf1_eboot.h"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <thread>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <fcntl.h>

namespace fs=std::filesystem;
using Bachata::Saf::BSF1::Client;
using Bachata::Saf::BSF1::Config;
using Bachata::Saf::P54::Outcome;
using Bachata::Saf::P54::TryOpenInitialEboot;

static bool ReadExactly(int fd, void* target, size_t count) {
    auto* out=static_cast<unsigned char*>(target);
    while(count) {
        const auto n=::recv(fd,out,count,0);
        if(n<=0)return false;
        out+=n;
        count-=static_cast<size_t>(n);
    }
    return true;
}

static void VerifyAndroidWireAndFd(const fs::path& root) {
    std::string socket_name="p58_bsf1_test_"+std::to_string(::getpid());
    const std::string expected_token(32,'a');
    int listener=::socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);
    assert(listener>=0);
    sockaddr_un address{};
    address.sun_family=AF_UNIX;
    std::memcpy(address.sun_path+1,socket_name.data(),socket_name.size());
    const socklen_t len=static_cast<socklen_t>(
        offsetof(sockaddr_un,sun_path)+1+socket_name.size());
    assert(::bind(listener,reinterpret_cast<sockaddr*>(&address),len)==0);
    assert(::listen(listener,1)==0);

    bool valid_contract=false;
    std::thread server([&]{
        int sock=::accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);
        assert(sock>=0);
        // P42 Android DataInputStream.readInt(), readUnsignedByte() x2,
        // readUnsignedShort(), readInt(), readFully(token), readFully(path).
        std::array<unsigned char,12> header{};
        assert(ReadExactly(sock,header.data(),header.size()));
        const std::array<unsigned char,12> expected_header{
            0x42,0x53,0x46,0x31,0x01,0x03,0x00,0x20,0x00,0x00,0x00,0x09};
        valid_contract=(header==expected_header);
        if(valid_contract) {
            std::array<char,41> bytes{};
            valid_contract=ReadExactly(sock,bytes.data(),bytes.size());
            valid_contract=valid_contract &&
                std::memcmp(bytes.data(),expected_token.data(),32)==0 &&
                std::memcmp(bytes.data()+32,"eboot.bin",9)==0;
        }
        if(valid_contract) {
            int file=::open((root/"synthetic-eboot.bin").c_str(),O_RDONLY|O_CLOEXEC);
            assert(file>=0);
            std::array<unsigned char,10> response{'B','S','F','1',1,0,0,0,0,0};
            std::array<char,CMSG_SPACE(sizeof(int))> ancillary{};
            iovec iov{response.data(),response.size()};
            msghdr msg{};
            msg.msg_iov=&iov;msg.msg_iovlen=1;
            msg.msg_control=ancillary.data();msg.msg_controllen=ancillary.size();
            cmsghdr* c=CMSG_FIRSTHDR(&msg);
            assert(c!=nullptr);
            c->cmsg_level=SOL_SOCKET;c->cmsg_type=SCM_RIGHTS;
            c->cmsg_len=CMSG_LEN(sizeof(int));
            std::memcpy(CMSG_DATA(c),&file,sizeof(int));
            assert(::sendmsg(sock,&msg,MSG_NOSIGNAL)==static_cast<ssize_t>(response.size()));
            ::close(file);
        }
        ::close(sock);
        ::close(listener);
    });
    Config config{socket_name,expected_token,2000};
    auto result=TryOpenInitialEboot(Client(config),"eboot.bin",std::optional<fs::path>(root));
    server.join();
    assert(valid_contract);
    assert(result.outcome==Outcome::EbootFdReady);
    assert(result.fd.get()>=0);
    std::ifstream test(result.proc_fd_path,std::ios::binary);
    char bytes[8]{};
    test.read(bytes,sizeof(bytes));
    assert(std::memcmp(bytes,"ELF-FAKE",8)==0);
}

int main() {
    const auto root=fs::temp_directory_path()/("p58-bsf1-golden-"+std::to_string(::getpid()));
    fs::create_directories(root);
    {std::ofstream f(root/"synthetic-eboot.bin",std::ios::binary);
     f<<"ELF-FAKE-TEST-ONLY-NOT-A-REAL-GAME";}
    VerifyAndroidWireAndFd(root);
    fs::remove_all(root);
}
