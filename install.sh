#!/usr/bin/env bash
# Install the shorts-video-studio skill into a skill directory.
#
# Usage:
#   bash install.sh                     # project-level, ./.opencode/skills/
#   bash install.sh --global            # ~/.config/opencode/skills/
#   bash install.sh --target claude     # ./.claude/skills/
#   bash install.sh --target agents     # ./.agents/skills/
#   bash install.sh --target all        # every location above (project-level)
#   bash install.sh --copy              # copy instead of symlink (for packaging)
#   bash install.sh --dir ~/myproj      # install relative to another project root
#   bash install.sh --uninstall         # remove the links/copies this script made
#
# A symlink keeps the skill in sync with this checkout; use --copy if you are
# vendoring the skill into another repository or a release archive.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$HERE/skills/shorts-video-studio"
NAME="shorts-video-studio"

[ -f "$SRC/SKILL.md" ] || { echo "ERROR: $SRC/SKILL.md not found" >&2; exit 1; }

GLOBAL=0; COPY=0; UNINSTALL=0; TARGET="opencode"; ROOT="$PWD"
while [ $# -gt 0 ]; do
  case "$1" in
    --global)    GLOBAL=1 ;;
    --copy)      COPY=1 ;;
    --uninstall) UNINSTALL=1 ;;
    --target)    TARGET="${2:-}"; shift ;;
    --dir)       ROOT="${2:-}";  shift ;;
    -h|--help)   sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "unknown option: $1 (try --help)" >&2; exit 1 ;;
  esac
  shift
done

if [ "$GLOBAL" = "1" ]; then
  case "$TARGET" in
    opencode) BASES=("$HOME/.config/opencode") ;;
    claude)   BASES=("$HOME/.claude") ;;
    agents)   BASES=("$HOME/.config/agents") ;;
    all)      BASES=("$HOME/.config/opencode" "$HOME/.claude") ;;
    *) echo "unknown --target: $TARGET" >&2; exit 1 ;;
  esac
else
  case "$TARGET" in
    opencode) BASES=("$ROOT/.opencode") ;;
    claude)   BASES=("$ROOT/.claude") ;;
    agents)   BASES=("$ROOT/.agents") ;;
    all)      BASES=("$ROOT/.opencode" "$ROOT/.claude" "$ROOT/.agents") ;;
    *) echo "unknown --target: $TARGET" >&2; exit 1 ;;
  esac
fi

for base in "${BASES[@]}"; do
  dest="$base/skills/$NAME"
  if [ "$UNINSTALL" = "1" ]; then
    if [ -L "$dest" ] || [ -d "$dest" ]; then rm -rf "$dest" && echo "removed  $dest"; else echo "absent   $dest"; fi
    continue
  fi
  mkdir -p "$base/skills"
  if [ -e "$dest" ] && [ ! -L "$dest" ]; then
    echo "skipped  $dest (already exists and is not a symlink - remove it yourself if you want it replaced)"
    continue
  fi
  rm -f "$dest"
  if [ "$COPY" = "1" ]; then
    cp -R "$SRC" "$dest"
    echo "copied   $dest"
  else
    ln -s "$SRC" "$dest"
    echo "linked   $dest -> $SRC"
  fi
done

if [ "$UNINSTALL" != "1" ]; then
  cat <<EOF

Installed. Next:
  1. bash "$SRC/scripts/setup.sh"
  2. source "$HERE/.venv/bin/activate"
  3. open your agent in this folder and ask for a short video, or paste prompt.md
EOF
fi
