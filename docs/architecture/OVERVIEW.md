# Architecture

Original components: static website/onboarding simulation and POSIX Python
Markdown discovery. The website does not invoke the engine or access real notes.
The engine has one trusted host policy, private local indexing, bounded passages,
explicit governing-source references and provider-neutral receipts. Three modes:
FULL_BRAIN, PROJECT_SCOPED, ASK_TO_EXPAND. Public users choose explicitly.

Ordinary notes remain data. Index/cache inputs do not grant root/policy authority.
Future provider adapters must reference shared policy and canonical instructions,
not copy preferences. Provider capability detection and action enforcement are not
implemented. See packages/discovery/README.md and REQUIREMENTS-STEP39.md.

Step 43B adds a separate `apps/local` Python localhost host. It reuses engine read/
exclusion primitives with pinned, explicit project approvals and fresh user-selected
sources, without persisted indexes. Only ignored path/exclusion registrations persist.
Bundled UI assets and authenticated same-origin JSON operations have separate allowlists;
there is no arbitrary file-serving route, note editing, provider call or terminal execution.
FULL_BRAIN/ASK_TO_EXPAND remain standalone engine capabilities and are unavailable in
the app. See `apps/local/README.md`; live socket/browser acceptance is pending.
