# Step 43F — Session-Aware Continuity · 2026-10-09

## Unified continuation — Bidirectional Catch-Up + Step 43E acceptance · 2026-10-09

**Latest verified result: 255 tests / 210 planted faults; both builds passed.**
This extends Step 43F; the earlier 227/182 report below is historical evidence.

Daniel's permanent principle: **Skeptic isn't the AI. Skeptic is the layer that lets
you change AIs without losing your work.** Obsidian remains canonical; the dashboard
is a companion. No dashboard is required to switch or catch up a returning provider.

DONE: automatic provider-neutral catch-up through the existing assemble/launch engine;
`catchup --with PROVIDER` preview, `checkpoint --with PROVIDER` for explicitly identified
participation, and `transitions` metadata inspection. Owner-only transitions.json stores
root/project identity, provider and known local model ID (cloud model unknown), event
and source-observation timestamps, incoming selected-session references, checkpoint /
handoff references, source/claim hashes, bounded Git/dirty-file metadata, gaps and exit
status. It stores no note bodies, transcript bodies, prompts or competing project memory.

Returning providers receive freshly approved sources, changed checkpoint/HEAD/branch /
status/file metadata, intervening Skeptic transitions and attributed new/changed claim
lines. Source-documented completion and session claims remain unverified. Changed or
conflicting checkpoints require reconciliation; old files/handoffs are never restored.
Current untracked files inside existing directories are individually observed; protected,
quoted and renamed filenames are withheld. Missing canonical notes/transcripts, unsupported
Codex paginated/app history, ongoing unsaved work and evicted baselines stay disclosed gaps.
No automatic private-session scanning from the index. Select a supported intervening
transcript explicitly to include its accessible claims. Original windows remain intact.

Security refinements: exact selected-file metadata consent for reverse Codex JSONL;
secrets filtered from source excerpts, explicit task text and Git display; session launches
show the exact filtered packet and require `send`. Revoked scopes or a changed packet
during review abort launch. No unsafe provider flags, host permission acceptance, auth,
original-session writes/signals or arbitrary Markdown/transcript execution.

Bounds: 64 events within 60 KB, 16 source fingerprints, 32 dirty-file metadata candidates,
40 checkpoint-line hashes (10 per section), 6 KB catch-up within the existing 48 KB packet.
Old entries may be evicted; metadata-only comparisons cannot prove semantic freshness or
completed work. Filtering is heuristic; review real handoffs. Index corruption/contention
warns and leaves current-context switching available; it does not overwrite invalid state.
Provider nonzero exits and failed launches are recorded without inventing continuity success.
Post-exit capture uses existing grants only; home-started captures require an explicit
session and never scan home as a repository. Cross-session filesystem races remain a limit.

VERIFIED: full current-checkout `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate.py`:
- Terminal: 105 tests (46 base, 34 session, 25 catch-up); 20/25/27 fault checks.
- Migration 1; website 18; local Python 73; local UI 4; discovery 36; baseline 18.
- Total 255 tests / 210 deliberately planted faults. Each of 28 new regressions failed
  under its associated fault; the Codex sibling-grant regression also reproduced before fix.
- Both website/local builds, JS syntax and source diff checks passed. Synthetic Claude →
  Codex → Claude, Codex → Claude → Codex, local model identities, stale/conflicting context,
  dirty/untracked changes, safe fake-provider launch, failure handling, attribution, context
  limits, revocation and original-session preservation verified. No real AI in tests.
- Installed launcher help exposes the new commands. Claude Code 2.1.296 / Codex 0.162.0
  detected; auth/quota/cloud model unknown; no configured local model reported.
- Log: `/private/tmp/skeptic-unified-validation-final.log` (ephemeral local evidence).

