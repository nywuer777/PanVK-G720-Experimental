// SPDX-License-Identifier: GPL-2.0-or-later
// Two authenticated, local mock broker calls: Stat then OpenRead exact path.
#include "platform/bachata/p60_saf_libc_stage.h"
#include <array>
#include <cassert>
#include <cstddef>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <thread>
#include <fcntl.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
namespace fs=std::filesystem;
using Bachata::Saf::BSF1::Client;
using Bachata::Saf::BSF1::Config;
using Bachata::Saf::P60::ProbeAndStageLibc;
using Bachata::Saf::P60::Status;

static void ReceiveExact(int fd, void* data, size_t n) {
    auto* p=static_cast<unsigned char*>(data);
    while(n) {
        auto got=::recv(fd,p,n,0);
        assert(got>0);
        p+=got;n-=static_cast<size_t>(got);
    }
}
static void SendExact(int fd, const void* data, size_t n) {
    const auto* p=static_cast<const unsigned char*>(data);
    while(n) {
        auto sent=::send(fd,p,n,MSG_NOSIGNAL);
        assert(sent>0);
        p+=sent;n-=static_cast<size_t>(sent);
    }
}
static void SendResponse(int sock,bool denied,int file_fd) {
    const std::array<unsigned char,10> header{
        'B','S','F','1',1,static_cast<unsigned char>(denied?1:0),
        0,0,0,static_cast<unsigned char>(file_fd==-2 && !denied?17:0)};
    if (file_fd>=0 && !denied) {
        std::array<char,CMSG_SPACE(sizeof(int))> aux{};
        iovec iov{const_cast<unsigned char*>(header.data()),header.size()};
        msghdr msg{};
        msg.msg_iov=&iov;msg.msg_iovlen=1;
        msg.msg_control=aux.data();msg.msg_controllen=aux.size();
        auto* cms=CMSG_FIRSTHDR(&msg);
        assert(cms);
        cms->cmsg_level=SOL_SOCKET;cms->cmsg_type=SCM_RIGHTS;
        cms->cmsg_len=CMSG_LEN(sizeof(int));
        std::memcpy(CMSG_DATA(cms),&file_fd,sizeof(int));
        assert(::sendmsg(sock,&msg,MSG_NOSIGNAL)==10);
    } else {
        SendExact(sock,header.data(),header.size());
    }
    if(file_fd==-2 && !denied) {
        std::array<unsigned char,17> meta{};
        // Byte 0: isDirectory=false. Remaining fields are informational.
        meta[8]=0x20;
        SendExact(sock,meta.data(),meta.size());
    }
}

static void CheckRequest(int sock,int expected_operation) {
    std::array<unsigned char,12> header{};
    ReceiveExact(sock,header.data(),header.size());
    const std::array<unsigned char,12> expected{
      'B','S','F','1',1,static_cast<unsigned char>(expected_operation),
      0,32,0,0,0,19
    };
    assert(header==expected);
    std::array<char,51> contents{};
    ReceiveExact(sock,contents.data(),contents.size());
    assert(std::memcmp(contents.data(),"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",32)==0);
    assert(std::memcmp(contents.data()+32,"sce_module/libc.prx",19)==0);
}

static void Exercise(bool reject_stat) {
    const auto base=fs::temp_directory_path()/
         ("p60-mock-"+std::to_string(::getpid())+(reject_stat?"-denied":"-ready"));
    assert(fs::create_directory(base));
    fs::permissions(base,fs::perms::owner_all);
    const auto source=base/"mock.prx";
    {std::ofstream f(source,std::ios::binary);for(int i=0;i<4096;++i)f.put(char(i&255));}
    std::string label="p60_bsf1_"+std::to_string(::getpid())+(reject_stat?"_den":"_ok");
    int listener=::socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);
    assert(listener>=0);
    sockaddr_un sockaddr{};sockaddr.sun_family=AF_UNIX;
    assert(label.size()<sizeof(sockaddr.sun_path)-1);
    std::memcpy(sockaddr.sun_path+1,label.data(),label.size());
    socklen_t len=static_cast<socklen_t>(offsetof(sockaddr_un,sun_path)+1+label.size());
    assert(::bind(listener,reinterpret_cast<const struct sockaddr*>(&sockaddr),len)==0);
    assert(::listen(listener,4)==0);
    bool received_stat=false,received_open=false;
    std::thread server([&]{
        int fd=::accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);
        assert(fd>=0);
        CheckRequest(fd,1);
        received_stat=true;
        SendResponse(fd,reject_stat,-2);
        ::close(fd);
        if(!reject_stat) {
            int second=::accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);
            assert(second>=0);
            CheckRequest(second,3);
            received_open=true;
            int file=::open(source.c_str(),O_RDONLY|O_CLOEXEC);
            assert(file>=0);
            SendResponse(second,false,file);
            ::close(file);::close(second);
        }
        ::close(listener);
    });
    Config cfg{label,std::string(32,'a'),2000};
    auto result=ProbeAndStageLibc(Client(cfg),base);
    server.join();
    assert(received_stat);
    if(reject_stat) {
        assert(!received_open && result.status==Status::BrokerStatRejected);
        assert(!fs::exists(base/"sce_module"));
    } else {
        assert(received_open && result.status==Status::Ready);
        assert(fs::file_size(result.path)==4096);
        result = {};
        assert(!fs::exists(base/"sce_module"));
    }
    fs::remove_all(base);
}

int main(){
    Exercise(false);
    Exercise(true);
}
