# Step 43B — Unified workspace continuation

A local, read-only bridge between your existing Obsidian knowledge and approved local
Git repositories. No editor, duplicate vault, provider connection or cloud service.
Python 3.9+ on POSIX; standard library only. Node 18+/npm are needed for full repository
validation, not to run the app.

```sh
python3 -B ~/Developer/skeptic/apps/local/app.py
```

Open **http://127.0.0.1:4317**. Stop with Ctrl-C. Restart an older running process to
load the upgraded assets. Do not stop another person's process. From another clone,
run `python3 -B apps/local/app.py` in its repository instead.

Approved identity: black #000000 and white #FFFFFF, with supporting neutral grays.
“Not everything is black and white.” Primary CTAs are black/white, secondary controls
white/black, with visible focus and text-based status labels.

## Connect and resume

1. Choose **Connect My Workspace** → Obsidian vault. Paste your exact vault path
   (for Daniel: `~/brain`). Review exclusions, select a policy and explicitly approve.
2. Connect a **Local Git repository root** separately (a repository itself or its
   parent folder). Additional project locations use their own approvals.
3. Select an existing project in **All Projects**. Review attributed state, pending
   work, canonical STATUS Handoff, source hashes, instructions and missing information.
4. Repository association requires an exact path in frontmatter `paths:` or an explicit
   repository/product-source/work-location label. Exact evidence is displayed. Multiple
   matches and name-only matches require clicking **Confirm suggested match**.
5. Open **Resume work**, review the selected sources, then **Continue with Claude Code**
   or **Continue with Codex**. Review and copy the generated prompt yourself.

Sidebar: All Projects, Recent Projects (session only), Knowledge Sources, Repositories,
Handoffs, Permissions, Activity. Legacy individual-folder registrations remain visible
as additional project roots and can be reapproved without reconstructing their notes.

**READY TO RESUME** means STATUS contains Current State, Next Actions and Handoff and
there is no unresolved repository suggestion. It is not proof of freshness/completion.
**NEEDS REVIEW** means checkpoint context or association needs review; **MISSING
CHECKPOINT** means no exact STATUS; **NOT CONNECTED** marks an approved repository
without associated knowledge. Repository-only prompts require knowledge sources first.
Current milestone/completed work remain literal attributed source excerpts, never
inferred dates or percentages. Canonical STATUS Handoff comes first; standalone
handoff files are ordered by modification time, which does not prove semantic recency.

## Policies and privacy

- **FULL_BRAIN** (preferred default): fresh local search of eligible Markdown inside
  approved roots, including supporting knowledge. It grants no upload, edit, provider
  access or access outside the roots.
- **PROJECT_SCOPED**: enumerate eligible paths and read discovered project folders plus
  governing instruction files; unrelated knowledge bodies are not read.
- **ASK_TO_EXPAND**: read exact project STATUS checkpoints and recognized instructions
  only. Other file bodies require a separately approved policy change.

Policies are shown in onboarding, project cards/details and Permissions. Changing a
root/policy always requires an explicit approval checkbox. Parent PRINCIPLES/AGENTS/
CLAUDE files are included only within approved boundaries. Exact relative/wikilinks
and absolute local Markdown links resolve only to safe sources already eligible under
approved roots/policies; unresolved or unapproved links remain unknown. No basename
search, URL fetch or implicit expansion occurs. Nested instructions remain references:
receiving tools must determine applicability and read the full files.

Permissions → **Disconnect root** revokes access, removes its registration and clears
session associations. **Remove project** hides that candidate for this session; its
root permission remains, as the UI states. Root disconnection is the access-revocation
control. Source files are never changed. All saved roots need fresh approval after
restart. Confirmed associations and recent/hidden projects last only for this session.

Only ignored owner-only `.skeptic-local/projects.json` stores paths, exclusions, source
kinds and policies. No note content, prompts, derived index, sync state or second memory
is persisted. Startup does not scan saved roots. Legacy routes cannot bypass policies
on workspace roots. Local browser API responses contain only bounded authorized
excerpts; there is no raw-file endpoint or unrestricted vault serving.

Step 42 engine reads/exclusions remain in place: exact-case/no-follow ancestry and
pinned roots, traversal/link/hardlink/special-file refusal, protected normalization,
credential quarantine with names withheld, bounded reads. Credential/cache/private
folders are excluded. Fixed 127.0.0.1, exact Host/Origin/CSRF token, CSP/no-store/no CORS,
three public assets only. Markdown is rendered with textContent, never executed.
Git inspection reads only bounded HEAD, exact branch refs and packed-refs using safe
file descriptors. No Git executable, hooks, configs, remote queries or commands run.
Branch/commit are observations; working-tree dirtiness and GitHub freshness are unknown.

