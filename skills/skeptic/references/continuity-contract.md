# Provider-neutral continuity contract — Step 44

Status: local development; fixture writer only. No live integration activation.

Canonical truth is user-owned Markdown. Operational receipts are integrity and execution evidence, not a competing knowledge database. Transcript access remains governed by existing consent adapters. No transcript is required for filesystem recovery; missing conversational intent stays unknown.

A project has a user-assigned stable ID and canonical record. A checkout identifies its absolute root, device/inode, Git directory and common Git directory; the latter distinguishes repository lineage from a worktree. Session and agent IDs are independent of Terminal tabs. Unconfirmed associations never become verified identities.

Checkpoint proposals record objective, constraints, decisions, unverified completion claims, pending work, failures/interruptions, uncertainty, writer observation, Git HEAD/branch and porcelain status, staged/unstaged diff hashes and explicitly approved source content hashes. Deleted sources are recorded as missing. Receipt freshness compares current source and Git observations plus evidence content. Hashes do not attest authorship or semantic correctness. Caller-reported command results remain explicitly attributed.

Recovery uses the same proposal envelope. Destination must inspect its actual checkout, verify the package fingerprint and fresh sources, review failed/stale evidence, resolve writer uncertainty and identify pending work before edits. Returning agents receive a new proposal, not a claim that stale conversations were updated.

States: identity_uncertain → checkpoint_proposed → handoff_blocked or awaiting_approval → ready_for_transfer → destination_launched → reconciliation_pending → destination_acknowledged → handoff_complete. Failure or changed evidence blocks advancement. Launched is never complete. Existing managed-switch journal states remain unchanged.

Writer clear is an explicit scoped observation, not proof of global quiescence. Existing managed reservations are cooperative; escaped processes and unrelated agents cannot be ruled out. No automatic stop or process adoption is supported.

Fixture writes require exact destination plus reviewed content digest. They append, preserve previous bytes, use a cooperative lock, recheck source state, fsync and atomically replace. This cannot prevent an uncooperative writer racing the final replacement; live canonical writes remain disabled. Fixture Git must ignore `.skeptic-*` bookkeeping. Interrupted temporary output never becomes canonical truth.

Current bounds: sources at most 256 and 8 MiB each; canonical source may use a separately explicit approved Markdown root. Its root identity and content fingerprint are revalidated independently. A production-grade write protocol remains pending. Source bodies and diffs are not included in proposals. Paths and hashes may still be sensitive: packages remain local until explicit transfer review.
