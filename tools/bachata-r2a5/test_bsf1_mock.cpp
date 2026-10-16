// SPDX-License-Identifier: GPL-2.0-or-later
// Deterministic local mock broker; no production Android token, APK or device.
#include "saf_bsf1_client.h"
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

using Bachata::Saf::BSF1::Client;
using Bachata::Saf::BSF1::Config;
using Bachata::Saf::BSF1::Error;
namespace {
const std::string Token = "0123456789abcdef0123456789abcdef"; // synthetic only
std::atomic<int> Sequence{};
int Passed = 0;
void Be32(std::vector<uint8_t>& a, uint32_t n) {
    a.push_back(n >> 24);a.push_back(n >> 16);a.push_back(n >> 8);a.push_back(n);
}
void Be64(std::vector<uint8_t>& a, uint64_t n) {
    for (int i=7;i>=0;--i) a.push_back(n >> (i*8));
}
uint32_t U32(const uint8_t* p) {return uint32_t(p[0])<<24 | uint32_t(p[1])<<16 | uint32_t(p[2])<<8 | p[3];}
bool ReadAll(int fd, void* p, size_t len) {
    auto* c=static_cast<uint8_t*>(p);
    while(len){auto n=::recv(fd,c,len,0);if(n<0 && errno==EINTR)continue;if(n<=0)return false;c+=n;len-=n;}return true;
}
bool WriteAll(int fd, const uint8_t* p, size_t len) {
    while(len){auto n=::send(fd,p,len,MSG_NOSIGNAL);if(n<0&&errno==EINTR)continue;if(n<=0)return false;p+=n;len-=n;}return true;
}
std::vector<uint8_t> Frame(uint8_t status, std::vector<uint8_t> payload) {
    std::vector<uint8_t> f{'B','S','F','1',1,status};Be32(f,static_cast<uint32_t>(payload.size()));f.insert(f.end(),payload.begin(),payload.end());return f;
}
std::vector<uint8_t> StatPayload(bool dir, uint64_t a, uint64_t b) {
    std::vector<uint8_t> data{static_cast<uint8_t>(dir)};Be64(data,a);Be64(data,b);return data;
}
std::vector<uint8_t> ListPayload() {
    std::vector<uint8_t> data;Be32(data,2);
    for(auto [name,dir]: {std::pair<std::string,bool>{"eboot.bin",false},{"sce_module",true}}){
        data.push_back(static_cast<uint8_t>(name.size()>>8));data.push_back(static_cast<uint8_t>(name.size()));
        data.insert(data.end(),name.begin(),name.end());
        data.push_back(dir);Be64(data,dir?4096:128);Be64(data,44);
    }return data;
}
int ReadOnlyFile(){
    char pattern[]="/tmp/r2a5_mock_fd_XXXXXX";int fd=::mkstemp(pattern);assert(fd>=0);
    assert(::write(fd,"BSF1-DATA",9)==9);::close(fd);
    fd=::open(pattern,O_RDONLY|O_CLOEXEC);assert(fd>=0);::unlink(pattern);return fd;
}
int WritableFile(){
    char pattern[]="/tmp/r2a5_bad_fd_XXXXXX";int fd=::mkstemp(pattern);assert(fd>=0);::unlink(pattern);return fd;
}
void SendWithFds(int socketfd,std::vector<uint8_t> message,std::vector<int> fds={}){
    msghdr m{};iovec iov{message.data(),message.size()};m.msg_iov=&iov;m.msg_iovlen=1;
    std::array<unsigned char,CMSG_SPACE(sizeof(int)*2)> c{};
    if(!fds.empty()){
        assert(fds.size()<=2);
        m.msg_control=c.data();m.msg_controllen=CMSG_SPACE(sizeof(int)*fds.size());
        cmsghdr* h=CMSG_FIRSTHDR(&m);h->cmsg_level=SOL_SOCKET;h->cmsg_type=SCM_RIGHTS;
        h->cmsg_len=CMSG_LEN(sizeof(int)*fds.size());
        std::memcpy(CMSG_DATA(h),fds.data(),sizeof(int)*fds.size());
    }
    const auto n=::sendmsg(socketfd,&m,MSG_NOSIGNAL);assert(n>0);
    const size_t sent=static_cast<size_t>(n);
    if(sent<message.size()) assert(WriteAll(socketfd,message.data()+sent,message.size()-sent));
}
struct Request {uint8_t op{};std::string path;bool valid{};};
Request ReceiveRequest(int fd){
    uint8_t h[10]{};if(!ReadAll(fd,h,10))return {};
    if(std::memcmp(h,"BSF1",4)||h[4]!=1)return {};
    const uint32_t n=U32(h+6);if(n>128)return {};
    std::vector<uint8_t> token(n);
    if(!ReadAll(fd,token.data(),n))return {};
    uint8_t l[4];if(!ReadAll(fd,l,4))return {};
    uint32_t path_length=U32(l);if(path_length>4096)return {};
    std::string p(path_length,'\0');if(!ReadAll(fd,p.data(),path_length))return {};
    const bool tok=(std::string(token.begin(),token.end())==Token);
    return {h[5],p,tok};
}
struct Server {
    std::string label;
    std::thread runner;
    explicit Server(const std::function<void(int,Request)>& serve){
        label="r2a5-mock-"+std::to_string(::getpid())+"-"+std::to_string(++Sequence);
        int fd=::socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);assert(fd>=0);
        sockaddr_un a{};a.sun_family=AF_UNIX;std::memcpy(a.sun_path+1,label.data(),label.size());
        socklen_t length=offsetof(sockaddr_un,sun_path)+1+label.size();
        assert(::bind(fd,reinterpret_cast<sockaddr*>(&a),length)==0);
        assert(::listen(fd,1)==0);
        runner=std::thread([fd,serve]{
            int client=::accept4(fd,nullptr,nullptr,SOCK_CLOEXEC);assert(client>=0);
            Request req=ReceiveRequest(client);
            serve(client,req);
            ::close(client);::close(fd);
        });
    }
    ~Server(){ if(runner.joinable())runner.join(); }
};
void test(const std::string& name,const std::function<void(const Config&)>& check,
          const std::function<void(int,Request)>& serve){
    Server server(serve);
    Config c{server.label,Token,300};
    check(c);
    ++Passed;
    std::cout<<"PASS "<<name<<'\n';
}
}
int main(){
    const Config sample{"r2a5-example",Token,200};
    assert(Client::ValidateConfig(sample));++Passed;
    assert(!Client::ValidateConfig({"/tmp/broker",Token,200}));++Passed;
    assert(!Client::ValidateConfig({"any","short",200}));++Passed;
    assert(!Client::ValidateConfig({"any",Token,99}));++Passed;
    for(std::string p:{"games/..","/etc/passwd","../root","games//foo","foo/./bar","a\\b","a\n"}){
        assert(!Client::ValidatePath(p));++Passed;
    }
    assert(Client::ValidatePath("CUSA00325/eboot.bin"));++Passed;
    test("stat-success",[](const Config& c){Client x(c);auto v=x.Stat("game/eboot.bin");assert(v);assert(!v.value->is_directory);assert(v.value->field_a==123);assert(v.value->field_b==456);},
        [](int fd,Request r){assert(r.valid&&r.op==1&&r.path=="game/eboot.bin");SendWithFds(fd,Frame(0,StatPayload(false,123,456)));});
    test("stat-directory",[](const Config& c){Client x(c);auto v=x.Stat("game/dir");assert(v&&v.value->is_directory);},
        [](int fd,Request r){assert(r.valid&&r.op==1);SendWithFds(fd,Frame(0,StatPayload(true,0,0)));});
    test("stat-bad-length",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v&&v.error==Error::PayloadInvalid);},
        [](int fd,Request r){assert(r.valid);SendWithFds(fd,Frame(0,{1,2,3}));});
    test("stat-bad-magic",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v&&v.error==Error::InvalidFrame);},
        [](int fd,Request r){assert(r.valid);auto f=Frame(0,StatPayload(false,1,1));f[1]='X';SendWithFds(fd,f);});
    test("stat-bad-version",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v&&v.error==Error::InvalidFrame);},
        [](int fd,Request r){assert(r.valid);auto f=Frame(0,StatPayload(false,1,1));f[4]=2;SendWithFds(fd,f);});
    test("stat-oversize",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v&&v.error==Error::InvalidFrame);},
        [](int fd,Request r){assert(r.valid);std::vector<uint8_t> f{'B','S','F','1',1,0};Be32(f,0x400001);SendWithFds(fd,f);});
    test("remote-failure",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v&&v.error==Error::RemoteError);},
        [](int fd,Request r){assert(r.valid);SendWithFds(fd,Frame(3,{}));});
    test("stat-truncated",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v&&v.error==Error::InvalidFrame);},
        [](int fd,Request r){assert(r.valid);std::vector<uint8_t> f={'B','S','F','1',1,0};Be32(f,17);f.push_back(0);SendWithFds(fd,f);});
    test("stat-fragmented",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(v);},
        [](int fd,Request r){assert(r.valid);auto f=Frame(0,StatPayload(false,1,1));for(size_t i=0;i<f.size();i+=3)assert(WriteAll(fd,f.data()+i,std::min(size_t(3),f.size()-i)));});
    test("list-success",[](const Config& c){Client x(c);auto v=x.List("game");assert(v&&v.value->size()==2);assert((*v.value)[0].name=="eboot.bin");assert((*v.value)[1].metadata.is_directory);},
        [](int fd,Request r){assert(r.valid&&r.op==2);SendWithFds(fd,Frame(0,ListPayload()));});
    test("list-empty",[](const Config& c){Client x(c);auto v=x.List("game");assert(v&&v.value->empty());},
        [](int fd,Request r){assert(r.valid);std::vector<uint8_t> a;Be32(a,0);SendWithFds(fd,Frame(0,a));});
    test("list-invalid-count",[](const Config& c){Client x(c);auto v=x.List("game");assert(!v&&v.error==Error::PayloadInvalid);},
        [](int fd,Request r){assert(r.valid);std::vector<uint8_t> a;Be32(a,4097);SendWithFds(fd,Frame(0,a));});
    test("list-invalid-name",[](const Config& c){Client x(c);auto v=x.List("game");assert(!v&&v.error==Error::PayloadInvalid);},
        [](int fd,Request r){assert(r.valid);std::vector<uint8_t> a;Be32(a,1);a.push_back(0);a.push_back(2);a.push_back('.');a.push_back('.');a.insert(a.end(),17,0);SendWithFds(fd,Frame(0,a));});
    test("list-trailing-data",[](const Config& c){Client x(c);auto v=x.List("game");assert(!v&&v.error==Error::PayloadInvalid);},
        [](int fd,Request r){assert(r.valid);std::vector<uint8_t> a;Be32(a,0);a.push_back(5);SendWithFds(fd,Frame(0,a));});
    test("openread-fd",[](const Config& c){Client x(c);auto v=x.OpenRead("game/eboot.bin");assert(v);char b[9];assert(::read(v.value->get(),b,9)==9);assert(std::string(b,9)=="BSF1-DATA");},
        [](int fd,Request r){assert(r.valid&&r.op==3);int f=ReadOnlyFile();SendWithFds(fd,Frame(0,{}),{f});::close(f);});
    test("openread-missing-fd",[](const Config& c){Client x(c);auto v=x.OpenRead("game");assert(!v&&v.error==Error::MissingFd);},
        [](int fd,Request r){assert(r.valid);SendWithFds(fd,Frame(0,{}));});
    test("openread-writable-fd",[](const Config& c){Client x(c);auto v=x.OpenRead("game");assert(!v&&v.error==Error::UnexpectedFd);},
        [](int fd,Request r){assert(r.valid);int f=WritableFile();SendWithFds(fd,Frame(0,{}),{f});::close(f);});
    test("openread-many-fds",[](const Config& c){Client x(c);auto v=x.OpenRead("game");assert(!v&&v.error==Error::InvalidFrame);},
        [](int fd,Request r){assert(r.valid);int f=ReadOnlyFile(),g=ReadOnlyFile();SendWithFds(fd,Frame(0,{}),{f,g});::close(f);::close(g);});
    test("stat-unexpected-fd",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v&&v.error==Error::InvalidFrame);},
        [](int fd,Request r){assert(r.valid);int f=ReadOnlyFile();SendWithFds(fd,Frame(0,StatPayload(false,1,1)),{f});::close(f);});
    test("openread-unexpected-payload",[](const Config& c){Client x(c);auto v=x.OpenRead("game");assert(!v&&v.error==Error::PayloadInvalid);},
        [](int fd,Request r){assert(r.valid);int f=ReadOnlyFile();SendWithFds(fd,Frame(0,{7}),{f});::close(f);});
    test("timeout-no-response",[](const Config& c){Client x(c);auto v=x.Stat("game");assert(!v);},
        [](int fd,Request r){assert(r.valid);std::this_thread::sleep_for(std::chrono::milliseconds(350));(void)fd;});
    std::cout<<"R2A5_MOCK_BROKER_TESTS_PASS count="<<Passed<<'\n';
}
