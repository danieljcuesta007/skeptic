# Step 43F recovery repair — 2026-10-09

Session identity/storage, original cwd and selected project roots are independent.

## Diagnosed failures

The installed launcher points at this repository's switcher. Failure 1 is raised by `repository()` when a selected destination has a regular `.git` entry. Inspection of ONLY the local transition mapping for session `2be6a8f6-18ee-4a9b-b6dc-693511b2275a` found its saved destination was `~/.worktrees/brain-model-blind`. A metadata-only lstat confirmed a regular `.git` file there. No pointer content was read/followed, no transcript was read. This was not a claim that HOME was a Git repository.

Failure 2 came from `ClaudeAdapter.discover()` constructing the storage bucket from `--project`, before opening it. The home-launched session remains in the home bucket, regardless of work in Skeptic. Missing buckets now explain the distinction instead of exposing raw Python errors.

## Repair

`--id UUID` requests consent-gated storage metadata discovery independent of `--project`. Only matching UUID files have bounded metadata buffers read; other session bodies are not opened. Actual discovered bucket/path is retained for extraction and preservation checks. Root discovery permission and selected transcript extraction permission remain distinct. Missing/moved/inaccessible files never authorize permission expansion.

`--cwd PATH` explicitly overrides a saved destination. Conversation recovery can proceed if project/Git verification is unsafe/unavailable; unsafe pointers remain unfollowed. `--conversation-only` skips project/Git/vault reads entirely while retaining bounded, filtered, attributed selected-session evidence and disclosed gaps. Home remains unscanned. Conversation claims are not verified project facts.

For work across repositories, repeat `--repo PATH` (maximum four). Each extra root requires its own existing read approval; instructions/status and safe Git observations are bounded and attributed. Unsafe extra metadata is withheld. Session references remain unverified candidate hints; selecting a destination does not authorize reading it. No automatic home/repository scan.

## Real Mac acceptance — original Claude stays open

The installed CLI already uses the current source. Run in a second Terminal:

```sh
export PATH="$HOME/.local/bin:$PATH"
skeptic session handoff --id 2be6a8f6-18ee-4a9b-b6dc-693511b2275a --cwd "$HOME/Developer/skeptic" --conversation-only
```

Approve metadata scope and the intended transcript when requested. Review the conversation-only preview: correct title/ID, original home cwd, latest unfinished request, source attribution, omissions and unverified Git state. No provider launches.

Then preview with separately approved project/canonical evidence:

```sh
skeptic session handoff --id 2be6a8f6-18ee-4a9b-b6dc-693511b2275a --cwd "$HOME/Developer/skeptic"
skeptic session continue --id 2be6a8f6-18ee-4a9b-b6dc-693511b2275a --cwd "$HOME/Developer/skeptic" --with codex
```

Review the exact filtered outgoing context and type `send` only if it is correct. No Codex launch before approval. After launch confirm Codex's cwd and latest unfinished task, and visually confirm the original Claude window remains open. `skeptic session verify` checks sampled original transcript bytes, not process liveness; a live Claude append may require a fresh preview.

Secrets filtering is heuristic: inspect the real preview for sensitive omissions before cloud transfer. No hidden reasoning, unsaved state or completeness guarantee. Full raw transcript is never sent automatically.

## Actual verification

Final full repository validator passed: **268 tests, 216 planted faults caught**. Website and local asset builds passed. No real transcript/provider reads or provider launch occurred. Synthetic fixtures cover recovery and preservation; prior security/catch-up regressions remain passing. Main HEAD 3a188b8, index empty; prior dirty/untracked files preserved.

## Real acceptance repair — 2026-10-09

Daniel reports Ctrl+Z suspension, same-terminal Skeptic/Codex launch, approved project
and Obsidian reads, reviewed handoff and preserved files. Task recovery FAILED: command
stdout was selected; review notifications appeared as user requests. This is reported
acceptance evidence, not an independently observed process test.

Read-only diagnosis of the exact authorized transcript found 482 records / 1,677,815 bytes
within the snapshot limit. Full parent traversal reaches 306 records including original
brief; attachment filtering caused a false gap. Generated user-role command/notification
bodies passed substantive_request. Request clipping discarded the closing constraints.

Repair constructs the scoped structural graph before display filtering; attachment and
unknown structural bodies remain excluded. Generated messages are excluded as instructions.
Original/latest recorded requests and last visible assistant work remain attributed and
unverified. Long requests retain head/tail with omitted byte ranges and source references.
Current unfinished status is explicitly NOT established; newer canonical state must be
reconciled. Recovered text grants no execution authority. Preview begins with readable
recovery/Git summary; `evidence` displays the exact outgoing packet and its hash. Snapshot
verification, consent renewal and identical-packet check still gate sending.

Synthetic regressions first reproduced five failures against old behavior (two negative
controls already passed). Added structural/notification/preview coverage and exact reviewed
packet versus fake-provider received-prompt assertion. Validation results recorded below
after completion. No real provider launched; no unrelated sessions read; original untouched.
Next milestone design: ../architecture/UNIFIED-TERMINAL.md (proposal only).

Final verification: **296 tests passed / 225 planted faults caught**, complete validator finished successfully;
website/local builds passed; all configured mutation suites caught their faults
(including nine frozen/recovery-classification faults). Focused frozen suite: 27 tests.
Initial full run exposed a PTY test waiting for changed prompt text; prompt compatibility
restored. Later runs exposed mutation-target drift after source changes; mutation targets
updated, checks retained. An attempted classification mutation was ineffective because
another guard still blocked generated records; corrected mutation is now caught.
Final full run: /private/tmp/skeptic-validation-approved.log (temporary local evidence).
`git diff --check` passed; preexisting tracked changes retained; index remains empty.
No commit, push, deployment, global permissions or managed terminal changes.

Read-only repaired extraction of the exact authorized real session: original brief head/tail
and last substantive assistant work found, false quota/notification candidates absent,
chain_gap=false; 11,565-byte excerpt at that check, truncation explicitly true. This verifies
extraction, not repaired live end-to-end sending or whether historical work is still unfinished.
Canonical STATUS Current State/Handoff/Next Actions/Recent Work updated with results and proposal.
