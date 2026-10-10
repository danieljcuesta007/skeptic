# Step 44 — Managed multi-session integration and recovery hardening

Engineering implementation in an isolated worktree. **Not ready for production acceptance.**
New code remains restricted to explicitly selected temporary projects and state. There is no
production registry/grant migration, existing-process adoption, installer activation or service.
Earlier Step 43H results below are historical; they do not validate this changed engine.

## Prerequisites and provider contracts

Python 3.9+, Unix PTYs/local Unix sockets; Node/npm for the existing full builds.
Native Claude/Codex installation and authentication remain user-owned. No downloads,
credential inspection, authentication changes or permission bypasses are performed.
The inspected launch contracts are Claude Code **2.1.296** and Codex CLI **0.162.0**;
other versions fail closed until their interface is inspected. Installed `--help`/`--version`
and [Claude CLI reference](https://code.claude.com/docs/en/cli-reference) and
[OpenAI CLI reference](https://developers.openai.com/codex/cli/reference) informed the plans.
These versions are contract-inspected, **not live-provider acceptance-tested**.

Claude requests an explicit native UUID; native confirmation is unverified. Codex interactive
launch cannot assign/extract a verified native session ID here; it is recorded as unknown.
Codex uses `--no-daemon --cd PROJECT` to avoid sharing the existing user-session server.
Both launch with explicit argv, no shell, option boundary before the prompt, native approvals
and config. Native config/hooks can affect behavior. Documented native conversation resume
exists, but managed resume is unsupported. Safe quiescence, native checkpoint/recovery
provider-native recovery proof, process adoption and supervisor-restart reconnection are
unsupported. The CLI offers an explicit operator review/acknowledgement after actual destination
PTY output is captured; it records a human attestation, not a model-authored proof.

## Development commands

Use this checkout's `apps/terminal/switcher.py` with Python, or an already-installed
launcher deliberately pointing to it. No launcher was installed or repointed by this work.
Create a private temporary directory and separate project directories. Example variables:

```sh
fixture=$(mktemp -d /private/tmp/sk-demo-XXXXXX)
mkdir "$fixture/project"
python3 -B apps/terminal/switcher.py managed initialize --state "$fixture/state"
python3 -B apps/terminal/switcher.py managed start --state "$fixture/state" --cwd "$fixture/project" --name 'Daily Brief'
```

Default provider is the fixed echo fixture. To launch a newly managed native session, add
`--provider claude` or `--provider codex` and **explicitly** add `--approve-provider`.
That flag authorizes native quota usage and access to the selected project under native
security settings. Do not add it to an automated test without the required live-test approval.
`managed providers --state TEMP/state` inspects versions/capabilities without model calls.

Start prints the session UUID and attaches in an interactive terminal. Ctrl+] detaches;
`managed attach --state TEMP/state --id UUID` reconnects while its supervisor survives.
`--observe` cannot write; `--cursor N` requests bounded output replay. Exact screen/alternate
screen restoration is unsupported. Detach immediately abandons all unacknowledged pending
bytes plus non-escape bytes in the current input chunk, reports their count and never replays
these bytes. A failed input acknowledgement reports delivery uncertainty; users must inspect
before retyping. EOF also detaches. Partial writes retry only acknowledged-unsent bytes.

`managed status`/`managed list` and transaction inspection use read-only SQLite connections;
missing/corrupt storage produces an error without initialization or repair. `initialize` is
an explicit additive integration-schema operation in temporary state only. No existing
production database is touched. Unknown integration versions are refused without migration.

`managed start --id UUID` gives a caller-selected startup identity. Durable owner-only intent
precedes spawn. Retries with the same identity reconcile a reachable supervisor; unresolved
receipts refuse another launch and report the UUID. A crash between intent and spawn can
require manual investigation: automatic relaunch is deliberately refused. Different project,
provider or packet under the same identity is refused. Requested native ID/version persist
in the startup receipt. SQLite records supervisor/agent/generation/project identities.

## Three switching scopes

```sh
python3 -B apps/terminal/switcher.py switch codex --state TEMP/state --id SOURCE_UUID --task 'Latest user objective'
python3 -B apps/terminal/switcher.py switch --select codex --state TEMP/state --task 'Prompt for each objective'
python3 -B apps/terminal/switcher.py switch --all codex --state TEMP/state --task 'Prompt for each objective'
```

`SKEPTIC_MANAGED_STATE` and `SKEPTIC_SESSION_ID` provide explicit current-session identity
inside a newly managed provider's tool environment. A parent shell after detach does not
inherit that environment: supply `--state` and `--id`. Skeptic never guesses from PID/TTY.
Bare legacy `skeptic` and `switch --with PROVIDER` retain the existing unmanaged workflow.

The picker lists all sessions in the selected managed registry, their name/project/provider,
terminal status, destination, eligibility/exclusion and checkpoint readiness. It accepts comma
separated row numbers. Batch switching asks separately for each latest user objective.
It does not reuse one project's task for another or scan private provider histories.
Unmanaged processes are not discovered/adopted; they require the existing consent-gated
recovery workflow. `--all` means eligible entries in this explicit managed registry.

**Only observed exited sources are currently eligible.** Active, detached, suspended,
unreachable, already-destination and overlapping live-writer sessions are excluded. The
supervisor also requires its PTY output drain to finish and the child process group to disappear.
This catches children that remain in the managed group. A provider descendant that creates a new
session/process group cannot be proven quiescent by this check; the preflight still requires
explicit confirmation about other writers, and unmanaged agents remain outside Skeptic's control.
This does **not** automatically pause or switch a live quota-blocked source.

The quiescence signal is deliberately narrow: it requires observed agent exit, complete PTY drain,
and no remaining process in the managed agent's original process group. It cannot discover a child
that called `setsid`/changed process group, an already reparented descendant, or an unmanaged writer.
No platform-independent process-tree proof is claimed. The switch preflight's operator confirmation
about other writers is not a guarantee about escaped descendants. If those cannot be ruled out,
defer switching. Active, detached, suspended, unreachable and ambiguous sessions remain excluded.
Project locks coordinate Skeptic's managed launches and switch transactions only; they cannot stop
arbitrary filesystem writes.

The user types `preflight`, approves existing project/vault read scopes through the existing
switcher, inspects each exact bounded packet and types `send` per destination. Packet
preparation uses existing `assemble`/grounded-packet/privacy/continuity logic. Source excerpts
and tool output remain untrusted evidence; only the explicit user objective is an instruction.
No raw PTY bytes or private conversation histories are copied. Completion/pending-work claims
remain attributed, potentially incomplete documentation rather than invented working memory.
`--vault` and `--permissions-state` can select synthetic scope/state for testing.

Each packet has immutable transaction identity, owner-only file and SHA-256 binding to source,
destination and objective. Grants, source fingerprints, project identity, Git observations
and packet content are refreshed immediately before native launch; changed/revoked evidence
blocks delivery. Same-user tampering and the final filesystem race are not eliminated.
Packets/startup receipts contain approved context: keep this temporary state private and
out of Git. Native prompts may be visible in same-user process inspection and provider storage.
No automatic commits, stash, reset, worktree rewriting, publication or remote writes occur.

## Journal, concurrency and recovery

The existing registry stores schema version, display metadata, stable logical lineage,
checkpoints, pending transactions, recovery metadata, events and project locks. Physical
source/target IDs differ; the logical Skeptic identity continues across targets. Runtime
writer/observer metadata comes from the owning supervisor, not PID inference.

Separate source/project locks and serialized durable launch intent prevent duplicate
automatic launch. Canonical path overlap includes nested project roots. A destination's project
reservation remains after recovery acknowledgement because it may still write. Locks coordinate
these managed operations; they cannot control unmanaged tools or guarantee filesystem
exclusivity. Native fresh launches also refuse overlapping live/unresolved managed receipts.
Existing Git worktrees are preserved; the existing Git reader may report linked metadata as
unknown rather than expanding permissions into another checkout.
Release a target's reservation only after that managed target exits, drains output, and its owned
process group is absent: `managed release --state STATE --id TARGET_UUID`. This preserves the
transaction/evidence history and refuses while any overlapping managed writer remains.

Stages record discovered/eligible/locked/checkpointing/checkpoint validated/authorized/
launching/started/recovery verifying. Sources are never terminated by switching.
`managed transactions --state TEMP/state` lists transaction/source/target/stage/error.
`managed reconcile --state TEMP/state --id TRANSACTION_UUID` can verify a reachable target's
identity after interrupted launch and restore **recovery verifying**, not recovery success.
`managed revoke --state TEMP/state --id TRANSACTION_UUID` revokes future launch authorization.
Revocation cannot retract delivered data or stop an independently running target; a potentially
launched target retains its project lock. A partial batch failure retains its evidence/intent
and does not prevent independent projects from proceeding. Never remove a lock or retry with
a new identity until the original target and all potential writers have been investigated.

Native launch reports `recovery_verifying`; process startup alone never means recovery success.
After attaching or reconnecting to the destination, run
`managed acknowledge --state STATE --id DESTINATION_UUID --transaction TRANSACTION_UUID`.
The command verifies reachable session/provider/project identity, captures the current bounded
PTY output from cursor zero without gaps, escapes terminal control bytes, and shows both that
output and the exact checkpoint. The operator must enter the exact destination/session/project/
objective/checkpoint/provider values and state the pending item they observed. The immutable
acknowledgement record hashes the output and binds it to the reviewed checkpoint. This is
**operator-verified recovery**, not automated semantic verification or proof that the provider
retained all context. Missing output, gaps, changed identity/evidence, revoked authorization or
wrong answers leave the transaction in `recovery_verifying`. An echo fixture has no recovery
adapter and is refused before provider spawn. Source retirement and rollback that relaunches an
uncertain target are unsupported. No native-provider acknowledgement has been run in this
workspace.

## Migration boundary

`managed_migration.py` is a rehearsal utility for synthetic registries created under temporary
directories. Its tests review a content-hashed plan, copy only an exited schema-v1 registry and
owner-only metadata into a new destination, retain the source, and roll back by moving the
unchanged destination to a uniquely named archive. Changed plans, active/owned sessions, extra
destination files, and altered copied files are refused; partial copies remain marked for manual
inspection. Three planted migration faults are caught. This is not a production migration tool:
there is no supported production registry root/schema or managed-session inventory, and no legacy
permissions or grants are imported. It never reads `~/.skeptic-cli`; production migration and
rollback remain disabled pending a separately reviewed schema and backup/restore plan.

## Verification and remaining acceptance

New hardening/provider/journal/CLI and synthetic migration tests are included in
`python3 -B tests/validate.py`. Daniel reports that the full validator passed in ordinary Mac
Terminal on the pre-continuation snapshot: **344 tests, 240 planted faults and both builds**. That
owner-reported run included the then-current recovery acknowledgement, owned process-group
quiescence and gated project-lock release, but predates the migration rehearsal and new three-PTY
acceptance test below.

On current code, `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate.py
--without-managed-runtime` passed **350 tests and 243 planted faults**, plus website/local builds.
The validator explicitly skipped `test_managed.py` and `mutation_managed.py`, so this is partial
validation. The previous test failure came from a 104-byte Darwin socket path produced by its long
temporary prefix. The fixture now uses a short prefix and asserts the socket fits; `managed_cli.start`
preflights this path before creating registry state or spawning. A regression confirms overlong paths
are refused without registry creation or spawn. The focused PTY test was retried, but the tool
sandbox denies AF_UNIX binding; no leftover Step 44 supervisor remained. It must pass in ordinary
Mac Terminal before claiming current-code full PTY acceptance.

Daniel's latest ordinary Mac Terminal full-validator attempt stopped at that three-session test
after its 51-test focused integration/migration group passed. The corrected code has not yet had a
full ordinary-Terminal run; no downstream results are inferred from the stopped run.

Socket-independent validation exercises three separate Daily Brief/Website/Research projects,
current/selected/all scopes, independent objectives, third-project preservation, partial
failure, exclusion reporting, changed evidence/revoked grants, no duplicates, receipt mismatches
and source retention. Launch boundaries and observations are synthetic; these are **not**
three live managed/provider sessions. `test_managed.ThreeSessionPTYAcceptance` adds the actual
three-agent managed-PTY scenario and synthetic destination-context echo check; it has not passed
in this sandbox. Neither synthetic path proves Claude/Codex context recovery.
Explicit partial validation command: `python3 -B tests/validate.py --without-managed-runtime`.
It prints both excluded commands and a partial-acceptance result; default validation still
requires them. Both website/local builds and independent existing suites were run. No real model requests.

Still required: rerun the full changed-engine PTY/fault validator in ordinary Mac Terminal;
newly owned Claude and Codex live tests with explicit bounded quota approval; a safe policy for
escaped provider descendants (currently not provable); a separately reviewed production
migration/rollback (currently disabled); native-provider three-session acceptance. Synthetic
three-project coverage is verified at
the journal/CLI boundary, not live PTYs or real providers. Supervisor
failure/reboot survival, full shell Ctrl+Z, Swift integration, exact VT restoration and
existing-process adoption remain unverified or unsupported.

---

## Historical Step 43H evidence

# Step 43H — Shared fake-agent terminal engine

Implemented first slice, 2026-10-09. Product: Your work. Your memory. Any AI. Any interface.
Python 3.9+, Unix PTYs; macOS acceptance uses Python stdlib and system getpeereid.
No pip/Homebrew, provider, account, native build, background service or desktop dependency.
All working directories and state must be explicit isolated temporary fixtures. No
production root migration, source scanning, vault reads, native provider or arbitrary argv.

## CLI (development only; no installation needed)

Create a temporary fixture/project yourself; from that project use the checkout's
`apps/terminal/switcher.py managed start --state TEMP/state --cwd TEMP/project` with
Python 3. `skeptic managed ...` also works when an already installed launcher points
at this checkout. No installer was run. `start` prints the stable session UUID and
attaches when run in an interactive Terminal. Fixed fake agent only.

Ctrl+] detaches. The fake process and supervisor remain alive. Another Terminal uses
`managed attach --state TEMP/state --id UUID`; `--observe` forbids input and resize.
`--cursor N` resumes byte replay at the disclosed offset; default 0 replays retained bytes.
Fake commands: ordinary lines echo, `exit` exits zero, `fail` exits seven, `stop` stops
via SIGSTOP, `burst` exercises output overflow. Agent commands are synthetic fixtures,
not Skeptic control commands. Ctrl+C reaches PTY signal handling; resume a stopped
fixture through the documented `continue` RPC (CLI UI for continue is deferred).

