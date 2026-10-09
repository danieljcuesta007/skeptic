# Security review checkpoint

Synthetic protections tested: three modes, exclusion-before-read, constrained source
requests, symlink/hardlink handling, source hashes, bounded fresh passages, governing
revalidation, preference conflicts, private index files, Git-destination refusal and
no external actions. These are prototype tests, not independent security certification.

Next: independently review malformed/hostile caches and policies, path/root races,
Unicode/case aliases, size/resource limits, filename leakage, index retention/encryption,
provider data handling and install/uninstall ownership. No real vault testing until
separately authorized. Preserve the existing mandatory Claude PR review gate.
