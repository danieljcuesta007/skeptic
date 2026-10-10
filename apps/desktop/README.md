# Skeptic — local macOS development app (Step 43G vertical slice)

Your work. Your memory. Any AI. Switch AI agents without starting over.

## Install and launch

Requires macOS 12+, macOS Python 3 and Xcode Command Line Tools for building. No external dependencies are downloaded or installed.

```sh
python3 -B ~/Developer/skeptic/apps/desktop/install.py
open "$HOME/Applications/Skeptic.app"
```

The installer builds an actual AppKit/WKWebView bundle and copies it to your Applications folder. Use Spotlight, Finder or add it to the Dock afterward. Existing unknown apps are preserved; reinstalling requires quitting and explicitly removing the previous development bundle. This is a local development application, not a Developer ID signed/notarized release. Do not disable Gatekeeper or remove quarantine to run it.

## Behavior and security

The app owns one Python child. A random available loopback port avoids conflicts with port 4317; no LAN listener. A private lock refuses duplicate backend processes. Closing the last window or quitting closes the child’s stdin lifetime lease; backend shutdown closes its server and session approvals. Native navigation allows only the exact selected loopback origin. Backend Host, Origin, CSRF, exclusions, path and symlink protections remain intact. App startup reads no AI history and launches no providers.

Appearance (light/dark/system) and completed welcome state persist owner-only under `~/.skeptic-desktop`; Model Usage and registrations also persist there. Source read approvals remain session-local and require explicit renewal after reopening. Desktop registrations are separate from the development-server registry. Your canonical Markdown remains in its existing location. CLI switching is independent of the app.

Current UI: existing projects, sources, permissions, handoffs, activity and Model Usage; persistent monochrome appearance, introductory welcome and command/help reference. The welcome is an introductory slice, **not** the complete four-step onboarding. Agent detection wizard, managed Markdown workspace, Finder reveal and knowledge graph remain follow-up. The supplied graph attachment was unavailable; no React migration was attempted. Existing Markdown folders work through the existing explicit root connector.

## Mac acceptance

Launch from Applications. Select Dark, Light and System; inspect contrast and focus. Dismiss welcome, connect one approved test Markdown folder, inspect project and Model Usage. Close the window; confirm no Skeptic backend remains with Activity Monitor. Reopen: welcome stays dismissed, theme and registrations remain; source reads require renewed approval. Keep any Claude session open throughout. Follow `apps/local/BROWSER-ACCEPTANCE.md` for usage acceptance. Test a second app launch and a missing Python runtime: errors must be safe and no private source read should occur.

Native compilation passed here. Live loopback startup was denied by the execution environment; native window/browser acceptance remains unverified. No real transcripts or providers were used for testing.
