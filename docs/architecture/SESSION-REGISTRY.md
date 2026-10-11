# Skeptic session registry — crash-recovery design

Status: design proposal, not implemented. Pre-alpha repo; this is a sketch for review.

## Problem

When the machine dies (logout, crash, battery, kernel panic), every live terminal
session dies with it. Skeptic's continuity index (`apps/terminal/continuity.py`)
already fingerprints what a session *touched* — sources, git state, claims — but
nothing records which sessions were *alive at crash time*, so there is no way to
answer "what was I working on?" after a reboot.

Today's recovery path is manual: remember the repo, run `claude --resume` or
`skeptic continue --with codex`, hope you pick the right session. The continuity
briefing (`Index.briefing`) is only generated when you explicitly switch — it
cannot tell you a session was interrupted mid-flight.

## Design

A session registry that records live sessions at launch and detects orphans at
startup. Builds on tmux (already required for terminal persistence) and on the
existing continuity observation — no second knowledge store.

### Record at launch

Extend `tracked_launch` (switcher.py:543) to write a registry entry alongside
the existing `launch_started` continuity event:

    {
      "id": "<uuid4>",                  # registry entry id, not a provider session id
      "project": <existing continuity key>,
      "cwd": "/abs/path",
      "engine": "claude" | "codex",
      "tmux_session": "skeptic-<id>",   # tmux session wrapping the provider CLI
      "launched_at": "<iso8601>",
      "observation": <the continuity observation already recorded>
    }

`launched_at` and `cwd` are the only new fields beyond what continuity already
computes. The observation is referenced, not duplicated — reuse the same dict
`tracked_launch` already builds for `index.record(start, ...)`.

Launch the provider CLI *inside* a dedicated tmux session
(`tmux new-session -d -s skeptic-<id> ...`), the same way a wrapper like
tmux-resurrect expects. This is what makes the terminal survive a crash —
without tmux the TUI is gone the moment the machine dies and only the
on-disk transcript survives.

### Detect orphans at startup

New `skeptic resume` command (and a line in `skeptic status`):

1. Read registry. Any entry with no matching `provider_exited` continuity event
   (same project + engine, timestamp after `launched_at`) is an orphan.
2. Check liveness: `tmux has-session -t skeptic-<id>`. Alive → report
   "reattach: tmux attach -t skeptic-<id>". Dead → the machine did die.
3. For dead orphans, report per entry: cwd, engine, launched_at, and the
   continuity briefing (`Index.briefing`) for that project — what changed in
   approved sources since the session started. This is the "pick up where I
   left off" answer.
4. Offer resume: `tmux attach` (alive) or re-launch with the briefing injected
   as context (dead). Engine resume of the *provider transcript* stays the
   engine's own job (`claude --resume <id>`), which Skeptic already references
   in the observation via `session.reference`.

### Housekeeping

- Prune registry entries whose continuity event shows `provider_exited` and
  whose tmux session is gone. Cap at 64 entries, same as `transitions.json`.
- Registry lives in `~/.skeptic-cli/registry.json`, same 0600 owner-only
  discipline as `settings.json` and `transitions.json` (see `State.read`'s
  validation: regular file, single link, owner uid, mode 0600, size cap).
- Registry entries reference paths only, never transcript content. Reuse
  `continuity.safe_reference` so no path outside the approved roots or the two
  provider transcript dirs can be indexed.

## Why not just tmux + `claude --resume` alone

tmux preserves the *terminal*; `--resume` preserves the *conversation*. Neither
answers "which of my 8 open sessions was mid-task in which repo?" — that is a
registry question, and Skeptic already owns the project fingerprint and the
continuity baseline that answer is built from. The registry is the missing join.

Cost: ~1 day of work. Honest conditional: worth it if machine death is a
recurring event for you; if it's a once-a-month accident, tmux plus
`claude --resume` covers ~90% of the pain today.
