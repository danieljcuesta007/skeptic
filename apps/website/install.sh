#!/bin/sh
# Skeptic installer: https://skeptic.pages.dev/install.sh
#
# Read this before you run it. It is short on purpose. It:
#   1. downloads one release archive from GitHub,
#   2. checks it against the SHA-256 printed below and stops if they differ,
#   3. unpacks it to ~/.local/share/skeptic/<version>,
#   4. runs Skeptic's own installer, which puts `skeptic` in ~/.local/bin
#      and adds the /skeptic helpers for Claude Code and Codex.
# No sudo, no admin rights, nothing outside your home folder.
# Remove later with: rm -rf ~/.local/share/skeptic ~/.local/bin/skeptic
#
# Options are passed through to the installer, for example:
#   curl -fsSL https://skeptic.pages.dev/install.sh | sh -s -- --no-profile
set -eu

VERSION="0.1.0"
SHA256="UNRELEASED"
URL="${SKEPTIC_URL:-https://github.com/danieljcuesta007/skeptic/releases/download/v$VERSION/skeptic-$VERSION.tar.gz}"  # override only for testing; the checksum still applies
PREFIX="${SKEPTIC_HOME:-$HOME/.local/share/skeptic}"

say() { printf 'skeptic: %s\n' "$*"; }
die() { printf 'skeptic: %s\n' "$*" >&2; exit 1; }

[ "$SHA256" != "UNRELEASED" ] || die "no release is published yet. Watch https://skeptic.pages.dev for v$VERSION."
for tool in curl shasum tar python3 git; do
  command -v "$tool" >/dev/null 2>&1 || die "needs $tool. On a Mac: xcode-select --install"
done
python3 -c 'import sys; sys.exit(sys.version_info < (3, 9))' || die "needs Python 3.9 or newer"

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT INT TERM

say "downloading v$VERSION"
curl -fsSL "$URL" -o "$tmp/skeptic.tar.gz" || die "download failed: $URL"

actual=$(shasum -a 256 "$tmp/skeptic.tar.gz" | cut -d' ' -f1)
[ "$actual" = "$SHA256" ] || die "checksum mismatch (expected $SHA256, got $actual). Nothing was installed."
say "checksum verified"

mkdir -p "$PREFIX/$VERSION"
tar -xzf "$tmp/skeptic.tar.gz" -C "$PREFIX/$VERSION" --strip-components 1
ln -sfn "$VERSION" "$PREFIX/current"

python3 -B "$PREFIX/$VERSION/apps/terminal/install.py" --upgrade-integrations "$@"
say "done. Open a new Terminal window, then run: skeptic"
