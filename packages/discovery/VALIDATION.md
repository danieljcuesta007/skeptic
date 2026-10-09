# Synthetic validation checkpoint

17 V2 unittests passed; 17 targeted in-memory mutations caught. 18 baseline V1
tests passed. Original archive verified against all 14 manifest hashes after work.
Synthetic demo returned bounded references/passages and wrote an owner-only local
index outside notes. No live-brain scans, remote embeddings or provider APIs used.

A regression first reproduced forged cached passage output, then passed after
retrieval was changed to reconstruct passages from freshly read source bytes.
The index remains a trusted input for ranking; production hardening is incomplete.
Scoped discovery prunes unrelated directories as well as preventing body reads.

No production installation, integration, publication or activation occurred.

## Step 39 — recovered requirements checkpoint (supersedes prior counts)

24 V2 unittests passed with ResourceWarning treated as errors; 24/24 targeted
mutations caught. Preserved baseline: 18 tests passed and 18/18 mutations caught.
Zero final suite failures. Previous regression tests remain present.

Added governing-source revalidation independent of passage budget, current handoff,
structured preference conflicts, constrained catalog requests, Git cache-destination
refusal and quarantine filename protection. Requirements assessment and release plan
are in REQUIREMENTS-STEP39.md and RELEASE-READINESS.md. No live integration.

Remaining limits: trusted host policy, imperfect secret detection, plaintext private
index, no OS sandbox or authenticated cache, malformed-cache/DoS and filesystem race
hardening incomplete. Natural-language conflict detection and native provider acceptance
remain unverified. Revalidation is an API contract, not automatic action enforcement.

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
