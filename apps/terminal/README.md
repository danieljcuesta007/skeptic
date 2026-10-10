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

## Keep your existing Claude session open

Open a **second Mac Terminal**. The installed launcher works from any directory.
These commands locate home-started sessions, preview locally, launch, and verify:

```sh
skeptic sessions --project "$HOME" --title "Email contact with Boris"
skeptic session handoff --project "$HOME" --title "Email contact with Boris"
skeptic session continue --project "$HOME" --title "Email contact with Boris" --with codex
skeptic session verify
```

Discovery asks permission before listing the approved project's session files or reading
bounded head/tail buffers for title/cwd. Those buffers can contain messages; only metadata
is displayed. Extraction asks separately for the selected transcript. Duplicate matches
use an arrow picker displaying title, timestamp, directory and UUID. `--id UUID` selects
exactly. If it was started elsewhere, use `--project /actual/start/directory`; only use
`--all-projects` if you approve broader metadata discovery. At most 64 newest candidates
are inspected; `--id` narrows before that cap. Missing/expired history cannot be recovered.

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

Returning to Claude from the confirmed project directory:

```sh
cd /your/confirmed/project
skeptic catchup --with claude
skeptic continue --with claude
```

Returning to Codex: use the same commands with `--with codex`. The ordinary `skeptic`
arrow picker also applies catch-up automatically. Local model IDs reported by `skeptic
models` use the same index and engine. Compatibility remains provider-dependent.

If the project stays at home, retain the original session mapping:

```sh
skeptic session handoff --project "$HOME" --title "Email contact with Boris" --with claude
skeptic session continue --project "$HOME" --title "Email contact with Boris" --with claude
```

These re-read the current approved canonical files/Git rather than restoring Friday's
snapshot. To include accessible intervening Codex conversation claims, explicitly select
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
