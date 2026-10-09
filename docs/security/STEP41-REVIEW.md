# Step 41 — independent source review and acceptance checkpoint

**Decision: pre-alpha; release blocked.** Review of existing implementations, not a
rebuild, security certification, or Claude's required PR review. No application code
was changed. Only synthetic security fixtures were used; no real notes were scanned.

## Repository verification

Starting branch `main`, clean status, sole initial commit
`e92253d8c0bd59b11106bd764d1227ec6805c11c`, no remotes. Inspected 59 tracked
text files: no nested Git repositories or unexpected generated files. Only ignored
`apps/website/dist/` appears after building. Pattern inspection found no private-home
paths, brain project paths, credential tokens or private-key blocks in tracked files.
This is a limited content review, not proof of absence of every possible secret.
The repository has independent initial history, not the brain's history.

## Confirmed findings

### S41-01 — HIGH: protected-directory case alias bypass

On this host's case-insensitive fixture filesystem, `protected/hidden.md` and
`PROTECTED/hidden.md` resolve to the same file. `excluded()` uses case-sensitive
string matching. A modified cache document with the uppercase path passes the
FULL_BRAIN scope check and is read and returned by `query()` despite the host
exclusion `protected`. The normal index excludes the lowercase file correctly.

Preconditions: case-insensitive filesystem, attacker-controlled cache and matching
source digest for passage disclosure. The reproduction supplies a known synthetic
digest; this does not show recovery of an unknown real credential. An unauthorized
read occurs before digest rejection even when the supplied digest is wrong.
Evidence: `case_insensitive_fixture True`, `protected_alias_returned True`.
Affected: `Engine.excluded`, `Engine.scoped`, `Engine.query`, `Engine.inspect`.
Recommendation: enforce exclusions against filesystem-equivalent names/identities,
validate cache paths independently and test aliases on supported filesystems.

### S41-02 — HIGH: stale governing handoff bypasses credential quarantine

Index a safe project status, then replace its Handoff with a synthetic token matching
the existing credential detector. `query()` freshly reads it and emits the token in
`current_handoff.excerpt` (also under `governing.handoff`), despite recording the status
as stale. Ordinary stale passages are withheld, but this separate output is not.
Evidence: `handoff_leak True`, stale list `['atlas/STATUS.md']`.
Affected: `Engine.revalidate_governing` and `Engine.query`.
No network transmission was demonstrated; this is disclosure into the neutral receipt,
which could subsequently be passed to a provider. Writing a secret into an allowed
file is a precondition. Recommendation: apply a consistent output quarantine and
withhold stale handoff contents until successful reindex/validation.

### S41-03 — MEDIUM: malformed cache causes unhandled retrieval failure

Set a cached rule chunk's `line` to the string `invalid`. `query()` subtracts one
from it and raises uncaught `TypeError`. Cache schema and field types are not validated.
Evidence: `malformed_cache_exception TypeError`. This proves availability failure,
not code execution or additional access. Recommendation: bounded schema validation,
safe invalid-cache rejection/rebuild, and regression cases for malformed fields.

No CRITICAL issue was confirmed. No application fixes were authorized or applied.

## Reproduction (synthetic only)

Run from the repository root. Uses a fresh temporary directory, not real brain data.
Do not run against a personal vault. Token text is intentionally not printed.

```python
import copy, hashlib, json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path('packages/discovery').resolve()))
from engine import Engine
base = Path(tempfile.mkdtemp(prefix='skeptic-review-')).resolve()
root = base / 'notes'
(root / 'atlas').mkdir(parents=True)
(root / 'protected').mkdir()
(root / 'PRINCIPLES.md').write_text('Canonical fixture rule.')
status = root / 'atlas/STATUS.md'
status.write_text('## Handoff\nSynthetic safe next action.')
(root / 'protected/hidden.md').write_text('SYNTHETIC_PROTECTED_CANARY')
policy = dict(root=str(root), mode='FULL_BRAIN', rules=['PRINCIPLES.md'],
              excluded=['protected'], projects=[dict(id='atlas',
              status='atlas/STATUS.md', paths=['atlas'])])
with Engine(policy) as engine:
    index = engine.index('atlas')
    token = 'ghp_' + 'A' * 30
    status.write_text('## Handoff\n' + token)
    receipt = engine.query(index, 'fixture', 'atlas')
    print('handoff_leak', token in json.dumps(receipt), 'stale', receipt['stale'])
    status.write_text('## Handoff\nSynthetic safe next action.')
    index = engine.index('atlas')
    bad = copy.deepcopy(index)
    bad['documents']['PRINCIPLES.md']['chunks'][0]['line'] = 'invalid'
    try:
        engine.query(bad, 'fixture', 'atlas')
    except Exception as error:
        print('malformed_cache_exception', type(error).__name__)
    alias = root / 'PROTECTED/hidden.md'
    print('case_insensitive_fixture', alias.exists())
    if alias.exists():
        bad = copy.deepcopy(index)
        data = (root / 'protected/hidden.md').read_bytes()
        bad['documents']['PROTECTED/hidden.md'] = dict(
            sha256=hashlib.sha256(data).hexdigest(),
            chunks=[dict(line=1, text='canary')])
        receipt = engine.query(bad, 'canary', 'atlas', limit=20)
        print('protected_alias_returned', any(
            p['path'] == 'PROTECTED/hidden.md' for p in receipt['passages']))
```

