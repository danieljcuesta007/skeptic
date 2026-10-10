# Proposed shared Skeptic Terminal — next milestone after Step 43F

Proposed by Codex under Daniel's 2026-10-09 design scope. Implementation NOT authorized
by this document. Product: Your work. Your memory. Any AI. Any interface.

## Current facts

CLI uses ~/.skeptic-cli; desktop uses ~/.skeptic-desktop; local web app uses its
own .skeptic-local. They share some Python code, not a unified registry or permissions.
CLI launches provider subprocesses on the caller's terminal. Swift hosts WKWebView
and launches backend.py with stdin as a lifetime lease; closing the desktop stops
that backend. Neither owns reconnectable agent PTYs. Existing continuity.py stores
bounded fingerprints, not conversation bodies or knowledge. Obsidian remains canonical.

## One engine, two clients

CLI ── private local socket ── engine ── PTY supervisor ── provider processes
Swift client ────────────────┘       ├─ project/session registry
                                    ├─ grants + adapters + existing continuity
                                    └─ canonical Markdown / approved Git observations

Extract existing policy/continuity code behind a versioned engine API; neither client
implements its own recovery, grants, launch decisions or catch-up algorithm. Use one
portable configured state root (default ~/.skeptic), Python stdlib SQLite for transactional
operational state, owner-only directory/files (700/600), and a short private AF_UNIX
socket path. SQLite stores project IDs, confirmed roots/knowledge mapping, session IDs,
provider-native IDs when available, launch receipts, lifecycle events and grant identities.
It is disposable operational state, never a competing semantic memory system.
Use a singleton lock, versioned migrations and transactional events. Resolve symlinks,
unsafe pointers and source identity through existing permission policy. No inferred grants.
Existing CLI/desktop/local roots require an explicit reviewed migration: import projects
as candidates, retain originals, revalidate identities and reapprove grants; never union
permissions blindly. No migration or root change in this milestone.

Launch engine on demand as a detached user process, without launchd/service installation.
It remains alive while it owns live PTYs, even when no client is attached; explicit engine
shutdown distinguishes detach from terminate. Authenticate clients by socket directory
ownership, peer UID using macOS-specific APIs (not Linux SO_PEERCRED), plus a private
session capability; reject other users, unsafe paths, stale generations and oversized RPCs.
Use length-framed versioned messages with request IDs; control messages separate from
binary PTY output. Serialize grant/registry updates through engine. No network listener
required. Agents still use their native provider authentication and approvals.

## PTY and process ownership

Apple documents forkpty/login_tty creating a session and controlling terminal:
https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man3/openpty.3.html
Python documents Unix PTYs and a macOS hazard when fork is mixed with higher-level APIs:
https://docs.python.org/3/library/pty.html

Use a dedicated fresh, single-threaded supervisor executable/process for PTY creation;
do not fork the existing threaded desktop HTTP server or urllib-using switcher.
Validate on macOS before choosing Python forkpty versus a small native helper. Supervisor
owns master FD and child waitpid lifecycle. Child has controlling PTY, explicit approved
cwd, argv (no shell interpolation), closed unrelated FDs and documented environment.
Track engine generation, owner capability and observed child identity; PID alone never
permits signaling/adoption. Client disconnect closes its stream, never master FD.
One writer lease per session; explicit writer transfer; observers cannot send input.
Foreground process groups handle Ctrl+C/Ctrl+Z through PTY termios; resize uses winsize
and SIGWINCH; distinguish suspended/continued/exited from waitpid events. CLI detachment
uses a reserved Skeptic escape command, restoring caller termios on all exits. Do not
translate an ordinary Ctrl+Z into a provider switch or inject commands into a shell.

Detached output must keep draining with bounded backpressure; first slice drops old
in-memory output with a visible gap marker rather than blocking agents or logging secrets.
No raw terminal output persisted by default. Test terminal escape sequences, alternate
screen, Unicode, paste, resize and slow readers. Surface lack of full screen restoration.

## Three different continuities

| Promise | Feasibility and limit |
| --- | --- |
| Process/session continuity | Reconnect clients to an engine-owned PTY while its supervisor remains alive. No adoption of an arbitrary existing Terminal process. |
| Conversation continuity | Provider-native resume by explicit known ID when supported, otherwise a fresh reviewed handoff using approved sources. Resume creates/uses provider conversation state; it does not prove same PID or fresh knowledge. |
| Exact terminal-screen continuity | Requires a shared terminal emulator state/checkpoint, size policy and replay semantics. Raw bounded output replay cannot reproduce all prior screen state. Deferred; visibly report output gaps. |

