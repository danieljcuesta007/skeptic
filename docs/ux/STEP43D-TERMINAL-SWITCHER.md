# Step 43D — Terminal Model Switching

2026-10-09 · Codex · Daniel's explicit urgent switcher mission.
This authorizes the local CLI, provider launch adapters and native handoff helpers;
it supersedes earlier planning-only/no-provider scope for this specific workflow.
Step 43A website/deployment, Step 43B acceptance, Step 43C saved history and existing
Step 44/45 proposals are preserved. No deploy, commit or push.

## Delivered

`apps/terminal/switcher.py`: `skeptic`, `continue`, direct Codex/Claude destinations,
`status`, `doctor`, `models`, proposed `handoff`, permission listing/revocation and
optional analytics. POSIX arrow-key picker with keyboard cancellation, availability
and recent selections. Native integrations invoke this same engine; dashboard and
CLI share `app.grounded_packet` plus existing descriptor reads/source parsing.
No local HTTP dependency or package-manager runtime dependency.

Installation creates owner-local `~/.local/bin/skeptic`, appends one marked PATH
addition without replacing `.zshrc`, and optionally installs provider skill files.
Installed here: launcher/PATH and Claude handoff skill. Fresh interactive zsh
resolved the launcher; `skeptic doctor` ran successfully. Codex skill is packaged,
not installed here: `~/.agents` is read-only under this execution permission profile.
Ordinary Mac Terminal can run the supplied installer for both integrations.
Skill Creator validator could not run because its optional PyYAML dependency is
absent; no dependency was installed. Both integration layouts are fixture-tested.
Host skill execution itself remains unverified.

Detected: Codex CLI **0.162.0**, Claude Code **2.1.295**, Git, Python **3.9.6**.
No Ollama executable; no local model reported by accessible fixed loopback probes.
This is not proof that no local service exists outside this sandbox. Authentication,
cloud default models, usage/quota and actual local-model compatibility are unknown.

## Actual verification

Final complete `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate.py`:
**179 tests passed / 141 planted faults caught**, website eight-asset and local
three-asset builds, local JS syntax and existing HTTP/security regression checks.
Breakdown: terminal **46 tests / 20 faults**; website 18/11; local 60/56;
discovery 36/36; baseline 18/18; migration one test.
Full output was inspected; final source diff/AST/syntax checks passed.

Terminal tests use synthetic vaults/repos and fake executables only. Actual PTYs
exercise Up/Down, Escape/q cancellation, terminal restoration and complete picker
→ fake Codex launch; direct fake Claude launch also passes with exact cwd, bounded
prompt, governing content and checkpoint. Tests cover approvals, persistent reuse,
replaced roots, revocation, protected/link/traversal exclusions, exact/ambiguous/no
repository associations, subdirectory instructions, missing handoffs/vault, canonical
checkpoint priority, linked notes, dirty staged/unstaged/untracked preservation,
source attribution, prompt data boundaries, size budgets, missing/local providers,
malformed loopback replies, safe argv, process exit failures and optional logging.
Twenty terminal faults planted only in memory are rejected. A first redundant
instruction-removal mutation survived because another legitimate instruction path
remained; it was replaced by a real source-omission fault, which the test rejected.
The initial PTY test drain loop hung on EOF; corrected and repeated successfully.
Shared-formatter refactor initially had a name-shadowing error; tests rejected it,
then the final correction passed the complete suite. Historical successes were
not substituted for final verification.

## Not verified / boundaries

No user-selected existing Claude project was provided for acceptance during this
implementation. No real provider was launched, no private sessions scraped, no
real-root discovery performed by the new CLI and no cloud context uploaded.
**Real Codex launch/usable continuity is NOT VERIFIED; product-ready acceptance is
not claimed from synthetic tests.** User must approve the first project's printed
repository/vault scopes in Terminal and verify the checkpoint in the destination.

Native Claude `/skeptic` is a skill-based proposed-handoff helper, not an arrow-key
switcher. Codex uses `$skeptic`/skill picker, not a promised custom `/skeptic` slash
command. No documented mechanism was established for a skill to replace its parent
interactive application. Both use the reliable shell fallback; see README sources.

Existing Step 42 engine and Step 43B HTTP/Host/Origin/CSRF protections are unchanged.
CLI grants are separate, explicit, persistent, identity-pinned and revocable; app
restart grants remain session-only. Vault matching reads only canonical project
STATUS candidates, then confirmed-project/governing/exact-linked sources. No blanket
Developer/vault scan. Git observations refuse dangerous local/worktree config,
links/alternates or metadata-budget overflow, disable external helpers/hooks/locks
and withhold protected filenames. Unsupported `.git` pointers are refused.
Markdown never becomes shell code. No source edits, automatic canonical checkpoint
writes, auth, downloads or approval bypasses. Analytics defaults off and stores only
Skeptic-controlled launch/exit events, never token/cost/quota/success inventions.

Known limits: same-user access/process argument visibility/provider session storage,
filesystem/config races, imperfect secret detection and downstream prompt-injection
compliance; no production security certification. 48 KB context bound, excerpts and
Git listing truncation, unknown external/unsaved state, no semantic freshness proof,
fixed local ports and unsupported worktree/submodule metadata pointers. Sources
outside approved boundaries and ancestor instructions above the repository remain
unread. Missing Git/provider conditions are reported rather than fabricated.

## Git / first real acceptance

Source: `main`, HEAD `3a188b8293a5f13141776a5691acf0e81a109233`.
Pre-existing tracked website/product/docs/local-app modifications and untracked
local app/website lock/report are preserved. This change adds `apps/terminal`,
updates shared formatting in untracked `apps/local/app.py`, source README and
validation runner, and adds this report. No staging/commit/push/branch switch.
Only canonical Model-Blind OS STATUS/dashboard/Handoff changed in the brain;
unrelated dirty knowledge/preferences/Obsidian files remain untouched.

Exact Mac installation:

```sh
python3 -B ~/Developer/skeptic/apps/terminal/install.py
export PATH="$HOME/.local/bin:$PATH"; rehash
```

Shortest real acceptance: in the chosen existing Claude project use `/exit`, run
`skeptic`, select Codex with arrows/Enter, approve the printed read scopes once,
then have Codex identify its cwd and the next unfinished action from the checkpoint.
Confirm the instructions/checkpoint match before continuing edits. No copy/paste
prompt or dashboard needed. Direct fallback: `skeptic continue --with codex`.
Stop implementation here; record that real result before calling this product ready.
