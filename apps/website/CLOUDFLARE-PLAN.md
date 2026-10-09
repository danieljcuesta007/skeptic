# Cloudflare Pages readiness — prepared, not deployed

## Build and environment

Build command: `npm run build` (Node 18+). Output directory: `dist`.
Seven allowlisted static files only; no server functions, secrets, API keys or runtime
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
