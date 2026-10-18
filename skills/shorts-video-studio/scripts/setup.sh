#!/usr/bin/env bash
# One-time setup for shorts-video-studio.
#
# Creates a local virtualenv at the repo root (.venv) and installs the Python
# dependencies there, so nothing is written into your system Python (PEP 668 /
# "externally-managed-environment" safe). Also verifies ffmpeg/ffprobe and the
# bundled fonts.
#
# Usage:
#   bash skills/shorts-video-studio/scripts/setup.sh            # venv (default)
#   bash skills/shorts-video-studio/scripts/setup.sh --system   # install into the current Python
#   VENV_DIR=/tmp/ssv bash skills/shorts-video-studio/scripts/setup.sh
#
# After a venv install, activate it before running the engine:
#   source .venv/bin/activate && python video.py
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_DIR="$(cd "$HERE/.." && pwd)"
REPO_DIR="$(cd "$SKILL_DIR/../.." && pwd)"
MODE="venv"; [ "${1:-}" = "--system" ] && MODE="system"

# ---------------------------------------------------------------- ffmpeg check
missing=""
for bin in ffmpeg ffprobe; do command -v "$bin" >/dev/null 2>&1 || missing="$missing $bin"; done
if [ -n "$missing" ]; then
  echo "ERROR: missing required binary:$missing" >&2
  echo "  Debian/Ubuntu : sudo apt-get install -y ffmpeg" >&2
  echo "  Fedora        : sudo dnf install -y ffmpeg" >&2
  echo "  macOS         : brew install ffmpeg" >&2
  echo "  Termux        : pkg install -y ffmpeg" >&2
  exit 1
fi
echo "ffmpeg  : $(ffmpeg -version | head -1 | cut -d' ' -f1-3)"

# ------------------------------------------------------------------ Python deps
REQ="$REPO_DIR/requirements.txt"
[ -f "$REQ" ] || REQ="$HERE/../requirements.txt"
if [ ! -f "$REQ" ]; then
  echo "ERROR: requirements.txt not found (looked in $REPO_DIR and $HERE/..)" >&2
  exit 1
fi

if [ "$MODE" = "system" ]; then
  echo "python  : installing into the current interpreter ($(command -v python3))"
  python3 -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
  python3 -m pip install --quiet -r "$REQ"
  PY=python3
else
  VENV_DIR="${VENV_DIR:-$REPO_DIR/.venv}"
  if [ ! -d "$VENV_DIR" ]; then
    echo "venv    : creating $VENV_DIR"
    python3 -m venv "$VENV_DIR" || {
      echo "ERROR: could not create a venv. On Debian/Ubuntu install python3-venv:" >&2
      echo "  sudo apt-get install -y python3-venv" >&2
      exit 1
    }
  fi
  PY="$VENV_DIR/bin/python"
  "$PY" -m pip install --quiet --upgrade pip >/dev/null 2>&1 || true
  echo "python  : installing into $VENV_DIR"
  "$PY" -m pip install --quiet -r "$REQ"
fi

# ------------------------------------------------------------------ self-check
"$PY" - <<'PY'
import sys
mods = {}
import numpy, cv2, PIL, scipy
mods = {"numpy": numpy.__version__, "opencv": cv2.__version__, "pillow": PIL.__version__, "scipy": scipy.__version__}
print("deps    : " + " | ".join(f"{k} {v}" for k, v in mods.items()))
from PIL import features
print(f"PIL     : freetype={features.check('freetype2')} raqm={features.check('raqm')}")
if not features.check("freetype2"):
    sys.exit("ERROR: Pillow was built without freetype2; text rendering will fail")
PY

# ------------------------------------------------------------------------ fonts
FONTS="$SKILL_DIR/assets/fonts"
if ls "$FONTS"/*.ttf >/dev/null 2>&1; then
  echo "fonts   : $(ls "$FONTS"/*.ttf | wc -l | tr -d ' ') files in $FONTS"
else
  echo "WARNING: no .ttf files in $FONTS - pass FONT_DIR=<dir> to the engine" >&2
fi
if [ ! -f "$FONTS/NotoColorEmoji.ttf" ]; then
  echo "WARNING: NotoColorEmoji.ttf missing - icons will render blank." >&2
  echo "         Debian/Ubuntu: sudo apt-get install -y fonts-noto-color-emoji" >&2
fi

echo
echo "Setup OK."
if [ "$MODE" = "venv" ]; then
  echo "Activate the venv before rendering:"
  echo "  source \"${VENV_DIR:-$REPO_DIR/.venv}/bin/activate\""
  echo
fi
echo "Smoke test (writes contact-sheet PNGs, no video):"
echo "  TEST=1 OUT_DIR=./out WORK=./work python \"$HERE/shorts_engine_template.py\""