`managed status --state TEMP/state --id UUID` and `managed list --state TEMP/state`
report observed state. `managed shutdown` refuses live agents; after fake agent exit
it closes the supervisor. Detach never means shutdown. Explicit temp fixture cleanup is
user-owned; the CLI never deletes existing state or silently duplicates a session.
No persistence of terminal bytes across supervisor death or reboot.

## Shared architecture implemented

managed_engine.py provides registry, framed protocol, client transport, status reconciliation
and per-session PTY supervisor. managed_cli.py is a thin client. switcher.py dispatches
`managed` before constructing existing production CLI State. Existing unmanaged recovery
and switching are unchanged; no production permissions are imported or expanded.

One operational SQLite registry serves all fake sessions/clients in the selected state root.
One fresh single-threaded engine supervisor per session owns that session's master FD and
child waitpid lifecycle. This is a shared engine with per-session workers, not independently
implemented terminal backends. There is no always-on global coordinator yet. Persistent
metadata: session UUID, project identity (path/device/inode), cwd identity, fixed fake provider,
generation, supervisor/agent PIDs, last observed status and exit code. No prompt, terminal
body or key is stored in registry. Random capabilities are separate owner-only .key files.
State/socket files are owner-only; paths/symlinks, socket type, peer UID, capability and
engine generation are checked. PID alone never authorizes reconnection/signaling.

