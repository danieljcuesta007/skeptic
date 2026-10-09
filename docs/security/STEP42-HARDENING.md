# Step 42 — Security Hardening & Shared Development Step Naming

## Objective and outcome

Fix S41-01/02/03, preserve the existing architecture/history, and establish shared
project step numbering in canonical Markdown. Completed locally on synthetic fixtures;
no live provider integration, brain scan, remote, push or deployment.
The pre-existing Step 41 report is preserved unchanged and included in the local commit.

## Before / after evidence

Executed the synthetic Python reproduction in STEP41-REVIEW.md before edits:
`handoff_leak True`, `malformed_cache_exception TypeError`,
`case_insensitive_fixture True`, `protected_alias_returned True`.
After fixes: `handoff_leak False`, `malformed_cache_exception Denied`,
`case_insensitive_fixture True`, `protected_alias_returned False`.
No synthetic token bodies were printed.

| Finding | Fix | Evidence |
| --- | --- | --- |
| S41-01 HIGH | Casefolded NFKC exclusion matching, exact directory-entry names before body opens, host-policy filtering of all cached records | Case-alias/cache/catalog tests; excluded body reads absent; actual case-insensitive fixture |
| S41-02 HIGH | Freshness and shared credential quarantine before governing handoff/preference output; fresh passage quarantine even for forged digests | Stale safe handoff withheld; credential handoff withheld with original/forged hashes; forged passage quarantined |
| S41-03 MEDIUM | Cache envelope/record/type/size validation before refresh, retrieval and public governing revalidation; generic Denied rejection | Malformed types, paths, metadata and bounds rejected before source reads; no external fallback |

Cache loading is bounded to 32 MiB and rejects symlinks, special/hard-linked files,
duplicate JSON keys, non-finite values, null/non-object JSON and excessive nesting.
Invalid caches require explicit inspection/rebuild; they do not silently expand scope
or invoke another provider. Revoked/protected or non-Markdown ordinary cache records
are ignored rather than consulted. Config remains trusted host authorization.

## Related checks

Preserved regressions cover all modes, catalog role/root tampering, scoped unauthorized
reads, symlinks/hardlinks, stale selected passages, policy changes, private cache files,
Git-destination refusal and no network/process calls. New tests cover case aliases,
noncanonical instruction aliases, malformed records, protected filenames, stale and
credential-bearing handoffs, poisoned cache passages and no external error fallback.
Direct governing revalidation also rejects stale policy/project cache decisions.

Exclusion checks occur before note body opens. Exact-name checks use pinned directory
descriptors. Ordinary notes cannot assign roles or execute code through this engine.
Cache ranking can still be poisoned/omitted; hashes are not cache authentication.

## Validation

Full `python3 -B tests/validate.py` passes:

- Website build: 7 files; 10 Node tests passed.
- V2: 24 existing + 12 new security tests passed (36).
- V2 mutations: 24 existing + 12 new targeted faults caught (36).
- Preserved V1: 18 tests passed; 18 faults caught.
- Migration demo: 1 test passed.
- Total: **65 tests passed / 54 mutations caught**, zero final suite failures.

Every new regression failed under a corresponding in-memory fault. Existing mutation
anchors were updated for the factored credential helper and layered cache scope guard;
no previous regression was removed. Two early ad-hoc commands had incorrect working
paths; they failed before running the intended suite and were corrected. Final full
validation succeeded. Tests are evidence for these boundaries, not certification.

## Shared naming and continuity

The canonical convention is added once to `~/brain/AGENTS.md`; the existing
`~/brain/CLAUDE.md` now points to it. Current entry inspection shows Codex's existing
shared-context block references brain/AGENTS; Claude's existing entry symlink resolves
to brain/CLAUDE. Static reference traversal verifies discoverability through both.
The old AGENTS claim that both global AGENTS entry files are symlinks was corrected
from filesystem evidence; entry files/symlinks/configuration were not altered.
No live fresh-Claude acceptance is claimed. Existing recap, handoff, session-switch,
privacy and mandatory Claude PR review requirements remain intact.

Step numbers belong to projects across providers/sessions. Read canonical STATUS,
resume interrupted work, never invent completion or reuse a number for unrelated work.
Checkpoints/recaps include number/title, objective, outcomes, evidence, issues, Git state
and next step. The reusable development checklist now reflects this convention.
The private canonical instructions are not copied into public source configurations.

## Remaining limitations / release gates

- Plaintext indexes contain sensitive derived content and filenames. Owner-only files
  do not solve same-user access, backups, retention or encryption.
- The credential regex remains incomplete and may falsely exclude benign text. No
  sanitizer guarantees arbitrary secrets are detected; protected path policy is primary.
- Cache schema validation is not authentication; a hostile valid cache can rank/omit
  authorized sources. Complete resource/large-vault performance acceptance is pending.
- Conservative Unicode/case matching can overexclude. Alias checks add enumeration
  cost. Full concurrent directory/root/parent replacement race hardening is not proven;
  index persistence still uses pathname-based operations after parent checks.
- No OS sandbox or downstream prompt-injection enforcement; provider capabilities,
  data handling, installers/uninstallers and real brain operation remain unverified.
- Real-browser desktop/mobile/accessibility acceptance and screenshots remain pending.
  No live fresh-Claude test or production security certification occurred.

## Git and next action

Starting `main` at `e92253d8c0bd59b11106bd764d1227ec6805c11c`, with only the
untracked Step 41 report. One reviewed local Step 42 commit includes that report and
related source/tests/documentation; no remote or history rewrite. The resulting full
commit is recorded in the canonical project STATUS/dashboard and final recap rather
than recursively embedded in this committed file. Brain HEAD/index remain unchanged;
only shared AGENTS/CLAUDE and the authorized project STATUS/dashboard are edited there.

**Next recommended: Step 43 — Browser Experience & Accessibility.**
Then **Step 44 — Private GitHub & CI Setup**. Both remain proposals requiring the
next task's authorization. Preserve Claude `/code-review` and posted "Review by Claude"
before any PR merge; this Codex work does not satisfy that gate.
