# Skeptic terminal switcher — Steps 43D / 43F

Skeptic is the layer that lets you change AIs without losing accessible work.
Python 3.9+, Git and an independently installed destination CLI are required.
No dashboard, pip, Homebrew, account setup, service or third-party runtime dependency.

## Use today

Install from ordinary Mac Terminal (also installs the native handoff helpers):

```sh
python3 -B ~/Developer/skeptic/apps/terminal/install.py --upgrade-integrations
export PATH="$HOME/.local/bin:$PATH"; rehash
```

The installer adds one marked PATH line to `.zshrc`; existing terminals need the
export above. It creates an owner-local launcher pointing to this checkout and
refuses to overwrite differing launchers/skills. `--upgrade-integrations` upgrades
only recognized original Step 43D helpers; unknown skills remain preserved. Rerun after moving the checkout;
review an existing differing launcher manually. `--no-profile` avoids shell profile
changes; `--integration claude|codex|none` selects integrations. No admin required.

For repository-only continuation, run this in another Terminal opened at the project:

```sh
skeptic
```

Use Up/Down, Enter to choose Codex; Esc, q or Ctrl-C cancels. Missing CLIs are
visible and cannot launch. Recent selections appear first. Direct alternatives:

```sh
skeptic continue --with codex
skeptic continue --with claude
skeptic status
skeptic doctor
skeptic models
skeptic handoff
```

First use asks for explicit `approve` for the current repository and vault.
Vault approval covers only canonical project STATUS matching, governing files,
the confirmed project's Markdown and exact one-hop linked notes. It does not scan
all vault content or `~/Developer`. No name-only automatic association: one exact
repository reference is automatic; multiple matches use a picker. A missing exact
match permits an explicit mapping or repository-only continuation. Confirmed
mappings and device/inode-pinned read grants persist in `~/.skeptic-cli` until
revoked; replaced roots require reapproval. Dashboard approvals remain separate
and session-scoped. Do not approve a root you do not want read.

```sh
skeptic permissions
skeptic permissions revoke "$HOME/brain"
```

`--vault PATH` selects a different vault; `--task 'specific current request'` is
optional when the request is not saved. `handoff` prints a proposed packet for
review; it never overwrites canonical STATUS or creates a competing checkpoint.
No hidden reasoning, private conversation or inaccessible history is recovered.
Unsaved work remains a clearly reported continuity gap. Selected-session extraction is available with separate explicit local consent (see below).
Only a bounded filtered derived handoff crosses providers; raw transcripts are not uploaded.

Before launch Skeptic prints the project, knowledge match, checkpoint, Git facts,
provider and gaps. It passes bounded context as one positional prompt argument to
`codex -- PROMPT` or `claude -- PROMPT`, in the exact current directory. Interactive
trust and tool permissions remain with the destination host. Authentication/quota
failures return the provider's exit code; Skeptic never authenticates or retries
by bypassing permissions. Selection explicitly requests sending this bounded
context to that provider. `status`/`handoff` never launch one.

## Review multiple Claude sessions without launching a provider

Run the integration checkout directly (the installed launcher may use older code):

```sh
python3 -B "$HOME/Developer/skeptic-managed-integration/apps/terminal/switcher.py" sessions review --project "$HOME" --all-projects --fresh-session-approval
```

Approve only the discovery scope you intend. Across-project discovery reads bounded
head/tail metadata buffers that can contain message text; it is not a live-window inventory.
For a narrower scope omit `--all-projects` and set `--project` to Claude's starting directory.
Use `--id UUID` to narrow to an older known session beyond the 64-candidate discovery cap.

Use the existing arrow picker: Enter toggles a session, then choose **Review selected
sessions**. Select your actual UUIDs; the newest nine are not assumed to be your nine windows.
Toggling keeps the current row and scrolling viewport in the same picker; arrows, resizing
and Esc/q cancellation still work. Rows show a shortened UUID, existing title, update date
and abbreviated recorded directory; selected details retain the full UUID/date/directory.
Each selected transcript receives its own extraction approval. Declining a transcript leaves
its status unknown and allows the remaining selection to be reviewed. Originals stay untouched.
Only after that approval, a bounded user-request excerpt from already extracted records is
offered as an explicitly unverified conversation hint. Untitled review/task headings use it
when available; source titles/files are never rewritten. No extra read or provider call is
made for labels. Untitled sessions without a recoverable hint retain their metadata/UUID
and unknown context; no completion or relevance judgment is inferred from the missing title.

