# Contributing (pre-alpha)

Start with the [README](README.md) for installation and current limitations. Skeptic
is pre-alpha; real-project/provider acceptance is still in progress.

## Useful first contributions

- Report a reproducible bug using the issue template and a synthetic example.
- Fix an unclear installation instruction or a broken documentation link.
- Suggest an improvement by describing the problem and your current workaround.

Search existing issues before opening one. For a substantial code or architecture
change, discuss the approach in an issue first. Never upload a vault or a session
transcript to demonstrate a problem.

## Pull requests

Branch from `dev` and target `dev`; release PRs promote `dev` to `main`. Keep each
PR focused and describe Why / What / Testing / Review notes.

Preserve existing architecture and dirty work. Use synthetic fixtures, minimal changes,
and tests that catch behavior failures. Run `python3 tests/validate.py` before review.
Never include real notes, keys, indexes or user-specific configurations. Do not add
provider/network calls, note writes or automatic preference promotion without scope
approval. Keep instructions provider-neutral and state capability limits.

Future PRs should include Why / What / Testing / Review notes. Before any merge,
Claude or Codex reviews the PR, findings are addressed or explained, and the review is posted
as "Review by Claude" or "Review by Codex", matching the reviewer. Risky/external actions require appropriate approval.
No remote, PR service, automation or contributor workflow is activated by this file.