Step 43E preserved. Current full regression includes all quota freshness/manual persistence,
individual deletion and renderer checks. App startup and socket smoke reattempted; localhost
binding denied. No available browser control capability; **live browser acceptance did not
occur**. No real quota extraction repeated in this continuation. Historical local quota
extraction/user-confirmed Vitals evidence remains separate; Vitals unchanged. Follow the
exact Model Usage checklist in apps/local/BROWSER-ACCEPTANCE.md and README.md.

NOT VERIFIED: real Boris-session existence/access, real Codex/Claude transition, live native
helper invocation, end-to-end user continuation, dashboard browser behavior. No real history
read without explicit approval. Native `/skeptic` is a supported Claude helper directing the
second-Terminal workflow; it cannot replace Claude's TUI. Codex uses `$skeptic`/skill picker;
a custom slash takeover is not claimed. Updated Codex helper installation remains a normal
Mac-Terminal action; it is not installed into protected ~/.agents by this continuation.

Exact first acceptance, keep original Claude open and use a second Mac Terminal:
```sh
python3 -B ~/Developer/skeptic/apps/terminal/install.py --upgrade-integrations
export PATH="$HOME/.local/bin:$PATH"; rehash
skeptic sessions --project "$HOME" --title "Email contact with Boris"
skeptic session handoff --project "$HOME" --title "Email contact with Boris"
skeptic session continue --project "$HOME" --title "Email contact with Boris" --with codex
```
Approve only intended printed local scopes, confirm project/knowledge, inspect the filtered
handoff, then type `send`. Omit `--with codex` to use arrows. Confirm Codex's cwd, instructions
and latest unfinished work; visually confirm Claude remains open. `skeptic session verify`
after returning from Codex checks original sampled bytes, not process liveness.

Switch back in another Terminal at the confirmed project directory (leave Codex open):
```sh
cd /your/confirmed/project
skeptic catchup --with claude
skeptic continue --with claude
```
For a home-based project, use the original source mapping:
```sh
skeptic session handoff --project "$HOME" --title "Email contact with Boris" --with claude
skeptic session continue --project "$HOME" --title "Email contact with Boris" --with claude
```
These re-read current canonical sources/Git. If intervening conversation is needed, use
an explicitly approved legacy Codex file with `--source codex --session-file PATH --with
claude` on one line. No manual prompt reconstruction. Save important new decisions in
canonical notes through the existing reviewed workflow; Skeptic never silently updates them.

Future model intelligence remains a design path: measured Skeptic events/process exits,
provider-reported quota/export data and explicitly entered preferences. Task recommendations,
cost/speed comparisons and perceived reliability must distinguish measured facts from
subjective judgments. No speculative recommendations, usage costs or quotas implemented.

FILES: apps/terminal/continuity.py, switcher.py, sessions.py, test_continuity.py,
mutation_continuity.py, test_sessions.py, mutation_sessions.py, README.md;
tests/validate.py; apps/local/BROWSER-ACCEPTANCE.md and README.md; Step43E/43F reports;
canonical STATUS/development-dashboard/Handoff. Step43E app/UI/storage implementation unchanged.

SESSION: main HEAD 3a188b8293a5f13141776a5691acf0e81a109233, empty index, pre-existing
tracked dirty and untracked work preserved. Implementation used an isolated detached worktree,
then per-file hash guards before copying scoped edits back. No commits/pushes/merges/deploy,
other real-project edits, Vitals changes or real session/provider access. Stop implementation;
next is the approved real two-window Boris-session acceptance.

---

DONE: read-only consent-gated Claude JSONL discovery/selection; home-started session
support; active-branch user/assistant/compaction evidence, tool summaries, unfinished
tasks and safe file references; conservative secret filtering; approved vault/Git
association through the shared engine; preview, arrow picker, safe Codex/Claude launch
and snapshot verification. Original windows never resumed, forked, closed or signaled.
Explicit-file legacy Codex reverse adapter included; paginated/app history unsupported.

