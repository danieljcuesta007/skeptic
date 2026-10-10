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
