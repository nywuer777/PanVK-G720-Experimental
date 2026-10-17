// SPDX-License-Identifier: GPL-2.0-or-later
#include "core/file_sys/directories/saf_directory.h"
#include <algorithm>
#include <array>
#include <cstring>
#include <limits>
#include <string_view>
#include "core/libraries/kernel/file_system.h"

namespace Core::Directories {
namespace {
constexpr size_t BlockSize = 512;
#pragma pack(push, 1)
struct Dirent {
    u32 fileno;
    u16 reclen;
    u8 type;
    u8 namlen;
    char name[256];
};
#pragma pack(pop)
static_assert(offsetof(Dirent, name) == 8);
constexpr size_t NameLimit = 246;
size_t Align4(size_t length) { return (length + 3u) & ~size_t(3u); }
bool ValidName(std::string_view name) {
    if (name.empty() || name.size() > NameLimit ||
        name == "." || name == "..") return false;
    for (const unsigned char c : name) {
        if (c == '/' || c == '\\' || c == '\0' || c < 0x20 || c == 0x7f)
            return false;
    }
    return true;
}
}

bool SafDirectory::ValidEntries(
    const std::vector<Bachata::Saf::BSF1::Entry>& entries) {
    for (const auto& entry : entries)
        if (!ValidName(entry.name)) return false;
    return true;
}

SafDirectory::SafDirectory(std::vector<Bachata::Saf::BSF1::Entry> entries) {
    if (!ValidEntries(entries)) return;
    size_t last_record_offset = 0;
    for (const auto& entry : entries) {
        const size_t length = Align4(offsetof(Dirent, name) + entry.name.size() + 1);
        const size_t remaining = BlockSize - (dirent_cache_bin.size() % BlockSize);
        if (length > remaining && !dirent_cache_bin.empty()) {
            u16 prev_length = 0;
            std::memcpy(&prev_length, dirent_cache_bin.data() + last_record_offset + 4,
                        sizeof(prev_length));
            prev_length = static_cast<u16>(prev_length + remaining);
            std::memcpy(dirent_cache_bin.data() + last_record_offset + 4,
                        &prev_length, sizeof(prev_length));
            dirent_cache_bin.resize(dirent_cache_bin.size() + remaining, 0);
        }
        Dirent record{};
        record.fileno = next_fileno();
        record.reclen = static_cast<u16>(length);
        record.type = entry.metadata.is_directory ? 4 : 8;
        record.namlen = static_cast<u8>(entry.name.size());
        std::memcpy(record.name, entry.name.data(), entry.name.size());
        const size_t offset = dirent_cache_bin.size();
        dirent_cache_bin.resize(offset + length, 0);
        std::memcpy(dirent_cache_bin.data() + offset, &record, length);
        last_record_offset = offset;
    }
    if (!dirent_cache_bin.empty()) {
        const size_t remainder = dirent_cache_bin.size() % BlockSize;
        if (remainder) {
            const size_t padding = BlockSize - remainder;
            u16 last_length = 0;
            std::memcpy(&last_length, dirent_cache_bin.data() + last_record_offset + 4,
                        sizeof(last_length));
            last_length = static_cast<u16>(last_length + padding);
            std::memcpy(dirent_cache_bin.data() + last_record_offset + 4,
                        &last_length, sizeof(last_length));
            dirent_cache_bin.resize(dirent_cache_bin.size() + padding, 0);
        }
    }
    directory_size = dirent_cache_bin.size();
}

s64 SafDirectory::read(void* buf, u64 size) {
    if (buf == nullptr) return ORBIS_KERNEL_ERROR_EFAULT;
    if (file_offset < 0 || static_cast<u64>(file_offset) >= directory_size) return 0;
    const u64 count = std::min<u64>(size, directory_size - static_cast<u64>(file_offset));
    std::memcpy(buf, dirent_cache_bin.data() + file_offset, static_cast<size_t>(count));
    file_offset += static_cast<s64>(count);
    return static_cast<s64>(count);
}

s64 SafDirectory::getdents(void* buf, u64 size, s64* basep) {
    if (buf == nullptr) return ORBIS_KERNEL_ERROR_EFAULT;
    if (basep) *basep = file_offset;
    if (file_offset < 0 || static_cast<u64>(file_offset) >= directory_size) return 0;
    const u64 aligned = size - (size % BlockSize);
    const u64 count = std::min<u64>(
        aligned, directory_size - static_cast<u64>(file_offset));
    if (!count) return 0;
    std::memcpy(buf, dirent_cache_bin.data() + file_offset, static_cast<size_t>(count));
    file_offset += static_cast<s64>(count);
    return static_cast<s64>(count);
}

s32 SafDirectory::fstat(Libraries::Kernel::OrbisKernelStat* stat) {
    if (!stat) return ORBIS_KERNEL_ERROR_EFAULT;
    stat->st_mode = 0040000u | 0000555u;
    stat->st_size = directory_size;
    stat->st_blksize = BlockSize;
    stat->st_blocks = (directory_size + BlockSize - 1) / BlockSize;
    return ORBIS_OK;
}
} // namespace Core::Directories
