# Contributing (pre-alpha)

Preserve existing architecture and dirty work. Use synthetic fixtures, minimal changes,
and tests that catch behavior failures. Run `python3 tests/validate.py` before review.
Never include real notes, keys, indexes or user-specific configurations. Do not add
provider/network calls, note writes or automatic preference promotion without scope
approval. Keep instructions provider-neutral and state capability limits.

Future PRs should include Why / What / Testing / Review notes. Before any merge,
Claude or Codex reviews the PR, findings are addressed or explained, and the review is posted
as "Review by Claude" or "Review by Codex", matching the reviewer. Risky/external actions require appropriate approval.
No remote, PR service, automation or contributor workflow is activated by this file.
