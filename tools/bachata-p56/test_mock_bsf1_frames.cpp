// SPDX-License-Identifier: GPL-2.0-or-later
// Mock BSF1 server: no Android broker or real game data.
#include "platform/bachata/p54_bsf1_eboot.h"
#include <array>
#include <cassert>
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

struct Scenario {
    const char* name;
    Outcome expected;
    std::array<unsigned char,10> header;
    int length;
    bool file_descriptor;
    bool duplicate_descriptor;
};

static void Test(const Scenario& test, int index, const fs::path& root) {
    std::string label="p56_bsf1_"+std::to_string(::getpid())+"_"+std::to_string(index);
    int listener=::socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);
    assert(listener>=0);
    sockaddr_un sa{};
    sa.sun_family=AF_UNIX;
    std::memcpy(sa.sun_path+1,label.data(),label.size());
    socklen_t len=offsetof(sockaddr_un,sun_path)+1+label.size();
    assert(::bind(listener,reinterpret_cast<sockaddr*>(&sa),len)==0);
    assert(::listen(listener,1)==0);

    std::thread server([&] {
        int client=::accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);
        assert(client>=0);
        // Request = 4 magic + 1 version + 1 opcode + 4 token-length
        // + 32 token + 4 path-length + 9 "eboot.bin" = 55 bytes.
        std::array<unsigned char,55> request{};
        size_t have=0;
        while(have<request.size()) {
            auto n=::recv(client,request.data()+have,request.size()-have,0);
            assert(n>0);have+=static_cast<size_t>(n);
        }
        assert(std::memcmp(request.data(),"BSF1",4)==0);
        assert(request[4]==1 && request[5]==3);
        assert(std::memcmp(request.data()+46,"eboot.bin",9)==0);
        if(test.length>0) {
            if(!test.file_descriptor) {
                // Sendall required to avoid short writes in synthetic test.
                size_t written=0;
                while(written<static_cast<size_t>(test.length)) {
                    ssize_t n=::send(client,test.header.data()+written,
                                      static_cast<size_t>(test.length)-written,MSG_NOSIGNAL);
                    assert(n>0);written+=static_cast<size_t>(n);
                }
            } else {
                int f=::open((root/"fixture.bin").c_str(),O_RDONLY|O_CLOEXEC);
                assert(f>=0);
                std::array<char,CMSG_SPACE(sizeof(int)*2)> ancillary{};
                iovec iov{const_cast<unsigned char*>(test.header.data()), static_cast<size_t>(test.length)};
                msghdr message{};
                message.msg_iov=&iov;message.msg_iovlen=1;
                message.msg_control=ancillary.data();
                message.msg_controllen=test.duplicate_descriptor?
                    CMSG_SPACE(sizeof(int)*2):CMSG_SPACE(sizeof(int));
                auto* c=CMSG_FIRSTHDR(&message);
                assert(c!=nullptr);
                c->cmsg_level=SOL_SOCKET;c->cmsg_type=SCM_RIGHTS;
                c->cmsg_len=CMSG_LEN(sizeof(int)*(test.duplicate_descriptor?2:1));
                int fds[2]{f,f};
                std::memcpy(CMSG_DATA(c),fds,sizeof(int)*(test.duplicate_descriptor?2:1));
                const auto n=::sendmsg(client,&message,MSG_NOSIGNAL);
                assert(n==test.length);
                ::close(f);
            }
        }
        ::close(client);
        ::close(listener);
    });
    Config cfg{label,std::string(32,'a'),2000};
    auto res=TryOpenInitialEboot(Client(cfg),"eboot.bin",std::optional<fs::path>(root));
    assert(res.outcome==test.expected);
    server.join();
}

int main(){
    auto root=fs::temp_directory_path()/("p56-frames-"+std::to_string(::getpid()));
    fs::create_directories(root);
    {std::ofstream f(root/"fixture.bin",std::ios::binary);f<<"synthetic_not_ps4";}
    const std::array<unsigned char,10> good{'B','S','F','1',1,0,0,0,0,0};
    auto wrong_magic=good;wrong_magic[0]='X';
    auto wrong_version=good;wrong_version[4]=2;
    auto oversize=good;oversize[6]=0x01; // 16MiB > 4MiB limit
    auto remote_denied=good;remote_denied[5]=1;
    auto one_byte_payload=good;one_byte_payload[9]=1;
    std::array<Scenario,9> scenarios{{
        {"closed",Outcome::BrokerHeaderClosed,good,0,false,false},
        {"short_header",Outcome::BrokerHeaderClosed,good,3,false,false},
        {"bad_magic",Outcome::BrokerHeaderBadMagic,wrong_magic,10,false,false},
        {"wrong_version",Outcome::BrokerHeaderBadVersion,wrong_version,10,false,false},
        {"oversize",Outcome::BrokerHeaderOversize,oversize,10,false,false},
        {"remote_denied",Outcome::BrokerDenied,remote_denied,10,false,false},
        {"payload_closed",Outcome::BrokerPayloadClosed,one_byte_payload,10,false,false},
        {"missing_fd",Outcome::BrokerFdInvalid,good,10,false,false},
        {"valid_fd",Outcome::EbootFdReady,good,10,true,false}
    }};
    for(size_t i=0;i<scenarios.size();++i) Test(scenarios[i],static_cast<int>(i),root);
    fs::remove_all(root);
}
