#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Separate opt-in native provider install. Runs only after REA base readiness.
set -euo pipefail
if [[ -z "$BACHATA_REA_HOME" || "$BACHATA_REA_HOME" != /* || "$BACHATA_REA_HOME" == "/" ]]; then
  echo 'REA_GHIDRA_UNSAFE_HOME' >&2; exit 2
fi
for cmd in node java javac curl unzip sha256sum; do command -v "$cmd" >/dev/null; done
REA_CLI="$BACHATA_REA_HOME/rea-src/scripts/rea.mjs"
test -s "$REA_CLI" || { echo 'REA_GHIDRA_BASE_CLI_NOT_BUILT' >&2; exit 2; }
GHIDRA_ZIP="$BACHATA_REA_HOME/ghidra_12.1.4_PUBLIC_20260921.zip"
GHIDRA_HOME="$BACHATA_REA_HOME/ghidra_12.1.4_PUBLIC"
GHIDRA_SHA='ddac49f903da9d5bac833e5cc79395098b9c33cfd3279be5f31bd00387d2d4db'
if [[ -e "$GHIDRA_HOME" ]]; then
  echo 'REA_GHIDRA_EXISTING_INSTALL_PREVENTS_OVERWRITE' >&2; exit 4
fi
if [[ ! -f "$GHIDRA_ZIP" ]]; then
  curl -fL --retry 3 --connect-timeout 25 \
    'https://github.com/NationalSecurityAgency/ghidra/releases/download/Ghidra_12.1.4_build/ghidra_12.1.4_PUBLIC_20260921.zip' \
    -o "$GHIDRA_ZIP.part"
  echo "$GHIDRA_SHA  $GHIDRA_ZIP.part" | sha256sum -c -
  mv "$GHIDRA_ZIP.part" "$GHIDRA_ZIP"
fi
echo "$GHIDRA_SHA  $GHIDRA_ZIP" | sha256sum -c -
unzip -q "$GHIDRA_ZIP" -d "$BACHATA_REA_HOME"
test -f "$GHIDRA_HOME/Ghidra/application.properties"
test -f "$GHIDRA_HOME/support/analyzeHeadless"
export GHIDRA_INSTALL_DIR="$GHIDRA_HOME"
# Ghidra native decompiler and JDK architecture checks are handled by REA.
node "$REA_CLI" doctor --provider ghidra --json \
  > "$BACHATA_REA_HOME/doctor-ghidra.json"
printf 'export GHIDRA_INSTALL_DIR=%q\n' "$GHIDRA_HOME" \
  >> "$BACHATA_REA_HOME/activate.sh"
echo 'REA_GHIDRA_12_1_4_CONFIGURATION_READY'
echo 'REA_BACHATA_PRIVATE_RUNTIME_NOT_ACCESSED'
