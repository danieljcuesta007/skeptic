# Step 39 browser acceptance — NOT PASSED / browser unavailable

Browser discovery returned an empty list. No real-browser run or screenshots were
possible. Node tests prove logic and static structure, not rendered accessibility.

## Run locally

    npm run build
    npm run preview

Open http://127.0.0.1:4173. The Python server does not apply Cloudflare _headers;
header behavior must later be checked on an explicitly authorized Pages preview.

## Manual checklist and evidence to capture

1. At 1440×900 and 1024×768, capture hero and walkthrough screenshots. Confirm
   white dominance, no clipped headings, legible text and intentional alignment.
2. At 390×844 and 320×568, capture the same views; scroll the full document and
   check for horizontal overflow. Also test browser text zoom at 200% and 400%.
3. Activate every header, footer and in-page link. Ensure targets are visible and
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
