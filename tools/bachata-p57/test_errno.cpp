// P57: deterministic errno-category tests, no Android socket or game files.
#include <cassert>
#include <cerrno>
#include <cstring>
#include "platform/bachata/p54_bsf1_eboot.h"
using Bachata::Saf::BSF1::Error;
using Bachata::Saf::BSF1::ClassifyReceiveErrno;
using Bachata::Saf::P54::Classify;
using Bachata::Saf::P54::Marker;
using Bachata::Saf::P54::Outcome;
int main() {
    assert(ClassifyReceiveErrno(ECONNRESET,false)==Error::HeaderPeerReset);
    assert(ClassifyReceiveErrno(ENOTCONN,false)==Error::HeaderPeerReset);
    assert(ClassifyReceiveErrno(EPIPE,false)==Error::HeaderPeerReset);
    assert(ClassifyReceiveErrno(EAGAIN,false)==Error::HeaderWaitExpired);
    assert(ClassifyReceiveErrno(EWOULDBLOCK,false)==Error::HeaderWaitExpired);
    assert(ClassifyReceiveErrno(ETIMEDOUT,false)==Error::HeaderWaitExpired);
    assert(ClassifyReceiveErrno(EPERM,false)==Error::HeaderPolicyDenied);
    assert(ClassifyReceiveErrno(EACCES,false)==Error::HeaderPolicyDenied);
    assert(ClassifyReceiveErrno(ENOSYS,false)==Error::HeaderSyscallUnavailable);
    assert(ClassifyReceiveErrno(EBADF,false)==Error::HeaderBadDescriptor);
    assert(ClassifyReceiveErrno(ENOTSOCK,false)==Error::HeaderBadDescriptor);
    assert(ClassifyReceiveErrno(EFAULT,false)==Error::HeaderBadDescriptor);
    assert(ClassifyReceiveErrno(EINVAL,false)==Error::HeaderInvalidArgument);
    assert(ClassifyReceiveErrno(EIO,false)==Error::HeaderSyscall);
    assert(ClassifyReceiveErrno(ECONNRESET,true)==Error::PayloadSyscall);
    assert(Classify(Error::HeaderPeerReset)==Outcome::BrokerHeaderPeerReset);
    assert(Classify(Error::HeaderWaitExpired)==Outcome::BrokerHeaderWaitExpired);
    assert(Classify(Error::HeaderPolicyDenied)==Outcome::BrokerHeaderPolicyDenied);
    assert(Classify(Error::HeaderSyscallUnavailable)==Outcome::BrokerHeaderSyscallUnavailable);
    assert(Classify(Error::HeaderInvalidArgument)==Outcome::BrokerHeaderInvalidArgument);
    assert(std::strcmp(Marker(Outcome::BrokerHeaderPeerReset),"BACHATA_P57_BSF1_HEADER_PEER_RESET")==0);
    assert(std::strcmp(Marker(Outcome::BrokerHeaderWaitExpired),"BACHATA_P57_BSF1_HEADER_WAIT_EXPIRED")==0);
    assert(std::strcmp(Marker(Outcome::BrokerHeaderPolicyDenied),"BACHATA_P57_BSF1_HEADER_POLICY_DENIED")==0);
    assert(std::strcmp(Marker(Outcome::BrokerHeaderInvalidArgument),"BACHATA_P57_BSF1_HEADER_INVALID_ARGUMENT")==0);
}