The review retains earlier requests in the accessible parent-linked branch. Direct user requests
form task candidates; a pasted implementation specification remains supporting context for its
enclosing request. Fenced/indented code, quotations, marked source/specification sections, technology
lists and tool/compaction material cannot independently authorize tasks. A wholly directive list
may split into multiple requests when it is not details of an enclosing build; explicit independent
task lists remain separate. Full bounded messages/constraints stay attached as context/evidence.
Clear anaphoric follow-ups (for example "make it smaller" or "use this instead") join the preceding
thread; corrections reopen completion claims. New independent requests remain separate. Cancellations
and replacements retain provenance and require scope confirmation. Ambiguous wording, multiple
possible parent tasks or missing transcript sections remain unknown rather than guessed; unrecognized
wording is retained as context with a gap warning. This is syntax-based recovery, not a semantic guarantee.
Inventories are bounded to the existing 8 MiB snapshot, 1,000 sanitized records / 256 KB,
and 100 task candidates per session. Missing ancestry, unread middle, malformed records,
clipped messages and omitted evidence are limitations; absence is not proof of no work.
Alternate/compacted history may be unavailable. No hidden thinking, attachments or raw
tool input/output is recovered; no additional private session is inferred or read.

Labels are conservative heuristic suggestions, not a semantic audit: completed and verified,
completion claimed but unverified, unfinished, blocked, future idea, or unknown. Assistant
completion claims never become verified completion. Open a task to inspect message evidence,
change its disposition with a reason, or confirm cancellation/supersession. **Completed and
verified** requires your evidence reference and explicit `verified` attestation after checking
current state; Skeptic does not independently establish the outcome. Cancellation/replacement
scope is uncertain until you confirm it. Unlisted compound requests may need manual review.

Starting directory, last recorded directory and actual task project are separate. Choose
**Confirm project and inspect approved current evidence** to confirm the task destination and
reuse existing repository/vault permission gates, safe Git observations and canonical retrieval.
File references are unverified hints, including for home-started or multi-project sessions.
No home scan or guessed permission is introduced. `--conversation-only` disables project reads.

Choose an unfinished/blocked task and **Prepare Codex handoff (preview only)**. Confirm its
destination and exact remaining scope. Skeptic prints the existing filtered packet targeted
to Codex, with earlier-task evidence; it never launches or sends. Source appends/replacements
or revoked grants refuse stale preparation. Before a later separately authorized launch,
refresh the handoff and check all project writers, then preserve the existing `project-clear`
and exact `send` gates. Quota exhaustion/suspension does not establish writer quiescence.

Task classifications/evidence stay in memory and terminal output, with a final recap on exit;
no semantic database, dashboard, project file or card is created. Existing consent and confirmed
destination mappings may be saved in Skeptic's operational state. Esc/q cancels.

Focused synthetic check (includes nine-session real PTY selection/review/earlier-task preview):

```sh
cd "$HOME/Developer/skeptic-managed-integration/apps/terminal"
python3 -B -W error::ResourceWarning -m unittest -v test_session_review
```

## Keep your existing Claude session open

Open a **second Mac Terminal**. Use the integration checkout directly so an older
installed launcher cannot select different code. The commands below discover sessions
under the selected original working directory; set `SOURCE_PROJECT` to that directory
(use `$HOME` for a home-started Claude session).

```sh
SKEPTIC="$HOME/Developer/skeptic-managed-integration/apps/terminal/switcher.py"
SOURCE_PROJECT="/actual/original/working-directory"
PROJECT="/actual/destination/project"
python3 -B "$SKEPTIC" sessions pick --project "$SOURCE_PROJECT" --fresh-session-approval
# Replace this value with the selected UUID after checking its displayed project/cwd.
SESSION_ID="selected-claude-session-uuid"
python3 -B "$SKEPTIC" session continue --id "$SESSION_ID" --project "$SOURCE_PROJECT" --cwd "$PROJECT" --fresh-session-approval --with codex
# After Codex exits and returns you to this shell:
python3 -B "$SKEPTIC" session verify
```

