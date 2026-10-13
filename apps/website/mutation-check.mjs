// Plant one fault per case in a scratch copy and confirm the named test rejects it.
import { mkdtemp, cp, readFile, writeFile, rm, mkdir } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
const cases = [
 ['broken fragment link', 'internal links and fragments resolve, IDs are unique per page', 'index.html', s => s.replace('href="#compare"', 'href="#nowhere"')],
 ['third-party tracker', 'local assets exist and nothing loads from another origin', 'index.html', s => s.replace('</head>', '<script src="https://analytics.example/t.js"></script></head>')],
 ['link to an unknown site', 'local assets exist and nothing loads from another origin', 'legal.html', s => s.replace('https://github.com/danieljcuesta007/skeptic/issues', 'https://example.com/issues')],
 ['inline style blocked by CSP', 'markup works under the strict content security policy', 'index.html', s => s.replace('<h1 id="hero-title">', '<h1 id="hero-title" style="color:#fff">')],
 ['CSP loosened', 'markup works under the strict content security policy', '_headers', s => s.replace("connect-src 'none'", "connect-src *")],
 ['second h1', 'each page has one h1, a skip link and labelled navigation', 'legal.html', s => s.replace('</main>', '<h1>Again</h1></main>')],
 ['tab without panel', 'install tabs are wired both ways', 'index.html', s => s.replace('aria-labelledby="t-curl"', 'aria-labelledby="t-none"')],
 ['affiliation note dropped', 'claims stay honest', 'legal.html', s => s.replace('is not affiliated with', 'works with')],
 ['comparison undated', 'claims stay honest', 'index.html', s => s.replace('as of October 2026', 'today')],
 ['brand colour creeps in', 'palette is monochrome', 'style.css', s => s.replace('--grey:#8c8c8c', '--grey:#3f8a4f')],
 ['unpack before checksum', 'installer verifies the download before unpacking and never escalates', 'install.sh', s => s.replace('mkdir -p "$PREFIX/$VERSION"\ntar -xzf', 'tar -xzf').replace('curl -fsSL "$URL" -o "$tmp/skeptic.tar.gz" || die "download failed: $URL"', 'curl -fsSL "$URL" -o "$tmp/skeptic.tar.gz" || die "download failed: $URL"\nmkdir -p "$PREFIX/$VERSION"\ntar -xzf "$tmp/skeptic.tar.gz" -C "$PREFIX/$VERSION" --strip-components 1')],
 ['formula out of step', 'install script and Homebrew formula point at the same release', '../../Formula/skeptic.rb', s => s.replace('v0.1.0/skeptic-0.1.0', 'v0.0.9/skeptic-0.0.9')],
 ['failure shown while a copy is in flight', 'site.js: tabs switch by click and arrow keys; copy writes the command', 'site.js', s => s.replace('if (successes > before || pending > 1) return;', 'if (successes > before) return;')],
 ['stale failure shown after a success', 'site.js: tabs switch by click and arrow keys; copy writes the command', 'site.js', s => s.replace('if (successes > before || pending > 1) return;', 'if (pending > 1) return;')],
 ['repeat result not re-announced', 'site.js: tabs switch by click and arrow keys; copy writes the command', 'site.js', s => s.replace("status.textContent === message ? message + '\\u00a0' : message", 'message')],
 ['claims a selection that did not happen', 'copy degrades: no selection API gives an honest message; no status line keeps the buttons', 'site.js', s => s.replace("selected ? 'Copy failed. The command is selected so you can copy it yourself.' : 'Copy failed. Copy the command above by hand.'", "'Copy failed. The command is selected so you can copy it yourself.'")],
 ['arrow keys ignored', 'site.js: tabs switch by click and arrow keys; copy writes the command', 'site.js', s => s.replace("e.key === 'ArrowRight' ? 1", "e.key === 'Nope' ? 1")],
];
for (const [name, expected, file, mutate] of cases) {
  const scratch = await mkdtemp(join(tmpdir(), 'skeptic-site-'));
  try {
    const site = join(scratch, 'apps/website');
    await mkdir(site, { recursive: true });
    await cp(new URL('.', import.meta.url), site, { recursive: true, filter: src => !src.split('/').includes('dist') && !src.split('/').includes('node_modules') });
    await cp(new URL('../../Formula', import.meta.url), join(scratch, 'Formula'), { recursive: true });
    const target = join(site, file), before = await readFile(target, 'utf8'), after = mutate(before);
    if (after === before) throw Error(`Fault not planted: ${name}`);
    await writeFile(target, after);
    if (spawnSync(process.execPath, ['build.mjs'], { cwd: site }).status !== 0) throw Error(`Scratch build failed: ${name}`);
    const result = spawnSync(process.execPath, ['--test', '--test-reporter=tap', 'test.mjs'], { cwd: site, encoding: 'utf8' });
    if (result.status === 0 || !result.stdout.split('\n').some(l => l.startsWith('not ok ') && l.endsWith(expected))) throw Error(`Not caught: ${name}`);
    console.log(`Caught: ${name}`);
  } finally { await rm(scratch, { recursive: true, force: true }); }
}
console.log(`${cases.length}/${cases.length} site mutations caught; source files unchanged.`);
