#!/bin/sh
# Build a Skeptic release archive and point the installers at it.
#   scripts/release.sh 0.1.0
# It builds dist/skeptic-<version>.tar.gz from HEAD, records its SHA-256 in
# apps/website/install.sh and Formula/skeptic.rb, and prints the publish steps.
# It never publishes anything itself: creating the GitHub release and deploying
# the site are separate, deliberate steps.
set -eu
VERSION="${1:?usage: scripts/release.sh <version, e.g. 0.1.0>}"
ROOT=$(cd "$(dirname "$0")/.." && pwd)
cd "$ROOT"

[ -z "$(git status --porcelain)" ] || { echo "release: commit or discard changes first" >&2; exit 1; }

# An upgrade can only replace a /skeptic helper it recognises. If the helper text
# changed since the last tag, the old text's hash must be in LEGACY_SKILLS, or
# every existing user's upgrade would stop with "Existing file differs".
last=$(git describe --tags --abbrev=0 2>/dev/null || true)
if [ -n "$last" ]; then
  for f in skeptic-claude.md skeptic-codex.md; do
    git cat-file -e "$last:apps/terminal/$f" 2>/dev/null || continue  # new since the last tag: nothing to upgrade from
    old=$(git show "$last:apps/terminal/$f" | shasum -a 256 | cut -d' ' -f1)
    new=$(shasum -a 256 "apps/terminal/$f" | cut -d' ' -f1)
    if [ "$old" != "$new" ] && ! grep -q "$old" apps/terminal/install.py; then
      echo "release: $f changed since $last; add $old to LEGACY_SKILLS in apps/terminal/install.py" >&2; exit 1
    fi
  done
fi

commit=$(git rev-parse HEAD)
mkdir -p dist
archive="dist/skeptic-$VERSION.tar.gz"
git archive --format=tar.gz --prefix="skeptic-$VERSION/" -o "$archive" HEAD
sha=$(shasum -a 256 "$archive" | cut -d' ' -f1)

url="https://github.com/danieljcuesta007/skeptic/releases/download/v$VERSION/skeptic-$VERSION.tar.gz"
sed -i '' -e "s|^VERSION=\".*\"|VERSION=\"$VERSION\"|" -e "s|^SHA256=\".*\"|SHA256=\"$sha\"|" apps/website/install.sh
sed -i '' -e "s|^  url \".*\"|  url \"$url\"|" -e "s|^  sha256 \".*\"|  sha256 \"$sha\"|" Formula/skeptic.rb

cat <<MSG
Built $archive
SHA-256 $sha
Updated apps/website/install.sh and Formula/skeptic.rb.

The archive is commit $commit. Tag THAT commit, so \`git archive v$VERSION\`
reproduces the same bytes (the checksum edits above land in a later commit).

To publish (each step is outward-facing; do it on purpose):
  1. git tag v$VERSION $commit && git push origin v$VERSION
  2. gh release create v$VERSION $archive --title "Skeptic $VERSION" --notes-file <notes>
  3. PR the install.sh + Formula change to dev, then dev to main.
  4. Deploy the site so /install.sh carries the new checksum.
MSG
