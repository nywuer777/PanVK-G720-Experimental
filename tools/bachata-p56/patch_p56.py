#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""P56: distinguish R2A5 BSF1 framing faults without changing accepted frames.

Run AFTER pinned P49+P53+P54 source integration. The original P42 private
host and APK are never modified. No sensitive token/path/byte logging.
"""
import argparse
import subprocess
from pathlib import Path

PIN="be6bc2e9c60799e071dd2fafa6216e8d80ec619c"

def one(data,before,after,why):
    n=data.count(before)
    if n!=1:raise ValueError(f"{why}: expected 1 anchor, got {n}")
    return data.replace(before,after,1)

def patch(header:str,client:str,bridge:str)->tuple[str,str,str]:
    header=one(header,
        "    InvalidFrame, RemoteError, MissingFd, UnexpectedFd, PayloadInvalid,",
        """    InvalidFrame, RemoteError, MissingFd, UnexpectedFd, PayloadInvalid,
    HeaderClosed, HeaderSyscall, HeaderAncillary, HeaderBadMagic,
    HeaderBadVersion, HeaderOversize, PayloadClosed, PayloadSyscall,
    PayloadAncillary,""", "R2A5 error enum")

    old="""bool RecvAllWithFd(int fd, uint8_t* dest, size_t size, ReadFd& received,
                   bool allow_fd) {"""
    new="""Error RecvAllWithFd(int fd, uint8_t* dest, size_t size, ReadFd& received,
                    bool allow_fd, bool payload_stage) {"""
    client=one(client,old,new,"R2A5 receiver signature")
    start=client.index(new)
    end=client.index("\n} // namespace",start)
    body=client[start:end]
    body=one(body,
        """        if (n < 0 && errno == EINTR) continue;
        if (n <= 0) return false;""",
        """        if (n < 0 && errno == EINTR) continue;
        if (n < 0) return payload_stage ? Error::PayloadSyscall : Error::HeaderSyscall;
        if (n == 0) return payload_stage ? Error::PayloadClosed : Error::HeaderClosed;""",
        "receive EOF/syscall")
    body=one(body,"        if (unexpected) return false;",
        "        if (unexpected) return payload_stage ? Error::PayloadAncillary : Error::HeaderAncillary;",
        "ancillary error")
    body=one(body,"    return true;\n}",
        "    return Error::None;\n}","receive success")
    client=client[:start]+body+client[end:]

    client=one(client,
        """    if (!RecvAllWithFd(sock.get(), header.data(), header.size(), recv_fd, want_fd))
        return {{}, Error::InvalidFrame};
    if (!std::equal(Magic.begin(), Magic.end(), header.begin()) || header[4] != Version ||
        Be32(header.data() + 6) > MaxPayload) return {{}, Error::InvalidFrame};""",
        """    const Error header_result = RecvAllWithFd(
        sock.get(), header.data(), header.size(), recv_fd, want_fd, false);
    if (header_result != Error::None) return {{}, header_result};
    if (!std::equal(Magic.begin(), Magic.end(), header.begin()))
        return {{}, Error::HeaderBadMagic};
    if (header[4] != Version) return {{}, Error::HeaderBadVersion};
    if (Be32(header.data() + 6) > MaxPayload) return {{}, Error::HeaderOversize};""",
        "response header")
    client=one(client,
        """    if (!reply.data.empty() && !RecvAllWithFd(sock.get(), reply.data.data(),
                                              reply.data.size(), reply.fd, want_fd))
        return {{}, Error::InvalidFrame};""",
        """    if (!reply.data.empty()) {
        const Error payload_result = RecvAllWithFd(
            sock.get(), reply.data.data(), reply.data.size(), reply.fd,
            want_fd, true);
        if (payload_result != Error::None) return {{}, payload_result};
    }""",
        "response payload")

    bridge=one(bridge,
        """    BrokerResponsePayloadInvalid,
    BrokerFdInvalid,""",
        """    BrokerResponsePayloadInvalid,
    BrokerHeaderClosed, BrokerHeaderSyscall, BrokerHeaderAncillary,
    BrokerHeaderBadMagic, BrokerHeaderBadVersion, BrokerHeaderOversize,
    BrokerPayloadClosed, BrokerPayloadSyscall, BrokerPayloadAncillary,
    BrokerFdInvalid,""",
        "P54/55 outcome enum")
    bridge=one(bridge,
        """    case Outcome::BrokerResponsePayloadInvalid:
        return "BACHATA_P55_BSF1_EBOOT_RESPONSE_PAYLOAD_INVALID";
    case Outcome::BrokerFdInvalid:""",
        """    case Outcome::BrokerResponsePayloadInvalid:
        return "BACHATA_P55_BSF1_EBOOT_RESPONSE_PAYLOAD_INVALID";
    case Outcome::BrokerHeaderClosed:
        return "BACHATA_P56_BSF1_HEADER_CLOSED";
    case Outcome::BrokerHeaderSyscall:
        return "BACHATA_P56_BSF1_HEADER_SYSCALL_ERROR";
    case Outcome::BrokerHeaderAncillary:
        return "BACHATA_P56_BSF1_HEADER_ANCILLARY_INVALID";
    case Outcome::BrokerHeaderBadMagic:
        return "BACHATA_P56_BSF1_HEADER_BAD_MAGIC";
    case Outcome::BrokerHeaderBadVersion:
        return "BACHATA_P56_BSF1_HEADER_BAD_VERSION";
    case Outcome::BrokerHeaderOversize:
        return "BACHATA_P56_BSF1_HEADER_OVERSIZE";
    case Outcome::BrokerPayloadClosed:
        return "BACHATA_P56_BSF1_PAYLOAD_CLOSED";
    case Outcome::BrokerPayloadSyscall:
        return "BACHATA_P56_BSF1_PAYLOAD_SYSCALL_ERROR";
    case Outcome::BrokerPayloadAncillary:
        return "BACHATA_P56_BSF1_PAYLOAD_ANCILLARY_INVALID";
    case Outcome::BrokerFdInvalid:""",
        "P54/55 safe marker mapping")
    bridge=one(bridge,
        """    case BSF1::Error::PayloadInvalid:
        return Outcome::BrokerResponsePayloadInvalid;
    default:""",
        """    case BSF1::Error::PayloadInvalid:
        return Outcome::BrokerResponsePayloadInvalid;
    case BSF1::Error::HeaderClosed:
        return Outcome::BrokerHeaderClosed;
    case BSF1::Error::HeaderSyscall:
        return Outcome::BrokerHeaderSyscall;
    case BSF1::Error::HeaderAncillary:
        return Outcome::BrokerHeaderAncillary;
    case BSF1::Error::HeaderBadMagic:
        return Outcome::BrokerHeaderBadMagic;
    case BSF1::Error::HeaderBadVersion:
        return Outcome::BrokerHeaderBadVersion;
    case BSF1::Error::HeaderOversize:
        return Outcome::BrokerHeaderOversize;
    case BSF1::Error::PayloadClosed:
        return Outcome::BrokerPayloadClosed;
    case BSF1::Error::PayloadSyscall:
        return Outcome::BrokerPayloadSyscall;
    case BSF1::Error::PayloadAncillary:
        return Outcome::BrokerPayloadAncillary;
    default:""",
        "P54/55 error-to-outcome mapping")
    return header,client,bridge

def run(root:Path):
    root=root.resolve()
    if not (root/".git").is_dir():raise ValueError("pinned git checkout required")
    rev=subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()
    if rev!=PIN:raise ValueError("upstream pin mismatch")
    base="src/platform/bachata/"
    paths=[root/(base+"saf_bsf1_client.h"),
           root/(base+"saf_bsf1_client.cpp"),
           root/(base+"p54_bsf1_eboot.h")]
    if any(not p.is_file() for p in paths):raise ValueError("P54 integration missing")
    if "BACHATA_P55_BSF1_EBOOT_RESPONSE_FRAME_INVALID" not in paths[2].read_text():
        raise ValueError("P55 diagnostics source prerequisite missing")
    if "BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY" not in paths[2].read_text():
        raise ValueError("P54 trusted fd prerequisite missing")
    changed=patch(*(p.read_text() for p in paths))
    for p,data in zip(paths,changed):p.write_text(data,encoding="utf-8",newline="")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("P56_BSF1_DIAGNOSTIC_FRAMING_PATCH_APPLIED")
    print("P56_PROTOCOL_WIRE_FORMAT=UNCHANGED")
    print("P56_PRIVATE_P42_APK=UNTOUCHED")
    print("P56_ANDROID_REAL_BROKER=NOT_TESTED")

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",type=Path,required=True)
    a=p.parse_args()
    run(a.source_root)
