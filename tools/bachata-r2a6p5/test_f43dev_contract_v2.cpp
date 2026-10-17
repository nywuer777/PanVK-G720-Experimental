// SPDX-License-Identifier: GPL-2.0-or-later
// Synthetic nonce only. Tests exactly the DEX-proven 32 lowercase hex HELLO wire.
#include "f43dev_contract_v2.h"
#include <cassert>
#include <cstring>
#include <iostream>
#include <string>
#include <string_view>
#include <vector>

using Platform::Bachata::ContractV2::BuildHello;
using Platform::Bachata::ContractV2::ValidNonce;

int main() {
    int passes=0;
    auto pass=[&](bool check){assert(check);++passes;};
    constexpr std::string_view sample="0123456789abcdef0123456789abcdef";
    constexpr std::string_view zeros="00000000000000000000000000000000";
    constexpr std::string_view highest="ffffffffffffffffffffffffffffffff";
    pass(ValidNonce(sample));
    pass(ValidNonce(zeros));
    pass(ValidNonce(highest));
    pass(!ValidNonce(""));
    pass(!ValidNonce(sample.substr(0,31)));
    pass(!ValidNonce(std::string(sample)+"0"));
    pass(!ValidNonce("0123456789ABCDEF0123456789ABCDEF"));
    pass(!ValidNonce("0123456789abcd_g0123456789abcdef"));
    pass(!ValidNonce("0123456789abcd-f0123456789abcdef"));
    pass(!ValidNonce("0123456789abcdef 123456789abcdef"));
    pass(!ValidNonce("0123456789abcdef\n123456789abcdef"));
    pass(!ValidNonce(std::string("0123456789abcdef\0""123456789abcdef",32)));
    auto line=BuildHello(sample);
    pass(line.has_value());
    pass(*line=="BACHATA/1 HELLO version=2 contract="+std::string(sample)+"\n");
    pass(line->find("version=1")==line->npos);
    pass(line->find("contract=")==26); // see below: checked by CI, not assumed
    pass(line->back()=='\n');
    pass(line->size()==std::string("BACHATA/1 HELLO version=2 contract=").size()+32+1);
    pass(!BuildHello("0123456789ABCDEF0123456789ABCDEF"));
    pass(!BuildHello(sample.substr(0,31)));
    pass(!BuildHello(std::string(sample)+"0"));
    pass(!BuildHello("0123456789abcdef/123456789abcdef"));
    pass(!BuildHello("0123456789abcdef\r123456789abcdef"));
    // Confirm there is no default HELLO without explicit session contract.
    pass(!BuildHello(std::string_view{}));
    pass(*BuildHello(zeros)=="BACHATA/1 HELLO version=2 contract="+std::string(zeros)+"\n");
    std::cout<<"R2A6P5_V2_HELLO_TESTS_PASS count="<<passes<<'\n';
}
