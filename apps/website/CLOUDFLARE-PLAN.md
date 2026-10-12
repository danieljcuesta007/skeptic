# Cloudflare Pages — deployed 12 Oct 2026

Live at https://skeptic.pages.dev on Daniel's personal Cloudflare account
(project `skeptic`). Deployed by direct upload of the built `dist` (8 files):
`npx wrangler pages deploy dist --project-name skeptic --branch main`
with `CLOUDFLARE_ACCOUNT_ID` set to the personal account. No Git connection
(the private repository is never linked), no custom domain, no functions or
secrets. Redeploy the same way after `npm run build`; roll back by redeploying
an earlier build or from the Pages dashboard. Take it down with
`npx wrangler pages project delete skeptic`.

The plan below is kept for the custom-domain and separate-repository steps.

# Original readiness plan

## Build and environment

Build command: `npm run build` (Node 18+). Output directory: `dist`.
Eight allowlisted static files only (homepage plus `guide.html`); no server functions, secrets, API keys or runtime
environment variables. Do not upload this development directory or private engine
archives. No package dependencies need installation.

## Repository separation

After separate approval, create a clean website-only repository from an explicit
source allowlist: HTML/CSS/JS modules, favicon, _headers, build script, package.json,
public-safe README/LICENSE/tests. Review docs for local paths before publication.
Never copy .git, the private knowledge repository, engine indexes, archives, logs, receipts with real user data
or provider configuration. Do not fork/export the private brain repository or its
history. Keep engine development and synthetic tests separate from website output.
No repository creation, commits, pushes or account connection occurred in Step 39.

## Preview approach

After authorization and security/visual acceptance, connect only the clean public
website repository to a dedicated Pages project. Use a preview branch or pull request,
keep production deployment disabled until launch approval, and inspect the generated
preview URL. Pages preview deployments are noindex by default; noindex is not access
control. Use access protection if a preview should be private. Git connection may
create automatic deployments on future pushes; disclose and configure that explicitly.

## Domain prerequisites

Choose a name after trademark/domain review, verify control, then add it through the
Pages custom-domain workflow before DNS changes. An apex domain requires the zone in
the same Cloudflare account; a subdomain can use the documented CNAME approach.
Verify certificate issuance and redirects before launch. No domain was purchased,
checked for availability or connected; no legal clearance is implied.

## Security headers

_headers is copied into dist and sets self-only scripts/styles/images, connect-src
none, form-action none, no framing, nosniff, no-referrer and disabled camera/mic/location.
It also requests revalidation of unversioned assets. Python preview does not apply
these rules. Verify actual preview response headers and browser behavior. If a real
signup backend is added later, review its disclosure/consent and narrowly revise CSP;
never enable broad network access just for convenience. Consider HSTS only after domain
ownership and HTTPS behavior are verified. No Cloudflare account settings were changed.

## Public launch checklist

- Real desktop/mobile/keyboard/screen-reader acceptance with screenshots.
- Final content truthfulness and private-data/build-allowlist inspection.
- Security-header and no-tracking/no-submission verification on preview.
- Approved name/domain/licensing and ownership disclosures.
- Tested build from clean source and a documented rollback release.
- Explicit approval to publish; only then production deployment and domain changes.
- Keep signup marked demo until a reviewed backend and privacy process exist.

## Primary references consulted for this plan

