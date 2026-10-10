# Step 43F — substantive frozen-session recovery and same-terminal workflow

2026-10-09. Your work. Your memory. Any AI.

## Implemented

The shared adapter now separates whole-message quota/service notices from substantive user tasks. Control-only followups such as “continue” need the prior task and do not replace it. A broken or detached quota tail can recover preceding user requests and the nearest substantive visible branch. Its assistant actions and user requests are explicitly labeled historical, outside the recovered chain and unverified. Hidden reasoning, raw commands, tool outputs and credentials remain excluded. A quota-only source reports **Substantive task NOT recovered**, rather than claiming success. Original objectives, recent substantive requests and bounded tool/file references receive preference; per-message clipping, chain gaps and omitted evidence are disclosed. The handoff includes a substantive request candidate with attribution, not a raw transcript dump or invented semantic summary. The full 1.68 MB real transcript has NOT been read by this worker.

Bare `skeptic` opens a beginner workflow menu: recover an approved Claude session, or continue the current project from approved notes/Git. Recovery offers consent-gated session selection, project confirmation including another-folder entry, the existing arrow-key provider picker and exact handoff review before `send`. Explicit IDs and destinations remain supported. No desktop/browser dependency. Provider authentication, cloud catalog and quota remain unknown unless actually reported; Skeptic does not authenticate. `--model IDENTIFIER` safely passes an explicitly chosen cloud model to documented installed CLI flags; the provider validates availability. Detected configured local models retain their existing adapter and no downloads occur. Recent providers persist; provider-native model configuration remains the normal default.

The recognized Claude helper was upgraded locally; unrelated/custom helpers are preserved. `/skeptic` remains a prompt skill, **not a guaranteed quota-independent command or interactive process takeover**. Its instructions now guide suspension and standalone recovery. Supported host customization documentation: [Claude skills](https://code.claude.com/docs/en/skills).

## Same terminal, no original-process termination

Claude documents Ctrl+Z suspension on Unix and `fg` resumption: [keyboard controls](https://code.claude.com/docs/en/interactive-mode). The user operates these keys; Skeptic injects no input, sends no signals to Claude and does not close/delete it. Once the shell owns the terminal, Skeptic launches the destination interactively there. If suspension is unavailable in the particular host/terminal, keep Claude open and use a second Terminal. A user may instead explicitly exit via the provider's own interface; Skeptic never does this automatically. Shell mode/skills inside Claude are not used to nest another interactive TUI.

### First real acceptance — existing frozen session

Inside Claude, press **Ctrl+Z**. Once an ordinary shell prompt appears:

```sh
"$HOME/.local/bin/skeptic" --id 2be6a8f6-18ee-4a9b-b6dc-693511b2275a --cwd "$HOME/Developer/skeptic"
```

Choose **Recover a Claude session** (Enter). Approve intended local scopes if requested. Choose Codex with arrows. Before typing `send`, verify the preview contains the actual unfinished task and instructions, not only notices, and marks historical/gap evidence correctly. If it lacks the substantive task, cancel and report the gap; do not call that recovery successful. Ask Codex to explain Claude's latest unfinished work and distinguish source claims from observed Git facts before changing files. Confirm its cwd. No manual prompt copying.

When Codex returns to the shell, `fg` resumes the suspended original. Visually confirm preservation. Resuming an old TUI does not provide new knowledge automatically. `skeptic session verify` checks sampled transcript bytes; live append/replacement may require a new preview and it does not establish process liveness.

When Claude quota returns, a fresh grounded continuation:

```sh
cd "$HOME/Developer/skeptic"
"$HOME/.local/bin/skeptic" catchup --with claude
"$HOME/.local/bin/skeptic" continue --with claude
```

Fresh approved sources/Git and intervening Skeptic transitions provide catch-up. This launches a new interactive Claude worker; it does not inject a briefing into the suspended old process. Unsaved Codex-only decisions remain a disclosed gap unless accessible approved notes or a supported explicitly selected export preserve them.

### Standalone and integration installation

The owner-local CLI and recognized Claude helper were updated in this session. Interactive Terminal PATH setup already exists; the absolute invocation above also works in older windows without reloading PATH. Reinstall supported integration from the source:

```sh
python3 -B ~/Developer/skeptic/apps/terminal/install.py --integration claude --upgrade-integrations
```

No provider installation/authentication or permanent background service. Existing owner-only, inode-pinned approvals persist and are revocable. Session discovery and selected transcript permissions remain separate; outgoing context always requires review.

## Verification and limits

Final repository validator: **285 tests passed, 221 planted faults caught**. Website/local builds passed. Synthetic quota tails (including 2,000 notices), detached/gapped chains, control-only followups, objective/task preservation, clipping, secrets, explicit model argv, default recovery→approved fake Codex, and existing bidirectional/security regressions passed. A Mac zsh PTY test suspended a fake original, ran the shared launch engine with a second fake agent on the **same TTY and correct cwd**, then resumed the original; source bytes remained unchanged. Real Claude Ctrl+Z, native helper execution at quota, this real transcript's recovery quality, real Codex launch and live returning-Claude catch-up remain unverified.

Follow-up, not claimed implemented: a managed-agent supervisor with explicit lifecycle controls; broad Trusted Owner/Choose My Sources onboarding; safely approved linked-worktree/common Git metadata; modern Codex paginated transcript support. Unsafe Git pointers still fall back to labeled conversation evidence; explicitly select the actual repository when available. No full-home scan or permission weakening. Session text filtering is heuristic: inspect sensitive previews before approving cloud transfer.

Desktop, website, Model Usage and Vitals unchanged. Original Claude/transcript files untouched. Main remains 3a188b8, empty index; prior dirty/untracked work preserved. No commits, push, merge, reset or deployment.
