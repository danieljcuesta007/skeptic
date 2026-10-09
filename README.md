# Skeptic

**Your AI can change. Your knowledge stays.**

Pre-alpha, provider-independent Markdown knowledge bridge. This repository contains
isolated website/onboarding and discovery prototypes, tested on synthetic data only.
It is not a production installer, knowledge editor, or replacement for Obsidian.

## Layout

- `apps/website/` — static marketing site, eight-step demo and manual browser checklist.
- `packages/discovery/` — local lexical index, three access modes and neutral receipts.
- `packages/discovery/baseline-v1/` — preserved V1 regression source and fixtures.
- `docs/` — architecture, product, roadmap, security and development plans.
- `tests/validate.py` — complete local validation entry point.

## Requirements and validation

Node 18+ with npm; Python 3.9+; POSIX filesystem descriptor APIs. No third-party
runtime packages, provider accounts, network calls or installation required.

    python3 tests/validate.py

Step 42: website build/10 tests, discovery 24 existing + 12 security tests,
24 existing + 12 security mutation checks, preserved baseline 18 tests/18 mutations,
and 1 migration regression: 65 tests and 54 mutation checks total.

## Preview

    cd apps/website
    npm run build
    npm run preview

Open http://127.0.0.1:4173. Stop with Ctrl-C. The demo reads no actual notes and
connects no accounts. Python preview does not apply Cloudflare response headers.

## Discovery sample

    cd packages/discovery
    PYTHONDONTWRITEBYTECODE=1 python3 run_demo.py

Uses only included synthetic notes. Writes its index to a new private temporary
cache outside this repository. Never point this pre-alpha at a private real vault.

## Status and boundaries

Step 41 review findings were fixed and regression-tested in Step 42; broader race,
resource and production security acceptance remain open. Browser acceptance, native
provider onboarding and safe install/uninstall remain release blockers. No remote is
configured and nothing is published. See [roadmap](docs/roadmap/ROADMAP.md),
[migration](docs/development/MIGRATION.md), [GitHub plan](docs/development/GITHUB-PLAN.md)
and [license decision](LICENSE-DECISION.md).

The owner's private canonical project checkpoint remains outside this source
repository. Documentation here is product/development material, not another personal
memory system. Progress updates are manual; no hooks or sync services are installed.
