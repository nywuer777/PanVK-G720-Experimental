// SPDX-License-Identifier: GPL-2.0-or-later
#include "saf_cli_contract.h"
#include <cassert>
#include <iostream>
#include <string>
#include <vector>

using namespace Platform::Bachata::R2A4;

static std::vector<std::string> redact(std::vector<std::string> a) {
    std::vector<char*> pointers;
    for (auto& x : a) pointers.push_back(x.data());
    return RedactArgv(static_cast<int>(a.size()), pointers.data());
}

int main() {
    const std::string valid = "0123456789abcdef0123456789abcdef";
    const std::string upper = "ABCDEF0123456789ABCDEF0123456789";
    assert(IsHex32(valid));
    assert(IsHex32(upper));
    assert(!IsHex32(""));
    assert(!IsHex32(valid.substr(1)));
    assert(!IsHex32(valid + "0"));
    assert(!IsHex32("g123456789abcdef0123456789abcdef"));
    assert(!IsHex32("0 23456789abcdef0123456789abcdef"));
    assert(IsAbstractSocketLabel("bachata-saf-1234abcd-56efabcd"));
    assert(IsAbstractSocketLabel("bachata.saf_broker_123"));
    assert(!IsAbstractSocketLabel(""));
    assert(!IsAbstractSocketLabel("/tmp/broker"));
    assert(!IsAbstractSocketLabel("@broken"));
    assert(!IsAbstractSocketLabel("illegal name"));
    assert(!IsAbstractSocketLabel("has\nnewline"));
    assert(!IsAbstractSocketLabel(std::string(107, 'x')));
    assert(ValidateContractCli(valid, "bachata-saf-1234abcd-56efabcd", valid));
    assert(!ValidateContractCli(std::nullopt, "bachata-saf-1234abcd-56efabcd", valid));
    assert(!ValidateContractCli(valid, std::nullopt, valid));
    assert(!ValidateContractCli(valid, "bachata-saf-1234abcd-56efabcd", std::nullopt));
    assert(!ValidateContractCli(valid, "/tmp/socket", valid));
    assert(!ValidateContractCli(valid, "broker", "wrong"));
    assert(!ValidateContractCli("not-valid", "broker", valid));
    {
        auto a = redact({"shadps4", "--bachata-contract", valid,
                         "--bachata-saf-socket", "bachata-saf-secret",
                         "--bachata-saf-token", upper, "-g", "eboot.bin"});
        assert(a.size() == 9);
        assert(a[2] == "[REDACTED]" && a[4] == "[REDACTED]" &&
               a[6] == "[REDACTED]" && a[8] == "eboot.bin");
        for (const auto& x : a) {
            assert(x.find(valid) == std::string::npos);
            assert(x.find(upper) == std::string::npos);
            assert(x.find("bachata-saf-secret") == std::string::npos);
        }
    }
    {
        auto a = redact({"shadps4", "--bachata-contract="+valid,
                         "--bachata-saf-token="+upper,
                         "--bachata-saf-socket=secret-socket"});
        assert(a.size() == 4);
        assert(a[1] == "--bachata-contract=[REDACTED]");
        assert(a[2] == "--bachata-saf-token=[REDACTED]");
        assert(a[3] == "--bachata-saf-socket=[REDACTED]");
    }
    {
        auto a = redact({"shadps4", "--game", "eboot.bin"});
        assert(a[1] == "--game" && a[2] == "eboot.bin");
    }
    std::cout << "R2A4_SAF_CLI_TESTS_PASS\n";
}
