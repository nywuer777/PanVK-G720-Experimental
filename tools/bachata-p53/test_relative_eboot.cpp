#include "relative_eboot.h"
#include <cassert>
#include <filesystem>
#include <fstream>
#include <optional>
#include <string>
#include <system_error>
#include <unistd.h>

namespace fs=std::filesystem;
using Platform::Bachata::P53::ResolveEboot;
int main() {
    auto base=fs::temp_directory_path()/("p53-fixture-"+std::to_string(getpid()));
    fs::create_directories(base/"valid");
    fs::create_directories(base/"outside");
    {
        std::ofstream valid(base/"valid"/"eboot.bin",std::ios::binary);
        valid << "test-only synthetic placeholder, not a PS4 executable";
    }
    {
        std::ofstream out(base/"outside"/"eboot.bin",std::ios::binary);
        out << "non-game-data";
    }
    const std::optional<fs::path> root=base/"valid";
    assert(ResolveEboot("eboot.bin",root)==fs::canonical(base/"valid"/"eboot.bin"));
    assert(!ResolveEboot("eboot.bin",std::nullopt));
    assert(!ResolveEboot("../eboot.bin",root));
    assert(!ResolveEboot("./eboot.bin",root));
    assert(!ResolveEboot("EBOOT.BIN",root));
    assert(!ResolveEboot("eboot.bin/../outside",root));
    assert(!ResolveEboot("/app0/eboot.bin",root));
    assert(!ResolveEboot("CUSA00325",root));
    assert(!ResolveEboot("eboot.bin",std::optional<fs::path>("relative/path")));
    assert(!ResolveEboot("eboot.bin",std::optional<fs::path>(base/"missing")));
    assert(!ResolveEboot("eboot.bin",std::optional<fs::path>(base/"outside"/"eboot.bin")));
    std::error_code ec;
    fs::remove(base/"valid"/"eboot.bin");
    fs::create_symlink(base/"outside"/"eboot.bin",base/"valid"/"eboot.bin",ec);
    assert(!ec);
    assert(!ResolveEboot("eboot.bin",root)); // block symlink exfiltration
    fs::remove(base/"valid"/"eboot.bin");
    assert(!ResolveEboot("eboot.bin",root));
    fs::remove_all(base);
}