The continuation command displays the complete filtered recovery packet before the
final `send` approval and delivers that same packet as Codex's initial prompt. Check
the destination, recovered objective, omissions and risks; confirm project writers
are clear before typing `project-clear`, then approve the packet with `send`.
No manual copying or separate transcript extraction is needed. A separate preview is
optional: replace `session continue` with `session handoff` and omit `--with codex`.
`session handoff` prints a preview and saves only a verification receipt, never the
packet. Opening Codex independently afterward does not deliver that preview.

Discovery asks permission before listing the approved project's session files or reading
bounded head/tail buffers for title/cwd. Those buffers can contain messages; only metadata
is displayed. Extraction asks separately for the selected transcript. Duplicate matches
use an arrow picker displaying title, timestamp, directory and UUID. `--id UUID` selects
exactly. If it was started elsewhere, use `--project /actual/start/directory`; only use
`--all-projects` if you approve broader metadata discovery. At most 64 newest candidates
are inspected; `--id` narrows before that cap. Missing/expired history cannot be recovered.

The picker stays at the top of the alternate screen and scrolls within the terminal height.
Session titles occupy the list rows; the selected title, timestamp, directory and UUID wrap
in a detail area immediately below the list, using available space. Very small windows show
as much as fits; enlarge the window to reveal more details. Up/Down moves one item (wrapping
at the ends). Resizing redraws within approximately 0.1 seconds without needing a keypress,
and preserves selection. Selection or cancellation restores the previous display and input mode.
Picker-only regression check: `python3 -B -m unittest discover -s apps/terminal -p test_picker.py`
from the checkout root. Tests use synthetic labels and PTYs, without session discovery or providers.
`--fresh-session-approval` asks again for metadata and transcript consent even when a persistent
grant already exists. The handoff command only displays the filtered packet and never launches a
provider. The continue command displays the complete bounded filtered packet, then requires an explicit
`project-clear` response after you check that no Claude/Codex or other agent can still write the
destination, followed by `send` for that exact packet. Skeptic cannot prove unmanaged process
quiescence. If another writer may remain, cancel and choose an already-existing isolated worktree
with `--cwd`; Skeptic never creates a branch or worktree silently.

Omit `--with codex` for the existing provider arrow picker. Approve only desired repository
and vault scopes. A home-started session never grants or scans the entire home directory;
choose a referenced project directory or supply `--cwd /actual/project`. Multiple knowledge
matches require confirmation. Confirmed mappings and grants are reused. `skeptic sessions
revoke` removes session permissions; repository/vault permissions are separately revoked.

The selected source is read-only. Skeptic does not resume, fork, signal, close, delete or
write Claude sessions. Run `session verify` after returning from Codex to the second shell:
it checks the sampled original bytes and permits independent appends. It does not inspect
process liveness; visually confirm the original Claude window remains open. Launch uses
the same safe subprocess/context engine as repository continuation. Initial context is
an argv prompt, so the running provider may retain it according to its normal policy.

Claude JSONL extraction follows the visible parent-linked main branch, includes accessible
compaction/user/assistant text and unfinished TodoWrite items, summarizes tool names/status
and safe file references, and omits hidden thinking, attachments, raw tool input/output.
Source offsets/message IDs/timestamps and hashes accompany evidence. Historical claims are
untrusted; current Git and canonical files are independently observed. Raw snapshot reads
are bounded to 8 MiB; excerpt to 12 KB; total shared packet to 48 KB. Truncation, malformed
records, missing parents and in-flight/unsaved gaps are disclosed. Conservative secret
filtering is heuristic, not a guarantee: review the local preview before sending context.
Transcript instructions never execute in Skeptic; downstream model compliance cannot be
guaranteed by delimiters alone.

