# Step 43E — Model usage dashboard

Daniel requested the desktop Claude/Codex usage ability in the Skeptic board, with a
model/tool list including Hermes and Midjourney. This locally implemented slice adds
a usage page, not model execution or authentication.

## Implemented

Provider/tool picker, separate quota units, remaining allowances, primary/secondary
window labels, local reset dates, explicit last-seen/manual sources and timestamps.
User-enabled bounded Claude/Codex activity reads and disconnect; no auth or cloud
calls. Multi-model manual readings persist owner-locally and can be individually
removed. Unknown/expired data never becomes an invented zero or full allowance.

## Verification and limits

Synthetic quota/state and real HTTP-parser regressions; planted faults; asset build
and JavaScript syntax checks. Real local quota metadata reading verified without
returning conversations. Exact latest validation is recorded in canonical STATUS.
Localhost binding denied here; actual browser rendering and restart persistence must
be checked in ordinary Terminal. Other providers require manual readings. Live
provider adapters, account authentication and model switching are not implemented by
this page. Existing terminal switching and project permissions remain independent.

## Startup

Stop the existing Skeptic local server using Ctrl-C in its Terminal. Run:

```sh
python3 -B ~/Developer/skeptic/apps/local/app.py
```

Reload http://127.0.0.1:4317, open Model usage, and choose Connect local Claude & Codex
readings. See apps/local/README.md for units, manual readings and acceptance steps.

Existing dirty source work was preserved with narrow edits; originals of four local
UI/host files were copied to temporary scratch before modification. No commit, push,
merge, deployment, credentials, provider priorities or native-widget changes.

## Unified Step 43F continuation acceptance update · 2026-10-09

Full current repository validation: 255 tests / 210 planted faults and both builds
passed, including all existing usage freshness, owner-only persistence, multiple-label,
individual deletion and production-renderer regressions. Usage implementation and Vitals
widget unchanged. App startup/socket smoke retried; localhost binding denied, browser
control unavailable. No browser acceptance or fresh real quota extraction claimed.
Exact manual checklist: apps/local/BROWSER-ACCEPTANCE.md, Step 43E section. Original
local quota extraction/user-confirmed widget evidence above remains historical.