The child executes only the fixed fake script. It enters a held working-directory FD,
closes unrelated FDs, and receives a minimal environment. On this Mac, closing SQLite
objects in the post-fork child caused SIGSEGV; the repaired child does only directory/FD
operations and exec, without touching SQLite objects. No higher-level framework/HTTP APIs
or threads are introduced into this supervisor. Do not reuse desktop's threaded server
for fork. A different OS/provider needs its own validation before claiming support.

SQLite transactions provide atomic metadata updates; crashed uncommitted writes roll back.
Agent stop/continue/exit is observed by waitpid. Disconnect releases a writer lease without
closing the master. There is exactly one writer; authenticated clients may observe output.
Claim after explicit detach/connection EOF is allowed; no force-takeover of a live writer.
This slice arbitrates terminal INPUT, not filesystem writes by different agents/projects.
Do not infer production concurrency safety from these fixtures.

Status meanings: `starting` is recorded initialization; `live` has a writer; `detached` has
no writer (observers may remain); `suspended` is observed process stop; `exited` has an
observed exit code. If the saved engine cannot be authenticated/contacted, live records
become `stale` in the observation with `reachability=unreachable` and `recorded_status`.
Unreachable does not prove process death. No PID probing/adoption/relaunch repairs it.
An observed exit remains historical when its supervisor is unreachable. If supervisor
fails, its master may hang up the child: reconnectable state is not fabricated.