Reverse adapter: explicitly select an accessible legacy Codex JSONL file, then use
`skeptic session handoff --source codex --session-file /selected/rollout-UUID.jsonl`
and `skeptic session continue --source codex --session-file /selected/rollout-UUID.jsonl
--with claude` (on one line). No private-history discovery; paginated/app Codex history
is unsupported. The original Codex window also stays open.

## Native integrations: supported helpers

Claude `/skeptic` uses the documented `${CLAUDE_SESSION_ID}` skill substitution to give
an exact-ID second-Terminal command. Already-approved scopes may allow noninteractive
preview via the host's normal tool permissions. Claude capacity is needed for skill
execution; the terminal commands work independently when usage is exhausted. The installed
Claude helper was upgraded; live host invocation remains unverified.

Codex `$skeptic`/skill picker is a helper, not a promised custom slash command. Its updated
source is packaged; use the installer in ordinary Terminal to upgrade the recognized
installed helper. Native tool runners do not provide supported terminal takeover or an
interactive nested provider launch. **No exit from the original session is required.**

## Returning models and bidirectional catch-up — Step 43F continuation

Every Skeptic-controlled launch records a bounded provider-neutral observation in
owner-only `~/.skeptic-cli/transitions.json`. It stores project/root identity, selected
provider/model (cloud model unknown), timestamps, phase/exit code, checkpoint/handoff
references, source hashes, bounded claim hashes, Git fingerprints and safe dirty-file
metadata. Selected incoming session references are labeled as incoming, never invented
as the destination's session. No note bodies, transcript bodies or prompts are stored.
The index is discovery/comparison plumbing; Obsidian remains canonical.

Before leaving Codex, update the project's **existing canonical checkpoint** (normally
its associated `~/brain/03 Projects/<Project>/STATUS.md`, or the established repository
checkpoint). Preserve existing history and unrelated work. Record the current step,
completed work and files changed, pending tasks, decisions with attribution, exact
verification results, unverified claims/gaps, actual Git state and the next action in
the existing Current State/Handoff/Next Actions/Decisions sections. Include important
session-only decisions here: fingerprints and Git status cannot recover them. Confirm
Skeptic's displayed knowledge association points to this checkpoint before returning.

Ask Codex to inspect the actual changes and separate its work from pre-existing changes.
From the second shell, inspect the project again and record its observation:

```sh
cd "$PROJECT"
git status --short --branch
git diff --stat
git diff
git diff --cached
# Inspect relevant untracked files separately; Git diff does not include them.
python3 -B "$SKEPTIC" checkpoint --with codex
python3 -B "$SKEPTIC" catchup --with claude
# Review the return packet above before launching a new Claude session:
python3 -B "$SKEPTIC" continue --with claude
```

`checkpoint --with codex` records a source/Git observation; it does **not** write a
progress summary or update STATUS.md. `catchup` prints the proposed return packet;
it does not launch. `continue --with claude` rereads approved sources and starts a
**new Claude session** with current context. It does not resume or inject context into
the original Claude session, which remains intact. Check the destination is free of
writers before this launch too; repository-only continuation has no `project-clear`
or `send` gate. If files change after preview, rerun `catchup` before continuing.
Returning while Claude is unavailable stops at the checkpoint and reviewed handoff.

Linked worktrees can be used as explicit destinations, but Skeptic currently withholds
Git metadata when `.git` is a pointer file. The direct Git checks above remain necessary;
do not interpret withheld metadata or an exit code of zero as verified completion.

Returning to Codex: use the same commands with `--with codex`. The ordinary `skeptic`
arrow picker also applies catch-up automatically. Local model IDs reported by `skeptic
models` use the same index and engine. Compatibility remains provider-dependent.

The return workflow rereads current approved canonical files/Git. To include accessible
intervening Codex conversation claims, explicitly select
its supported legacy JSONL with `--source codex --session-file PATH --with claude`.
Private histories are never automatically scanned from the transition index. Unsupported
paginated/app history and missing/unsaved transcripts remain reported gaps.

