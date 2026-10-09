import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
const html = await readFile('index.html', 'utf8');
const css = await readFile('style.css', 'utf8');
const js = await readFile('app.js', 'utf8');
test('all internal links resolve and all nine sections exist', () => {
 const ids = new Set([...html.matchAll(/id="([^"]+)"/g)].map(m=>m[1]));
 for(const m of html.matchAll(/href="#([^"]+)"/g)) assert.ok(ids.has(m[1]), m[1]);
 for(const id of ['how','models','preview','markdown','ownership','roadmap','faq','start']) assert.ok(ids.has(id));
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

test('deployment headers are built and small red text uses black contrast correction',async()=>{
 const headers=await readFile('_headers','utf8');
 assert.match(headers,/connect-src 'none'/);assert.match(headers,/form-action 'none'/);assert.match(headers,/frame-ancestors 'none'/);
 assert.match(css,/\.step-number\{color:#000;border-left/);assert.match(css,/nav \.active\{color:#000;text-decoration/);
 const build=await readFile('build.mjs','utf8');assert.match(build,/'_headers'/);
});