## Local interface v1 (Swift integration later)

AF_UNIX, owner-only socket `s-FIRST12UUIDHEX.sock` inside the explicit temp state root.
Length prefix: four-byte network-order unsigned integer, then UTF-8 JSON; max 32768 bytes.
One outstanding request per connection (no pipelining). Each request has `v:1`, increasing
`id`, `key` from UUID.key, `generation` from registry and `op`. Responses have matching
`v/id`, `ok`, then `result` or `error`. Authenticated peer UID required on both sides.
Socket collision/refused startup does not overwrite an existing endpoint.

| Operation | Fields / result |
| --- | --- |
| hello | confirms generation |
| status | session metadata, reachability, output_complete, screen limitation |
| attach | mode write/observe; writer granted or denied |
| claim | exclusive writer request, no forced takeover |
| detach | releases this connection's writer lease, preserves process |
| input | base64 data, max 4096 decoded bytes; returns written count; retry unsent remainder |
| output | cursor offset; base64 data, new cursor/start/end, explicit gap flag |
| resize | writer-only rows/cols 1–1000; PTY winsize drives SIGWINCH |
| continue | writer-only SIGCONT for owned child process group |
| shutdown | only after observed agent exit; closes supervisor |

Bounded 64 KiB in-memory byte ring continues draining while detached. Older output is
lost with explicit gap; slow clients cannot grow buffers without limit. Maximum sixteen
connections per supervisor and bounded incomplete frames. CLI restores caller modes on
normal detach, EOF, errors and handled shutdown signals. Tests compare terminal mode flags
and control characters while allowing macOS's transient PENDIN (pending-input state) bit.
Exact screen restoration, alternate-screen reconstruction and production VT compatibility
are NOT verified. No terminal emulator state is persisted.

