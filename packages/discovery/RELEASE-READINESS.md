# Skeptic release readiness — Step 39

Status: isolated, synthetic-data prototypes. Not ready for public product release.
This plan is proposed work, not authorization to install, publish or spend money.
The website and engine remain separate; canonical user knowledge is never the public
website repository. No demand, willingness-to-pay or legal clearance is established.

## 1. Minimum viable product

An explicit on-demand Markdown context tool: choose an existing knowledge root,
choose a shared access mode, identify canonical rules, retrieve bounded context,
produce a neutral onboarding receipt, and preserve a user-approved checkpoint.
Exclude unattended services, silent writes, remote indexing and automatic inference
promotion from the first release. Three-mode retrieval is implemented and synthetically
tested; installer and native provider adapters are planned.

## 2. Ideal initial users

Hypothesis: technical Markdown/Obsidian users who already move between coding agents
and can assess file permissions. Recruit a small consented beta; validate actual pain,
frequency of switching and support burden before claiming a market. No user study ran.

## 3. Differentiation hypotheses

Against provider-specific instruction files: a shared policy and portable checkpoints.
Against manual prompt copying: source references and freshness evidence.
Against knowledge editors: complement existing files rather than replacing the editor.
Against hosted retrieval tools: local indexing and explicit selective transmission.
These are positioning hypotheses, not verified competitor feature comparisons or
claims of uniqueness. Research named alternatives and their current capabilities later.

## 4–7. Four first-run paths

- Claude-first: detect native instruction discovery, preview a pointer to shared rules,
  preserve existing files, and test fresh Claude recovery. Preserve mandatory Claude PR
  review and its "Review by Claude" comment before merges. Installer not implemented.
- Codex-first: detect native instruction locations, preview a shared pointer, preserve
  existing config, and test recovery independently. Do not copy provider credentials.
- Local-model-first: ask for the host/agent, detect filesystem/tool support and context
  limits, disclose any outbound calls, and degrade to a sanitized context package when
  file access is absent. Do not equate local inference with capable agent tooling.
- Starting fresh: guided creation of a minimal user-selected Markdown workspace only
  after permission. Existing notes remain preferred. Website illustrates this path;
  no folders or provider configuration are created by the demo.

## 8. Compatibility

Ordinary Markdown requires no proprietary frontmatter or vault restructuring.
Obsidian, Foam and SilverBullet are compatibility targets through their Markdown,
not validated native integrations. Attachments, external symlinked roots and app-private
metadata are outside the engine's tested surface. Test representative synthetic vaults.

## 9. Safe installation/uninstall

Before any real installer: dry-run change plan, exact ownership inventory, narrow
writes, originals preserved, rollback and uninstall tests on clean synthetic homes.
Uninstall removes Skeptic-owned adapters/indexes only and leaves user notes intact.
Never reset a repository or overwrite changed originals. Current prototypes install
nothing and their directories can be removed after checking for later work.

## 10. Capability detection

Host adapters should report actual file/tool access, native instruction entry points,
model context constraints and provider destination/data handling. Unknown stays unknown.
Probe only safe local capabilities with consent; no automatic account login or escalated
permissions. Capability detection is planned; receipts currently disclose unknowns.

## 11. Shared access policy

FULL_BRAIN: ordinary eligible notes across the selected root, with protected exclusions.
PROJECT_SCOPED: shared rules plus approved project paths. ASK_TO_EXPAND: shared rules
and status only until an approved host policy change. One host policy governs all
adapters. FULL_BRAIN is the owner's personal design default; public onboarding requires
explicit choice. Catalog requests may narrow/select, never redefine host authority.

## 12. Automatic project continuity

Current behavior is agent-followed Markdown convention, not automatic synchronization.
A future adapter may propose verified checkpoint updates, show the target and diff,
serialize concurrent ownership and obey scope approval. Persist outcomes, uncertainties,
Git state and next action. Crash/kill recovery cannot guarantee a checkpoint.

## 13. Preference learning with approval

