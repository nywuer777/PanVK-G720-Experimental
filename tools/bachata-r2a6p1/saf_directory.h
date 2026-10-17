// SPDX-License-Identifier: GPL-2.0-or-later
// Read-only Orbis directory snapshot backed by validated BSF1 List entries.
#pragma once
#include <memory>
#include <vector>
#include "core/file_sys/directories/base_directory.h"
#include "platform/bachata/saf_bsf1_client.h"

namespace Core::Directories {
class SafDirectory final : public BaseDirectory {
public:
    explicit SafDirectory(std::vector<Bachata::Saf::BSF1::Entry> entries);
    ~SafDirectory() override = default;
    s64 read(void* buffer, u64 bytes) override;
    s64 getdents(void* buffer, u64 bytes, s64* basep) override;
    s32 fstat(Libraries::Kernel::OrbisKernelStat* stat) override;
    static bool ValidEntries(const std::vector<Bachata::Saf::BSF1::Entry>& entries);
};
} // namespace Core::Directories