Workspace bounds: 10 active roots, 100 knowledge projects, 50 repositories per root,
2,048 Markdown files / 12,000 entries / depth 16 / 16 MB per knowledge root,
20 MB and 4,096 safe source reads across the inventory; 128 KB/file. Repository scans
use 4,000 entries/depth 8 per root. Excerpts and prompt limits from the original MVP
remain bounded; linked external sources are capped at 30. Over-budget operations fail
explicitly. A large vault may need narrower approved roots; no partial completeness is
claimed. Additional exclusions can only reduce access.

Remaining limits: pasted paths rather than a native picker; no semantic freshness or
conflict resolution; literal Markdown parsing can include quoted/fenced examples;
exact path-based associations only, no remote matching; bare repositories and linked
worktree/submodule .git pointer files unsupported. No working-tree status, automatic
memory updates, editing, provider launches, sync or APIs. Same-user access, incomplete
secret heuristics and broader concurrent filesystem races remain security limitations;
independent review and production certification are outstanding.

## Validation and browser acceptance

```sh
python3 -B tests/validate.py
python3 -B apps/local/network_smoke.py
python3 -B apps/local/workspace_fixture.py
```

Full final synthetic validation: **133 tests / 121 planted faults caught**, website
8-asset and local 3-asset builds, JS syntax. The socket smoke now covers both legacy
and unified flows. This development environment still refuses socket binding and has
no available browser. Daniel confirmed the original MVP dashboard/smoke previously;
that evidence does not verify this upgrade. Follow [browser checklist](BROWSER-ACCEPTANCE.md).
All automated fixtures are synthetic; the app has not discovered the real workspace
in development. Your real vault requires your explicit in-app approval.

For no-cloud verification: work offline, inspect Developer Tools → Network for only
127.0.0.1 requests, and inspect the registration JSON for settings only. No provider,
GitHub or Cloudflare account is needed. [Implementation/history](../../docs/ux/STEP43B-LOCAL-MVP.md).

---

## Historical initial MVP guide

The following text preserves the initial implementation record. Its one-folder UI,
unavailable-policy and old validation statements are superseded by the guide above.

# Skeptic local app · Step 43B

Read-only, local-first project discovery and continuation prompts. Python 3.9+
standard library on macOS/POSIX; no npm installation, accounts or API keys needed.
This is an implemented MVP awaiting actual localhost/browser acceptance, not a
production security certification. The public website is independent.

## Start

From any Terminal directory:

```sh
python3 -B ~/Developer/skeptic/apps/local/app.py
```

Open **http://127.0.0.1:4317** in your browser. Keep Terminal open. Stop with
**Ctrl-C**. If the port is busy, append `--port 4318` and use the printed address.
The address must use `127.0.0.1`; `localhost` and remote Host aliases are refused.
No background service is installed and no browser or terminal command is launched.

## First use

1. Open Skeptic locally and choose **Add a project**.
2. Paste one local project folder path. Finder: select folder, Option–Command–C,
   then paste. `~` is supported. Use the exact real folder; aliases/symlinks fail.
3. Review PROJECT_SCOPED access; add any private subfolder/filename exclusions
   (one per line). Check the explicit read approval and choose **Approve folder & discover**.
4. Review instructions, checkpoint sources, verbatim status/summary/decisions,
   handoffs, unchecked task lines and missing information. Source paths/line numbers
   and SHA-256 identify the evidence. Modified times order checkpoint files; they
   do not prove milestone completion. The app neither infers progress nor checks Git.
5. Choose **Resume work**, Claude Code or Codex, task and relevant Markdown sources.
   Generate, review and copy the prompt. It re-reads the sources and includes bounded
   excerpts, full instruction references, uncertainty and approval reminders.
6. Paste it into your chosen tool yourself. The receiving worker must read applicable
   full instructions and check current files/Git. Pasting is a separate external action.

Add multiple folders the same way. Switch using the project list. Re-approving an
existing path updates its exclusions. Use **Refresh files** after editing in Obsidian.
**Remove project** deletes only its registration and revokes access; it never deletes
the project. Refresh/selection/task/provider changes clear previously generated prompts.
Session activity retains filenames until the page closes. Restart requires fresh
read approval for every saved folder; opening the app itself reads no project files.

## Actually working

- Multiple saved project registrations, explicit session approvals and custom exclusions.
- Recursive Markdown discovery within one approved folder per project entry.
- Exact-name `AGENTS.md`, `CLAUDE.md`, `PRINCIPLES.md` references, `STATUS.md`
  checkpoints, recognized Markdown sections, nested handoffs, handoff-named sources
  and literal unchecked task lines (all source claims, not verified completion).