Keep explicit preferences, observed patterns and tentative inferences distinct. Show
evidence and scope, propose exact wording, obtain approval, then narrowly update the
appropriate canonical source. No dossier or global rule silently created. Current
conflict checking supports explicit `Preference: key = value` in designated rules only;
natural-language conflict detection and approval UI are planned.

## 14. Security/privacy

Implemented synthetic boundaries: exclusion-before-read, directory scope pruning,
no-follow reads, hard-link rejection, bounded passages, fresh governing hashes,
cache/catalog scope checks, private index files and Git-destination refusal. No network
or execution integration. Secret-string quarantine is a secondary heuristic after local
reading, not a complete detector. Index content and filenames are private derived data.
Remaining gates: adversarial cache/schema/size tests, race review, retention/encryption,
Unicode/case aliases, performance/DoS bounds and independent security assessment.
A model instruction contract is not an OS sandbox. Direct host filesystem access could
bypass a broker unless the host enforces mediation; this is not solved by the prototype.

## 15. Packaging/code signing

Start with reproducible source/CLI packaging and declared Python/POSIX requirements.
For a desktop installer later, assess platform signing/notarization and distribution
requirements from primary platform documentation. No signing identity or certificate
was acquired, and Windows support is not established. Keep secrets outside source.

## 16. Documentation/support

Ship beginner guides for four paths, policy examples, explicit provider disclosures,
troubleshooting, uninstall/rollback and a support channel that requests sanitized logs.
Current READMEs and website intro are prototypes; no live support service exists.

## 17. Website deployment

See website CLOUDFLARE-PLAN.md. Static build and headers are prepared; browser and hosted
header acceptance are pending. Deploy only a reviewed clean website repository, never
private brain history, engine caches or development archives. Separate approval required.

## 18. Early-access beta

Current signup is intentionally inert. Before collecting anything: choose minimal
fields, retention/deletion process, consent/disclosure and a secured backend. Invite a
small voluntary beta; use synthetic data first, then separately consented personal data.
No actual waitlist, tracking or submissions are active.

## 19. Pricing/licensing possibilities

Options to validate: free local core with paid support, one-time desktop license, or a
subscription for maintained adapters/team features. No price, conversion or market-size
claim is supported. Existing prototype LICENSE is MIT; review component rights and
future licensing deliberately before release. Do not silently change existing licenses.

## 20. Domain/trademark research

Before selecting a public name: research relevant product categories, official trademark
registers and domain availability in intended markets; document findings and obtain
qualified advice where needed. "Skeptic" is a working name. No clearance, domain
availability, registration or purchase is claimed. Do not imitate other brands' assets.

## 21. Release acceptance and next milestone

Next milestone: independent security review plus real-browser acceptance on synthetic
fixtures. Then separately approved provider onboarding tests, packaging/uninstall
fixtures and beta preparation. Public MVP requires:

- Three modes and all regressions pass from clean source; mutation checks remain useful.
- Protected data never reaches unauthorized results; policy and cache threats assessed.
- Governing instructions freshly verified before consequential action; conflicts block it.
- Real desktop/mobile/keyboard/assistive-tech QA and no-tracking/network inspection.
- Native Claude/Codex/local onboarding either verified or explicitly excluded from release.
- Safe install/uninstall, sanitized support, licensing/name and provider disclosures ready.
- Explicit release/publication approval and required Claude review for any PR merge.

## Capability status

| Capability | Status |
| --- | --- |
| White-first website and eight-step walkthrough | Implemented prototype; logic/static tests pass; browser unverified |
| Local Markdown index and bounded passages | Implemented prototype; synthetic tests pass |
| Three shared modes and automatic ordinary-note discovery | Implemented prototype; synthetic tests pass |
| Neutral receipt, freshness and structured conflicts | Implemented prototype; synthetic tests pass |
| Approved memory writes/automatic continuity | Documented/planned; no automatic writes |
| Installers, native adapters, capability detection | Planned/unverified |
| Production security, signed package, support and beta | Not release-ready |
| Cloudflare launch, domain and live signup | Not deployed or connected |