VERIFIED: `python3 -B tests/validate.py` passed: 227 tests and 182 planted faults,
including 31 new session tests / 24 new session faults. Both asset builds passed.
Synthetic PTY chooses fake Codex, checks argv/cwd/context, and preserves an independently
running original fixture session and its file. No real provider launched by tests.
Installed launcher/help/models and upgraded Claude helper verified locally; detected
Claude Code 2.1.296 and Codex 0.162.0, auth/quota unknown; no configured local model
reported by terminal detector. Source diff check passed. Log:
`/private/tmp/skeptic-session-final-validation.log` (local ephemeral evidence).

NOT VERIFIED: real “Email contact with Boris” existence/transcript, real Codex launch,
real Mac two-window acceptance, live native helper invocation. User's real history was
not accessed: explicit scoped approval remains required. Updated Codex skill source is
packaged; installation into protected ~/.agents must run from ordinary Mac Terminal.

Security: separate persistent inode-pinned metadata and selected-transcript consent;
revocation checked before launch; no symlinks, hardlinks, special files, traversal or
case aliases; home never scanned as repository. Metadata buffers can contain messages,
disclosed before consent. Read limit 8 MiB, session excerpt 12 KB, shared packet 48 KB.
No raw tool commands/results, thinking, credentials intentionally retained or executed.
Filtering is heuristic: review preview. Prompt boundaries reduce exposure but do not
guarantee downstream model compliance. Appended/in-flight/missing/partial history is
disclosed; verification proves sampled bytes, not process liveness. Handoff enters the
selected provider as an argv prompt and follows its normal retention/permission rules.

Daniel's explicit new mission authorizes selected, filtered derived session evidence
subject to explicit history approval; this supersedes the earlier protocol's blanket
cross-provider transcript-copy exclusion only for that bounded evidence. Canonical
STATUS/governing instructions remain authoritative. Raw transcripts are not copied.

Installation in Mac Terminal:
```sh
python3 -B ~/Developer/skeptic/apps/terminal/install.py --upgrade-integrations
export PATH="$HOME/.local/bin:$PATH"; rehash
```
Keep Claude open; in a second Terminal:
```sh
skeptic sessions --project "$HOME" --title "Email contact with Boris"
skeptic session handoff --project "$HOME" --title "Email contact with Boris"
skeptic session continue --project "$HOME" --title "Email contact with Boris" --with codex
# After returning from Codex to this second shell:
skeptic session verify
```
Approve only the displayed intended local scopes. Confirm inferred directory/knowledge;
use `--cwd /actual/project` if needed. Duplicate titles prompt selection; `--id UUID`
narrows precisely. Omit `--with codex` for arrows. Verify Codex cwd, instructions and
unfinished request; visually check original Claude still open. No manual prompt copy.

Claude `/skeptic` is a supported personal skill with documented session-ID substitution,
guiding an exact-ID second-terminal transfer. It cannot take over Claude's terminal and
requires remaining Claude capacity. Codex `$skeptic`/skill picker is the supported
helper, not a custom slash command. No host permissions bypass or nested interactive
provider. The independent CLI works with exhausted Claude capacity.

References: [Claude local directory](https://code.claude.com/docs/en/claude-directory),
[session behavior](https://code.claude.com/docs/en/sessions),
[read-only SDK sessions](https://code.claude.com/docs/en/agent-sdk/sessions),
[skills/session-ID substitution](https://code.claude.com/docs/en/skills).

FILES: apps/terminal/sessions.py, switcher.py, install.py, test_sessions.py,
mutation_sessions.py, README.md, skeptic-claude.md, skeptic-codex.md;
apps/local/app.py shared formatter only; tests/validate.py; this report;
canonical STATUS/development-dashboard/existing Handoff; known Claude skill/launcher.

SESSION: main HEAD 3a188b8293a5f13141776a5691acf0e81a109233. Existing dirty website,
local-app, Step43E usage and unrelated documentation preserved. No commits, staging,
pushes, deployments or modifications to other real projects. Step43D/E history and
43A/44/45 plans preserved. Implementation stops here; next action is real acceptance.
