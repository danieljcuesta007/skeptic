# Skeptic discovery V2 — isolated development copy

Provider-independent, on-demand lexical indexing and bounded retrieval over ordinary
Markdown. No provider SDK, remote embeddings, networking, hooks, daemon or live-brain
integration. Python 3.9+ standard library, POSIX descriptor APIs required.

The preserved archive is copied unchanged into baseline-v1/ with its original manifest.
This directory is independent of that archive and of the website. Nothing is installed.

## Synthetic demonstration

    PYTHONDONTWRITEBYTECODE=1 python3 run_demo.py
    PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v test_engine.py

The demo uses only sample/ and creates a private sample-index.json in a new temporary directory,
outside this Git repository and the notes. FULL_BRAIN is this project's owner's personal design default;
public users must choose an explicit mode. Do not run this prototype against real notes.

## Shared policy

One host-approved JSON config controls root, mode, protected exclusions, canonical rule
paths, project identities/paths and maximum file size. FULL_BRAIN enumerates ordinary
Markdown automatically, including newly added files. PROJECT_SCOPED opens only rules
and project context. ASK_TO_EXPAND opens rules/status only; requests outside that scope
are denied. Expansion requires a separately approved host policy change, never a note
instruction. Project matching is exact; full brain can search without a project.

Built-in path exclusions cover Git/application state, .env files, credential/secret
names and private keys. Explicit protected paths are excluded before traversal/reads.
Files with unexpected secret-like strings are quarantined after local reading; this
heuristic is imperfect and cannot replace explicit exclusions. All eligible ordinary
notes are searchable: no per-note catalog, no proprietary frontmatter and no note edits.

## Index, search and freshness

The private JSON lexical index stores bounded text chunks, hashes and stat signatures.
It is sensitive derived data and must never be bulk uploaded or automatically committed.
Search uses Unicode word overlap, ranks explicit files/rules/status before matching data,
and returns at most five passages / 1,800 characters by default. Limits are configurable.
It recomputes relevance for every task. Instruction files are explicit references;
ordinary notes always have role=data, including hostile instructions found in prose.

A refresh detects additions, edits, deletion and hash-match rename candidates. Unchanged
stat signatures avoid body rereads during refresh. Selected passages are freshly rehashed
before returning; changed/deleted sources are withheld with a reindex signal. Policy
changes require reindexing and revoked content is removed from the resulting index.
Required missing rules/status block the next action. No claim of semantic preference
conflict detection or automatic preference learning is made.

Source access uses a pinned root descriptor and O_NOFOLLOW on traversed directories/files.
Symlinks are skipped during discovery and rejected on direct reads; hard-linked files are
rejected. Atomic index persistence uses owner-only files outside the knowledge root.

## Trust boundaries and limitations

Host policy is trusted authorization; persisted indexes and catalogs are untrusted data.
Cache envelopes, scoped records, types and resource bounds are validated before source
reads; protected/revoked and non-Markdown ordinary cache records are discarded. Invalid
caches raise `Denied` with generic diagnostics; the CLI exits without a traceback or
fallback provider. Rebuild explicitly after inspecting the cache/policy. The CLI limits
cache input to 32 MiB, rejects duplicate JSON keys, non-finite constants and unsafe
cache files. Cache records cannot grant source roles or expand host scope.

Exclusions match casefolded, NFKC-normalized names conservatively on every platform.
Descriptor reads require each path component to match an actual directory entry exactly,
rejecting alternate aliases before opening note bodies. This can overexclude names and
adds directory enumeration cost. Returned passages come from freshly read bytes and are
credential-checked again; governing handoffs/preferences must also be fresh and pass
that heuristic before emission. Governing validation does not bypass cache validation.

No cryptographic cache authentication, encrypted index, hostile-parent race defense or
OS sandbox is provided. A malicious valid cache can influence ranking/omissions and
hash-based freshness is not authentication against an attacker controlling cache and
sources. JSON bounds mitigate some malformed-input failures, not all resource attacks;
large-vault performance and concurrent root/parent changes remain unverified. File mode
0600 does not protect against same-user processes. Metadata alone is not proof of byte
freshness. Source budgets do not guarantee every required rule fits into returned
passages; agents must read applicable full rule references.

Lexical ranking is deliberately simple, not semantic search. Markdown-only; attachments,
external symlinked folders and proprietary app data are not covered. On-disk text chunks
are sensitive. No agent/provider/Git/concurrency capability detection, automatic approval,
or production installation/uninstallation exists. Preserve Claude's PR review gate.

## Productization gates

Before release: independent security review, adversarial cache/path/race tests, encryption
and retention decisions, provider disclosures, policy UI, packaging/uninstall tests,
measured performance on synthetic large vaults, native onboarding acceptance and browser
accessibility QA. Add adapters as references to one shared policy, not permission copies.

Rollback: no live rollback is needed. Inspect for later work and remove only this isolated
development directory if desired. Keep the original private archive intact.

## Step 39 additions

See REQUIREMENTS-STEP39.md and RELEASE-READINESS.md. Query now revalidates every designated
rule and project status, even beyond passage limits, and includes a current bounded
handoff plus hashes. `revalidate_governing()` is available for future hosts to call
immediately before consequential actions. No host/action integration is active.

Optional catalog requests can only list already-scoped source paths; they cannot supply
roots, rule roles or policies. Root configuration remains trusted host authorization.
Structured rule declarations use `Preference: key = value`; conflicts block next action.
Private index persistence rejects Git-ancestor destinations. Quarantine output withholds
filenames. These additions do not authenticate hostile caches or enforce an OS sandbox.

## Step 42 — Security Hardening & Shared Development Step Naming

S41-01/02/03 are fixed with synthetic adversarial regressions. See
`../../docs/security/STEP42-HARDENING.md` for evidence, remaining limits and verification.
Run `python3 -B -m unittest -v test_engine.py test_security.py`, then
`python3 -B mutation_check_v2.py` and `python3 -B mutation_check_security.py`.
The preserved baseline is unchanged. No live scanning or provider integration is installed.
