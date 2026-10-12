# Step 43B — Monochrome brand & unified workspace acceptance

**12 Oct 2026:** `network_smoke.py` PASSES on a real loopback socket (launch, workspace approvals, inventory, repository association, grounded detail, both prompts, origin/traversal refusal, project removal, root revocation). Automated *visual* acceptance is not possible: the Chrome extension's navigation arrives as `Sec-Fetch-Site: cross-site`, which the app correctly refuses. The visual checklist below is Daniel's (type the address yourself).

**Earlier:** Upgrade not yet accepted in a real browser. Daniel confirmed the original MVP
browser/dashboard and original socket smoke. Current agent socket bind is denied;
browser selection reports no browser and discovery is empty. Handler tests are not
live/browser evidence. Step 43A acceptance and Cloudflare launch remain separate.

From the repository in ordinary Mac Terminal:

```sh
python3 -B ~/Developer/skeptic/apps/local/network_smoke.py
python3 -B ~/Developer/skeptic/apps/local/workspace_fixture.py
python3 -B ~/Developer/skeptic/apps/local/app.py
```

Keep the two printed fixture roots. If the old app is running, stop that app with
Ctrl-C first. Open http://127.0.0.1:4317 and reload to load upgraded assets.

1. Before approving roots, confirm no discovery or source reads. Saved roots display
   NOT CONNECTED / fresh approval required. Approve only the printed synthetic vault
   using Connect My Workspace → Obsidian vault → FULL_BRAIN and the checkbox.
2. All Projects contains Atlas and Missing checkpoint; ordinary.md is not a project,
   private/STATUS.md is absent. Cards show sourced state/pending/handoff and honest
   readiness. All seven sidebar items work; Recent Projects updates after selection.
3. Open Atlas. Confirm checkpoint three, source paths/lines/hashes, vault instructions,
   unfinished acceptance and canonical Handoff. Repository is not connected yet;
   referencing its path does not scan it or approve it.
4. Separately approve the printed repository root. Atlas links to atlas automatically
   from exact STATUS paths evidence. Detail shows main and forty “a” commit characters,
   association source and repository instructions. Working-tree status is unknown;
   commit is never described as project progress. Repositories view works.
5. Resume work → Continue with Claude Code, then Codex. Review identity, source paths,
   governing references, checkpoint, unfinished work, Git observation, limitations,
   recommended action and preserve-unrelated-work instruction. Copy or Command–C
   fallback works. Nothing launches or uploads. Changing source/task/tool clears prompt.
6. For suggested matching, edit only the synthetic STATUS to remove its frontmatter
   paths block, then refresh. Same-name match needs review/explicit confirmation;
   no silent association. Confirm it and verify its user-confirmed label.
7. Permissions → review/change vault approval to PROJECT_SCOPED: Activity no longer
   reads ordinary.md. Change to ASK_TO_EXPAND: notes.md and handoff.md no longer read;
   STATUS and instructions remain. Changing policy requires explicit approval.
8. Remove Atlas: it is hidden this session, files still exist; UI explains root access
   remains. Disconnect roots: projects/repositories and continuation access disappear.
   Restart: saved remaining roots require fresh approval; no body reads at startup.
9. Verify an entirely monochrome wordmark, black primary/white secondary CTAs, neutral
   diagrams/cards/icons/checkboxes, readable active sidebar labels, visible keyboard
   focus and text-based readiness labels. No status depends on color alone.
   At 390, 768 and 1440px and 200% zoom, check readability, overflow, keyboard focus,
   labels, disabled controls and status announcements. Save synthetic screenshots of
   list, project, prompt and permissions. Observe no untrusted HTML execution.
10. Developer Tools Network: only 127.0.0.1 requests; repeat offline. No credentials,
    note bodies or prompts in persisted registration JSON; no arbitrary raw-file route.

Record timestamp, OS/browser, viewport/screenshots, smoke result, defects and retests.
After synthetic acceptance, the user may explicitly approve the real `~/brain` vault
and selected repository roots through the same UI. That approval is a distinct action;
development/testing does not silently discover the real workspace. Large approved
roots can hit bounded scan limits; approve narrower roots and report the exact limit.
No source edits, provider integration, deployment, commit or push are authorized by
this checklist. Fixture edits in step 6 are only disposable synthetic test data.

## Step 43E — Model Usage acceptance (still pending)

The unified Step 43F continuation reattempted app startup and the synthetic socket
smoke; localhost binding was denied. No live browser acceptance occurred. The Vitals
widget remains unchanged. Use ordinary Mac Terminal:

```sh
python3 -B ~/Developer/skeptic/apps/local/app.py
```

Open http://127.0.0.1:4317 → Model usage. Stop/restart only your own older Skeptic
server first if necessary. This usage acceptance does not require approving vaults.

1. Before connecting, verify automatic readings are unknown and no local provider
   activity is read. Filter Claude, Codex, Hermes, Midjourney, Gemini, OpenRouter,
   local models and Other; only matching cards remain, with honest unknown states.
2. Explicitly choose Connect local Claude & Codex readings. This grants fixed quota
   cache/bounded event-tail access as described in README, not session continuity
   permission. Activity buffers may contain conversation data; only quotas are exposed.
3. Verify reported remaining amounts, window units, reading timestamp/freshness and
   local-time reset dates against the authorized provider-reported data. Missing/reset
   readings stay unknown; neither a predicted reset nor an expired allowance implies
   available quota. No fabricated model availability or automatic account authentication.
4. Add synthetic manual Other entries `Acceptance A` (5/10 credits) and `Acceptance B`
   (2/4 GPU hours), using separate future reset dates. Confirm both coexist, units and
   labels remain separate, provider filtering works, and editing A does not replace B.
5. Disconnect local readings: automatic cards clear; manual entries remain. Restart
   the server and reload: both manual cards persist, automatic connection requires new
   explicit consent. Reconnect only if desired. The file is the system of record.
6. Delete only Acceptance A from its own card. B must remain after reload/restart.
   Delete B afterwards to clean up these synthetic entries. Other entries remain intact.
7. Verify `apps/local/.skeptic-local/usage.json` is mode 600 and its directory mode 700;
   it is ignored by Git. Do not paste its real contents into reports. Developer Tools
   Network shows only 127.0.0.1 traffic; nothing scrapes Chrome/provider websites.

Record actual OS/browser/time, filtering/card/freshness/reset results, persistence,
individual deletion and any defects. Supported quota timestamps are reported data;
manual reset dates are user-entered. No model reliability/recommendation analytics is
claimed from these acceptance checks.
