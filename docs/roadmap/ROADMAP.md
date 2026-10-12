# Pre-alpha roadmap

| Milestone | Evidence / status |
| --- | --- |
| Steps 33B–33C | V1 synthetic prototype and preserved validation |
| Steps 35–38 | Website/onboarding extended; separate V2 discovery prototype |
| Step 39 | Requirements recovered; V2 24 tests/24 mutations; website 10 tests; baseline 18/18; private archives preserved |
| Step 40 | Permanent isolated local Git project; initial local commit after validation; linked private Obsidian dashboard |
| Step 41 — Independent Review & Browser Acceptance | Three security defects confirmed; browser unavailable |
| Step 42 — Security Hardening & Shared Development Step Naming | Three findings fixed; 65 tests/54 mutations; shared canonical naming convention |
| Step 43 — Website UX Refinement & Browser Accessibility | Local refinement validated; rendered acceptance pending |
| Step 43A — Visual Architecture & Cloudflare Website Launch | Partial; browser/Cloudflare pending and separate from the app |
| Step 43B — Local Application MVP | Daniel authorized implementation 2026-10-09, superseding planning-only/after-website scope; local code/build and synthetic tests implemented, real socket/browser acceptance pending |
| Step 43C — Safe Save & Tomorrow’s Handoff | Earlier saved commit/private backup verified by Daniel; newer work remains uncommitted |
| Step 44 — Managed Multi-session Integration and Recovery Hardening | Master directive authorizes engineering; isolated temporary-project implementation and synthetic verification; PTY/native recovery/production acceptance incomplete |
| Step 45 — Cloudflare Pages Deployment Preparation | Superseded by Step 47 (deployed 12 Oct 2026) |
| Step 46 — Consolidation & Live Readiness (12 Oct 2026) | Done. Five checkouts folded into one line (#1); approvals survive reboots (#2); `skeptic ready` gives a live verdict per open agent with the exact continue command (#3, #9); installer retargets its own launcher (#5, #7). Vitals tile shows the verdict with one-tap Continue (ai-search-tracker#119). tests/validate.py passes. |
| Step 47 — Website Launch (12 Oct 2026) | Done. Live at https://skeptic.pages.dev (Cloudflare Pages, direct upload of the 8-file `dist`, no Git connection, no custom domain). Browser acceptance in Chrome: both pages at 1440 and 390/320 px (no overflow), eight-step walkthrough, required-choice errors, Back keeps choices, restart clears, 14/14 FAQ, signup disabled with no submission, no third-party requests, no console errors. Live response headers verified (CSP, nosniff, no-referrer, DENY framing, permissions). |
| Later | Local app visual pass by Daniel (automation cannot load it: extension navigation is cross-site and the app correctly refuses it); native provider acceptance of a full Claude→Codex handoff in Terminal; custom domain; approved beta |

Unverified work is not complete: browser screenshots/accessibility, arbitrary-language
preference conflicts, broader resource/race hardening, platform packaging and provider
integrations. The website is public at skeptic.pages.dev; the product stays pre-alpha. Local app reads only explicitly approved project
folders on demand; no entire-brain scan or automatic note updates. Milestone numbers
are preserved; newer canonical proposals supersede the earlier stale Step 44 label.
