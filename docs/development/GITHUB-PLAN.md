# GitHub preparation — not executed

1. Naming: `skeptic` or `skeptic-os` are candidates, subject to name/domain review.
   No availability or trademark clearance claimed.
2. Visibility: begin with a separately authorized private source repository if desired;
   public release needs additional review. Private visibility is not a secrets vault.
3. Licensing: resolve LICENSE-DECISION.md while retaining existing MIT notices.
4. Secret scanning: inspect every tracked file and complete initial history, test
   fixtures included; run an approved independent scanner before any first push.
5. Separation: only reviewed product source/history. Never import private knowledge
   Git history, archives, notes, real indexes or provider configuration. A public
   website-only repository remains an option before website deployment.
6. Clean history: this project starts with one new reviewed local root commit.
   Do not rewrite existing histories. No remote or GitHub repository exists yet.
7. CI: after approval, run website build/tests and Python V2/baseline regressions and
   mutation checks on POSIX, with no provider credentials and no real notes.
   CI configuration itself is planned, not active.
8. Tags: after acceptance, propose signed/versioned pre-alpha tags and changelog;
   no release tag created now.
9. Contributions: follow CONTRIBUTING.md; small changes, tests and truthful evidence.
10. Security: SECURITY.md specifies sanitized reporting; choose a real private reporting
    channel before making a public repository.
11. Documentation: maintain root README, capability limitations, install/uninstall
    plans, provider disclosures and licensing provenance.
12. PR gate: Claude must review every PR before merge; address findings or explain
    dispositions and post a comment headed "Review by Claude". Codex cannot substitute.
    Publication, pushes and risky merges still require applicable approval.

Step 40 authorizes only the initial local commit. No future push, remote configuration,
GitHub creation, deployment or live integration is authorized by this plan.
