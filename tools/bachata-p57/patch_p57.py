#!/usr/bin/env python3
# P57: after P56. Diagnostic-only errno category mapping, fail closed.
import argparse, subprocess
from pathlib import Path
PIN="be6bc2e9c60799e071dd2fafa6216e8d80ec619c"
def one(x,a,b,tag):
    n=x.count(a)
    if n!=1: raise ValueError(f"{tag}: expected 1 anchor, got {n}")
    return x.replace(a,b,1)
def patch(h,c,b):
    h=one(h,"    PayloadAncillary,",
        """    PayloadAncillary, HeaderPeerReset, HeaderWaitExpired,
    HeaderPolicyDenied, HeaderSyscallUnavailable, HeaderBadDescriptor,
    HeaderInvalidArgument,""","error enum")
    h=one(h,"class Client {",
        """// Pure categorization. Never expose errno, path or token in logs.
Error ClassifyReceiveErrno(int saved_errno, bool payload_stage) noexcept;
class Client {""","public mapping declaration")
    c=one(c,"Error RecvAllWithFd(int fd,",
        """Error ClassifyReceiveErrnoImpl(int code, bool payload_stage) noexcept {
    if (payload_stage) return Error::PayloadSyscall;
    if (code == ECONNRESET || code == ENOTCONN || code == EPIPE)
        return Error::HeaderPeerReset;
    if (code == EAGAIN || code == EWOULDBLOCK || code == ETIMEDOUT)
        return Error::HeaderWaitExpired;
    if (code == EPERM || code == EACCES)
        return Error::HeaderPolicyDenied;
    if (code == ENOSYS) return Error::HeaderSyscallUnavailable;
    if (code == EBADF || code == ENOTSOCK || code == EFAULT)
        return Error::HeaderBadDescriptor;
    if (code == EINVAL) return Error::HeaderInvalidArgument;
    return Error::HeaderSyscall;
}
Error RecvAllWithFd(int fd,""","receiver classifier")
    c=one(c,
        "if (n < 0) return payload_stage ? Error::PayloadSyscall : Error::HeaderSyscall;",
        """if (n < 0) {
            const int saved_errno = errno;
            return ClassifyReceiveErrnoImpl(saved_errno, payload_stage);
        }""","recvmsg errno snapshot")
    c=one(c,"ReadFd::~ReadFd() {",
        """Error ClassifyReceiveErrno(int saved_errno, bool payload_stage) noexcept {
    return ClassifyReceiveErrnoImpl(saved_errno, payload_stage);
}
ReadFd::~ReadFd() {""","testable pure classifier")
    b=one(b,"    BrokerHeaderAncillary,",
        """    BrokerHeaderAncillary, BrokerHeaderPeerReset, BrokerHeaderWaitExpired,
    BrokerHeaderPolicyDenied, BrokerHeaderSyscallUnavailable,
    BrokerHeaderBadDescriptor, BrokerHeaderInvalidArgument,""","bridge enum")
    b=one(b,
        """    case Outcome::BrokerHeaderSyscall:
        return "BACHATA_P56_BSF1_HEADER_SYSCALL_ERROR";""",
        """    case Outcome::BrokerHeaderSyscall:
        return "BACHATA_P56_BSF1_HEADER_SYSCALL_ERROR";
    case Outcome::BrokerHeaderPeerReset:
        return "BACHATA_P57_BSF1_HEADER_PEER_RESET";
    case Outcome::BrokerHeaderWaitExpired:
        return "BACHATA_P57_BSF1_HEADER_WAIT_EXPIRED";
    case Outcome::BrokerHeaderPolicyDenied:
        return "BACHATA_P57_BSF1_HEADER_POLICY_DENIED";
    case Outcome::BrokerHeaderSyscallUnavailable:
        return "BACHATA_P57_BSF1_HEADER_SYSCALL_UNAVAILABLE";
    case Outcome::BrokerHeaderBadDescriptor:
        return "BACHATA_P57_BSF1_HEADER_BAD_DESCRIPTOR";
    case Outcome::BrokerHeaderInvalidArgument:
        return "BACHATA_P57_BSF1_HEADER_INVALID_ARGUMENT";""","fixed non-secret markers")
    b=one(b,
        """    case BSF1::Error::HeaderSyscall:
        return Outcome::BrokerHeaderSyscall;""",
        """    case BSF1::Error::HeaderSyscall:
        return Outcome::BrokerHeaderSyscall;
    case BSF1::Error::HeaderPeerReset:
        return Outcome::BrokerHeaderPeerReset;
    case BSF1::Error::HeaderWaitExpired:
        return Outcome::BrokerHeaderWaitExpired;
    case BSF1::Error::HeaderPolicyDenied:
        return Outcome::BrokerHeaderPolicyDenied;
    case BSF1::Error::HeaderSyscallUnavailable:
        return Outcome::BrokerHeaderSyscallUnavailable;
    case BSF1::Error::HeaderBadDescriptor:
        return Outcome::BrokerHeaderBadDescriptor;
    case BSF1::Error::HeaderInvalidArgument:
        return Outcome::BrokerHeaderInvalidArgument;""","bridge classification")
    return h,c,b
def apply(root):
    root=root.resolve()
    if not (root/".git").is_dir():raise ValueError("Git source required")
    if subprocess.check_output(["git","-C",str(root),"rev-parse","HEAD"],text=True).strip()!=PIN:
        raise ValueError("Pinned upstream changed")
    base=root/"src/platform/bachata"
    files=[base/"saf_bsf1_client.h",base/"saf_bsf1_client.cpp",base/"p54_bsf1_eboot.h"]
    if any(not f.is_file() for f in files):raise ValueError("P56 sources missing")
    if "BACHATA_P56_BSF1_HEADER_SYSCALL_ERROR" not in files[2].read_text():
        raise ValueError("P56 diagnostics missing")
    changed=patch(*(f.read_text() for f in files))
    for f,content in zip(files,changed):f.write_text(content,encoding="utf-8",newline="")
    subprocess.run(["git","-C",str(root),"diff","--check"],check=True)
    print("P57_RECVMSG_ERRNO_CLASSES=STAGED")
    print("P57_PROTOCOL_AND_SOCKET_FLAGS=UNCHANGED")
    print("P57_REAL_ANDROID_BROKER=NOT_VERIFIED")
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--source-root",type=Path,required=True)
    apply(p.parse_args().source_root)
