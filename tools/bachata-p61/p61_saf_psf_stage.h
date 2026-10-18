// SPDX-License-Identifier: GPL-2.0-or-later
// P61: exact authorized sce_sys/param.sfo, bounded PSF validation, no synthetic TITLE_ID.
#pragma once
#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <span>
#include <string>
#include <string_view>
#include <utility>
#include <vector>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>
#include "platform/bachata/saf_bsf1_client.h"

namespace Bachata::Saf::P61 {
inline constexpr std::string_view kRelativePsf = "sce_sys/param.sfo";
inline constexpr std::size_t kMaxPsfSize = 1024 * 1024;
enum class Status {
    NotAttempted, UnsafeRoot, BrokerStatRejected, BrokerStatUnavailable,
    BrokerStatInvalid, BrokerNotRegular, BrokerOpenRejected, BrokerOpenFailed,
    InvalidFd, TooLarge, ReadFailed, InvalidPsf, MissingTitleId,
    InvalidPsfMagic, UnsupportedPsfVersion, InvalidPsfLayout,
    InvalidPsfEntryBounds, InvalidPsfKey, InvalidPsfFormat,
    InvalidPsfText, DuplicateTitleId, InvalidTitleIdFormat,

    TitleIdMismatch, CreateDirectoryFailed, UnsafeDirectory, ExistingFile,
    CreateFileFailed, WriteFailed, Ready
};
inline constexpr const char* Marker(Status s) noexcept {
    switch(s) {
    case Status::NotAttempted: return "BACHATA_P61_PSF_NOT_ATTEMPTED";
    case Status::UnsafeRoot: return "BACHATA_P61_PSF_UNSAFE_ROOT";
    case Status::BrokerStatRejected: return "BACHATA_P61_PSF_BROKER_STAT_REJECTED";
    case Status::BrokerStatUnavailable: return "BACHATA_P61_PSF_BROKER_STAT_UNAVAILABLE";
    case Status::BrokerStatInvalid: return "BACHATA_P61_PSF_BROKER_STAT_INVALID";
    case Status::BrokerNotRegular: return "BACHATA_P61_PSF_BROKER_NOT_REGULAR";
    case Status::BrokerOpenRejected: return "BACHATA_P61_PSF_BROKER_OPEN_REJECTED";
    case Status::BrokerOpenFailed: return "BACHATA_P61_PSF_BROKER_OPEN_FAILED";
    case Status::InvalidFd: return "BACHATA_P61_PSF_FD_INVALID";
    case Status::TooLarge: return "BACHATA_P61_PSF_TOO_LARGE";
    case Status::ReadFailed: return "BACHATA_P61_PSF_READ_FAILED";
    case Status::InvalidPsf: return "BACHATA_P61_PSF_INVALID";
    case Status::InvalidPsfMagic: return "BACHATA_P62_PSF_BAD_MAGIC";
    case Status::UnsupportedPsfVersion: return "BACHATA_P62_PSF_UNSUPPORTED_VERSION";
    case Status::InvalidPsfLayout: return "BACHATA_P62_PSF_LAYOUT";
    case Status::InvalidPsfEntryBounds: return "BACHATA_P62_PSF_ENTRY_BOUNDS";
    case Status::InvalidPsfKey: return "BACHATA_P62_PSF_KEY";
    case Status::InvalidPsfFormat: return "BACHATA_P62_PSF_FORMAT";
    case Status::InvalidPsfText: return "BACHATA_P62_PSF_TEXT";
    case Status::DuplicateTitleId: return "BACHATA_P62_PSF_DUPLICATE_TITLE_ID";
    case Status::InvalidTitleIdFormat: return "BACHATA_P62_PSF_TITLE_ID_FORMAT";

    case Status::MissingTitleId: return "BACHATA_P61_PSF_TITLE_ID_MISSING";
    case Status::TitleIdMismatch: return "BACHATA_P61_PSF_TITLE_ID_MISMATCH";
    case Status::CreateDirectoryFailed: return "BACHATA_P61_PSF_CREATE_DIR_FAILED";
    case Status::UnsafeDirectory: return "BACHATA_P61_PSF_UNSAFE_DIR";
    case Status::ExistingFile: return "BACHATA_P61_PSF_ALREADY_EXISTS_NOT_OVERWRITTEN";
    case Status::CreateFileFailed: return "BACHATA_P61_PSF_CREATE_FILE_FAILED";
    case Status::WriteFailed: return "BACHATA_P61_PSF_WRITE_FAILED";
    case Status::Ready: return "BACHATA_P61_PSF_SAF_PRIVATE_STAGE_READY";
    }
    return "BACHATA_P61_PSF_UNKNOWN";
}
class ScopedFd {
public:
    explicit ScopedFd(int fd=-1) noexcept : fd_(fd) {}
    ~ScopedFd() { if(fd_>=0) ::close(fd_); }
    ScopedFd(const ScopedFd&)=delete;
    ScopedFd& operator=(const ScopedFd&)=delete;
    int get() const noexcept { return fd_; }
private:
    int fd_;
};
struct Stage {
    Status status=Status::NotAttempted;
    std::filesystem::path path, root;
    bool created_dir=false;
    Stage()=default;
    explicit Stage(Status s):status(s){}
    Stage(Status s,std::filesystem::path p,std::filesystem::path r,bool d)
        :status(s),path(std::move(p)),root(std::move(r)),created_dir(d){}
    Stage(const Stage&)=delete;
    Stage& operator=(const Stage&)=delete;
    Stage(Stage&& o) noexcept
        :status(o.status),path(std::move(o.path)),root(std::move(o.root)),
          created_dir(o.created_dir) {
        o.path.clear();o.root.clear();o.created_dir=false;o.status=Status::NotAttempted;
    }
    Stage& operator=(Stage&& o) noexcept {
        if(this!=&o) {
            Cleanup();status=o.status;path=std::move(o.path);root=std::move(o.root);
            created_dir=o.created_dir;o.path.clear();o.root.clear();
            o.created_dir=false;o.status=Status::NotAttempted;
        }
        return *this;
    }
    ~Stage(){Cleanup();}
    explicit operator bool() const noexcept {return status==Status::Ready;}
private:
    void Cleanup() noexcept {
        if(!path.empty()){::unlink(path.c_str());path.clear();}
        if(created_dir && !root.empty()) ::rmdir((root/"sce_sys").c_str());
        root.clear();created_dir=false;
    }
};
inline bool SafeDir(int fd) noexcept {
    struct stat st{};
    return fd>=0 && ::fstat(fd,&st)==0 && S_ISDIR(st.st_mode) &&
        st.st_uid==::geteuid() && (st.st_mode&(S_IWGRP|S_IWOTH))==0;
}
inline std::uint16_t Le16(const unsigned char* p) {
    return std::uint16_t(p[0]) | (std::uint16_t(p[1])<<8);
}
inline std::uint32_t Le32(const unsigned char* p) {
    return std::uint32_t(p[0]) | (std::uint32_t(p[1])<<8) |
           (std::uint32_t(p[2])<<16) | (std::uint32_t(p[3])<<24);
}
inline bool ValidTitle(std::string_view v) {
    if(v.size()!=9 || v.substr(0,4)!="CUSA") return false;
    return std::all_of(v.begin()+4,v.end(),[](char c){return c>='0'&&c<='9';});
}
// P62: PSFHeader uses BE magic, LE offsets; PSFRawEntry uses BE param_fmt
// (upstream src/core/file_format/psf.h). A Text entry is the first NUL-
// terminated string, not necessarily the full param_len field. Reject any
// malformed entries *before* upstream PSF::Open reads pointer-based values.
// Only status categories are logged; never log game strings or SAF tokens.
inline Status ValidatePsf(std::span<const unsigned char> b,std::string_view expected) {
    if(!ValidTitle(expected)) return Status::InvalidTitleIdFormat;
    if(b.size()<20 || b[0]!=0 || b[1]!='P' || b[2]!='S' || b[3]!='F')
        return Status::InvalidPsfMagic;
    const auto ver=Le32(b.data()+4);
    if(ver!=0x100 && ver!=0x101) return Status::UnsupportedPsfVersion;
    const std::size_t keys=Le32(b.data()+8);
    const std::size_t data=Le32(b.data()+12);
    const std::size_t count=Le32(b.data()+16);
    if(count==0 || count>512 || count>(b.size()-20)/16 ||
       keys<20+count*16 || keys>data || data>b.size())
        return Status::InvalidPsfLayout;
    bool found=false;
    for(std::size_t i=0;i<count;++i) {
        const auto* e=b.data()+20+i*16;
        const auto key_off=std::size_t(Le16(e));
        const auto fmt=(std::uint16_t(e[2])<<8) | e[3];
        const auto len=std::size_t(Le32(e+4));
        const auto max=std::size_t(Le32(e+8));
        const auto off=std::size_t(Le32(e+12));
        if(key_off>=data-keys || len>max || off>b.size()-data ||
           len>b.size()-data-off) return Status::InvalidPsfEntryBounds;
        const auto* begin=b.data()+keys+key_off;
        const auto* end=static_cast<const unsigned char*>(
            std::memchr(begin,0,data-keys-key_off));
        if(!end || end==begin || (end-begin)>128) return Status::InvalidPsfKey;
        const auto key=std::string_view(reinterpret_cast<const char*>(begin),end-begin);
        const auto* value=b.data()+data+off;
        const unsigned char* zero=nullptr;
        if(fmt==0x0204) {
            if(len==0) return Status::InvalidPsfText;
            zero=static_cast<const unsigned char*>(std::memchr(value,0,len));
            if(!zero) return Status::InvalidPsfText;
        } else if(fmt==0x0404) {
            if(len!=4) return Status::InvalidPsfEntryBounds;
        } else if(fmt!=0x0004) return Status::InvalidPsfFormat;
        if(key=="TITLE_ID") {
            if(found) return Status::DuplicateTitleId;
            if(fmt!=0x0204) return Status::InvalidTitleIdFormat;
            found=true;
            // An actual PSF can store a padded text slot; shadPS4::PSF::Open
            // reads C string until the FIRST NUL. Never compare extra padding.
            const auto actual=std::string_view(
                reinterpret_cast<const char*>(value),zero-value);
            if(!ValidTitle(actual)) return Status::InvalidTitleIdFormat;
            if(actual!=expected) return Status::TitleIdMismatch;
        }
    }
    return found ? Status::Ready : Status::MissingTitleId;
}
inline Stage StageAuthorizedPsf(int fd,const std::filesystem::path& trusted_root,
                                std::string_view expected_title_id) {
    if(!trusted_root.is_absolute() || trusted_root!=trusted_root.lexically_normal())
        return Stage(Status::UnsafeRoot);
    ScopedFd root(::open(trusted_root.c_str(),O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW));
    if(!SafeDir(root.get())) return Stage(Status::UnsafeRoot);
    struct stat source{};
    if(fd<0 || ::fstat(fd,&source)!=0 || !S_ISREG(source.st_mode) || source.st_size<0)
        return Stage(Status::InvalidFd);
    if(static_cast<std::uint64_t>(source.st_size)>kMaxPsfSize) return Stage(Status::TooLarge);
    std::vector<unsigned char> bytes;
    std::array<unsigned char,16384> buffer{};
    for(;;) {
        const auto remaining=kMaxPsfSize-bytes.size();
        const auto request=std::min(remaining+std::size_t(1),buffer.size());
        const ssize_t n=::pread(fd,buffer.data(),request,static_cast<off_t>(bytes.size()));
        if(n<0 && errno==EINTR) continue;
        if(n<0) return Stage(Status::ReadFailed);
        if(n==0) break;
        if(static_cast<std::size_t>(n)>remaining) return Stage(Status::TooLarge);
        bytes.insert(bytes.end(),buffer.begin(),buffer.begin()+n);
    }
    if(source.st_size>0 && bytes.size()!=static_cast<std::size_t>(source.st_size))
        return Stage(Status::ReadFailed);
    const auto validated=ValidatePsf(bytes,expected_title_id);
    if(validated!=Status::Ready) return Stage(validated);
    bool created=false;
    if(::mkdirat(root.get(),"sce_sys",0700)==0) created=true;
    else if(errno!=EEXIST) return Stage(Status::CreateDirectoryFailed);
    ScopedFd dir(::openat(root.get(),"sce_sys",O_RDONLY|O_DIRECTORY|O_CLOEXEC|O_NOFOLLOW));
    if(!SafeDir(dir.get())) {
        if(created) ::unlinkat(root.get(),"sce_sys",AT_REMOVEDIR);
        return Stage(Status::UnsafeDirectory);
    }
    const auto path=trusted_root/"sce_sys"/"param.sfo";
    ScopedFd dst(::openat(dir.get(),"param.sfo",O_WRONLY|O_CREAT|O_EXCL|O_CLOEXEC|O_NOFOLLOW,0600));
    if(dst.get()<0) {
        if(created) ::unlinkat(root.get(),"sce_sys",AT_REMOVEDIR);
        return Stage(errno==EEXIST?Status::ExistingFile:Status::CreateFileFailed);
    }
    Stage stage(Status::CreateFileFailed,path,trusted_root,created);
    struct stat st{},rst{};
    if(::fstat(dst.get(),&st)!=0 || ::fstat(root.get(),&rst)!=0 ||
       !S_ISREG(st.st_mode) || st.st_uid!=::geteuid() || st.st_nlink!=1 ||
       (st.st_mode&0777)!=0600 || st.st_dev!=rst.st_dev) return stage;
    std::size_t off=0;
    while(off<bytes.size()) {
        const auto n=::write(dst.get(),bytes.data()+off,bytes.size()-off);
        if(n<0 && errno==EINTR) continue;
        if(n<=0){stage.status=Status::WriteFailed;return stage;}
        off+=static_cast<std::size_t>(n);
    }
    stage.status=Status::Ready;
    return stage;
}
inline Stage ProbeAndStageParamSfo(const BSF1::Client& broker,
                                  const std::filesystem::path& root) {
    const auto metadata=broker.Stat(kRelativePsf);
    if(!metadata) {
        if(metadata.error==BSF1::Error::RemoteError) return Stage(Status::BrokerStatRejected);
        if(metadata.error==BSF1::Error::PayloadInvalid) return Stage(Status::BrokerStatInvalid);
        return Stage(Status::BrokerStatUnavailable);
    }
    if(metadata.value->is_directory) return Stage(Status::BrokerNotRegular);
    auto opened=broker.OpenRead(kRelativePsf);
    if(!opened) return Stage(opened.error==BSF1::Error::RemoteError?
                            Status::BrokerOpenRejected:Status::BrokerOpenFailed);
    if(!opened.value || !*opened.value) return Stage(Status::InvalidFd);
    return StageAuthorizedPsf(opened.value->get(),root,root.filename().string());
}
} // namespace Bachata::Saf::P61
