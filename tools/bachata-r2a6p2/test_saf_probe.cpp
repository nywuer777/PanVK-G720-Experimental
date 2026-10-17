// SPDX-License-Identifier: GPL-2.0-or-later
// Synthetic broker only. Real Android sessions and user data are never used.
#include "saf_probe.h"
#include <array>
#include <atomic>
#include <cassert>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <functional>
#include <iostream>
#include <string>
#include <thread>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>
#include <vector>

using namespace Bachata::Saf;
namespace {
std::atomic<int> Serial{0};
const std::string FakeToken="0123456789abcdef0123456789abcdef";
int Checks=0;

void be32(std::vector<uint8_t>& out,uint32_t n) {
    for(int i=24;i>=0;i-=8)out.push_back(static_cast<uint8_t>(n>>i));
}
void be64(std::vector<uint8_t>& out,uint64_t n) {
    for(int i=56;i>=0;i-=8)out.push_back(static_cast<uint8_t>(n>>i));
}
bool exact(int fd,void* ptr,size_t len){
    auto* b=static_cast<uint8_t*>(ptr);
    while(len){
        ssize_t n=::recv(fd,b,len,0);
        if(n<0&&errno==EINTR)continue;
        if(n<=0)return false;
        b+=n;len-=static_cast<size_t>(n);
    }
    return true;
}
uint32_t decode(const uint8_t* v){
    return uint32_t(v[0])<<24|uint32_t(v[1])<<16|uint32_t(v[2])<<8|uint32_t(v[3]);
}
struct Request{uint8_t op{};bool valid{};};
Request read_request(int fd){
    uint8_t hdr[10]{};
    if(!exact(fd,hdr,10)||std::memcmp(hdr,"BSF1",4)!=0||hdr[4]!=1)return {};
    uint32_t token_length=decode(hdr+6);
    if(token_length>128)return {};
    std::string token(token_length,'\0');
    if(!exact(fd,token.data(),token_length))return {};
    uint8_t bytes[4]{};
    if(!exact(fd,bytes,4))return {};
    uint32_t path_length=decode(bytes);
    if(path_length>512)return {};
    std::string path(path_length,'\0');
    if(!exact(fd,path.data(),path_length))return {};
    return {hdr[5],token==FakeToken && path=="fixture/nonsecret.txt"};
}
std::vector<uint8_t> frame(uint8_t status,std::vector<uint8_t> payload={}) {
    std::vector<uint8_t> a{'B','S','F','1',1,status};
    be32(a,static_cast<uint32_t>(payload.size()));
    a.insert(a.end(),payload.begin(),payload.end());return a;
}
void respond(int sock,std::vector<uint8_t> data,int optional_fd=-1){
    msghdr m{};iovec io{data.data(),data.size()};
    m.msg_iov=&io;m.msg_iovlen=1;
    std::array<char,CMSG_SPACE(sizeof(int))> control{};
    if(optional_fd>=0) {
        m.msg_control=control.data();
        m.msg_controllen=control.size();
        auto* hdr=CMSG_FIRSTHDR(&m);
        hdr->cmsg_level=SOL_SOCKET;
        hdr->cmsg_type=SCM_RIGHTS;
        hdr->cmsg_len=CMSG_LEN(sizeof(int));
        std::memcpy(CMSG_DATA(hdr),&optional_fd,sizeof(int));
    }
    auto n=::sendmsg(sock,&m,MSG_NOSIGNAL);
    assert(n==static_cast<ssize_t>(data.size()));
}
int fake_readonly_fd(){
    char tmpl[]="/tmp/r2a6p2-fake-XXXXXX";
    int fd=::mkstemp(tmpl);assert(fd>=0);
    assert(::write(fd,"TEST",4)==4);
    ::close(fd);
    fd=::open(tmpl,O_RDONLY|O_CLOEXEC);assert(fd>=0);
    ::unlink(tmpl);
    return fd;
}
struct Server {
    std::string label;
    std::thread worker;
    Server(int expected,const std::function<void(int,Request,int)>& handle) {
        label="r2a6p2-test-"+std::to_string(::getpid())+"-"+std::to_string(++Serial);
        int listenfd=::socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);assert(listenfd>=0);
        sockaddr_un a{};a.sun_family=AF_UNIX;
        std::memcpy(a.sun_path+1,label.data(),label.size());
        auto len=static_cast<socklen_t>(offsetof(sockaddr_un,sun_path)+1+label.size());
        assert(::bind(listenfd,reinterpret_cast<sockaddr*>(&a),len)==0);
        assert(::listen(listenfd,4)==0);
        worker=std::thread([listenfd,expected,handle] {
            for(int i=0;i<expected;++i) {
                int c=::accept4(listenfd,nullptr,nullptr,SOCK_CLOEXEC);assert(c>=0);
                Request req=read_request(c);
                handle(c,req,i);
                ::close(c);
            }
            ::close(listenfd);
        });
    }
    ~Server(){if(worker.joinable())worker.join();}
};
void run(const char* name, int expected,
         const std::function<void(int,Request,int)>& response,
         Probe::Outcome desired) {
    Server server(expected,response);
    BSF1::Client client({server.label,FakeToken,200});
    const auto result=Probe::Run(client,"fixture/nonsecret.txt");
    assert(result.outcome==desired);
    ++Checks;std::cout<<"PASS "<<name<<"\n";
}
void stat_response(int fd,bool directory){
    std::vector<uint8_t> p{static_cast<uint8_t>(directory)};
    be64(p,4);be64(p,0);
    respond(fd,frame(0,p));
}
}
int main(){
    {
        BSF1::Client client({"not-connected",FakeToken,200});
        const auto r=Probe::Run(client,"/absolute/forbidden");
        assert(r.outcome==Probe::Outcome::InvalidPath);
        ++Checks;
    }
    run("file-stat-and-fd",2,[](int fd,Request r,int i){
        assert(r.valid&&r.op==(i==0?1:3));
        if(i==0)stat_response(fd,false);
        else{int f=fake_readonly_fd();respond(fd,frame(0),f);::close(f);}
    },Probe::Outcome::FileOk);
    run("directory-stat-and-list",2,[](int fd,Request r,int i){
        assert(r.valid&&r.op==(i==0?1:2));
        if(i==0)stat_response(fd,true);
        else {std::vector<uint8_t> p;be32(p,0);respond(fd,frame(0,p));}
    },Probe::Outcome::DirectoryOk);
    run("stat-remote-error",1,[](int fd,Request r,int){
        assert(r.valid&&r.op==1);respond(fd,frame(2));
    },Probe::Outcome::StatFailed);
    run("directory-list-remote-error",2,[](int fd,Request r,int i){
        assert(r.valid);
        if(i==0)stat_response(fd,true);
        else{assert(r.op==2);respond(fd,frame(2));}
    },Probe::Outcome::ListFailed);
    run("open-read-missing-descriptor",2,[](int fd,Request r,int i){
        assert(r.valid);
        if(i==0)stat_response(fd,false);
        else{assert(r.op==3);respond(fd,frame(0));}
    },Probe::Outcome::OpenReadFailed);
    run("stat-bad-wire-magic",1,[](int fd,Request r,int){
        assert(r.valid);auto data=frame(0);data[0]='X';respond(fd,data);
    },Probe::Outcome::StatFailed);
    const char* codes[]={
        Probe::SafeDiagnostic(Probe::Outcome::FileOk),
        Probe::SafeDiagnostic(Probe::Outcome::DirectoryOk),
        Probe::SafeDiagnostic(Probe::Outcome::InvalidPath),
        Probe::SafeDiagnostic(Probe::Outcome::StatFailed),
        Probe::SafeDiagnostic(Probe::Outcome::ListFailed),
        Probe::SafeDiagnostic(Probe::Outcome::OpenReadFailed),
        Probe::SafeDiagnostic(Probe::Outcome::DescriptorRejected),
    };
    for(const char* code:codes){
        std::string text(code);
        assert(text.find(FakeToken)==std::string::npos);
        assert(text.find("fixture") ==std::string::npos);
        ++Checks;
    }
    std::cout<<"R2A6P2_PROBE_MOCK_TESTS_PASS count="<<Checks<<'\n';
}
