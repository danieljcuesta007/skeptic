# Skeptic

**Your AI can change. Your knowledge stays.**

## Install

```sh
brew tap danieljcuesta007/skeptic https://github.com/danieljcuesta007/skeptic
brew install skeptic && skeptic-setup
# or
curl -fsSL https://skeptic.pages.dev/install.sh | sh
```

The one-line installer checks the release's SHA-256 before unpacking anything and only
writes inside your home folder. Releases: `scripts/release.sh <version>` (see the script).

Pre-alpha, provider-independent Markdown knowledge bridge. This repository contains
website/onboarding and discovery prototypes plus a read-only local project app,
automatically tested on synthetic data only. Daniel confirmed the initial local MVP;
unified-workspace browser acceptance remains pending.
It includes a local terminal installer; it is not a knowledge editor or replacement for Obsidian.

## Terminal model switching — Step 43D

A terminal-first switcher is now implemented; real existing-project/provider acceptance
is pending. No dashboard or prompt copy/paste required:

```sh
python3 -B ~/Developer/skeptic/apps/terminal/install.py
export PATH="$HOME/.local/bin:$PATH"; rehash
```

Return from Claude Code to the shell in your existing project, then run `skeptic`
and choose Codex with Up/Down and Enter, or `skeptic continue --with codex`.
First use asks for explicit persistent read approval; `skeptic permissions revoke PATH`
revokes it. Claude is also a destination; detected loopback local models use Codex's
OSS adapter. Native commands prepare handoffs and require a return to shell for switching.
[Commands, installation, permissions, limitations and real acceptance](apps/terminal/README.md).
No commits, pushes or deployment are performed by the switcher.

## Layout

- `apps/website/` — the product site (skeptic.pages.dev) and `install.sh`.
- `Formula/skeptic.rb` — Homebrew formula; `scripts/release.sh` — release builder.
- `apps/local/` — local project approvals, attributed overviews and copyable resume prompts.
- `packages/discovery/` — local lexical index, three access modes and neutral receipts.
- `packages/discovery/baseline-v1/` — preserved V1 regression source and fixtures.
- `docs/` — architecture, product, roadmap, security and development plans.
- `tests/validate.py` — complete local validation entry point.

## Requirements and validation

Python 3.9+ and POSIX filesystem descriptor APIs for the local tools; no third-party
Python runtime packages or provider accounts are required for synthetic validation.
The website build requires Node 22+ with npm and its declared React, TypeScript
and Tailwind dependencies. Install them once before running full validation:

    npm ci --prefix apps/website

    python3 tests/validate.py

Step 43B: website eight-asset build/18 tests/11 mutations, local three-asset build/
60 tests/56 mutations, discovery 36/36, baseline 18/18 and one migration regression:
**133 tests and 121 mutations caught**. HTTP tests exercise actual parsing/handlers
with an in-memory transport; live socket/browser acceptance is pending. See the
[local MVP report](docs/ux/STEP43B-LOCAL-MVP.md) and the
[launch readiness report](docs/ux/STEP43A-LAUNCH-READINESS.md).
Website live at https://skeptic.pages.dev (Step 47; browser acceptance and live headers verified).
Is it safe to switch right now? Run `skeptic ready` (Step 46).

Approved identity: black and white with supporting neutral grays. “Not everything
is black and white.” Existing layouts and truthful implementation labels are retained.

## Preview

Local application (Python only, no installation/account):

```sh
python3 -B ~/Developer/skeptic/apps/local/app.py
```

Open http://127.0.0.1:4317. Stop with Ctrl-C. Connect your vault and repository roots
with explicit read approval;
no note edits/uploads/provider calls. [First-use, security and removal guide](apps/local/README.md).
Real socket/browser acceptance is pending; [manual checklist](apps/local/BROWSER-ACCEPTANCE.md).

Website:

    cd apps/website
    npm ci
    npm run build
    npm run preview

Open http://127.0.0.1:4173. Stop with Ctrl-C. The demo reads no actual notes and
connects no accounts. The website preview applies the production Cloudflare
security headers, including its strict content security policy.

## Discovery sample

    cd packages/discovery
    PYTHONDONTWRITEBYTECODE=1 python3 run_demo.py

Uses only included synthetic notes. Writes its index to a new private temporary
cache outside this repository. Never point this pre-alpha at a private real vault.

## Status and boundaries

Step 41 review findings were fixed and regression-tested in Step 42; broader race,
resource and production security acceptance remain open. Browser acceptance, native
provider onboarding and safe install/uninstall remain release blockers. The private
source backup was verified by the owner in Step 42B; no website is deployed. See [roadmap](docs/roadmap/ROADMAP.md),
[migration](docs/development/MIGRATION.md), [GitHub plan](docs/development/GITHUB-PLAN.md)
and [license decision](LICENSE-DECISION.md).

The owner's private canonical project checkpoint remains outside this source
repository. Documentation here is product/development material, not another personal
memory system. Progress updates are manual; no hooks or sync services are installed.


## Managed multi-session work — Step 44

Temporary-project managed switching now has current/selected/all scopes, explicit provider
contracts and a durable recovery journal. Engine runtime/native acceptance is incomplete;
active sources and production migration remain unsupported. The implementation is not
production ready. [Commands, evidence and limitations](apps/terminal/MANAGED.md).

## Step 44 continuity development

The isolated continuity slice adds checkpoint proposals, scoped verification receipts,
fixture-only reviewed writes, a portable skill, offline agent recovery contracts and
read-only engine observations. The existing desktop includes expandable continuity
cards and a compact view; it reports unconnected/unknown without an explicit fixture
engine. No new live hooks, login services or provider integrations are activated.

[Implementation, commands, security limits and live-readiness](docs/development/STEP44-CONTINUITY-IMPLEMENTATION.md).
[Portable continuity contract](skills/skeptic/references/continuity-contract.md).
Run the socket-independent validator as documented; full managed runtime acceptance
requires Unix sockets. Offline adapter tests do not establish real provider acceptance.
