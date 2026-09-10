#!/bin/sh
# One-command installer for macOS, Linux, and Git Bash on Windows.
set -eu

REPO="seeseeczl/ASECLI"
PATH="$HOME/.local/bin:$PATH"
export PATH

if [ -f "$HOME/.local/bin/env" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.local/bin/env"
fi

if ! command -v uv >/dev/null 2>&1; then
  curl -LsSf https://astral.sh/uv/install.sh | sh
  if [ -f "$HOME/.local/bin/env" ]; then
    # shellcheck disable=SC1091
    . "$HOME/.local/bin/env"
  fi
  PATH="$HOME/.local/bin:$PATH"
  export PATH
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv installed but not on PATH. Open a new terminal and re-run this command." >&2
  exit 1
fi

if [ -n "${ASECLI_REF:-}" ]; then
  TAG="$ASECLI_REF"
else
  TAG=$(curl -fsSL "https://api.github.com/repos/${REPO}/releases/latest" | sed -n 's/.*"tag_name": *"\([^"]*\)".*/\1/p' | head -n 1)
fi
if [ -z "$TAG" ]; then
  TAG="v0.7.0"
fi
VERSION=${TAG#v}
WHEEL="https://github.com/${REPO}/releases/download/${TAG}/asecli-${VERSION}-py3-none-any.whl"

uv tool install --force "$WHEEL"
if asecli install-skill --help 2>&1 | grep -q -- "--agent"; then
    asecli install-skill --agent all || echo "CLI is installed. Skill was skipped because a different copy already exists."
else
    asecli install-skill || echo "CLI is installed. Skill was skipped because a different copy already exists."
fi
echo
echo "Done. Try: asecli --help"
echo "If the command is not found, open a new terminal."
