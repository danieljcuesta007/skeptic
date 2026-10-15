import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, readdir, access } from 'node:fs/promises';
import { runInNewContext } from 'node:vm';

const pages = { 'index.html': await readFile('dist/index.html', 'utf8'), 'guide.html': await readFile('guide.html', 'utf8'), 'legal.html': await readFile('legal.html', 'utf8') };
const home = pages['index.html'], legal = pages['legal.html'];
const guide = pages['guide.html'];
const html = home + legal + guide;
const css = await readFile('style.css', 'utf8') + await readFile('dist/landing.css', 'utf8');
const js = await readFile('site.js', 'utf8');
const headers = await readFile('_headers', 'utf8');
const installer = await readFile('install.sh', 'utf8');
const formula = await readFile('../../Formula/skeptic.rb', 'utf8');
const SHIPPED = ['index.html', 'guide.html', 'legal.html', 'style.css', 'site.js', 'favicon.svg', 'install.sh', '_headers', 'landing.js', 'landing.css', 'utilities.css'];
const OUTBOUND = /^https:\/\/(github\.com\/danieljcuesta007(\/|$)|skeptic\.pages\.dev\/|danielcuesta007\.com$|addisuna\.com$|www\.linkedin\.com\/in\/danielcuesta007\/$)/;

test('internal links and fragments resolve, IDs are unique per page', () => {
  for (const [name, page] of Object.entries(pages)) {
    const ids = [...page.matchAll(/\sid="([^"]+)"/g)].map(m => m[1]);
    assert.equal(new Set(ids).size, ids.length, name);
    for (const [, href] of page.matchAll(/<a\b[^>]*href="([^"]+)"/g)) {
      if (/^https?:/.test(href)) continue;
      const [file, fragment] = href.split('#');
      if (file && !pages[file]) { assert.ok(SHIPPED.includes(file), href); continue; }
      if (fragment) assert.ok((pages[file || name]).includes(`id="${fragment}"`), `${name}: ${href}`);
    }
  }
  for (const id of ['how', 'install', 'creator']) assert.ok(home.includes(`id="${id}"`), id);
  for (const id of ['privacy', 'license', 'trademarks', 'credits', 'contact']) assert.ok(legal.includes(`id="${id}"`), id);
});