A live returning agent does not automatically receive context simply by attaching.
Prepare a fresh reviewed catch-up, then deliver only through a supported documented
input mechanism while user confirms the agent is ready; otherwise launch a fresh provider
conversation. No automatic injection into active tools or inference that context was read.
Switching preserves old processes but prevents simultaneous editing of the same project:
explicit pause/quiescence acknowledgement or isolated worktree approval before another
writer starts. A disconnected agent can still edit. Locks/grants alone cannot prove idle.
Unmanaged recovery remains exact-session consent-gated fallback, leaving original intact.

Crash recovery: losing a client is reconnectable; losing the sole supervisor/master FD
can hang up the child and cannot be fixed by a registry. Mark sessions unknown/interrupted,
never claim reattachment from PID; reconcile ownership without signaling unrelated processes.
Disk registry and native conversation IDs allow reviewed semantic recovery. Later independent
per-agent supervisors could survive engine restart, but require separate ownership/IPC tests.
No survival guarantee across reboot, supervisor crash or forced termination.

## Providers and permissions

Adapters declare launch, conversation resume, evidence extraction, local model capability
and version-tested limitations separately. Existing Claude/Codex native argv and explicitly
detected local models remain; no installation/download, broad private-history scan or quota
catalog query. Only exact approved transcript sources; no terminal stream in cloud handoff.
Grants are persistent, explicit, revocable, identity-checked and read-purpose scoped.
Revocation prevents future evidence reads/launches and invalidates prepared handoffs; it
cannot retract evidence already sent or revoke a running provider's independent filesystem
access. Explain that limit; do not imply Skeptic grants sandbox native agents.
Same project IDs, session events, approvals and evidence hashes visible in both clients.
No cloud sync or proprietary memory dependency. No default personal transcript recording.

## Smallest safe implementation slice (proposed)

1. Isolated stdlib engine + protocol + registry on synthetic projects; no production migration.
2. Mac CLI client launches one fake agent in an owned PTY, detaches and reconnects from
   another Terminal; writer arbitration, resize, job control, exit status, auth and crashes.
3. Add exact approved real provider launch only after fake-agent acceptance. Existing
   recovery/catch-up supplies reviewed immutable evidence; no automatic native resume yet.
4. Explicit production state migration after review, then provider switching and fresh
   returning context. No simultaneous project writers or unmanaged process adoption.

Acceptance: correct cwd/TTY, Ctrl+C/Ctrl+Z/continue semantics, clean termios restoration,
client disconnect leaves PID alive, same generation reattach, exclusive input lease,
resize signal, output-gap disclosure, accurate child exit, revocation after preview,
changed-evidence refusal, spoofed socket rejection, PID reuse refusal, engine crash marked
interrupted, and no writes outside synthetic state/project fixtures. Seed existing dirty
work and verify unchanged hashes. Start with a minimal local fake protocol client, not UI.

## Existing Swift desktop connection (later approved slice)

Keep the current app UI/backend for project views initially; add a native socket client
or a thin backend transport to the SAME engine. Move project/permission operations to engine
before claiming consistency. Desktop UI lifecycle detaches; it must not terminate engine.
Current Process termination handling applies only to its presentation backend.
Use an embedded AppKit terminal emulator that consumes engine bytes and sends input/resize,
not an emulator component that spawns a second local process. SwiftTerm is a candidate
third-party dependency, not installed/approved: https://github.com/migueldeicaza/SwiftTerm
Evaluate license, pinned version, accessibility, escape handling and packaging before use.
WKWebView alone is not a terminal emulator. Do not hand a local control capability to arbitrary
web content; bridge only validated same-origin UI requests with explicit native mediation.
Desktop acceptance: attach to CLI-owned fake agent, transfer writer lease, close desktop
without child loss, reconnect CLI, same project/grants/events; accurately disclose absent
screen history. Full screen reconstruction and provider-specific resume are later gates.

## Verification state

Architecture based on inspected current files and primary PTY/emulator documentation.
No shared engine, process reattachment, native terminal or migration implemented/tested.
The existing same-terminal acceptance is user-reported; new repair still needs a real
reviewed recovery preview. Claude review remains required before every PR merge.

## Step 43H first implementation slice — 2026-10-09

Daniel authorized the fake-agent CLI slice after this proposal. See
[implemented interface and limitations](../../apps/terminal/MANAGED.md).
Shared engine/registry and per-session supervisors now exist for temporary fake fixtures;
CLI start/detach/reconnect and ownership tests run on macOS. This supersedes only the
proposal's statement that no engine exists. Production state migration, global coordinator,
real adapters, canonical-context integration and Swift terminal remain proposals.
Per-session engine workers share one protocol/registry implementation. Supervisor death
still prevents live reattachment. No services or global permissions were installed.