`skeptic checkpoint --with claude` (or another provider ID) records an explicitly
identified current observation without launching; use this for participation outside
Skeptic when useful. `skeptic transitions` displays the bounded operational metadata.
Successful reads/zero process exit do not establish completed work or continuation success.
Failed launches are excluded as participation baselines. Exit captures use existing
permissions only; revocation/moved roots produce an unavailable-checkpoint gap.

The catch-up compares the target's last retained observation with freshly read sources:
changed checkpoint hashes, current Git HEAD/branch/status, dirty-file metadata, intervening
Skeptic transitions, and new/changed source-documented lines. Claims and conflicts require
review. It never executes retrieved instructions, edits notes or restores old files.
Model conversations are incomplete evidence; Skeptic cannot guarantee semantic freshness,
resolve every conflict, or identify exactly when an undocumented decision occurred.

Bounds: at most 64 events within 60 KB; oldest events evicted; 16 source fingerprints,
32 dirty-file metadata candidates, 40 claim hashes (10 per checkpoint section), and a
6 KB catch-up briefing inside the existing 48 KB total packet. Quoted/renamed/directory
Git paths and oversized/out-of-scope sources may be omitted. Missing prior baselines
are disclosed; the index does not grant filesystem/transcript permissions. Metadata
failures/lock contention do not prevent switching with current context.

Selected-session launches now print the exact filtered proposed context and require
`send` before passing it to the selected provider. A changed packet or revoked scope
during review aborts the launch, requiring fresh review. This review is separate from
persistent local read grants and does not accept the destination host's tool permissions.

## Local models and activity

