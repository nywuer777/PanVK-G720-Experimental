// SPDX-License-Identifier: GPL-2.0-or-later
// Synthetic same-UID authenticated read-only broker, not an Android host proof.
#include "platform/bachata/p54_bsf1_eboot.h"

#include <array>
#include <cassert>
#include <cstring>
#include <fcntl.h>
#include <filesystem>
#include <fstream>
#include <string>
#include <sys/socket.h>
#include <sys/un.h>
#include <thread>
#include <unistd.h>

namespace fs=std::filesystem;
using Bachata::Saf::BSF1::Client;
using Bachata::Saf::BSF1::Config;
using Bachata::Saf::P54::Outcome;
using Bachata::Saf::P54::TryOpenInitialEboot;
using Bachata::Saf::P54::Marker;

int main() {
    const auto sandbox = fs::temp_directory_path() /
        ("p54-bsf1-synthetic-" + std::to_string(::getpid()));
    fs::create_directories(sandbox/"direct-runtime");
    const auto root = sandbox/"direct-runtime";
    const std::optional<fs::path> override_root = root;
    assert(TryOpenInitialEboot(Client(Config{}), "CUSA00325", override_root).outcome
           == Outcome::NotApplicable);
    assert(TryOpenInitialEboot(Client(Config{}), "eboot.bin", std::nullopt).outcome
           == Outcome::InvalidOverrideRoot);
    assert(TryOpenInitialEboot(Client(Config{}), "eboot.bin",
                              std::optional<fs::path>("relative/root")).outcome
           == Outcome::InvalidOverrideRoot);
    assert(TryOpenInitialEboot(Client(Config{}), "eboot.bin",
                              std::optional<fs::path>(sandbox/"missing")).outcome
           == Outcome::InvalidOverrideRoot);
    fs::create_directory_symlink(root, sandbox/"symlink-root");
    assert(TryOpenInitialEboot(Client(Config{}), "eboot.bin",
                              std::optional<fs::path>(sandbox/"symlink-root")).outcome
           == Outcome::InvalidOverrideRoot);
    // Invalid config must produce a safe denial without any network access.
    assert(TryOpenInitialEboot(Client(Config{}), "eboot.bin", override_root).outcome
           == Outcome::BrokerUnavailable);
    assert(std::string(Marker(Outcome::EbootFdReady)) ==
           "BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY");

    // Same user synthetic Android broker: abstract AF_UNIX socket + BSF1 FD.
    const std::string socket_label="p54_test_"+std::to_string(::getpid());
    int listener=::socket(AF_UNIX,SOCK_STREAM|SOCK_CLOEXEC,0);
    assert(listener>=0);
    sockaddr_un sa{};
    sa.sun_family=AF_UNIX;
    std::memcpy(sa.sun_path+1,socket_label.data(),socket_label.size());
    const socklen_t address_length=static_cast<socklen_t>(
        offsetof(sockaddr_un,sun_path)+1+socket_label.size());
    assert(::bind(listener,reinterpret_cast<sockaddr*>(&sa),address_length)==0);
    assert(::listen(listener,1)==0);
    {
        std::ofstream file(sandbox/"fixture.bin", std::ios::binary);
        file<<"FAKE_P54_ELF_CONTENT_DO_NOT_RUN";
    }
    std::thread server([&] {
        int fd=::accept4(listener,nullptr,nullptr,SOCK_CLOEXEC);
        assert(fd>=0);
        std::array<char, 55> packet{};
        size_t have=0;
        while(have<packet.size()) {
            const auto n=::recv(fd,packet.data()+have,packet.size()-have,0);
            assert(n>0);
            have+=static_cast<size_t>(n);
        }
        assert(std::memcmp(packet.data(),"BSF1",4)==0);
        assert(packet[4]==1 && packet[5]==3);
        assert(packet[9]==32);
        assert(packet[45]==9);
        assert(std::memcmp(packet.data()+46,"eboot.bin",9)==0);
        int content=::open((sandbox/"fixture.bin").c_str(),O_RDONLY|O_CLOEXEC);
        assert(content>=0);
        std::array<char,10> response{'B','S','F','1',1,0,0,0,0,0};
        std::array<char,CMSG_SPACE(sizeof(int))> anc{};
        iovec iov{response.data(),response.size()};
        msghdr message{};
        message.msg_iov=&iov;message.msg_iovlen=1;
        message.msg_control=anc.data();message.msg_controllen=anc.size();
        cmsghdr* c=CMSG_FIRSTHDR(&message);
        assert(c!=nullptr);
        c->cmsg_level=SOL_SOCKET;c->cmsg_type=SCM_RIGHTS;
        c->cmsg_len=CMSG_LEN(sizeof(int));
        std::memcpy(CMSG_DATA(c),&content,sizeof(int));
        const auto n=::sendmsg(fd,&message,MSG_NOSIGNAL);
        assert(n==static_cast<ssize_t>(response.size()));
        ::close(content);::close(fd);
    });
    Config valid{socket_label,std::string(32,'a'),2000};
    auto result=TryOpenInitialEboot(Client(valid),"eboot.bin",override_root);
    assert(result.outcome==Outcome::EbootFdReady);
    assert(result.fd.get()>=0);
    assert(fs::is_regular_file(result.proc_fd_path));
    std::ifstream readable(result.proc_fd_path,std::ios::binary);
    std::array<char,4> first{};
    readable.read(first.data(),first.size());
    assert(std::memcmp(first.data(),"FAKE",4)==0);
    server.join();
    ::close(listener);
    fs::remove_all(sandbox);
}
