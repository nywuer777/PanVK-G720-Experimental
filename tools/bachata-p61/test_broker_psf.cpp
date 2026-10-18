// SPDX-License-Identifier: GPL-2.0-or-later
// Local BSF1 protocol proof: only sce_sys/param.sfo, Stat then OpenRead.
#include "platform/bachata/p61_saf_psf_stage.h"
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
using Bachata::Saf::P61::ProbeAndStageParamSfo;
using Bachata::Saf::P61::Status;
static void Recv(int fd,void* p,size_t n) {
    auto* b=static_cast<unsigned char*>(p);
    while(n){const auto v=::recv(fd,b,n,0);assert(v>0);b+=v;n-=static_cast<size_t>(v);}
}
static void Send(int fd,const void* p,size_t n) {
    const auto* b=static_cast<const unsigned char*>(p);
    while(n){const auto v=::send(fd,b,n,MSG_NOSIGNAL);assert(v>0);b+=v;n-=static_cast<size_t>(v);}
}
static void Response(int s,bool reject,int content_fd) {
    std::array<unsigned char,10> h{'B','S','F','1',1,
       static_cast<unsigned char>(reject?1:0),0,0,0,
       static_cast<unsigned char>(content_fd==-2 && !reject?17:0)};
    if(content_fd>=0&&!reject){
        std::array<char,CMSG_SPACE(sizeof(int))> aux{};
        iovec iov{h.data(),h.size()};msghdr msg{};
        msg.msg_iov=&iov;msg.msg_iovlen=1;
        msg.msg_control=aux.data();msg.msg_controllen=aux.size();
        auto* c=CMSG_FIRSTHDR(&msg);assert(c);
        c->cmsg_level=SOL_SOCKET;c->cmsg_type=SCM_RIGHTS;
        c->cmsg_len=CMSG_LEN(sizeof(int));
        std::memcpy(CMSG_DATA(c),&content_fd,sizeof(int));
        assert(::sendmsg(s,&msg,MSG_NOSIGNAL)==10);
    } else Send(s,h.data(),h.size());
    if(content_fd==-2&&!reject){
        std::array<unsigned char,17> meta{};meta[8]=0x40;
        Send(s,meta.data(),meta.size());
    }
}
static void Check(int s,int op){
    std::array<unsigned char,12> h{};Recv(s,h.data(),h.size());
    const std::array<unsigned char,12> expected{'B','S','F','1',1,
        static_cast<unsigned char>(op),0,32,0,0,0,17};
    assert(h==expected);
    std::array<char,49> b{};Recv(s,b.data(),b.size());
    assert(std::memcmp(b.data(),"aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",32)==0);
    assert(std::memcmp(b.data()+32,"sce_sys/param.sfo",17)==0);
}
static void WriteFixture(const fs::path& p){
    std::array<unsigned char,55> data{};
    data[1]='P';data[2]='S';data[3]='F';
    data[4]=1;data[5]=1;
    data[8]=36;data[12]=45;data[16]=1;
    data[22]=2;data[23]=4;data[24]=10;data[28]=10;
    std::memcpy(data.data()+36,"TITLE_ID",9);
    std::memcpy(data.data()+45,"CUSA00325",10);
    std::ofstream f(p,std::ios::binary);f.write(reinterpret_cast<const char*>(data.data()),data.size());
}
static void Exercise(bool reject){
    auto base=fs::temp_directory_path()/ ("p61-mock-"+std::to_string(::getpid())+(reject?"-deny":"-ok"));
    assert(fs::create_directory(base));fs::permissions(base,fs::perms::owner_all);
    const auto root=base/"CUSA00325";assert(fs::create_directory(root));
    fs::permissions(root,fs::perms::owner_all);
    const auto content=base/"source.psf";WriteFixture(content);
    const std::string label="p61_bsf1_"+std::to_string(::getpid())+(reject?"_den":"_ok");
    int listener=::socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);assert(listener>=0);
    sockaddr_un addr{};addr.sun_family=AF_UNIX;
    assert(label.size()<sizeof(addr.sun_path)-1);
    std::memcpy(addr.sun_path+1,label.data(),label.size());
    const auto n=static_cast<socklen_t>(offsetof(sockaddr_un,sun_path)+1+label.size());
    assert(::bind(listener,reinterpret_cast<const sockaddr*>(&addr),n)==0);
    assert(::listen(listener,4)==0);
    bool did_stat=false,did_open=false;
    std::thread t([&]{
        int s=::accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);assert(s>=0);
        Check(s,1);did_stat=true;Response(s,reject,-2);::close(s);
        if(!reject){
            s=::accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);assert(s>=0);
            Check(s,3);did_open=true;
            int f=::open(content.c_str(),O_RDONLY|O_CLOEXEC);assert(f>=0);
            Response(s,false,f);::close(f);::close(s);
        }
        ::close(listener);
    });
    auto result=ProbeAndStageParamSfo(Client(Config{label,std::string(32,'a'),2000}),root);
    t.join();assert(did_stat);
    if(reject){
        assert(!did_open && result.status==Status::BrokerStatRejected);
        assert(!fs::exists(root/"sce_sys"));
    } else {
        assert(did_open && result.status==Status::Ready);
        assert(fs::file_size(result.path)==55);
        result={};assert(!fs::exists(root/"sce_sys"));
    }
    fs::remove_all(base);
}
int main(){Exercise(false);Exercise(true);}
