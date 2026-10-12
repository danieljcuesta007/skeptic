# Step 44 — Continuity engine, offline adapters and observation slice

Local development only. No live configuration, source-session control, credentials, installation, canonical brain writes, merge, push or deployment.

## Implemented

- Explicit source/checkout inspection including staged and unstaged diff fingerprints, untracked status, missing sources, renames, detached/unborn Git and separate worktree identity.
- Separately explicit canonical Markdown roots; content and root identity freshness.
- Bounded Markdown checkpoint proposals, unverified completion claims, failures, decisions and pending tasks.
- Caller-reported receipts distinguished from observed fixture subprocess receipts; relevant source or evidence changes make receipts stale.
- Temporary-fixture reviewed append writer with destination/content approval, cooperative lock, source rechecks, fsync and atomic replacement.
- One portable skill, small Claude/Hermes/Codex notes, isolated packaging and bounded Claude hook-event parser. Events cannot launch, write checkpoints or establish quiescence.
- Offline provider-neutral assessment, destination reconciliation, explicit acknowledgement, per-session batch outcomes and returning-agent packages. Existing managed engine is preserved.
- Structured observation schema and standalone fixture-only service with pause/resume/shutdown through its inherited private stdin pipe. No network listener or login installation.
- Existing protected desktop backend reads fixture-engine observations only when explicitly configured; otherwise sessions remain unknown/unconnected. UI includes expandable continuity cards and compact presentation. No live switch controls.

## Local commands

From repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate.py --without-managed-runtime
python3 -B apps/desktop/build.py
python3 -B apps/terminal/continuity_cli.py propose --root "$APPROVED_REPOSITORY" --project-id "$PROJECT_ID" --canonical-root "$APPROVED_MARKDOWN_ROOT" --canonical STATUS.md --source src.py --agent claude --session selected-session --objective 'Continue the unfinished task'
```

The CLI emits a proposal to stdout and never writes canonical records. Explicit root arguments are caller-authorized scopes, not discovered grants. Do not redirect private proposals into committed source files. Existing transcript consent and managed-switch tools retain their separate permissions.

Service tests build owner-only package/state files in temporary directories. Run `continuity_service.py --state TEMP_STATE --packages PRIVATE_PACKAGES_JSON` only for fixtures; stdin accepts `pause`, `resume`, `shutdown`. The service continues without a desktop window while that stdin lease exists. EOF shuts it down. State snapshots older than five seconds become disconnected/unknown. Persistent/reboot supervision is not provided.

For fixture desktop connection only, launch the development backend with `SKEPTIC_FIXTURE_ENGINE` naming that owner-only temporary service directory. An existing app install is not changed. The HTTP observation route uses the existing Host/Origin/token checks and accepts no source path in requests.

## Guarantees and limits

Hashes establish integrity, not correctness. Command success is scoped evidence, not task completion. Destination acknowledgements here are explicit caller attestations in offline tests; they are not real provider-native responses. New hooks and skills were not activated or loaded by real agents. Hermes lifecycle integration remains unavailable; no undocumented mechanism is invented. The experimental subscription plugin is neither required nor installed.

The writer is fixture-only. Its cooperative lock cannot exclude uncooperative writers racing replacement. External canonical roots must be separately approved. Service observation is fixture-only and does not discover active sessions. Activity stays unknown; no quota predictions. The compact panel is a development UI, not a released macOS desktop widget. Existing desktop lease semantics remain unchanged; the separate service has its own lifetime.

Real Claude/Hermes/Codex delivery, installed-version compatibility, production writer safety, production migration, automatic project registration, reliable Terminal/transcript association, login activation, native visual/accessibility acceptance and reboot recovery remain pending. Full managed socket tests require a host that permits AF_UNIX.

## Acceptance scenarios

Tests preserve dirty/staged/untracked files; reject stale proposals/evidence, malformed receipts, missing/incorrect records, symlinks, permission failures, concurrent edits, unreviewed writes and interrupted replacements. Contract tests cover all six directed transitions, launch-without-acknowledgement rejection, wrong project, unavailable destination, writer conflicts, partial batches and a Claude→Hermes→Claude fixture with changed code and an observed assertion receipt. Service tests cover standalone subprocess lifecycle, pause/resume, restart, shutdown, stale connection and private-state checks. HTTP tests exercise the real parser over the existing memory transport.

No mocked response counts as live provider acceptance. Three planted faults must fail assertions: accepting stale inputs, treating launch as acknowledgement, bypassing checkpoint review.

## Verified development checkpoint — 2026-10-10

DONE: core proposals/receipts, external canonical roots, fixture append writes, portable skill, offline adapters/recovery, fixture service and desktop observation panel. This is a development slice of Step 44; the entire master plan is not complete.

VERIFIED:

- Initial recovery baseline: 218 tests, `python3 -B -W error::ResourceWarning -m unittest test_switcher test_sessions test_continuity test_recovery test_frozen test_open_sessions test_candidate_identification test_picker test_one_command test_session_review` from `apps/terminal`.
- Final `PYTHONDONTWRITEBYTECODE=1 python3 -B tests/validate.py --without-managed-runtime`: 436 Python tests plus 22 Node tests = **458 tests**; **258 planted faults** caught. Includes 28 new core/recovery/service tests and 3 new assertion-based faults. Website and local builds passed.
- `python3 -B apps/desktop/build.py`: native AppKit/WebKit compilation passed. Build includes shared observation modules and excludes private runtime state.
- `git diff --check` and credential-pattern/hardcoded-username checks on new core/skill files passed.
- Private preservation: primary archive copy/source/restore manifests matched, repository bundle verified and restored with fsck; supplementary brain bundle restored with fsck; historical test artifacts copied/revalidated. Final original-file comparison checked 1,061 files with zero content differences. Source repository refs necessarily gained the authorized development branch/worktree metadata.

NOT VERIFIED:

- Full managed runtime attempt: 23 tests, 22 startup errors and one readiness failure. Separate AF_UNIX bind probe returned `PermissionError` errno 1. No runtime success is claimed; socket-independent suite explicitly excludes these tests and their mutations.
- Browser discovery returned no available browsers. Native visual/accessibility acceptance is pending.
- Bundled skill validator could not import PyYAML. Required plain-scalar frontmatter/reference validation and fixture packaging passed; real host discovery/loading remains pending.
- No real agent launch, paid request, transcript read, hook activation, monitoring of real sessions, installation, canonical brain update or release.

FILES: `apps/terminal/{checkpoints,checkpoint_writer,continuity_adapters,continuity_cli,recovery_contract,continuity_service}.py`, focused tests and mutation runner; `skills/skeptic/`; desktop backend/build and local UI/HTTP route; validator and implementation docs.

NEXT: on a host permitting Unix sockets, rerun full managed validation in disposable fixtures. Complete native visual acceptance and version-specific adapter loading/lifecycle validation using isolated configurations before requesting any live activation. Real provider delivery and production monitoring require separate authorization. Preserve original worktrees and canonical records.

SESSION: isolated branch `work/skeptic-continuity-core`, based on `c91defb`; no merge, push or installation. Canonical STATUS was intentionally not updated. Continue from these files and current Git state; historical STATUS Git descriptions are stale.
