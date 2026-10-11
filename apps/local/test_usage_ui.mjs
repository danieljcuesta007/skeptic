import {readFileSync} from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
import test from 'node:test';

// DOM is the boundary: execute the production renderer, never duplicate it here.
class Element {
  constructor(tag='div'){this.tag=tag;this.children=[];this.value='';this.textContent='';this.handlers={};this.attributes={};}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;}
  addEventListener(name,handler){this.handlers[name]=handler;}
  setAttribute(name,value){this.attributes[name]=value;}
}
function fixture(){
  const ids=new Map();
  const document={getElementById:id=>{if(!ids.has(id))ids.set(id,new Element());return ids.get(id);},createElement:tag=>new Element(tag),querySelectorAll:()=>[]};
  const context=vm.createContext({document,Date,Map,Number,String,Error,JSON,console,setInterval:()=>{},Option:class extends Element{constructor(text,value){super('option');this.textContent=text;this.value=value;}}});
  let source=readFileSync(new URL('app.js',import.meta.url),'utf8').replace(/^run\(async\(\)=>\{const response=await fetch\('\/api\/session'\).*$/m,'');
  const faults={
    filter:s=>s.replace("filter==='all'||filter===p.id",'true'),
    units:s=>s.replaceAll('w.unit','"credits"'),
    remaining:s=>s.replace('meter.value=w.display_remaining','meter.value=100-w.display_remaining'),
    expired:s=>s.replace('Unknown — refresh needed','100% available'),
  };
  if(process.env.SKEPTIC_UI_FAULT)source=faults[process.env.SKEPTIC_UI_FAULT](source);
  vm.runInContext(source,context);
  context.fixture={catalog:[{id:'codex',name:'Codex',help:'Quota'},{id:'hermes',name:'Hermes',help:'Provider usage'},{id:'midjourney',name:'Midjourney',help:'Fast time'}],local_enabled:true,rows:[
    {provider:'codex',model:'Codex subscription',windows:[{display_remaining:75,remaining:75,limit:100,unit:'%',window_minutes:300,observed_at:Date.now()/1000,resets_at:Date.now()/1000+1000,source:'Last seen in local activity'}]},
    {id:'first',provider:'hermes',model:'Provider A / model one',windows:[{display_remaining:2,limit:5,unit:'USD',observed_at:Date.now()/1000,resets_at:null,source:'Manual reading'}]},
    {id:'second',provider:'hermes',model:'<img src=x onerror=alert(1)>',windows:[{display_remaining:null,remaining:10,limit:20,unit:'credits',observed_at:Date.now()/1000-10000,resets_at:Date.now()/1000-1,expired:true,source:'Manual reading'}]}
  ]};
  return {ids,context,render:filter=>{document.getElementById('usage-filter').value=filter;vm.runInContext('usageSnapshot=fixture;renderUsage();',context);return ids.get('usage-cards');}};
}
const text=el=>[el.textContent,...el.children.map(text)].join(' ');
test('picker filters providers and unconnected service remains unknown',()=>{const f=fixture();const cards=f.render('midjourney');assert.equal(cards.children.length,1);assert.match(text(cards),/Midjourney.*Usage unknown/);});
test('two Hermes models retain separate units and labels as plain text',()=>{const f=fixture();const cards=f.render('hermes');assert.match(text(cards),/2 USD remaining/);assert.match(text(cards),/Provider A \/ model one/);assert.match(text(cards),/<img src=x onerror=alert\(1\)>/);assert.equal(cards.children[0].children.some(c=>c.tag==='img'),false);});
test('Codex displays remaining, window and reset with an accessible meter',()=>{const f=fixture();const cards=f.render('codex');assert.match(text(cards),/5 hour window: 75 % remaining/);assert.match(text(cards),/Reset \/ renewal:/);const meter=cards.children[0].children.find(c=>c.tag==='progress');assert.equal(meter.value,75);assert.match(meter.attributes['aria-label'],/quota remaining/);});
test('expired manual quota is unknown and still shows provenance',()=>{const f=fixture();const cards=f.render('hermes');assert.match(text(cards),/Unknown — refresh needed/);assert.match(text(cards),/Manual reading/);assert.doesNotMatch(text(cards),/10 credits remaining/);});
test('continuity uses backend blockers and gates offline controls',async()=>{
 const f=fixture();f.context.fetch=async()=>({ok:true,json:async()=>({engine:'offline_fixture',monitoring:'fixture_only',capabilities:{prepare_offline:true},sessions:[{id:'fixture',project:'Long project name <script>',agent:'hermes',readiness:'handoff_blocked',activity:'unknown',verification:'stale',checkpoint_fresh:false,dirty:true,objective:'unfinished',cwd:'/fixture',writer:'unknown',pending:['finish'],blocked_reasons:['Source identity uncertain'],verification_provenance:['caller-reported']}]})});
 await vm.runInContext('refreshContinuity()',f.context);
 const cards=f.ids.get('continuity-sessions');assert.match(text(cards),/Source identity uncertain/);assert.match(text(cards),/stale/);assert.match(text(cards),/caller-reported/);assert.match(text(cards),/Prepare offline handoff/);assert.doesNotMatch(text(cards),/handoff_complete/);
 f.context.fetch=async()=>{throw new Error('disconnect')};await vm.runInContext('refreshContinuity()',f.context);assert.equal(cards.children.length,0);assert.match(f.ids.get('continuity-status').textContent,/disconnected.*unknown/);
});
