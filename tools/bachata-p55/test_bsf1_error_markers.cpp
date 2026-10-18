// P55 pure diagnostic mapping (no real host, paths, or content).
#include "platform/bachata/p54_bsf1_eboot.h"
#include <cassert>
#include <cstring>

using Bachata::Saf::BSF1::Error;
using Bachata::Saf::P54::Classify;
using Bachata::Saf::P54::Marker;
using Bachata::Saf::P54::Outcome;
int main() {
    assert(Classify(Error::Io)==Outcome::BrokerRequestSendFailed);
    assert(Classify(Error::InvalidFrame)==Outcome::BrokerResponseFrameInvalid);
    assert(Classify(Error::PayloadInvalid)==Outcome::BrokerResponsePayloadInvalid);
    assert(Classify(Error::Connection)==Outcome::BrokerUnavailable);
    assert(Classify(Error::PeerMismatch)==Outcome::BrokerUnavailable);
    assert(Classify(Error::InvalidConfig)==Outcome::BrokerUnavailable);
    assert(Classify(Error::RemoteError)==Outcome::BrokerDenied);
    assert(Classify(Error::InvalidPath)==Outcome::BrokerDenied);
    assert(Classify(Error::MissingFd)==Outcome::BrokerFdInvalid);
    assert(Classify(Error::UnexpectedFd)==Outcome::BrokerFdInvalid);
    assert(Classify(Error::None)==Outcome::BrokerProtocolMismatch);
    assert(std::strcmp(Marker(Outcome::BrokerRequestSendFailed),
      "BACHATA_P55_BSF1_EBOOT_REQUEST_SEND_FAILED")==0);
    assert(std::strcmp(Marker(Outcome::BrokerResponseFrameInvalid),
      "BACHATA_P55_BSF1_EBOOT_RESPONSE_FRAME_INVALID")==0);
    assert(std::strcmp(Marker(Outcome::BrokerResponsePayloadInvalid),
      "BACHATA_P55_BSF1_EBOOT_RESPONSE_PAYLOAD_INVALID")==0);
    assert(std::strcmp(Marker(Outcome::EbootFdReady),
      "BACHATA_P54_BSF1_EBOOT_AUTHENTICATED_FD_READY")==0);
    return 0;
}