- Verbatim, attributed overview; explicit unknowns when recognized sections are absent.
- User-selected context and copyable, provider-neutral continuation prompts.
- Permission display, selected-source relevance explanations and read/write activity.
- White/black/Ferrari-red UI, responsive layout, native controls, keyboard focus and
  clipboard fallback. Rendered appearance and accessibility acceptance are pending.

## Storage and security boundaries

The only persistent application data is `apps/local/.skeptic-local/projects.json`:
folder paths, IDs and extra exclusions. Directory `0700`, file `0600`, ignored by Git.
Writes use a pinned directory descriptor, an exclusive temporary file and atomic
replacement. Registry inputs are bounded and schema-checked. They grant no approval
after restart. No notes, indexes, prompts or activity history are saved. Your Markdown
remains the knowledge system; this registration file is not a competing memory store.

The server binds **127.0.0.1 only**, has no remote option, and serves only the three
bundled UI files. No arbitrary filesystem GET/download route exists. Static inputs
also reject links. Responses use no-store, strict CSP, frame denial and no CORS.
API POSTs require an exact local Host/Origin and unpredictable per-process token;
cross-site requests and unknown fields/routes are refused. Logs omit request details.
The browser renders file-derived content as text, never HTML. Source text never
executes commands or grants access. There are no provider calls or subprocess launches.

Folder ancestry is opened component-by-component with exact entry names and
`O_NOFOLLOW`. Root identity is pinned and rechecked before reads. The reused Step 42
engine rejects traversal, case/Unicode aliases, symlinks, hard links and special files;
reads are bounded and checked before/after opening. Normalized protected exclusions
are applied before traversal/body reads. Additional exclusions can only reduce access.
Secret-like content is quarantined after reading, with its filename withheld.

Built-ins protect Git/app state, environment/credential/secret/private-key names,
SSH/AWS/Claude/Codex/config folders, Library, Backups, build output, protected/sensitive/
password/token names and PEM/key files. Conservative matching may overexclude.
Review your own private folder names: secret heuristics cannot identify every secret.
Entire home/brain and broad system roots cannot be approved. FULL_BRAIN and
ASK_TO_EXPAND remain implemented in the standalone engine but unavailable in this app.
Outside folders require a separate explicit project registration; symlinks do not
expand access. Parent instructions and linked canonical folders are not auto-read.

Limits: 50 registrations, 64 KiB registry, 256 Markdown files, 4,000 directory entries,
depth 16, 128 KB/file, 2 MB total reads/operation. Over-budget traversal/read operations
fail rather than returning an apparently complete partial overview. Individual unsafe,
oversized, invalid UTF-8 or binary Markdown files are withheld and recorded in Activity.
Overview is bounded to 32 recognized sections/file, 128 total sections and 32 handoffs.
Prompts allow 1–30 selected files, at most 3,000 characters/file and 18,000 excerpt
characters total. Truncation is explicit and full source paths remain referenced.

## Verify there was no cloud upload

1. Disconnect Wi-Fi and use the workflow: everything should still work locally.
2. In browser Developer Tools → Network, clear the log, approve a **synthetic** folder
   and generate a prompt. All requests must be to `http://127.0.0.1:<port>`: three UI
   assets and `/api/...`. There should be no external domains, WebSockets or analytics.
3. Inspect `.skeptic-local/projects.json`: only registrations/exclusions, no note bodies.
4. Optional Terminal check: `lsof -nP -iTCP:4317` shows the Python listener on loopback
   and local browser connections. This is corroboration, not proof of the whole OS's
   network behavior. This app has no outbound network client; local API responses
   deliver reviewed context only to the local browser. Actual Network inspection is
   still pending in this agent environment.

## Validation

From the repository:

```sh
python3 -B tests/validate.py
python3 -B apps/local/network_smoke.py
```

The first command runs the existing suite plus local filesystem/HTTP-parser tests,
planted-fault checks, JavaScript syntax check and the **three-public-asset local build**.
Tests use temporary synthetic projects only. HTTP tests mock the socket bind/listen
boundary and use real request parsing/handlers. The second command tests actual
loopback sockets with a temporary synthetic project and shuts down its own server.
It must pass in ordinary Mac Terminal before claiming live-server acceptance.
In the development sandbox it reported binding denied; no live success is claimed.
See [manual acceptance](BROWSER-ACCEPTANCE.md) and [implementation report](../../docs/ux/STEP43B-LOCAL-MVP.md).

