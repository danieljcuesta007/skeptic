# Skeptic website

The product landing page at https://skeptic.pages.dev, with a giant interactive
halftone wordmark, product explanation, install commands, comparison, creator,
and privacy/license/trademarks page. Black, white and greys; serif product headings
and mono details retain Skeptic's existing brand. No third-party requests, cookies,
analytics, image downloads or hosted fonts.

Requires Node 22+ with npm. React and React DOM are bundled locally; TypeScript,
esbuild, PostCSS and Tailwind 4 are build dependencies. No Python is needed to
preview the website. Build output remains static, ready for Cloudflare Pages.

```sh
npm ci
npm run typecheck
npm run build
npm test                    # 24 regressions, including canvas lifecycle
node mutation-check.mjs      # 30 planted faults, all expected to fail
npm run preview              # http://127.0.0.1:4173, with production CSP
```

## Components and styles

`components/ui/halftone-wordmark-footer.tsx` is the supplied reusable React
component, adapted for Skeptic. `components/ui/demo.tsx` preserves its generic
demo. Props control wordmark, link columns, height, palette, grain, crop and
interaction; `as="section"` places the same wordmark in the landing masthead.
No state store, providers, stock imagery or additional icon package is needed.

The default component path is **`components/ui` within this website package**.
This is the shadcn convention: reusable UI stays discoverable and generated
components use the `@/components/ui` alias consistently. `components.json`
configures shadcn, TypeScript and the neutral Tailwind palette; `tsconfig.json`
resolves `@/*` from the package root. Shared class helpers live in `lib/utils.ts`.
To add a shadcn component later, run `npx shadcn@latest add button` here.
React, TypeScript and Tailwind are already installed; no project recreation is
needed. For a separate new app, `npx shadcn@latest init` sets up its own project.

Styles: `styles/globals.css` imports Tailwind theme and utilities without its
reset, preserving the established design. `style.css` remains the site's brand
stylesheet. Scoped `.hwf-` rules are in
`components/ui/halftone-wordmark-footer.css`, bundled to `dist/landing.css`.
The supplied component's inline style block moved here to preserve the existing
strict self-only CSP. Prop values use CSSOM properties, without allowing inline
style tags or loosening security headers.

`landing.tsx` supplies real Skeptic links and a monochrome palette. `render.tsx`
prerenders both wordmarks at build time; `client.tsx` hydrates their canvas effects.
The page, links and a static wordmark remain visible without JavaScript. At narrow
widths footer columns become two columns and the install panel stacks below the
headline. Links and buttons have 44px targets. Animation stops at rest, offscreen
or in hidden tabs, and respects live changes to reduced-motion preferences.

## Files

- `index.html` / `guide.html` / `legal.html`: compact landing, detailed guide and legal pages.
- `site.js`: existing install tabs, copy buttons and illustrative terminal replay.
- `build.mjs`: static prerender, React/CSS bundle and Tailwind compilation.
- `preview.mjs`: local server with the production security headers.
- `install.sh`: installer, served as plain text.
- `_headers`: unchanged Cloudflare Pages CSP and security headers.

`install.sh` and `../../Formula/skeptic.rb` carry the release checksum.
`scripts/release.sh <version>` fills both in; tests reject disagreements.

## Deploy

Cloudflare Pages project `skeptic`, Direct Upload of `dist/`:

```sh
npm run build
npx wrangler pages deploy dist --project-name skeptic
```

Deploying is deliberate and separate from local integration; the matching GitHub
release must exist so the install commands work.

The opening masthead opts into `scrollReveal`: its artwork stays pinned below the
sticky header as the following page section slides over it from below. The footer
is static with its light crop. Artwork follows scroll with a short frame-rate-independent easing and a softly
feathered page edge. Updates settle and stop rather than running continuously; reduced
motion disables pinning, and listeners/frames clean up on unmount. The dotted hood
favicon and matching halftone header remain in place.
