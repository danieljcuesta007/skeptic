# Step 40 validation

- Website production build passed (7 static files); 10 tests passed.
- Discovery V2: 24 tests passed; 24/24 targeted mutations caught.
- Preserved V1: 18 tests passed; 18/18 mutations caught.
- Permanent-location demo regression: 1 test passed.
- Total unittest/Node tests: 53; mutation checks: 42. No final failures.

Migration exposed a macOS temporary-path alias in the demo runner. Its cache path now
resolves canonically outside Git. The initial demo attempt failed, was corrected, and
is covered by the new migration regression. The runtime engine and website are unchanged.
Browser rendering/screenshots, native providers, independent security and installers
remain unverified. No deployment, real-note scan or account connection occurred.

## Step 42 — Security Hardening & Shared Development Step Naming

Full `python3 -B tests/validate.py` passed: website build (7 files) and 10 tests;
V2 24 existing + 12 security tests, 24 existing + 12 security mutations; V1 18 tests
and 18 mutations; migration 1 test. Total: 65 tests, 54 mutations caught, zero final
failures. Existing regressions and baseline source are preserved. Each new security
test was observed rejecting a targeted in-memory fault. Two ad-hoc test commands
initially used incorrect working paths and failed to import/create the new suite;
corrected full runs passed. No application failure is concealed by those command errors.
All three original Step 41 probes were rerun: handoff leak False, malformed cache
Denied (safe rejection), protected alias returned False on a case-insensitive fixture.
Real-browser and live fresh-Claude acceptance remain unverified.
