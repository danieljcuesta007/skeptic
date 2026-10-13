# Before Skeptic is sold or widely promoted

Researched 13 Oct 2026 by Claude for Daniel. Not legal advice; a starting point for a
real conversation (the ND IDEA Center offers this free).

## Done

- **License:** MIT, so anyone may use, copy and resell it with the notice. Selling still
  works (signed builds, support, a Pro tier). Future work could change license; existing
  MIT grants stay. See `LICENSE-DECISION.md`.
- **Affiliation:** the site names Claude Code, Codex and Hermes only to say what Skeptic
  works with, uses no logos, and states it is not affiliated or endorsed (site footer,
  `legal.html#trademarks`, FAQ). A test fails if that disclaimer disappears.
- **Privacy:** `legal.html#privacy` describes the app (local only, no telemetry, no
  network calls, `~/.skeptic-cli`, optional local activity log off by default) and the site
  (no cookies/analytics; Cloudflare handles standard request data).
- **Comparison:** compares approaches, not named competitors; dated "as of October 2026";
  says where the alternative wins. Keep it dated and true when it changes.
- **Safe install:** one-line installer verifies SHA-256 before unpacking, writes only in
  `$HOME`, no sudo (tested end to end in `tests/test_install_script.py`).

## Open: Daniel's decisions

1. **Name.** A USPTO record exists for SKEPTIC (serial 76587304) covering anti-virus /
   network-security software (owner hidden on the aggregator; verify on
   [TSDR](https://tsdr.uspto.gov/#caseNumber=76587304&caseType=SERIAL_NO)). Different
   goods from an AI-switching tool, so the risk looks low, but check status before
   spending on the brand or filing your own mark.
2. **Notre Dame IP policy** (2021, §3 Scope): it covers students "who make use of
   University facilities, equipment, or other resources or who receive funds from the
   University", and claims work made with *Substantial Use* of them (own laptop / public
   resources are excluded). Built on your own Mac, own time: very likely yours. Two things
   to confirm with the IDEA Center: (a) whether ND pays for the Claude plan used to build
   it (the CLI is signed in as your nd.edu account), and (b) that Skeptic was never part
   of a class, ND-funded program or IDEA Center grant.
3. **Repository goes public.** Homebrew and the one-line installer download from GitHub
   releases, so `danieljcuesta007/skeptic` must be public first. Before the flip: scan
   the full history for secrets (standing rule).
4. **Getting paid** (only if you sell): use a merchant of record (Lemon Squeezy or Paddle)
   so they handle sales tax; a business entity (e.g. an LLC) keeps it separate from you.

## Release checklist

1. `scripts/release.sh 0.1.0` on a clean `main`.
2. PR the updated `install.sh` + `Formula/skeptic.rb` (dev, then main).
3. Tag, push the tag, `gh release create` with the archive.
4. Deploy the site (`apps/website/README.md`).
5. Install it both ways on a clean account and run `skeptic --help`.
