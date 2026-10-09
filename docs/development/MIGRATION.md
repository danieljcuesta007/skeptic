# Step 40 migration

Source: verified Step 39 final development archive, preserved outside this repository.
The private archive manifest is intentionally not copied into Git.

Website runtime/build/tests and discovery engine/tests/fixtures are unchanged.
The demo runner alone now writes its index to a private temporary cache outside Git.
Markdown references to historical temporary paths were replaced with repository-relative
locations. Removed from this migration: generated baseline receipts, archive manifest,
and website extend.py (a one-time generator, not used by build/runtime/tests).
No private knowledge content, existing Git history, indexes, accounts or provider
configuration was imported. Original artifacts and archives remain intact.

Important source files compared byte-for-byte: - apps/website/index.html
- apps/website/style.css
- apps/website/app.js
- apps/website/onboarding.js
- apps/website/wizard-state.js
- apps/website/build.mjs
- apps/website/test.mjs
- apps/website/_headers
- apps/website/package.json
- packages/discovery/engine.py
- packages/discovery/test_engine.py
- packages/discovery/mutation_check_v2.py
- packages/discovery/run_demo.py (matched on copy; then cache location intentionally changed)
- packages/discovery/policy.example.json
- packages/discovery/baseline-v1/discovery.py
- packages/discovery/baseline-v1/test_discovery.py
- packages/discovery/baseline-v1/mutation_check.py

Documentation path adjustments:
- apps/website/VALIDATION.md
- apps/website/CLOUDFLARE-PLAN.md
