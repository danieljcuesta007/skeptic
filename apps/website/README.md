# Skeptic website V1
Local-only, white-first editorial prototype. HTML/CSS/vanilla JavaScript. No runtime dependencies, remote assets, accounts, analytics or API calls. Synthetic demo only.

Requires Node 18+ to build/test and Python 3 to preview:

    npm run build
    npm test
    npm run preview

Open http://127.0.0.1:4173. Stop preview with Ctrl-C.

Cloudflare Pages static configuration: build command `npm run build`, output directory `dist`. No deployment has been performed. Publishing requires separate authorization.

The onboarding simulator does not read files or connect to providers. The template download contains invented sample content. Project documentation and archive test evidence informed status labels; no private notes are included. Full-brain indexing, provider adapters and automatic preference learning remain unimplemented design targets.

## Homepage and guide

The homepage has six focused sections. `guide.html` preserves the full eight-step
walkthrough, sample receipt, product details, documentation, FAQ and inert signup.
Both pages share readable typography and wrapping controls. Browser acceptance
remains pending; see [Step 43 report](../../docs/ux/STEP43-REFINEMENT.md).

## Guided onboarding and product status

The eight-step walkthrough offers Claude Code, Codex, local model and starting-fresh paths; three knowledge sources; explicit policy selection; synthetic preference and handoff previews; completion and restart. Early access is a UI demo with a disabled example email: no collection, storage or submission.

`wizard-state.js` keeps state transitions separate from DOM rendering. `onboarding.js` provides the accessible view. The original receipt demo and Markdown download remain. Marketing distinguishes documented workflows, isolated prototypes and planned integrations. Engine V2 is developed independently; this website does not invoke it.

Release gates: real desktop/mobile visual QA, keyboard and assistive-technology testing, truthful provider disclosures, native adapter acceptance, privacy/security review and deployment approval. No production readiness claim is made.

## Visual architecture / Step 43A

Three responsive HTML architecture diagrams distinguish synthetic prototypes,
documented workflows and planned integrations. No external image/font dependencies.
Eight-asset Direct Upload readiness is documented in `CLOUDFLARE-PLAN.md`; no account,
project or deployment is confirmed. Browser acceptance blocks public upload.
Full evidence: [Step 43A report](../../docs/ux/STEP43A-LAUNCH-READINESS.md).
