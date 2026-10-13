#!/bin/sh
# Skeptic installer: https://skeptic.pages.dev/install.sh
#
# Read this before you run it. It is short on purpose. It:
#   1. downloads one release archive from GitHub,
#   2. checks it against the SHA-256 printed below and stops if they differ,
#   3. unpacks it to ~/.local/share/skeptic/<version> (older versions are removed),
#   4. runs Skeptic's own installer, which puts `skeptic` in ~/.local/bin, adds one
#      marked PATH line to ~/.zshrc (skip with --no-profile) and adds the /skeptic
#      helpers to ~/.claude/skills and ~/.agents/skills.
# No sudo, no admin rights, nothing outside your home folder. Files you changed
# yourself are never overwritten: the installer stops and says which one.
# Remove everything: see "Remove it" on https://skeptic.pages.dev/#install
#
# Options are passed through to the installer, for example:
#   curl -fsSL https://skeptic.pages.dev/install.sh | sh -s -- --no-profile
set -eu

VERSION="0.1.0"
SHA256="9988c22478bf3a9ea4cbed29e949e07320bc89401b7f234b8bf3f4e5dbdd22bf"
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

rm -rf "$PREFIX/$VERSION.new"
mkdir -p "$PREFIX/$VERSION.new"
tar -xzf "$tmp/skeptic.tar.gz" -C "$PREFIX/$VERSION.new" --strip-components 1
rm -rf "$PREFIX/$VERSION"
mv "$PREFIX/$VERSION.new" "$PREFIX/$VERSION"

python3 -B "$PREFIX/$VERSION/apps/terminal/install.py" --upgrade-integrations "$@"

# The launcher now points at this version; earlier versions are no longer used.
# Only folders that are clearly earlier Skeptic versions, never anything else in $PREFIX.
for old in "$PREFIX"/[0-9]*.[0-9]*; do
  [ "$old" != "$PREFIX/$VERSION" ] && [ -f "$old/apps/terminal/install.py" ] && rm -rf "$old"
done
say "done. Open a new Terminal window, then run: skeptic"
