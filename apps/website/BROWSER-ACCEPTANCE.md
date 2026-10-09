# Step 43A browser acceptance — NOT PASSED / browser unavailable

Step 43 default browser selection returned “No browser is available”; troubleshooting
then confirmed the available-browser list was `[]`. No real-browser run or screenshots were
possible. Node tests prove logic and static structure, not rendered accessibility.

## Run locally

    npm run build
    npm run preview

Open http://127.0.0.1:4173. The Python server does not apply Cloudflare _headers;
header behavior must later be checked on an explicitly authorized Pages preview.

## Manual checklist and evidence to capture

1. On both `index.html` and `guide.html`, at 1440×900, 1024×768 and 768×1024,
   capture hero, final CTA and walkthrough screenshots. Confirm
   white dominance, no clipped headings, legible text and intentional alignment.
2. At 375×812 and 390×844 (also 320×568 for reflow), capture the same views; scroll the full document and
   check for horizontal overflow. Also test browser text zoom at 200% and 400%.
3. Confirm “Explore the preview” has compact dimensions and adjacent controls wrap
   without clipping. Activate every header, footer and cross-page/in-page link. Ensure targets are visible and
   active state matches navigation. Check skip-to-content with Tab/Enter.
4. For Claude Code, Codex, Local model and Starting fresh, complete all eight
   steps. Exercise all three knowledge sources and access modes. Next before a
   required choice must show an error; Back preserves choices; progress marks the
   current step; restart clears state; no filesystem/account prompt occurs.
5. Use Tab/Shift-Tab/Enter/Space and select-arrow keys without a mouse. Confirm
   focus stays visible, follows step transitions, and never becomes trapped or
   disappears. Check screen-reader labels, progress/current-step and errors.
6. Generate receipts for each policy and task. Confirm context and approval text
   change; no real provider is contacted. Download and inspect the synthetic .md.
7. Open/close every FAQ item. Simulate early signup: email is disabled, no signup
   occurs and confirmation explicitly says nothing was submitted or saved.
8. Enable OS reduced-motion preference and confirm navigation stops smooth
   scrolling. Confirm focus styling, tap targets and responsive typography.
9. Verify browser Network has only local assets, no tracking or submissions, and
   Console has no errors. Capture final screenshots and record browser/version.
10. On a separately approved Pages preview, verify CSP and other response headers
    without weakening connect-src/form-action protections to make a demo work.

## Confirmed static correction

Calculated sRGB contrast: #FF2800 on white = 3.78:1, insufficient for small normal
text; black on #FF2800 = 5.56:1; #505050 on white = 8.06:1. Small step numbers and
active nav text now use black with red structural accents. Red focus outlines and
large/decorative accents remain. This is not complete rendered contrast acceptance.

## Step 43 source evidence

Six-section homepage and separate guide; 13 website tests, five UX mutations caught.
Typography, shrinkable grids, wrapping controls, focus and reduced-motion rules
checked in source. All five viewport results and actual keyboard/screen-reader
behavior remain NOT VERIFIED. See ../../docs/ux/STEP43-REFINEMENT.md.

## Step 43A additional acceptance — launch blocker

Browser listing again returned `[]`. No rendered acceptance/screenshots performed.
Website 15 tests/eight UX mutations passed; full suite 70 tests/62 mutations.

- At 375, 390, 768, 1024 and 1440px, inspect the three-layer homepage diagram;
  labels must remain readable, capabilities distinguish implemented/documented/planned,
  arrows align, no layer/CTA clips and no horizontal scroll appears.
- Inspect both guide diagrams; confirm their captions clearly describe synthetic
  retrieval versus documented handoffs and planned provider delivery.
- At 200%/400% zoom, all controls and diagram labels remain reachable/readable.
- Tab through both pages and all eight onboarding steps on every starting path;
  verify focus, errors, Back/restart, receipt/download/FAQ and inert signup.
- Check reduced motion, screen-reader caption/heading order, contrast and Console/Network.
- Capture browser/version, viewport/screenshots and pass/fail per item. Explicitly
  confirm manual acceptance before public upload, then confirm the Cloudflare account,
  exact project and public deployment approval. A public preview is also an upload.

No automatic Cloudflare deployment while acceptance is unavailable or failing.
See ../../docs/ux/STEP43A-LAUNCH-READINESS.md.
