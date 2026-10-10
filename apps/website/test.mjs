import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
const home = await readFile('index.html', 'utf8');
const guide = await readFile('guide.html', 'utf8');
const html = home + guide;
const css = await readFile('style.css', 'utf8');
const js = await readFile('app.js', 'utf8');
test('all page and fragment links resolve with unique IDs per page', () => {
 const pages = {'index.html':home, 'guide.html':guide};
 for (const [name, page] of Object.entries(pages)) {
  const values=[...page.matchAll(/id="([^"]+)"/g)].map(m=>m[1]);
  const ids=new Set(values); assert.equal(ids.size,values.length, name);
  for(const m of page.matchAll(/href="([^"]+)"/g)) {
   if(m[1].endsWith('.css')||m[1].endsWith('.svg')) continue;
   const [file,fragment]=m[1].split('#');
   const target=pages[file||name]; assert.ok(target, m[1]);
   if(fragment) assert.ok(target.includes(`id="${fragment}"`), m[1]);
  }
 }
 for(const id of ['how','models','preview','markdown','ownership','roadmap','faq','start']) assert.ok(html.includes(`id="${id}"`));
});
test('local asset references exist', async()=> { for(const m of html.matchAll(/(?:src|href)="([^"#]+\.(?:css|js|svg))"/g)) await access(m[1]); });
test('no external assets, network requests, accounts or private fixture paths',()=> { assert.doesNotMatch(html+js,/https?:\/\/|fetch\(|XMLHttpRequest|\/Users\/|skeptic-discovery/); });
test('keyboard labels, announcements and reduced motion present',()=> { for(const id of ['model','policy','task']) assert.ok(html.includes(`for="${id}"`)); assert.match(html,/aria-live="polite"/); assert.match(css,/prefers-reduced-motion/); assert.match(css,/:focus-visible/); });
test('marketing distinguishes unreleased features',()=> { assert.match(html,/Live indexing is not available yet/); assert.match(html,/Automatic preference learning is not available/); assert.match(html,/Universal provider onboarding has not been validated/); });
test('all access modes and synthetic download handler present',()=>{for(const mode of ['FULL_BRAIN','PROJECT_SCOPED','ASK_TO_EXPAND']) assert.ok(js.includes(mode)); assert.match(js,/text\/markdown/);});

test('demo submission updates all model, policy and task combinations without external actions', async()=> {
 const { runInNewContext } = await import('node:vm');
 const elements = new Map();
 function element(){return {value:'',textContent:'',listeners:{},children:[],addEventListener(type,fn){this.listeners[type]=fn},replaceChildren(...children){this.children=children},prepend(){},click(){}};}
 const document={querySelector(key){if(!elements.has(key))elements.set(key,element());return elements.get(key)},createElement:element};
 const downloads=[];
 runInNewContext(js,{document,window:{},Blob,URL:{createObjectURL(blob){downloads.push(blob);return 'blob:synthetic'},revokeObjectURL(){}},setTimeout(fn){fn()}});
 for(const model of ['Claude Code','Codex','Local model']) for(const policy of ['FULL_BRAIN','PROJECT_SCOPED','ASK_TO_EXPAND']) for(const task of ['writing','planning']) {
  document.querySelector('#model').value=model; document.querySelector('#policy').value=policy; document.querySelector('#task').value=task;
  document.querySelector('#policy').listeners.change();
  let prevented=false;document.querySelector('#demo-form').listeners.submit({preventDefault(){prevented=true}});
  assert.ok(prevented); assert.equal(document.querySelector('#receipt-title').textContent,`Ready for ${model}.`);
  const paths=document.querySelector('#receipt-context').children.map(e=>e.textContent);
  assert.equal(paths.length,policy==='ASK_TO_EXPAND'?1:2);
  assert.ok(paths[0].includes(task==='writing'?'essay':'atlas'));
  if(policy==='ASK_TO_EXPAND')assert.match(document.querySelector('#receipt-result').textContent,/requires approval/);
 }
 document.querySelector('#download').listeners.click();
 assert.equal(downloads.length,1);assert.match(await downloads[0].text(),/Synthetic checkpoint/);
});

test('eight-step onboarding covers every path/source/policy with back and restart state', async()=>{
 const {initial,advance,back,steps,paths,sources,modes,summary}=await import('./wizard-state.js');
 assert.equal(steps.length,8);
 for(const model of Object.keys(paths))for(const source of sources)for(const mode of Object.keys(modes)){
  let state=initial();state=advance(state).state;
  assert.ok(advance(state).error);state.model=model;state=advance(state).state;
  assert.ok(advance(state).error);state.source=source;state=advance(state).state;
  assert.ok(advance(state).error);state.mode=mode;state=advance(state).state;
  state=back(state);assert.equal(state.mode,mode);state=advance(state).state;
  while(state.step<7)state=advance(state).state;
  assert.equal(state.step,7);assert.ok(summary(state).includes(model));assert.equal(advance(state).state.step,7);
  assert.equal(initial().model,'');
 }
});
test('expanded marketing includes docs, compatibility and demo-only signup',()=>{
 for(const id of ['about','onboarding','features','docs','early-access']) assert.ok(html.includes(`id="${id}"`));
 for(const name of ['Foam','SilverBullet','Starting fresh'])assert.ok(html.includes(name)||name==='Starting fresh');
 assert.match(html,/No address is collected or saved/);assert.match(html,/type="email"[^>]*disabled/);
});

test('deployment headers and monochrome navigation preserve contrast',async()=>{
 const headers=await readFile('_headers','utf8');
 assert.match(headers,/connect-src 'none'/);assert.match(headers,/form-action 'none'/);assert.match(headers,/frame-ancestors 'none'/);
 assert.match(css,/\.step-number\{color:#000;border-left/);assert.match(css,/nav \.active\{color:#000;text-decoration/);
 const build=await readFile('build.mjs','utf8');assert.match(build,/'_headers'/);
});

test('homepage keeps six focused sections and full previews remain on the guide',()=>{
 assert.equal((home.match(/<section\b/g)||[]).length,6);
 for(const id of ['about','benefits','how','models','start']) assert.ok(home.includes(`id="${id}"`));
 for(const id of ['onboarding','preview','docs','faq','early-access']) {
  assert.ok(guide.includes(`id="${id}"`)); assert.ok(!home.includes(`id="${id}"`));
 }
 assert.match(home,/guide.html#onboarding/);
 for(const path of ['Claude-first','Codex-first','Local-model-first','Fresh start']) assert.ok(home.includes(path));
 assert.doesNotMatch(home,/<script/); // No demo handlers run against absent controls.
 assert.match(guide,/src="app.js"/); assert.match(guide,/src="onboarding.js"/);
});
test('compact CTA and responsive shrink rules never mask overflow',()=>{
 assert.doesNotMatch(css,/overflow(?:-x)?\s*:\s*(?:hidden|clip)/);
 assert.match(css,/\.cta-actions \.button\s*\{\s*width:fit-content/);
 assert.match(css,/min-height:44px/); assert.match(css,/flex-wrap:wrap/);
 assert.match(css,/minmax\(0,1fr\)/); assert.match(css,/overflow-wrap:anywhere/);
});
test('each page has one primary heading and a labeled navigation and skip link',()=>{
 for(const page of [home,guide]) {
  assert.equal((page.match(/<h1\b/g)||[]).length,1);
  assert.match(page,/aria-label="Main navigation"/);
  assert.match(page,/class="skip" href="#main"/);
  assert.match(page,/id="main" tabindex="-1"/);
 }
});

test('architecture diagrams retain accessible descriptions and truthful capability status',()=>{
 const captions=['architecture-caption','context-caption','handoff-caption'];
 for(const id of captions) {
  assert.match(html,new RegExp(`aria-labelledby="${id}"`));
  assert.match(html,new RegExp(`<figcaption id="${id}">`));
 }
 assert.equal((html.match(/<figure\b/g)||[]).length,3);
 for(const label of ['User-owned knowledge','Skeptic OS','Claude Code','Codex','Local AI']) assert.ok(home.includes(label));
 for(const label of ['Knowledge discovery','Session handoffs','Preference learning','Model onboarding','Memory updates','Context optimization']) assert.ok(home.includes(label));
 assert.match(home,/Preference learning<\/strong><span>Planned/);
 assert.match(home,/Memory updates<\/strong><span>Planned/);
 assert.match(home,/Knowledge discovery<\/strong><span>Implemented prototype/);
 assert.match(home,/Session handoffs<\/strong><span>Documented workflow/);
 assert.match(home,/no live connections/);
 assert.match(guide,/provider delivery is planned/);
 assert.match(guide,/Automated cross-model onboarding remains planned/);
 assert.match(css,/\.capability-grid\s*\{[^}]*minmax\(0,1fr\)/);
});

test('production package contains only reviewed local assets and inert signup',async()=>{
 const {readdir}=await import('node:fs/promises');
 const files=['index.html','guide.html','style.css','app.js','favicon.svg','onboarding.js','wizard-state.js','_headers'];
 assert.deepEqual((await readdir('dist')).sort(),files.sort());
 let contents='';
 for(const file of files) {
  const built=await readFile(`dist/${file}`,'utf8');
  assert.equal(built,await readFile(file,'utf8'),file);
  contents+=built.replace('http://www.w3.org/2000/svg','');
 }
 assert.doesNotMatch(contents,/\/Users\/|\/home\/|\/private\/tmp\/|BEGIN (?:RSA |OPENSSH )?PRIVATE KEY|AKIA[A-Z0-9]{16}|sk-[a-zA-Z0-9]{20,}/);
 assert.doesNotMatch(contents,/https?:\/\/|fetch\s*\(|XMLHttpRequest|sendBeacon|WebSocket|google-analytics|cloudflareinsights|localStorage|sessionStorage/);
 assert.match(guide,/type="email"[^>]*disabled/);
 assert.doesNotMatch(guide,/<form[^>]+action=/);
 assert.match(await readFile('onboarding.js','utf8'),/nothing was submitted or saved/);
});


test('monochrome primary CTA meets AAA contrast and preserves interaction states',()=>{
 const ratio=(1+.05)/(0+.05);
 assert.equal(ratio,21);
 assert.match(css,/--black:#000;/); assert.match(css,/--white:#fff;/);
 assert.match(css,/\.button \{[^}]*background:var\(--black\); color:#fff;[^}]*font-size:19px; font-weight:700/);
 assert.match(css,/\.button span \{ color:inherit/);
 for(const state of ['hover','active']) assert.match(css,new RegExp('\\.button:'+state+' \\{[^}]*background:var\\(--black\\); color:#fff;'));
 assert.match(css,/\.button:focus-visible \{ outline:3px solid #000/);
 assert.match(css,/\.button:disabled,\.button\[aria-disabled="true"\] \{[^}]*background:#505050; color:#fff;[^}]*opacity:1/);
});
test('homepage architecture has decorative inline icons and responsive cards',()=>{
 const figure=home.match(/<figure class="architecture premium-architecture"[\s\S]*?<\/figure>/)?.[0];
 assert.ok(figure);
 const icons=figure.match(/<svg\b[^>]*>/g)||[];
 assert.equal(icons.length,15);
 for(const svg of icons) { assert.match(svg,/aria-hidden="true"/); assert.match(svg,/focusable="false"/); assert.match(svg,/viewBox="0 0 24 24"/); }
 assert.equal((figure.match(/<li>/g)||[]).length,13);
 assert.match(css,/\.premium-architecture \.capability-grid li \{[^}]*border:1px solid/);
 assert.match(css,/@media\(max-width:560px\)[\s\S]*\.premium-architecture \.capability-grid \{ grid-template-columns:minmax\(0,1fr\)/);
 assert.match(css,/@media\(max-width:360px\)[\s\S]*\.premium-architecture \.knowledge-cards/);
});

// Palette regression covers every shipped CSS/SVG/HTML asset, including the favicon.
test('website ships only monochrome colors with contrasting secondary controls',async()=>{
 const assets=css+home+guide+await readFile('favicon.svg','utf8');
 for(const match of assets.matchAll(/#([0-9a-f]{3,8})\b/gi)) {
  const hex=match[1];if(![3,4,6,8].includes(hex.length))continue;
  const channels=hex.length<=4?hex.slice(0,3).split(''):[hex.slice(0,2),hex.slice(2,4),hex.slice(4,6)];
  assert.equal(new Set(channels.map(c=>c.toLowerCase())).size,1,`Non-neutral color: ${hex}`);
 }
 assert.doesNotMatch(assets,/--red|(?:color|background|fill|stroke)\s*[:=]\s*["']?(?:red|blue|green)|(?:rgb|hsl)a?\(/i);
 assert.match(css,/\.outline-button \{ background:white; color:black/);
 assert.match(css,/:focus-visible \{ outline:3px solid var\(--black\); outline-offset:4px/);
 assert.match(css,/input \{ accent-color:var\(--black\)/);
});
