# Recovered engine requirements — Step 39 assessment

All tests use invented fixtures; no actual brain was scanned. Existing regression suites
are preserved. Test evidence describes prototype behavior, not production enforcement.

| Requirement | Evidence / status |
| --- | --- |
| Added/changed/deleted Markdown, rename candidates | Index change summaries; automatic enumeration; regression tests |
| Policy changes | Policy hash requires reindexing; revoked sources filtered |
| Stale passages | Selected source freshly hashed; excerpt rebuilt from actual bytes |
| Governing rules before actions | revalidate_governing() reads every rule/status independently of passage budget; query invokes it; future host must call immediately before actions |
| Protected secrets | Path exclusions before reads; secondary content quarantine; not exhaustive detection |
| Symlink escapes | No-follow descriptor traversal; symlinks skipped; direct read rejected |
| Private names/metadata | Protected sources omitted; quarantine filenames withheld, including removed-path summaries |
| Index outside Git | save_index rejects note-root and Git-ancestor destinations; files owner-only |
| Unrelated transmission | Engine has no network/provider execution; website is synthetic and disconnected |
| Neutral package | Project, rules/references/hashes, governing-check time, handoff excerpt, capabilities, unknowns, next action |
| Ordinary notes cannot govern | Roles from host-designated rule paths only; text never executed |
| Untrusted catalog | Sources-only request schema; host root/policy/rules cannot be overridden |
| Untrusted cache scope | Requests filtered against current host policy; returned passage bytes re-read; malformed/adversarial schema/DoS hardening still incomplete |
| Preferences | Deterministic explicit declarations in rule files; conflicts block next action; arbitrary prose and inference remain unverified |

The root policy remains trusted host authorization. Supplying an untrusted file as the
host policy is not supported. Python callers with direct filesystem permissions can
bypass the engine; no claim of OS enforcement. A receipt is not edit/publish permission.