Later Swift should connect to this protocol (or the evolved central API) and consume
bytes/resize events; it must never spawn its own competing agent lifecycle implementation.
Closing desktop detaches its client. An embedded emulator, shared production migration,
permissions/continuity integration, real adapters and safe live-agent switch policy remain
separate approved milestones. Existing ~/.skeptic-cli/.skeptic-desktop remain untouched.

## Verification

`python3 -B -W error::ResourceWarning -m unittest -v test_managed.py` in apps/terminal,
then `python3 -B mutation_managed.py`; both are included in tests/validate.py.
Socket creation may need normal Mac Terminal or sandbox escalation; failure is disclosed.
Fake-only acceptance: actual CLI start on a Mac PTY, detach, new CLI reconnect with same
agent/cwd; exclusive simultaneous writers, observers, disconnect/lease transfer, resize,
interrupt, explicit stop/continue, exit and supervisor crash, stale PID refusal, fragmented/
oversized messages, byte-ring overflow, private-state guards and interrupted SQLite writes.
Eight meaningful faults are planted in temporary copied engines, never production sources.
No original Claude session, private history or real providers were accessed in this milestone.
Final validator results belong in canonical STATUS and the completion record below.

## Completed validation — 2026-10-09

Final full validator passed: **317 tests / 233 planted faults caught**, including both
website/local builds and all existing unmanaged recovery/switching suites. Managed suite:
21 deterministic tests, including actual macOS CLI start/detach/new-terminal reconnect,
stable PID/cwd/project identity, shared registry across two supervisors, simultaneous writer
contention, observer rejection, abrupt connection loss, SQLite process-crash rollback,
agent exit/drained output and supervisor failure. Eight behavioral mutations caught;
mutation runner requires assertion failures rather than infrastructure errors.
`git diff --check` passed; production CLI State is bypassed for fake `managed` commands.
No matching fake supervisors remained after tests. Temporary full-run log:
/private/tmp/skeptic-managed-approved.log. No production provider/session/vault accessed.

Early checks failed because the sandbox disallowed Unix sockets, then because post-fork
SQLite closure crashed the fake child. Socket/PTY tests ran with explicit escalation; child
launch fixed as described above. Terminal-mode tests distinguished Darwin PENDIN from mode
restoration. One failed-setup supervisor was identified by its exact fixture/session command
and cleaned up; later tests register teardown even when setup assertions fail. Default
py_compile cache was sandbox-blocked; syntax compilation passed with a temporary cache.
Full tests, not those failed initial checks, establish the completed acceptance.

NOT VERIFIED: real provider lifecycle, native conversation resume/catch-up, desktop attach,
production state/grant migration, complete VT/alternate-screen restoration, survival across
supervisor failure/reboot, or full shell Ctrl+Z job-control behavior. Stop/continue acceptance
uses the controlled fake's SIGSTOP command plus SIGCONT RPC. Future milestones require
separate approval. No commit, push, deploy, services or global permission changes.