Only existing fixed loopback interfaces are queried: Ollama
[`GET /api/tags`](https://docs.ollama.com/api/tags), LM Studio
[`GET /v1/models`](https://lmstudio.ai/docs/developer/openai-compat/models).
No proxies, redirects, remote endpoints, downloads or service starts. If Codex is
installed, valid reported models appear using its documented `--oss`,
`--local-provider ollama|lmstudio`, `--model` adapter. Model compatibility remains
unverified until used. Custom ports are unsupported today. Cloud CLIs are provider
choices; their configured default models, authentication and quotas are unknown.

Optional `skeptic analytics on` enables owner-only `activity.jsonl`; `analytics off`
disables it. It records Skeptic launch starts and provider exits/failures, provider
or local model ID, timestamp and exit code. No project content, paths, credentials,
tokens, costs, quotas or invented continuation success. Zero exit is process exit,
not proof that continuation succeeded. Logging failure never blocks switching.
The log stops growing at 1 MB; it is not a knowledge store.

## Engine and security

`switcher.py` is the single switching orchestration engine used by the CLI and
native adapters, reusable by future adapters. It uses existing `ScopedEngine`,
`approve_root`, `summarize`, `sections`, `references` and protected exclusions.
The dashboard and CLI both use `app.grounded_packet` for context grounding,
attribution, instruction references, canonical handoff priority and size bounds.
Dashboard source selection remains explicit; terminal selection is automatic
within separately consented scope. Dashboard HTTP authorization is unchanged.

Existing descriptor-based traversal, symlink, hardlink, case-alias, protected-path
and root-identity checks remain. No commands from Markdown, shell interpolation,
project writes, Git reset/stash/commit/push, host approval changes or remote queries.
Git process observation disables global/system config, fsmonitor, hooks and optional
locks, overrides worktree location, refuses filters/includes, metadata links,
alternates and oversized metadata. Those repositories report unknown Git state.
Linked `.git` worktree/submodule pointers are refused today rather than granting
access outside the approved root. Huge dirty lists are explicitly truncated;
protected filenames are withheld. No diff bodies are sent.

Packets are at most 48,000 UTF-8 bytes. Source SHA-256 and modification timestamps
identify the read text; progress claims remain unverified. Canonical STATUS Handoff
and current sections precede historical tails. Truncation/omissions are disclosed;
receiving providers must read referenced applicable instructions fully before acting.
Prompt-injection defenses frame documents as untrusted data and never execute them;
they cannot guarantee a downstream model will follow that boundary. Secret heuristics
are imperfect. Positional prompts can be visible to same-user process inspection and
provider session storage. Same-user tampering and adversarial filesystem/config races
are not eliminated by these application checks. No production security certification.

## Verification and first real acceptance

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B ~/Developer/skeptic/tests/validate.py
```

Automated tests use synthetic repositories/vaults and fake provider executables.
Real pseudo-terminals verify arrows, cancellation and full picker-to-launch flow.
No automated test invokes a real AI provider. Full website/local/discovery/baseline
regressions and builds remain in the validation runner; terminal mutations occur
only in memory.

Real acceptance is the two-window Boris session procedure above. Leave Claude open,
review the filtered handoff in the second Terminal, choose Codex and type `send` only
after approving the context. Verify Codex's current directory, instructions and latest
unfinished action, then visually confirm the original Claude window remains open.
Synthetic success does not establish real provider launch or usable continuation.

Removal: remove only the installed `skeptic` launcher, the marked two-line PATH
addition, the two `skeptic` skill folders and optional `~/.skeptic-cli` settings/log.
Leave canonical project files and other global configuration intact.

## Home-started recovery repair

Use stable `session handoff --id UUID --cwd ACTUAL_PROJECT` rather than assuming storage follows the destination. Add `--conversation-only` for filtered transcript-only recovery; repeat `--repo PATH` for separately approved additional repositories (max four). See `../../docs/ux/STEP43F-RECOVERY-REPAIR.md` for diagnosis and exact acceptance commands. No original Claude response or closure is needed.

## Frozen Claude: same-terminal workflow

User-operated Ctrl+Z returns to the shell with Claude suspended; run `skeptic` to recover a session and pick a destination. `fg` resumes the old process after the destination returns. If suspension is unavailable, use a second Terminal. `/skeptic` is a prompt helper and may be quota-blocked; no automatic takeover. `--model IDENTIFIER` passes a user-selected model safely to its provider without claiming availability. Substantive recovery now omits quota-only tails and quarantines earlier evidence when ancestry is uncertain. See `../../docs/ux/STEP43F-FROZEN-TERMINAL.md` for exact acceptance and limitations.

## Step 43H — Synthetic managed engine

A shared fake-agent PTY engine and CLI are available for isolated temporary fixtures only:
[commands, local interface, acceptance and limits](MANAGED.md). No real provider support,
production-state migration or desktop integration is enabled. Existing recovery stays available.


## One-command Claude → Codex continuation on Mac

```sh
skeptic
```

The installed launcher must point to this integration checkout. Bare `skeptic`
starts `sessions open --continue --with codex --project "$HOME"`; explicit existing
commands retain their behavior. `sessions open` without `--continue` stays review-only.
The launcher activation keeps an exact `~/.local/bin/skeptic.before-integration`
rollback copy and leaves shell profiles/native skills untouched. Restore that copy
to `~/.local/bin/skeptic` to return to the original launcher.

1. Type `discover` to authorize a one-time Terminal.app metadata inventory and its
   rechecks. macOS may request Automation permission. Read window IDs, tab numbers,
   TTYs and busy flags, then restricted per-TTY PID/executable/status and Claude PID
   birth metadata. No screens/history, arguments, environment, keystrokes or window
   control. Other terminal applications are not covered; maximum 128 tabs.
2. Open tabs come first. History is a separate explicit option, never a fallback.
   Known Claude PIDs permit bounded reads of only their exact
   `~/.claude/sessions/<pid>.json` metadata files. Owner/no-symlink/PID/UUID checks
   apply; no registry scan or transcript body reads. A native UUID/name/cwd hint is
   **uncertain**, not automatic proof: the format is undocumented and files may
   be stale. Select the tab and type `confirm` if you recognize the association.
   Multiple records stay distinct. Missing records require pasting an exact UUID
   or transcript path from independently identified original-session information;
   blank cancels. No guess from title, time or directory. PID birth is used only
   to detect changes, never to identify a transcript by timestamp.
3. Type `identify` to recognize work before confirming an association. Only UUIDs
   suggested by open tabs are looked up through existing exact-UUID metadata discovery.
   Metadata/extraction approvals remain separate for each transcript, with valid saved
   approvals reused. No historical conversation picker or extra title-generation reads.
   Conversation titles appear first, followed by window/tab, current TTY and explicit
   uncertainty. Project-directory, UUID and activity metadata stay in selected-row details;
   the selected row's first
   detail shows a bounded last recorded user-request excerpt. Each is explicitly a
   **candidate transcript, association unconfirmed**. Native cwd is a hint; recorded
   transcript cwd is observed metadata, not proof of the current project root. Untitled
   sources still show approved request hints; window/tab/UUID preserve distinct identity.
   Missing/declined/changed candidates show unavailable hints. Identification is offline
   and in memory, with at most the existing 8 MiB per separately approved source. Exact
   duplicate UUID hints reuse one profile, and unrelated transcript bodies are not read.
   After selecting the recognizable candidate, type `confirm` only if you can establish
   its window/UUID association. Otherwise type `transcript` to select the recognized
   conversation independently: window association stays UNCONFIRMED and source/writer
   state UNKNOWN in the handoff. Actual project and writer approvals still apply.
   The displayed `Last login` message describes a previous login, not a live TTY check.
4. Existing discovery and selected-transcript approvals apply independently.
   Review the recovered task inventory and select the work to resume. Claude
   saying done remains unverified. Future/canceled/superseded tasks require separate
   scope clarification through `sessions review`. Unknown tasks instruct Codex to
   clarify missing scope before implementing; no hidden/unsaved context is claimed.
5. Choose continuation (default) or preview. Confirm the actual project/worktree;
   repository and canonical knowledge approvals remain required. The packet includes
   the selected request/context, other task statuses/evidence gaps, bounded conversation,
   current safe Git observations and approved canonical sources. It explicitly requires
   Codex to reconcile completion claims and preserve existing work.
6. Review the final exact packet. Inspect original Claude and other writers yourself:
   a quota limit, idle/busy metadata, or an open tab cannot prove tools have stopped.
   Type `project-clear` only if the destination cannot have another writer; otherwise
   cancel or explicitly select an already-existing isolated worktree. Type `send`
   to authorize this packet and the Codex launch. Original windows remain intact.

The production selected-session handoff adapter (`launch_recovery`/`tracked_launch`)
is reused. It launches native Codex interactively in the operator Terminal; native
trust/auth/tool approvals still apply. Source bytes/grants/project evidence and open
source metadata are rechecked; source appends or changes refuse stale launch. A
cooperative reservation serializes these CLI writers sharing the same consent state
while the launching CLI remains alive. A frontend crash releases the reservation even if a provider survives; fresh manual writer checks remain necessary. It cannot detect unmanaged/escaped tools, differently
configured state roots or old launchers. No process is adopted, suspended or terminated.
A native record reporting busy refuses continuation.

**Managed supervisor limitation:** the separate `managed start`/switch PTY supervisor
remains restricted to temporary fixtures. Production continuation uses the proven
handoff adapter, not an expanded supervisor authorization. Future managed Claude
launch receipts already retain an explicitly assigned native UUID; this does not
retroactively identify unmanaged tabs. The documented Claude status-line input also
provides `session_id`/`transcript_path`, but no hook/settings change is installed here.
[Claude status-line schema](https://code.claude.com/docs/en/statusline).

Direct checkout command (no installation needed):

```sh
python3 -B "$HOME/Developer/skeptic-managed-integration/apps/terminal/switcher.py" sessions open --continue --with codex --project "$HOME"
```

Synthetic PTY tests cover discovery-to-approved fake-provider continuation; actual
GUI Terminal metadata and a real Codex conversation must be accepted separately.
Automation/process denial reports the limitation and never guesses or automatically
browses history. In a GUI-inaccessible tool runner, even the running-app probe can
return no visible tabs; that does not prove the desktop has no Terminal sessions.

## Step 44 — Managed integration under acceptance

An isolated implementation adds Claude/Codex launch contracts, durable startup/switch
journals and current/selected/all managed scopes. Temporary state/projects only; active
sources are excluded and native recovery acknowledgement is unsupported. New engine PTY
acceptance is blocked by this session's socket sandbox. See [current commands and exact
limits](MANAGED.md). Historical Step 43H results do not validate this changed implementation.