## Other security boundaries and limitations

- Descriptor-relative no-follow directory/file opens, regular-file and single-link
  checks, and before/after signatures protect tested symlink/hardlink substitutions.
  Full adversarial concurrent filesystem-race acceptance has not been performed.
  Index persistence checks paths then uses pathname-based creation/replacement;
  directory changes between these operations require further review. No race exploit
  is claimed here.
- Host policy explicitly designates instruction sources. Catalogs only request scoped
  paths; ordinary notes remain data. Scope tests pass, but the confirmed case-alias
  finding limits the cache boundary claim. Cache ranking/metadata remain untrusted
  inputs without complete schema/resource limits. Retrieved text is not executed by
  this engine; a downstream model's response to prompt injection is unverified.
- Indexes contain plaintext note bodies, paths and root metadata. File mode 0600 and
  refusal of Git destinations are tested; same-user processes, backups, retention,
  encryption and a private parent directory are not solved by file mode alone.
- Secret detection is a narrow regex applied after authorized local reads, not a
  comprehensive secrets classifier. Naming exclusions and output quarantine need
  strengthening. No receipt should be treated as sanitized automatically.
- Imports/source and regression tests show no engine provider/network/execution
  integration. This is not an OS sandbox: another host tool could bypass mediation.
  Provider-specific handling, outbound adapters and metadata minimization remain
  future acceptance gates. No unrelated notes were transmitted in this review.

## Website and browser acceptance

**Real-browser acceptance NOT VERIFIED.** Available browser discovery returned no
browser sessions. No screenshots or rendered accessibility claims are made.
Source/static tests confirm internal targets/assets, four model paths, all eight
steps, back/restart state, 36 model/source/policy combinations, progress/labels,
focus/reduced-motion styling and inert signup disclosures. These do not prove actual
keyboard behavior, screen-reader usability, contrast in every state or layout quality.
White/black/red identity is preserved; no redesign was performed.

Manual acceptance: `cd apps/website && npm run build && npm run preview`, open
`http://127.0.0.1:4173`. Follow `apps/website/BROWSER-ACCEPTANCE.md`: desktop 1440×900,
1024×768; mobile 390×844 and 320×568; 200/400% zoom; every internal link and skip link;
every model path through all eight steps and back/restart; required-choice errors;
keyboard Tab/Shift-Tab/Enter/select controls and visible focus; receipt/download;
FAQ and inert signup; no horizontal overflow; reduced-motion OS setting; computed
contrast and console/network inspection. Record screenshots and assistive-tech results.
Local Python preview does not apply Cloudflare `_headers`; hosted headers remain
unverified and deployment requires separate authorization.

## Validation results

Reran `python3 -B tests/validate.py` successfully:

| Check | Result |
| --- | --- |
| Website production build | Pass; 7 static output files |
| Website Node tests | 10 passed |
| Discovery V2 tests | 24 passed |
| V2 targeted mutation checks | 24/24 caught |
| Preserved baseline tests | 18 passed |
| Baseline mutation checks | 18/18 caught |
| Migration/demo regression | 1 passed |
| Total | 53 tests passed; 42 mutations caught; zero suite failures |

The three independent adversarial probes confirmed defects outside these suites.
Passing regressions and mutations do not establish security completeness.

## Product readiness and next action

Website/storytelling and synthetic onboarding are implemented prototypes; rendered
quality is pending. Provider adapters, capability/disclosure detection, native Claude/
Codex/local onboarding, installers/uninstall ownership, signing and real permission
flows remain planned. Automatic continuity and preference learning are documented
workflows, not active automation. FULL_BRAIN is the owner's design default, not live
activation. Signup has no backend. No public launch readiness or market evidence is
claimed. Privacy disclosures must explain plaintext derived data and provider handling.

Recommended next milestone, requiring new authorization: fix S41-01/02/03 with
synthetic regressions and hostile-cache coverage, then real-browser/accessibility
acceptance. Maintain required Claude PR review and posted "Review by Claude" before
any PR merge; this Codex review does not substitute. No remote, commit, push, deployment,
provider-config change or live integration occurred in Step 41.