## Known limitations

No native folder picker (paste a Finder path); one root per project entry; no automatic
repository ↔ canonical brain-project association or parent instruction discovery.
No semantic summaries, Git/concurrency detection, progress verification, conflict
resolution, editing, sync, providers, installers or automatic memory updates.
Malformed Markdown is displayed as text; headings/checklists are simple literal
matches, so quoted/fenced examples may appear as unverified source claims.

This app does not use the engine's persisted index/cache or lexical query interface:
it uses its tested read/exclusion primitives and fresh user-selected sources. The
engine's CLI and three modes remain unchanged. Existing security caveats still apply:
no OS sandbox, imperfect secret detection, same-user process access and no proof
against every adversarial concurrent filesystem replacement. Prompt framing cannot
guarantee downstream AI compliance. Independent security review and real-browser/
real-socket acceptance remain open. No Cloudflare deployment is part of Step 43B.

## Step 43E — Model usage dashboard

Latest unified Step 43F continuation: full 255 tests / 210 planted faults and both
builds passed. Usage implementation/Vitals unchanged. Socket binding still denied;
Chrome/browser acceptance remains pending. Follow the exact [Step43E browser checklist](BROWSER-ACCEPTANCE.md#step-43e--model-usage-acceptance-still-pending).
Earlier validation counts in this guide retain their historical milestone scope.

Choose **Model usage** in the local board's sidebar. The tool picker includes Claude
Code, Codex, Hermes, Midjourney, Gemini, OpenRouter, Ollama/local models and Other.
This picker filters usage cards; it does not change your active coding model.

**Connect local Claude & Codex readings** authorizes this process to read Claude's
fixed `~/.claude/state/rate-limits.json` quota file and bounded quota events from
`~/.codex/sessions`. Nothing is read before this action. Refresh occurs at most once
per minute while the page is open. Disconnect stops reading and clears cached cards;
a server restart requires connection again. No credentials are read and no provider
request, model turn or process is launched. Codex reads at most twelve recent session
tails (2 MiB each); only quota fields reach the browser. Activity files can contain
conversation data, but it is neither returned nor saved. These are **Last seen**
readings, not live provider polling. Claude's absent five-hour window stays unknown.
Quota remaining, window lengths and local reset/renewal dates appear separately.
Expired or future-dated readings show unknown; resetting never implies 100% available.

For other tools, expand **Add or update a manual reading**. Choose a tool, label the
model/account, enter remaining/total amounts and optionally a reset date. Blank values
mean unknown, not zero. Keep percentages, USD, credits, tokens, GPU hours and requests
separate. Saving the same tool + model/account updates it; different labels create
separate cards (up to 100). Remove a reading using its own card's button.

Manual readings persist in owner-only ignored `.skeptic-local/usage.json`, separate
from project registrations. They survive browser/server restarts and can be copied
with your local settings when migrating. No browser storage is the system of record.
Do not enter secrets in labels. A manual reading is timestamped at save time and does
not track subsequent spending automatically.

- Hermes is an agent/client whose usage depends on its model/provider. Label both;
  no single Hermes quota is inferred. [Nous Portal](https://hermes-agent.nousresearch.com/docs/integrations/nous-portal)
  provides account usage for Portal-backed models.
- Midjourney: [Usage Details](https://docs.midjourney.com/hc/en-us/articles/28014179406861-Managing-Your-Subscription)
  or Discord [`/info`](https://docs.midjourney.com/hc/en-us/articles/32084927086861-Info-Command)
  supplies remaining Fast GPU time and renewal information. No automatic connection
  or unofficial scraping is implemented.
- Unsupported/unconnected tools show unknown. A catalog entry does not prove a model,
  subscription or account is installed/connected.

Restart the existing local server (Ctrl-C in its Terminal, then rerun
`python3 -B apps/local/app.py`) and reload http://127.0.0.1:4317 to load this update.
Native Vitals widget installation remains separate and unchanged.

Usage regression and planted faults: `cd apps/local`, then
`python3 -B -m unittest test_usage.py` and `python3 -B mutation_usage.py`.
Live/browser acceptance: verify navigation, filter, local connection/disconnection,
remaining quota and resets, unknown tools, two distinct manual model labels, restart
persistence and independent deletion. No browser acceptance is claimed from this
sandbox, which denies localhost binding.

## Step 43G native app

See `../desktop/README.md` for the build/install path. Persistent light/dark/system appearance and welcome preferences are available in both entry points. The CLI remains independent. Full wizard, managed workspace and knowledge graph are follow-up; Vitals is unchanged.
