#!/usr/bin/env bash
#
# GSD (eval-gsd) installer — installs the GSD command set into a project,
# or globally, straight from this GitHub repo. No npm / npx required.
#
#   Install into a project:   ./install.sh /path/to/your-project
#   Install into current dir: ./install.sh
#   Install globally (~/.claude): ./install.sh --global
#   Pin a branch/tag:         ./install.sh --ref main /path/to/your-project
#
# Or in one line, without cloning first:
#   curl -fsSL https://raw.githubusercontent.com/gunawanwilljkt/eval-gsd/main/install.sh | bash -s -- /path/to/your-project
#
set -euo pipefail

REPO_URL="https://github.com/gunawanwilljkt/eval-gsd.git"
SCOPE="local"      # local | global
TARGET="$PWD"
REF="main"

err() { printf '\033[31m%s\033[0m\n' "$*" >&2; }
info() { printf '\033[36m%s\033[0m\n' "$*"; }

while [ $# -gt 0 ]; do
  case "$1" in
    --global) SCOPE="global"; shift ;;
    --ref) REF="${2:?--ref needs a value}"; shift 2 ;;
    -h|--help)
      sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    --*) err "Unknown option: $1"; exit 2 ;;
    *) TARGET="$1"; shift ;;
  esac
done

command -v git >/dev/null 2>&1 || { err "git is required."; exit 1; }

# Destination .claude directory
if [ "$SCOPE" = "global" ]; then
  DEST="$HOME/.claude"
else
  DEST="$TARGET/.claude"
fi

# Find a source .claude: next to this script (running from a clone) or clone fresh.
SRC=""
CLEANUP=""
SELF_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd || true)"
if [ -n "$SELF_DIR" ] && [ -d "$SELF_DIR/.claude/get-shit-done" ]; then
  SRC="$SELF_DIR/.claude"
  info "Installing from local clone: $SELF_DIR"
else
  TMP="$(mktemp -d)"; CLEANUP="$TMP"
  info "Cloning $REPO_URL ($REF)…"
  git clone --depth 1 --branch "$REF" "$REPO_URL" "$TMP/eval-gsd" >/dev/null 2>&1
  SRC="$TMP/eval-gsd/.claude"
fi

[ -d "$SRC/get-shit-done" ] || { err "Source .claude not found at $SRC"; exit 1; }

mkdir -p "$DEST"
# Copy everything except settings.local.json (machine-specific hook paths).
( cd "$SRC" && tar --exclude='./settings.local.json' -cf - . ) | ( cd "$DEST" && tar -xf - )

[ -n "$CLEANUP" ] && rm -rf "$CLEANUP"

VER="$(cat "$DEST/get-shit-done/VERSION" 2>/dev/null || echo "?")"
info "✓ GSD v$VER installed into $DEST  (scope: $SCOPE)"
echo "  Open Claude Code here and run /gsd-help  (or /gsd-new-project)."
echo "  Hooks are off by default; see .claude/settings.local.json in the repo to enable them."
