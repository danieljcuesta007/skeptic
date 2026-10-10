"""Create disposable synthetic browser-acceptance sources; never inspect a real vault."""
from pathlib import Path
import tempfile


def create(base):
    vault = base / 'vault'
    project = vault / '03 Projects' / 'Atlas'
    project.mkdir(parents=True)
    repo = base / 'repositories' / 'atlas'
    (repo / '.git' / 'refs' / 'heads').mkdir(parents=True)
    (repo / '.git' / 'HEAD').write_text('ref: refs/heads/main\n')
    (repo / '.git' / 'refs' / 'heads' / 'main').write_text('a' * 40 + '\n')
    (repo / 'AGENTS.md').write_text('# Instructions\nPreserve unrelated work. Ask before deploying.\n')
    (vault / 'PRINCIPLES.md').write_text('# Principles\nKeep the original notes.\n')
    (vault / 'AGENTS.md').write_text('# Instructions\nRead STATUS before continuing.\n')
    (vault / 'ordinary.md').write_text('# Ordinary knowledge\nThis is not a project.\n')
    (project / 'STATUS.md').write_text('---\npaths:\n  - ' + str(repo) + '\n---\n'
        '# Atlas\n## Objective\nBuild a synthetic project.\n## Current State\nStep 3 — acceptance incomplete.\n'
        '## Next Actions\n- [ ] Check the unified dashboard.\n## Handoff\nResume synthetic Step 3.\n')
    (project / 'notes.md').write_text('# Project notes\nSynthetic supporting context.\n')
    (project / 'handoff.md').write_text('# Older handoff\nHistorical fixture, review STATUS first.\n')
    missing = vault / '03 Projects' / 'Missing checkpoint'
    missing.mkdir(); (missing / 'dashboard.md').write_text('# Dashboard\nNo checkpoint exists.\n')
    private = vault / 'private'; private.mkdir(); (private / 'STATUS.md').write_text('Must remain excluded.\n')
    return vault, repo.parent


if __name__ == '__main__':
    base = Path(tempfile.mkdtemp(prefix='skeptic-workspace-')).resolve()
    vault, repositories = create(base)
    print('Synthetic vault:', vault)
    print('Synthetic repository root:', repositories)
    print('Connect each root separately in the local app. These are synthetic, not your real notes.')