- [Static HTML](https://developers.cloudflare.com/pages/framework-guides/deploy-anything/)
- [Headers](https://developers.cloudflare.com/pages/configuration/headers/)
- [Preview deployments](https://developers.cloudflare.com/pages/configuration/preview-deployments/)
- [Custom domains](https://developers.cloudflare.com/pages/configuration/custom-domains/)

## Step 43A — concrete deployment proposal (NOT LAUNCHED)

Website preview only. Local engine, private source/history, brain notes and provider
configuration must never be uploaded. Suggested project `skeptic-os` is unconfirmed;
no project, Cloudflare account or URL has been created/verified.

| Setting | Proposed value |
| --- | --- |
| Approach | Direct Upload of the reviewed eight-asset build, preferably dashboard upload |
| Project | `skeptic-os`, subject to availability and explicit approval |
| Local build root | `apps/website` |
| Local build command | `npm run build` |
| Local output | `apps/website/dist` (or `dist` relative to build root) |
| Framework/functions | None; static HTML/CSS/JS only |
| Environment variables | None for build/runtime |
| Authentication | Authorized Cloudflare dashboard session; account owner confirms account identity and target |
| Automation alternative | Approved Wrangler installation/authentication, then account-scoped Pages Edit credentials; never place tokens in source |
| Current access | No callable Cloudflare connector; `wrangler` absent; browser list empty. Account/permissions unknown |
| GitHub access for Direct Upload | None needed; no commit/push required for upload |

Direct Upload accepts prebuilt folders or ZIPs in the dashboard. Choose the project
mode deliberately: a Direct Upload project cannot later switch to native Git
integration without creating another project. See [Direct Upload docs](https://developers.cloudflare.com/pages/get-started/direct-upload/).

Git integration is optional, not required here. It would grant the Cloudflare GitHub
app selected-repository access and enable build triggers. This session authorizes
neither app installation nor pushes. The existing plan favors an independently
reviewed website-only repo; do not connect the private mixed engine repository
without a separate access decision. If an approved website-only repository is used,
set build root to that repo's website root, command `npm run build`, output `dist`.
A selected monorepo would use root `apps/website`, command `npm run build`, output
`dist`; only the built website may be served. Repository access is broader than the
output allowlist. See [GitHub integration](https://developers.cloudflare.com/pages/configuration/git-integration/github-integration/).

### Preview and production sequence — do not execute until gates pass

1. Complete local manual browser acceptance at all five widths and obtain its
   confirmation. Confirm deployment approach, exact Cloudflare account, project and
   explicit public-upload approval. A Pages preview URL is also an external upload;
   browser unavailability blocks it here.
2. Upload only the reviewed eight assets. For a controlled nonproduction deployment,
   choose preview environment/branch in an existing approved Direct Upload project.
   Wrangler can explicitly select a preview branch distinct from the production
   branch. Do not let implicit branch detection choose production.
3. Inspect deployed response headers/CSP, both pages, scripts, all internal links,
   downloads, onboarding and Network/Console. Python preview cannot validate hosted
   headers. Any newly injected analytics must be disabled and investigated.
4. Publish the accepted exact artifact to the approved production target only with
   explicit production approval. Record the actual URL/deployment ID and hashes in
   the canonical checkpoint. Do not promise `skeptic-os.pages.dev` until confirmed.

### Rollback

Keep the accepted ZIP/manifest and deployment IDs outside the served output.
Subsequent production releases can roll back to a previous successful production
 deployment through the Pages dashboard; preview deployments are not rollback
 targets. For the first launch there is no previous production deployment: keep
 production blocked until acceptance, and agree an unpublish/redeploy response
 separately if needed. No rollback or project deletion is preauthorized.
See [Rollbacks](https://developers.cloudflare.com/pages/configuration/rollbacks/).

### Current gates

Build/tests, static privacy review, truthful pre-alpha labels and source-level
navigation checks passed. Browser/visual/keyboard acceptance, real demo interaction,
correct account identity/permissions, explicit project/public deployment approval and
hosted header behavior are NOT VERIFIED. **Stop at readiness; not launched.**

## Updated local artifact — 2026-10-09T15:22:48+00:00

User-observed visual corrections implemented under Step 43A; full validation 72 tests /
64 mutations passed. Rebuilt eight-asset ZIP/manifest match source/dist (55,955 bytes);
ZIP SHA-256 `69ac4a1f01ff45ef0fa9733cc432b0c2578dd846cf437704832737cf78b214af`. Prior hashes superseded.
Browser feedback does not complete acceptance; revised rendered checks and all
account/target/manual-acceptance/public-upload approval gates remain pending.
No deployment. See `BROWSER-ACCEPTANCE.md`.
