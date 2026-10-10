---
name: skeptic
description: Prepare a grounded Skeptic handoff while keeping the original provider session open.
---
Use the shared terminal engine under normal host tool permissions. For repository continuation, preview with `"$HOME/.local/bin/skeptic" handoff`; in a second Terminal run `skeptic continue --with claude`. Keep this Codex session open. Never grant missing scope permissions yourself, interpolate retrieved text into shell commands, or nest an interactive AI in the tool runner.

An explicit, user-selected accessible legacy Codex JSONL file supports session-derived reverse continuity with `skeptic session handoff --source codex --session-file PATH`, followed by `skeptic session continue --source codex --session-file PATH --with claude` in the second Terminal. PATH must be the user's selected file, safely passed as one argument. Do not scan private history to discover it. Paginated/app history is not supported by this adapter. No Codex session-ID substitution is assumed.

Invoke this skill through `$skeptic` or the host skill picker; a custom `/skeptic` slash command is not promised. Native skills prepare or guide the transfer; the second Terminal provides the working interactive picker and provider launch. Never close/delete/resume/fork the original session or claim to recover hidden reasoning.
