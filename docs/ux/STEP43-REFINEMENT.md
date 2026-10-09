# Step 43 — Website UX Refinement & Browser Accessibility

2026-10-09 · Codex · Authorized local refinement; no commit, push or deployment.

## Original problems and evidence

Daniel reported difficult text, excessive scrolling, oversized red “Explore the
preview” CTA and adjacent controls clipping. The Step 42 homepage had 14 sections
and 1,597 text words (HTMLParser data tokens, including navigation/metadata). It
mixed marketing, onboarding, receipt configuration, compatibility, privacy,
roadmap, FAQs, feature descriptions, docs, signup and final actions.

Source inspection confirmed 7–11px labels, 13px body text in cards, 75px section
padding on each side, and a mobile `.start .button` rule forcing full width. The
final download control used independent margins rather than a wrapping action row.
These are source-level findings: the reported rendered CTA/clipping could not be
reproduced because no real browser was available. No before/after screenshots exist.

## Before → after

- Homepage: 14 → six sections (57% fewer); 1,597 → 377 text words (76% fewer).
  Actual rendered page height/scroll reduction is unmeasured.
- Six sections: hero/value proposition, simple explanation, three benefits,
  how it works, four starting paths, final CTA. Approved identity/bridge retained.
- Receipt demo, eight-step onboarding, detailed provider status, Markdown example,
  privacy, roadmap, feature availability, FAQ, introductory docs and inert signup
  moved to `guide.html`. Sample checkpoint download remains there. Important product
  disclosures remain available through header/section links and guide navigation.
- Repeated ownership/context marketing consolidated into short benefit/step copy.
  Source-level section padding reduced from 75px to 48px desktop / 36px mobile.
- Headings use responsive sizes with proportional tracking; normal body text is
  16px, path cards 15px, supporting text 14px, metadata at least 12px. Paragraph
  width is capped at 65ch. No tiny mobile typography override remains.
- Buttons use content-based width, 10px/16px padding and a 44px minimum target.
  Both final CTA groups wrap with gaps. Homepage mobile CTA stays content width;
  guide Back/Continue controls wrap. No `overflow:hidden`/`clip` workaround.
- Simpler onboarding headings/explanations retain explicit access selection,
  approval before permanent preference updates and no real setup claims.
  Claude-first, Codex-first, local-model-first and fresh-start paths are preserved.

## Responsive implementation and acceptance

| Width | Source rules implemented | Rendered result |
| --- | --- | --- |
| 375px | Wrapped header; one-column cards/demo/wizard; stacked final actions; 20px gutters | NOT VERIFIED |
| 390px | Same mobile rules; content-width red CTA and wrapping control labels | NOT VERIFIED |
| 768px | One-column split/demo/wizard; wrapped progress list; two path columns | NOT VERIFIED |
| 1024px | Two path columns; stacked receipt field pairs; 32px gutters | NOT VERIFIED |
| 1440px | 1200px maximum container; three benefit/step columns; four path columns | NOT VERIFIED |

Grid tracks use `minmax(0,1fr)`, children can shrink, long references wrap, native
selects have minimum width zero, buttons wrap, and meaningful content remains visible.
These source checks do not prove absence of horizontal scrolling, clipping, zoom
issues or correct native-select rendering. Manual acceptance is still required.

## Accessibility findings

Each page has one h1, labeled navigation, a skip link and a focusable main target.
Visible focus applies to all elements, including programmatically focused wizard
headings. Native buttons/selects/details, labels, live receipt/status/error regions,
current-step progress, Back state and reduced-motion rules remain.

Calculated sRGB contrast: black/red 5.56:1; muted gray/white 8.06:1; muted gray/paper
7.52:1. Red/white 3.78:1 and red/paper 3.52:1 are suitable for focus/structural
accents, not normal small text; text on red remains black. These calculations do
not constitute a rendered contrast or full WCAG audit. Disabled controls remain
visually distinct and inert. Screen-reader, keyboard, reduced-motion, pointer,
zoom and visual consistency acceptance remain unverified.

## Browser evidence and manual next check

Browser skill was read and runtime setup succeeded, but default selection returned
“No browser is available.” Following its troubleshooting documentation, browser
listing returned `[]`. No browser tabs, browser tests or screenshots were produced.

Run `npm run build` then `npm run preview` in `apps/website`; open
http://127.0.0.1:4173. Follow `BROWSER-ACCEPTANCE.md`: inspect both pages at all five
widths, keyboard through all eight steps on all four paths, generate receipts,
inspect the download, open FAQs, exercise inert signup, check zoom/reduced motion,
Console/Network and capture screenshots of the hero, CTA and guide/wizard.
Python preview does not apply Cloudflare headers. Hosted acceptance remains gated.

## Validation and review

`python3 -B tests/validate.py` passed:

- Website production build: eight allowlisted assets, including `guide.html`.
- Website: 13 tests (previous 10 updated for two pages, three focused regressions).
- Discovery V2: 36 tests / 36 mutations, including all Step 42 security checks.
- Preserved V1: 18 tests / 18 mutations; migration: one test.
- UX: five mutations rejected by their expected regression tests in disposable
  temporary copies: broken guide link, repeated section, extra primary heading, hidden overflow, full-width
  mobile CTA. Baseline passes; no production source is mutated by the runner.
- Total: **68 tests / 59 mutations caught**, zero final failures.
- Complete tracked diff and new files reviewed; `git diff --check` passed.
  Discovery engine, security files and `_headers` remain unchanged.

The initial extraction script omitted multiline matching and stopped before writing
website files; corrected extraction succeeded. No test requirements were weakened.

## Changed files

- Website: `index.html`, new `guide.html`, `style.css`, `onboarding.js`,
  `wizard-state.js`, `build.mjs`, `test.mjs`, new `mutation-check.mjs`,
  `BROWSER-ACCEPTANCE.md`, `CLOUDFLARE-PLAN.md`, `README.md` (under `apps/website`).
- Validation: `tests/validate.py`, `docs/development/VALIDATION.md`.
- Product/development docs: root `README.md`, `docs/product/README.md`, this report.
- Existing canonical Obsidian `STATUS.md` and `development-dashboard.md` only;
  unrelated dirty brain files and Handoff preserved.

## Git, continuity and remaining blockers

Started clean on `main` at `a4da6daacf04ca6f08d2013a9f32e8ea562afce7`.
Finished on the same HEAD with local tracked modifications/new files, nothing staged.
No commit, push, GitHub visibility change, Cloudflare deployment, provider change,
real-note access, service installation or brain commit. Existing unrelated brain
changes and inactive Handoff preserved. Canonical STATUS/dashboard updated narrowly.
Remote visibility/HEAD were not reverified in this session; prior evidence is Daniel’s.
Claude review with a “Review by Claude” comment remains mandatory before any PR merge.

Remaining release blockers: real browser/assistive technology acceptance, provider
capability and data-handling acceptance, packaging/install/uninstall, independent
security review and broader cache/resource/filesystem-race hardening. Plaintext
indexes, imperfect secret heuristics and malicious cache ranking remain limitations.
No released native integrations or automatic preference learning.

Proposed only: Step 44 — Provider Onboarding Planning & Controlled Integration Design;
Step 45 — Cloudflare Pages Deployment Preparation. Neither task was started.
