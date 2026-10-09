# Portable brain onboarding — workflow requirement

Daniel requested this on 2026-10-09. Product notes, not implemented UI behavior.
Do not claim the existing Skeptic app already creates or compounds a brain.

## Onboarding sequence
1. Explain Markdown ownership, portability, provider independence and local scope.
2. Ask for a selected folder and explicit read approval; inspect only approved files.
3. Detect existing PRINCIPLES/AGENTS/preferences/profile files. Reuse the user's
   structure and sources; never overwrite or silently replace existing instructions.
4. Interview the user about roles, priorities, values, communication and desired
   assistant support. Draft USER.md with confirmed facts and explicit unknowns;
   SOUL.md for communication; IDENTITY.md for assistant responsibilities.
5. Show a preview mapping People, Projects, Decisions, Companies, Meetings, Daily,
   Knowledge and optional MOCs into existing folders. Avoid forced migration.
6. Offer meeting extraction and daily templates, keeping originals and attribution.
7. Explain compounding: reviewed extraction, meaningful links, updated maps,
   commitments, contradictions and duplicate candidates. A scan is not understanding.
8. Preview exact file changes and get write approval separately from read approval.
9. Offer an optional separate local nightly review queue; explain scope, missed runs,
   uninstall and that no model call, source rewrite or cloud transfer is implicit.
10. Show what is created, unknown, pending review and scheduled; provide a portable
    continuation prompt and a guide that remains understandable without Skeptic.

## Acceptance requirements for future implementation
- Existing vault and brand-new vault flows; no duplicate authoritative preferences.
- Unknown identity facts remain unknown. No preference promotion from AI inference.
- Source preservation, attributable summaries and human-reviewed merge proposals.
- Relocation/new username/OS support; no hardcoded personal paths in shipped files.
- Explicit separate read/write/schedule/provider permissions and clear revocation.
- Never claim ongoing semantic improvement from backup, indexing or graph density.
- Synthetic tests and actual browser acceptance before marking UI workflow complete.

## Reference implementation
Daniel's canonical brain: USER.md, SOUL.md, IDENTITY.md, BRAIN-WORKFLOW.md,
meeting/daily templates, 07 MOCs/Brain map.md and bin/brain-review.py.
Reference via approved folder registration; do not ship Daniel's profile or notes
as example content. Current local app remains read-only; onboarding writes and
scheduling need future implementation and security review.
