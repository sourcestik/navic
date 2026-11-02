#!/bin/sh
set -eu
cd "$(dirname "$0")/../frontend"
NAVIC_RUNTIME="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies/node"
if command -v pnpm >/dev/null 2>&1 && command -v node >/dev/null 2>&1; then
  pnpm install --frozen-lockfile
  pnpm run build
elif test -x "$NAVIC_RUNTIME/bin/node"; then
  # Convenience for this development Mac. Other machines use the standard pnpm branch.
  NAVIC_NODE="$NAVIC_RUNTIME/bin/node"
  NAVIC_PNPM="$NAVIC_RUNTIME/node_modules/pnpm/bin/pnpm.cjs"
  export PATH="$NAVIC_RUNTIME/bin:$PATH"
  "$NAVIC_NODE" "$NAVIC_PNPM" install --frozen-lockfile --store-dir ../.pnpm-store
  "$NAVIC_NODE" node_modules/vite/bin/vite.js build
else
  echo 'Install Node 22.12+ and pnpm 11.25.0, then rerun this script.' >&2
  exit 1
fi
