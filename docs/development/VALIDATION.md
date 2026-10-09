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
