#!/usr/bin/env bash
# SPDX-License-Identifier: MIT
# Isolated REA tools; NO ChatGPT/MCP registration, APK or game files.
set -euo pipefail
: "$BACHATA_REA_HOME"
if [[ -z "$BACHATA_REA_HOME" || "$BACHATA_REA_HOME" != /* || "$BACHATA_REA_HOME" == "/" ]]; then
  echo 'REA_SETUP_UNSAFE_ABSOLUTE_HOME' >&2; exit 2
fi
if [[ -L "$BACHATA_REA_HOME" ]]; then
  echo 'REA_SETUP_SYMLINK_HOME_REJECTED' >&2; exit 2
fi
for cmd in node npm curl sha256sum java javac ps; do command -v "$cmd" >/dev/null; done
node -e '
const [major,minor]=process.versions.node.split(".").map(Number);
if (!((major===22&&minor>=19)||(major===24&&minor>=11)||major>=26)) process.exit(4);
' || { echo 'REA_NODE_VERSION_BELOW_REQUIRED_MINIMUM' >&2; exit 4; }
if ! java --list-modules 2>/dev/null | grep -q '^jdk.compiler@'; then
  echo 'REA_JAVA_FULL_JDK_REQUIRED' >&2; exit 5
fi
mkdir -p "$BACHATA_REA_HOME"
chmod 700 "$BACHATA_REA_HOME"
if [[ -e "$BACHATA_REA_HOME/node_modules/rea-agents/package.json" ]]; then
  echo 'REA_EXISTING_INSTALL_PREVENTS_SILENT_UPGRADE' >&2; exit 6
fi
echo 'REA_SETUP_INSTALL_PINNED_PACKAGE_V6_6_0'
npm install --prefix "$BACHATA_REA_HOME" --no-audit --no-fund \
  --package-lock=true --save-exact 'rea-agents@6.6.0'
CLI="$BACHATA_REA_HOME/node_modules/rea-agents/scripts/rea.mjs"
test -s "$CLI"
node "$CLI" --version
mkdir -p "$BACHATA_REA_HOME/android"
JAR="$BACHATA_REA_HOME/android/jadx-headless-mcp-0.7.1-all.jar"
EXPECTED="6e5eacf500b64292bfb73c49797c1958f6ee44646e43e868039ae7feb573ff75"
if [[ ! -f "$JAR" ]]; then
  curl --fail --location --retry 3 --connect-timeout 20 \
    "https://github.com/1013503897/jadx-headless-mcp/releases/download/v0.7.1/jadx-headless-mcp-0.7.1-all.jar" \
    -o "$JAR.part"
  (cd "$BACHATA_REA_HOME/android"; echo "$EXPECTED  jadx-headless-mcp-0.7.1-all.jar.part" | sha256sum -c -)
  mv "$JAR.part" "$JAR"
fi
(cd "$BACHATA_REA_HOME/android"; echo "$EXPECTED  jadx-headless-mcp-0.7.1-all.jar" | sha256sum -c -)
printf 'export BACHATA_REA_HOME=%q\n' "$BACHATA_REA_HOME" > "$BACHATA_REA_HOME/activate.sh"
printf 'export REA_JADX_MCP_JAR=%q\n' "$JAR" >> "$BACHATA_REA_HOME/activate.sh"
printf 'rea() { node %q "$@"; }\n' "$CLI" >> "$BACHATA_REA_HOME/activate.sh"
chmod 600 "$BACHATA_REA_HOME/activate.sh"
export REA_JADX_MCP_JAR="$JAR"
# Scoped read-only readiness. No APK, root or device is accessed.
node "$CLI" doctor --provider jadx --json > "$BACHATA_REA_HOME/doctor-jadx.json"
echo 'REA_JADX_CONFIGURATION_READY'
echo 'REA_PRIVATE_BACHATA_APK_ACCESSED=NO'
echo 'REA_CLIENT_MCP_REGISTERED=NO'