test('local assets exist and nothing loads from another origin', async () => {
  for (const [, ref] of html.matchAll(/(?:src|href)="([^"#:]+\.(?:css|js|svg|sh))(?:\?[^"]*)?"/g)) await access(`dist/${ref}`);
  assert.doesNotMatch(html, /<(?:script|link|img|iframe)\b[^>]*(?:src|href)="https?:/);
  for (const [, href] of html.matchAll(/<a\b[^>]*href="(https?:[^"]+)"/g)) assert.match(href, OUTBOUND, href);
  assert.doesNotMatch(js, /fetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|localStorage|sessionStorage|https?:\/\//);
});

test('markup works under the strict content security policy', () => {
  for (const rule of ["default-src 'none'", "script-src 'self'", "style-src 'self'", "connect-src 'none'", "form-action 'none'", "frame-ancestors 'none'"]) assert.ok(headers.includes(rule), rule);
  assert.doesNotMatch(html, /\sstyle="/, 'inline style attributes are blocked by style-src');
  assert.doesNotMatch(html, /\son[a-z]+="/, 'inline handlers are blocked by script-src');
  assert.doesNotMatch(html, /<script>(?!<\/script>)|<script\b(?![^>]*\bsrc=)[^>]*>/, 'inline scripts are blocked');
  assert.doesNotMatch(html, /<form\b/);
  assert.match(headers, /\/install\.sh\n\s+Content-Type: text\/plain/);
});

test('each page has one h1, a skip link and labelled navigation', () => {
  for (const page of Object.values(pages)) {
    assert.equal((page.match(/<h1\b/g) || []).length, 1);
    assert.match(page, /class="skip" href="#main"/);
    assert.match(page, /id="main" tabindex="-1"/);
    assert.match(page, /aria-label="Main navigation"/);
  }
  assert.match(css, /prefers-reduced-motion:reduce/);
  assert.match(css, /min-height:44px/);
  assert.doesNotMatch(css, /body\s*\{[^}]*overflow(?:-x)?\s*:\s*(?:hidden|clip)/);
});

test('install tabs are wired both ways', () => {
  const tabs = [...home.matchAll(/role="tab" id="([^"]+)" aria-controls="([^"]+)" aria-selected="(true|false)"/g)];
  assert.equal(tabs.length, 3);
  assert.equal(tabs.filter(t => t[3] === 'true').length, 1);
  for (const [, id, panel] of tabs) assert.match(home, new RegExp(`role="tabpanel" id="${panel}" aria-labelledby="${id}"`));
});

test('claims stay honest', () => {
  assert.match(guide, /as of October 2026/);
  assert.match(home, /illustrative replay/i);
  assert.match(home, /Daniel Cuesta/);
  assert.doesNotMatch(home, /with&nbsp;Claude|student founder/);
  for (const page of Object.values(pages)) assert.match(page, /not affiliated with/);
  assert.match(legal, /no telemetry/);
  assert.doesNotMatch(html, /notari[sz]ed|Developer ID|coming soon|award-winning|#1 /i);
});

// Brand v1 is ink, paper and greys. Allow a channel spread of 2 for the brand ink #0B0B0C.
test('palette is monochrome', async () => {
  const assets = css + html + await readFile('favicon.svg', 'utf8');
  for (const [, hex] of assets.matchAll(/#([0-9a-f]{3}|[0-9a-f]{6})\b/gi)) {
    const ch = hex.length === 3 ? [...hex].map(c => parseInt(c + c, 16)) : [0, 2, 4].map(i => parseInt(hex.slice(i, i + 2), 16));
    assert.ok(Math.max(...ch) - Math.min(...ch) <= 2, `non-neutral colour #${hex}`);
  }
  for (const [, r, g, b] of css.matchAll(/rgba?\((\d+),\s*(\d+),\s*(\d+)/g)) assert.ok(r === g && g === b, `non-neutral rgba(${r},${g},${b})`);
  assert.doesNotMatch(assets, /hsla?\(|\b(?:red|blue|green|purple|orange)\b\s*[;"]/i);
});

test('installer verifies the download before unpacking and never escalates', () => {
  assert.match(installer, /^set -eu$/m);
  const check = installer.indexOf('checksum mismatch'), unpack = installer.indexOf('tar -xzf');
  assert.ok(check > 0 && unpack > check, 'checksum must be checked before tar runs');
  assert.match(installer, /"\$SHA256" != "UNRELEASED" \] \|\| die/);
  const code = installer.split('\n').filter(l => !l.trimStart().startsWith('#')).join('\n');
  assert.doesNotMatch(code, /\bsudo\b|chmod 777|\/usr\/local/);
});

test('install script and Homebrew formula point at the same release', () => {
  const version = installer.match(/^VERSION="([^"]+)"/m)[1];
  const sha = installer.match(/^SHA256="([^"]+)"/m)[1];
  assert.ok(formula.includes(`/releases/download/v${version}/skeptic-${version}.tar.gz`), 'formula url');
  assert.ok(formula.includes(`sha256 "${sha}"`), 'formula sha256');
  assert.match(formula, /--skills-only/);
});

test('site.js: tabs switch by click and arrow keys; copy writes the command', async () => {
  const el = (attrs = {}) => ({ attrs, hidden: false, tabIndex: 0, textContent: 'Copy', dataset: {}, listeners: {}, classList: { add() {}, remove() {} },
    getAttribute(k) { return this.attrs[k]; }, setAttribute(k, v) { this.attrs[k] = v; }, addEventListener(t, f) { this.listeners[t] = f; }, focus() { focused = this; }, remove() { this.removed = true; } });
  let focused = null;
  const panels = { 'p-a': el(), 'p-b': el() };
  const tabs = [el({ 'aria-controls': 'p-a', 'aria-selected': 'true' }), el({ 'aria-controls': 'p-b', 'aria-selected': 'false' })];
  const root = { querySelectorAll: () => tabs, querySelector: sel => panels[sel.slice(1)] };
  const copy = el(); copy.dataset.copy = 'brew install skeptic';
  const written = [];
  const document = { querySelector: sel => sel === '[data-copy-status]' ? status : null, querySelectorAll: sel => sel === '[data-tabs]' ? [root] : sel === '[data-copy]' ? [copy] : [] };
  const timers = new Map(); let next = 0;
  const writes = [];
  const selected = []; const code = { tagName: 'PRE' }; copy.previousElementSibling = code;
  const status = { textContent: '' };
  runInNewContext(js, { getSelection: () => ({ selectAllChildren: el => selected.push(el) }), document, navigator: { clipboard: { writeText: t => { written.push(t); return new Promise((ok, fail) => writes.push({ ok, fail })); } } },
    setTimeout: fn => { timers.set(++next, fn); return next; }, clearTimeout: id => timers.delete(id) });
  tabs[1].listeners.click();
  assert.equal(tabs[1].attrs['aria-selected'], 'true'); assert.equal(panels['p-a'].hidden, true); assert.equal(panels['p-b'].hidden, false);
  tabs[1].listeners.keydown({ key: 'ArrowRight', preventDefault() {} });
  assert.equal(tabs[0].attrs['aria-selected'], 'true'); assert.equal(focused, tabs[0]);
  const click = () => { const done = copy.listeners.click(); const w = writes.at(-1); return { ok: async () => { w.ok(); await done; }, fail: async () => { w.fail(new Error('denied')); await done; } }; };
  const fire = () => { [...timers.values()].at(-1)(); timers.clear(); };
  // A slow failure that settles after a newer success (even after the reset) changes nothing.
  let slow = click(), fast = click();
  await fast.ok(); assert.equal(copy.textContent, 'Copied'); assert.equal(status.textContent, 'Copied to clipboard');
  fire(); await slow.fail(); assert.equal(copy.textContent, 'Copy', 'a stale failure never shows');
  // An early failure stays quiet while another copy is still in flight, and that copy wins.
  slow = click(); fast = click();
  await fast.fail(); assert.equal(copy.textContent, 'Copy'); assert.deepEqual(selected, []);
  await slow.ok(); assert.equal(copy.textContent, 'Copied');
  assert.equal(status.textContent, 'Copied to clipboard', 'our reset cleared our own message, so this one is announced fresh');
  // A lone failure selects the command and says so.
  fire(); await click().fail();
  assert.equal(copy.textContent, 'Copy failed'); assert.deepEqual(selected, [code]); assert.match(status.textContent, /copy it yourself/);
  fire(); await click().ok();
  status.textContent = 'Copy failed. The command is selected so you can copy it yourself.'; // another button just said this
  await click().fail(); assert.match(status.textContent, /\u00a0$/, 'a repeat from any button is re-announced');
  assert.deepEqual(written, Array(7).fill('brew install skeptic'));
  assert.equal(timers.size, 1, 'exactly one reset timer is running');
  [...timers.values()][0]();
  assert.equal(copy.textContent, 'Copy', 'the reset restores the original label');
  const lone = el(); lone.dataset.copy = 'x';
  runInNewContext(js, { document: { querySelector: () => null, querySelectorAll: s => s === '[data-copy]' ? [lone] : [] }, navigator: {}, setTimeout() {}, clearTimeout() {} });
  assert.equal(lone.removed, true, 'copy buttons disappear when there is no clipboard');
});

test('copy degrades: no selection API gives an honest message; no status line keeps the buttons', async () => {
  const copy = { textContent: 'Copy', dataset: { copy: 'x' }, listeners: {}, previousElementSibling: { tagName: 'PRE' }, addEventListener(t, f) { this.listeners[t] = f; }, remove() { this.removed = true; } };
  const status = { textContent: '' };
  runInNewContext(js, { getSelection: () => { throw new Error('no selection here'); }, document: { querySelector: () => status, querySelectorAll: s => s === '[data-copy]' ? [copy] : [] },
    navigator: { clipboard: { writeText: async () => { throw new Error('denied'); } } }, setTimeout() {}, clearTimeout() {} });
  await copy.listeners.click();
  assert.equal(copy.textContent, 'Copy failed'); assert.match(status.textContent, /copy the command manually/); assert.doesNotMatch(status.textContent, /above|selected/);
  const kept = { textContent: 'Copy', dataset: { copy: 'x' }, listeners: {}, addEventListener(t, f) { this.listeners[t] = f; }, remove() { this.removed = true; } };
  runInNewContext(js, { document: { querySelector: () => null, querySelectorAll: s => s === '[data-copy]' ? [kept] : [] }, navigator: { clipboard: { writeText: async () => {} } }, setTimeout() {}, clearTimeout() {} });
  await kept.listeners.click();
  assert.equal(kept.removed, undefined); assert.equal(kept.textContent, 'Copied');
  const lost = { textContent: 'Copy', dataset: { copy: 'x' }, listeners: {}, addEventListener(t, f) { this.listeners[t] = f; } };
  runInNewContext(js, { document: { querySelector: () => null, querySelectorAll: s => s === '[data-copy]' ? [lost] : [] }, navigator: { clipboard: { writeText: async () => { throw new Error('denied'); } } }, setTimeout() {}, clearTimeout() {} });
  await lost.listeners.click();
  assert.equal(lost.textContent, 'Copy failed', 'a failure without a status line still shows on the button');
});

test('two copy buttons share the status line without wiping each other', async () => {
  const timers = [];
  const mk = () => ({ textContent: 'Copy', dataset: { copy: 'x' }, listeners: {}, addEventListener(t, f) { this.listeners[t] = f; } });
  const a = mk(), b = mk(); const status = { textContent: '' };
  let fail = false;
  runInNewContext(js, { getSelection: () => ({ selectAllChildren() {} }), document: { querySelector: () => status, querySelectorAll: s => s === '[data-copy]' ? [a, b] : [] },
    navigator: { clipboard: { writeText: async () => { if (fail) throw new Error('denied'); } } }, setTimeout: fn => timers.push(fn), clearTimeout() {} });
  await a.listeners.click();
  fail = true; await b.listeners.click();
  const said = status.textContent;
  timers[0]();  // A's reset fires after B spoke
  assert.equal(a.textContent, 'Copy'); assert.equal(status.textContent, said, "B's message survives A's reset");
  timers[1]();  // B's own reset clears B's message
  assert.equal(status.textContent, '', 'no stale result left behind');
  // Same result from two buttons in a row: A's older timer must not clear B's newer message.
  fail = false; timers.length = 0;
  await a.listeners.click(); await b.listeners.click(); await b.listeners.click(); // the text cycles back to A's exact string
  const newest = status.textContent;
  timers[0]();
  assert.equal(status.textContent, newest, "A's timer leaves B's identical, newer message alone");
  timers[2](); assert.equal(status.textContent, '', "B's latest timer clears it");
});

test('the page has the status line copy results are announced in', () => {
  const tags = home.match(/<[^>]*data-copy-status[^>]*>/g) || [];
  assert.equal(tags.length, 1, 'exactly one status line');
  assert.match(tags[0], /role="status"/);
  assert.match(tags[0], /class="visually-hidden"/, 'the status line must stay invisible');
});

test('build ships exactly the reviewed files, unchanged and free of private data', async () => {
  assert.deepEqual((await readdir('dist')).sort(), [...SHIPPED].sort());
  for (const file of SHIPPED) {
    const built = await readFile(`dist/${file}`, 'utf8');
    if (!['index.html', 'landing.js', 'landing.css', 'utilities.css'].includes(file)) assert.equal(built, await readFile(file, 'utf8'), file);
    if (file === 'index.html') { assert.match(built, /<canvas/); assert.doesNotMatch(built, /HALFTONE_(?:MASTHEAD|FOOTER)/); }
    assert.doesNotMatch(built, /\/Users\/|\/private\/tmp\/|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,}|@nd\.edu/);
  }
});

test('homepage keeps the pitch compact and routes reference content to the guide', () => {
  assert.doesNotMatch(home, /class="(?:trust|compare|faq|install)"/);
  for (const id of ['install','compare','faq']) assert.match(guide, new RegExp('id="'+id+'"'));
  assert.match(home, /href="guide.html"/);
});

// Wide screens, 14 Oct: "no matter what computer it's loaded in it fixes itself accordingly."
// A fixed 1180px column left dead margins either side of anything wider than ~1300px.
test('the content cap tracks the window instead of stopping at a fixed width', () => {
  assert.match(css, /--gutter:clamp\(16px,5vw,64px\); --max:1180px;/, 'the base cap is unchanged below 1350px');
  for (const [bp, cap] of [['1350', '1460px'], ['1850', '1700px'], ['2450', '1900px']]) {
    assert.ok(css.includes(`@media (min-width:${bp}px) { :root { --max:min(${cap}, calc(100vw - 2 * var(--gutter))); } }`),
      `above ${bp}px the cap becomes ${cap} or the window minus its gutters`);
  }
  assert.match(css, /\.section-head \{ max-width:var\(--max\)/, 'sections read the cap, so every one of them follows');
});
