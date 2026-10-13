# Skeptic website

The product site at https://skeptic.pages.dev: what Skeptic does, how to install it
(Homebrew, a one-line script, or from source), an honest comparison, the creator, and
a privacy/license/trademarks page. Static HTML/CSS with one small script, no
dependencies, no third-party requests, no cookies or analytics.

Requires Node 18+ to build and test, Python 3 to preview:

    npm run build             # copies the 7 shipped files to dist/
    npm test                  # 11 tests: links, CSP, accessibility, palette, honesty, installer
    node mutation-check.mjs   # plants 13 faults and confirms each is caught
    npm run preview           # http://127.0.0.1:4173

## Files

| File | What |
| --- | --- |
| `index.html` | The product page |
| `legal.html` | Privacy, license, trademarks, credits, contact |
| `style.css` | Brand v1: ink, paper, greys; serif headings, mono labels |
| `site.js` | Install tabs, copy buttons, the terminal replay |
| `install.sh` | The one-line installer, served at `/install.sh` as plain text |
| `_headers` | Cloudflare Pages security headers (strict CSP) |

`install.sh` and `../../Formula/skeptic.rb` carry the release checksum.
`scripts/release.sh <version>` fills both in; the tests fail if they disagree.

## Deploy

Cloudflare Pages project `skeptic` (personal account), Direct Upload of `dist/`:

    npm run build && npx wrangler pages deploy dist --project-name skeptic

Deploying is a deliberate step: only after the matching GitHub release exists, so the
install commands on the page work.
