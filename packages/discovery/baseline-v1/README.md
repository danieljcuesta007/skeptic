# Skeptic discovery — isolated synthetic prototype

On-demand local Python 3.9+ CLI and library. Standard library only; POSIX
`dir_fd`, `O_NOFOLLOW`, and directory descriptors required. No installation,
provider calls, background jobs, Git commands, canonical writes or preference updates.
The included notes are invented fixtures, not copies of a private brain.

## Run only the synthetic example

From this directory:

```sh
PYTHONDONTWRITEBYTECODE=1 python3 discovery.py --catalog catalog.example.json --project synthetic-demo --task alpha --allow-root "b=$PWD/sample" > receipt.example.json
PYTHONDONTWRITEBYTECODE=1 python3 discovery.py --catalog catalog.example.json --project synthetic-demo --task beta --allow-root "b=$PWD/sample" --previous receipt.example.json > receipt.second.json
PYTHONDONTWRITEBYTECODE=1 python3 -W error::ResourceWarning -m unittest -v test_discovery.py
PYTHONDONTWRITEBYTECODE=1 python3 mutation_check.py
```

The first command's redirect is a local explicit write. The CLI itself prints
JSON; it does not persist changes. Results include a receipt and a reusable
state. Do not redirect onto existing files you intend to preserve.

## Authority and architecture

The caller supplies trusted catalog JSON, exact project ID, explicit task and
allowed root aliases. No prefix matching or recursive vault walk occurs.
Catalog entries are the approved source set, including approved linked notes;
links inside Markdown do not expand authority. Exclusions win over explicit
selection. Only relative root-qualified source paths are accepted. Symlinks
(including directory traversal) are rejected rather than followed, even when
pointing inside a permitted root. Missing project status is fatal.

Every successful body open is logged. Files are hashed through descriptor-relative
no-follow access; ordinary bodies are not parsed, executed, retained or emitted.
All authorized catalog candidates are hashed on first discovery, including
currently irrelevant candidates. Task selection uses approved metadata tags,
not body search. Explicit selections rank first, then rules, status, relevant notes.
A catalog role is host authority, never a role inferred from note prose.

The state contains hashes and stat signatures, no bodies. Unchanged stat signatures
reuse hashes; changed candidates are rehashed. Task relevance is recalculated each
call. Removed paths and same-hash rename candidates are reported after policy
filtering; rename candidates do not prove identity. A catalog must be updated
explicitly to introduce newly approved sources or renamed paths.

Handoff freshness compares optional caller-supplied checkpoint hashes, not timestamp
recency. Without these hashes it is unknown. Preferences are optional host-approved
structured declarations attached to rules. Conflicts block the next action; no
preference is resolved or written automatically. This does not parse arbitrary
natural-language contradictions. Preserve Claude's review gate in future adapters.

## Trust and limitations

This is NOT a sandbox for hostile plugins, hostile cache files, or concurrent
filesystem attackers. Catalog and previous-result JSON are trusted local inputs
read separately from note access policy. Do not supply them from an untrusted agent.
Root policy and source classification require human approval. Root replacement
races, hard-link identity, cache tampering and OS-wide enforcement are not solved.
Metadata-based reuse is freshness evidence, not a cryptographic proof of current
bytes; a new receiving model still needs to read the applicable rule references.
No Git/branch validation, concurrency detection, semantic conflict engine, real
provider onboarding or native adapter integration is included. The CLI accepts
explicit roots; synthetic-only operation is an operating restriction, not an OS
jail. Do not point this prototype at the real brain.

## Tests and future integration

Tests create only synthetic temporary trees. They instrument os.open and body-read
receipts, reject excluded and unauthorized reads, test file/directory symlinks,
changed rules, task changes, deletion/rename, ambiguous project IDs, stale handoffs,
structured conflicts, root cache invalidation and missing status. Network/socket
and process launch entry points are trapped in the no-external-action test; source
contains no networking or process execution. Mutation checks plant one fault per
regression test in memory, then require that test to fail; production source is
unchanged.

Future separately approved integration: router context selection could call this
library; adapters could consume references and freshness receipts. Add trust-boundary
and OS isolation review before any private data use. Nothing is wired in now.

## Rollback

No live rollback is needed. After inspecting for later additions, remove only this
isolated prototype directory. Do not restore, reset or clean any repository.
