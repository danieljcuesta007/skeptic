'use strict';
const $ = id => document.getElementById(id);
let token, current, inventory = {projects:[], roots:[], repositories:[]}, overview, events = [], busy = false, page = 'all';
const recent = [];
const node = (tag, text, cls) => { const el=document.createElement(tag); if(text!==undefined)el.textContent=text;if(cls)el.className=cls;return el; };
const message = text => { $('message').textContent=text; };
async function api(route,data={}) {
  const response=await fetch('/api/workspace/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-Skeptic-Token':token},body:JSON.stringify(data)});
  const result=await response.json();if(!response.ok)throw new Error(result.error);return result;
}
async function run(work) {
  if(busy)return;busy=true;
  const controls=[...document.querySelectorAll('button,input,textarea,select')], prior=controls.map(b=>b.disabled);
  controls.forEach(b=>b.disabled=true);
  try{await work();}catch(error){message(error.message);}
  finally{controls.forEach((b,i)=>b.disabled=prior[i]);$('copy').disabled=!$('prompt').value;busy=false;}
}
function activity(text){events.unshift(text);events=events.slice(0,40);$('events').replaceChildren(...events.map(t=>node('p',t)));}
function clearPrompt(){$('prompt').value='';$('copy').disabled=true;}
function sourceList(id,paths,fallback){$(id).replaceChildren(...(paths.length?paths:[fallback]).map(p=>node('p',p,'path')));}
function cards(id,sections){$(id).replaceChildren(...(sections.length?sections.map(s=>{const c=node('article',undefined,'source-card');c.append(node('strong',s.heading),node('p',`${s.path}:${s.line} · SHA-256 ${s.sha256.slice(0,12)}`,'reference'),node('pre',s.text,'excerpt'));if(s.truncated)c.append(node('p','Excerpt truncated; read the full source.'));return c;}):[node('p','No recognized source section. Review missing information.')]));}
function showView(view){document.querySelectorAll('.view').forEach(el=>el.hidden=el.id!==view);document.querySelectorAll('[data-view]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.view===view)));}
function renderAudit(result){sourceList('reads',result.reads,'No Markdown files read.');const counts=new Map();result.excluded.forEach(e=>counts.set(e.reason,(counts.get(e.reason)||0)+1));$('exclusions').replaceChildren(...[...counts].map(([reason,count])=>node('p',`${count} · ${reason}`)));}
function button(text,work,cls='secondary'){const b=node('button',text,cls);b.type='button';b.addEventListener('click',()=>run(work));return b;}
function policyExplanation(){const policy=$('access-policy').value;$('policy-explanation').textContent={FULL_BRAIN:'FULL_BRAIN: search eligible Markdown locally within this approved root. No upload, provider access, editing or access outside this boundary. Protected paths always remain excluded.',PROJECT_SCOPED:'PROJECT_SCOPED: discover candidates and read project folders plus ancestor instructions within this root. Unrelated knowledge bodies remain unread.',ASK_TO_EXPAND:'ASK_TO_EXPAND: read exact STATUS checkpoints and governing instructions only. Other knowledge requires a separately approved policy change.'}[policy];}
function connect(root){clearPrompt();current=undefined;$('model-usage').hidden=true;$('workspace').hidden=true;$('inventory').hidden=true;$('onboarding').hidden=false;$('approve-form').reset();if(root){$('path').value=root.path;$('kind').value=root.kind;$('access-policy').value=root.policy;$('excluded').value=root.excluded.join('\n');}policyExplanation();$('path').focus();}
function renderInventory(){
  $('model-usage').hidden=page!=='usage';
  if(page==='usage'){ document.querySelectorAll('[data-page]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.page===page))); $('workspace').hidden=true;$('onboarding').hidden=true;$('inventory').hidden=true;return loadUsage(); }
  $('workspace').hidden=true;$('onboarding').hidden=true;$('inventory').hidden=false;
  const labels={all:'All Projects',recent:'Recent Projects',knowledge:'Knowledge Sources',repositories:'Repositories',handoffs:'Handoffs',permissions:'Permissions',activity:'Activity'};
  $('page-title').textContent=labels[page];$('page-description').textContent='Source claims remain attributed. READY TO RESUME means required checkpoint sections exist; it does not verify completion or freshness.';
  document.querySelectorAll('[data-page]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.page===page)));
  $('inventory-cards').replaceChildren();$('root-list').replaceChildren();$('inventory-audit').replaceChildren();
  let projects=inventory.projects;
  if(page==='recent')projects=recent.map(id=>projects.find(p=>p.id===id)).filter(Boolean);
  if(page==='handoffs')projects=projects.filter(p=>p.handoff);
  if(['all','recent','handoffs'].includes(page)){
    $('inventory-cards').replaceChildren(...projects.map(p=>{
      const c=node('article',undefined,'source-card');c.append(node('p',p.readiness,'eyebrow'),node('h3',p.name),node('p',p.knowledge?`Obsidian / Markdown: ${p.knowledge}`:'Knowledge not connected','path'),node('p',`Policy: ${p.policy}`,'small'),node('p',`Checkpoint: ${p.checkpoint||'Missing'}`,'path'));
      if(p.current)c.append(node('p','Current milestone / state — source excerpt'),node('pre',p.current.text,'excerpt'),node('p',`${p.current.source}:${p.current.line}`,'reference'));
      if(p.pending)c.append(node('p','Pending work — source excerpt'),node('pre',p.pending.text,'excerpt'),node('p',`${p.pending.source}:${p.pending.line}`,'reference'));
      c.append(node('p',`Handoff: ${p.handoff?'Available in STATUS':'Needs review / missing'}`),node('p',`Repository: ${p.repository?p.repository.path:p.suggestions.length?'Suggested match; confirmation required':'Not connected'}`,'path'),button('Open project',()=>openProject(p.id)));return c;
    }));if(!projects.length)$('inventory-cards').append(node('p','No projects in this view. Connect a root or review its approval.'));
  }
  if(['knowledge','permissions'].includes(page)){
    inventory.roots.forEach(r=>{const c=node('article',undefined,'source-card');c.append(node('strong',`${r.kind} · ${r.policy}`),node('p',r.path,'path'),node('p',r.approved?'Approved this session':'NOT CONNECTED · fresh approval required'),node('p',`Additional exclusions: ${r.excluded.join(', ')||'None; built-in protections apply.'}`));c.append(button(r.approved?'Review / change approval':'Approve this session',async()=>connect(r)),button('Disconnect root',async()=>{await api('disconnect',{id:r.id});clearPrompt();current=undefined;overview=undefined;activity('Revoked root access; files unchanged.');await refresh();}));$('root-list').append(c);});
    $('root-list').append(node('p','Approvals never survive restart. Protected credentials, caches and symlinks remain inaccessible. Only root registrations persist; no notes, prompts or derived memory are stored.'));
  }
  if(page==='repositories')inventory.repositories.forEach(r=>{const c=node('article',undefined,'source-card');c.append(node('h3',r.name),node('p',r.path,'path'),node('p',`Branch: ${r.branch||'Unknown'} · Commit: ${r.commit||'Unknown'}`,'path'),node('p',r.limitations));$('inventory-cards').append(c);});
  if(page==='activity')$('inventory-audit').append(...events.map(e=>node('p',e)),node('h3','Latest inventory source reads'),...inventory.reads.map(p=>node('p',p,'path')),node('p',`${inventory.excluded.length} exclusions; protected names withheld.`));
}
async function refresh(){if(page==='usage'){await renderInventory();return;}inventory=await api('inventory');activity(`Read-only inventory: ${inventory.projects.length} candidates, ${inventory.reads.length} Markdown sources. Git metadata inspection runs no commands.`);await renderInventory();}
async function openProject(id){
  clearPrompt();if(current!==id)$('task').value='';const result=await api('detail',{id});current=id;overview=result;recent.splice(0,recent.length,...[id,...recent.filter(k=>k!==id)].slice(0,20));
  $('model-usage').hidden=true;$('inventory').hidden=true;$('onboarding').hidden=true;$('workspace').hidden=false;const p=result.project;
  $('project-name').textContent=p.name;$('project-path').textContent=p.path;sourceList('missing',result.missing,'No missing sections detected; review factual freshness.');sourceList('checkpoints',result.checkpoints,'No checkpoint discovered.');sourceList('instructions',result.instructions,'No recognized instructions within approved boundaries.');cards('sections',result.sections.filter(s=>s.heading.toLowerCase()!=='handoff'));cards('handoffs',result.handoffs);
  $('repository-detail').replaceChildren();if(p.repository){$('repository-detail').append(node('p',p.repository.path,'path'),node('p',`Branch: ${p.repository.branch||'Unknown'} · Commit: ${p.repository.commit||'Unknown'}`,'path'),node('p',p.repository.evidence||'Approved local repository'),node('p',p.repository.limitations));(p.repository.evidence_sources||[]).forEach(s=>$('repository-detail').append(node('p',`Association source: ${s.path} · SHA-256 ${s.sha256.slice(0,12)}`,'reference')));}else $('repository-detail').append(node('p','Not connected. Sources cannot grant access to another root.'));
  p.suggestions.forEach(r=>$('repository-detail').append(button(`Confirm suggested match: ${r.path}`,async()=>{await api('confirm',{id,repository:r.id,approval:true});activity('User confirmed repository association.');await openProject(id);}))); 
  $('sources').replaceChildren(...result.sources.map(s=>{const label=node('label',undefined,'check source-choice'),check=node('input');check.type='checkbox';check.value=s.path;check.checked=result.default_selection.includes(s.path);check.addEventListener('change',clearPrompt);const detail=node('span',`${s.path} · ${s.reason} · ${s.characters} characters`,'path');label.append(check,detail);return label;}));
  $('policy').replaceChildren(node('p',`Selected access policy: ${p.policy} · read-only`),node('p',p.knowledge||'No connected knowledge root','path'),node('p','Review every approved root and revoke permissions in sidebar → Permissions. Parent sources above approved roots were not read.'));
  renderAudit(result);showView('overview');message(`${p.readiness}. Sources read freshly. Review attributed checkpoints and unknowns before continuing.`);activity(`Opened ${p.name}; ${result.reads.length} source reads used for this detail. Inventory may read other eligible sources under the displayed policy.`);
}
async function generate(provider){clearPrompt();$('provider').value=provider;const selected=[...document.querySelectorAll('#sources input:checked')].map(el=>el.value);const result=await api('resume',{id:current,selected,provider,task:$('task').value});$('prompt').value=result.prompt;renderAudit(result);activity(`Generated ${provider} prompt locally from ${selected.length} selected sources.`);message('Review the prompt, then copy and paste into your tool. No provider was launched.');}
$('add').addEventListener('click',()=>connect());$('cancel-connect').addEventListener('click',renderInventory);$('access-policy').addEventListener('change',policyExplanation);
$('approve-form').addEventListener('submit',e=>{e.preventDefault();run(async()=>{if(!$('approval').checked)throw new Error('Explicit read approval required.');const result=await api('connect',{path:$('path').value.trim(),kind:$('kind').value,policy:$('access-policy').value,excluded:$('excluded').value.split('\n').map(s=>s.trim()).filter(Boolean),approval:true});activity(result.activity);await refresh();message('Root connected. Select an existing project.');});});
$('refresh').addEventListener('click',()=>run(()=>openProject(current)));
$('remove').addEventListener('click',()=>run(async()=>{const result=await api('remove',{id:current});activity(result.activity);current=undefined;overview=undefined;clearPrompt();await refresh();message(result.activity);}));
document.querySelectorAll('[data-page]').forEach(b=>b.addEventListener('click',()=>run(async()=>{page=b.dataset.page;clearPrompt();await refresh();})));
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
$('generate').addEventListener('click',()=>run(()=>generate($('provider').value)));
$('claude-resume').addEventListener('click',()=>run(()=>generate('Claude Code')));$('codex-resume').addEventListener('click',()=>run(()=>generate('Codex')));
['task','provider'].forEach(id=>$(id).addEventListener('input',clearPrompt));
$('copy').addEventListener('click',()=>run(async()=>{try{await navigator.clipboard.writeText($('prompt').value);message('Copied. Paste into your tool when ready.');}catch{$('prompt').focus();$('prompt').select();message('Press Command–C to copy the selected prompt.');}}));
run(async()=>{const response=await fetch('/api/session');if(!response.ok)throw new Error('Use the exact 127.0.0.1 address.');token=(await response.json()).token;policyExplanation();await refresh();await refreshContinuity();message('Connect My Workspace to approve your existing vault and repository roots. No discovery before approval.');});

let usageSnapshot;
async function usageApi(data){const r=await fetch('/api/usage',{method:'POST',headers:{'Content-Type':'application/json','X-Skeptic-Token':token},body:JSON.stringify(data)});const body=await r.json();if(!r.ok)throw new Error(body.error);return body;}
async function loadUsage(op='read'){
  usageSnapshot=await usageApi({op});
  const selected=$('usage-filter').value;
  $('usage-filter').replaceChildren(new Option('All tools','all'),...usageSnapshot.catalog.map(p=>new Option(p.name,p.id)));
  $('usage-filter').value=selected||'all';
  const provider=$('usage-provider').value;
  $('usage-provider').replaceChildren(...usageSnapshot.catalog.map(p=>new Option(p.name,p.id)));
  if(provider)$('usage-provider').value=provider;
  renderUsage();
}
function renderUsage(){
  const snap=usageSnapshot;if(!snap)return;
  $('usage-status').textContent=snap.local_enabled?'Local activity readings connected. Refreshes every minute while this page is open; activity may be older.':'Local readings disconnected. Connect to read bounded Claude quota and Codex session quota fields. No credentials, prompts or cloud calls.';
  $('usage-connect').disabled=snap.local_enabled;$('usage-disconnect').disabled=!snap.local_enabled;
  const filter=$('usage-filter').value;
  $('usage-cards').replaceChildren(...snap.catalog.filter(p=>filter==='all'||filter===p.id).map(p=>{
    const card=node('article',undefined,'source-card');card.append(node('h3',p.name),node('p',p.help,'small'));
    const readings=snap.rows.filter(r=>r.provider===p.id);
    if(!readings.length)card.append(node('p','Usage unknown · no reading connected','notice'));
    readings.forEach(r=>{card.append(node('strong',r.model));r.windows.forEach(w=>{
      const age=Math.max(0,Math.floor(Date.now()/1000-w.observed_at));
      const freshness=age<60?'just now':age<3600?`${Math.floor(age/60)} minutes ago`:age<86400?`${Math.floor(age/3600)} hours ago`:`${Math.floor(age/86400)} days ago`;
      const window=w.window_minutes===10080?'Weekly':w.window_minutes?`${w.window_minutes/60} hour window`:w.unit;
      card.append(node('p',`${window}: ${w.display_remaining===null?'Unknown — refresh needed':`${Number(w.display_remaining.toFixed(2))} ${w.unit} remaining`}${w.limit!==null?` / ${w.limit} ${w.unit}`:''}`));
      if(w.unit==='%'&&w.display_remaining!==null){const meter=node('progress');meter.max=100;meter.value=w.display_remaining;meter.setAttribute('aria-label',`${r.model} quota remaining`);card.append(meter);}
      card.append(node('p',w.resets_at?`Reset / renewal: ${new Date(w.resets_at*1000).toLocaleString()}${w.expired?' · elapsed':''}`:'Reset / renewal unknown'));
      card.append(node('p',`${w.source} · ${freshness}`,'small'));
      if(w.source==='Manual reading')card.append(button('Remove manual reading',async()=>{usageSnapshot=await usageApi({op:'delete',id:r.id});renderUsage();}));
    });});
    if(p.url){const a=node('a','Open provider account');a.href=p.url;a.target='_blank';a.rel='noopener noreferrer';card.append(a);}
    return card;
  }));
}
$('usage-filter').addEventListener('change',renderUsage);
$('usage-connect').addEventListener('click',()=>run(()=>loadUsage('enable')));
$('usage-disconnect').addEventListener('click',()=>run(()=>loadUsage('disable')));
$('usage-refresh').addEventListener('click',()=>run(()=>loadUsage()));
$('usage-form').addEventListener('submit',e=>{e.preventDefault();run(async()=>{
  const amount=id=>$(id).value===''?null:Number($(id).value);
  usageSnapshot=await usageApi({op:'save',reading:{provider:$('usage-provider').value,model:$('usage-model').value.trim(),remaining:amount('usage-remaining'),limit:amount('usage-limit'),unit:$('usage-unit').value,resets_at:$('usage-reset').value?new Date($('usage-reset').value).getTime()/1000:null,observed_at:null}});
  renderUsage();message('Manual reading saved locally. Update it when provider usage changes.');
});});
setInterval(()=>{if(token&&page==='usage'&&!busy&&!document.hidden)run(()=>loadUsage());},60000);

// Appearance and welcome persist in owner-only local files, never browser storage.
let desktopPreferences = {theme: 'system', welcomed: false};
async function preferenceRequest(data) {
  const session = await fetch('/api/session'); const authorization = await session.json();
  const response = await fetch('/api/preferences', {method:'POST', headers:{'Content-Type':'application/json','X-Skeptic-Token':authorization.token}, body:JSON.stringify(data)});
  const result = await response.json(); if (!response.ok) throw new Error(result.error || 'Preferences unavailable'); return result;
}
function applyAppearance() { document.documentElement.dataset.theme = desktopPreferences.theme; $('appearance').value = desktopPreferences.theme; $('welcome').hidden = desktopPreferences.welcomed; }
$('appearance').addEventListener('change', () => run(async () => { desktopPreferences = await preferenceRequest({action:'save',theme:$('appearance').value,welcomed:desktopPreferences.welcomed}); applyAppearance(); }));
$('welcome-done').addEventListener('click', () => run(async () => { desktopPreferences = await preferenceRequest({action:'save',theme:desktopPreferences.theme,welcomed:true}); applyAppearance(); }));
$('help-toggle').addEventListener('click', () => { $('command-guide').hidden = !$('command-guide').hidden; });
run(async () => { desktopPreferences = await preferenceRequest({action:'get'}); applyAppearance(); });

async function refreshContinuity(){
 const status=$('continuity-status'),list=$('continuity-sessions');
 try{
  const response=await fetch('/api/continuity',{method:'POST',headers:{'Content-Type':'application/json','X-Skeptic-Token':token},body:'{}'});
  if(!response.ok)throw new Error('Engine unavailable');
  const data=await response.json();
  status.textContent=`${data.engine} · ${data.monitoring} · ${data.sessions.length} observed sessions`;
  list.replaceChildren(...data.sessions.map(s=>{
   const card=node('details',undefined,'source-card');card.append(node('summary',`${s.project} · ${s.agent} · ${s.readiness}`));
   card.append(node('p',`Activity: ${s.activity} · verification: ${s.verification} · checkpoint: ${s.checkpoint_fresh?'fresh':'stale'} · dirty work: ${s.dirty?'present':'none observed'}`));
   card.append(node('p',s.objective),node('p',s.cwd,'path'),node('p',`Writer: ${s.writer}`));
   card.append(node('h3','Outstanding work'),...s.pending.map(t=>node('p',t)),node('h3','Handoff blockers'),...s.blocked_reasons.map(t=>node('p',t)));
   return card;
  }));
 }catch(error){status.textContent='Engine disconnected · readiness unknown';list.replaceChildren();}
}
$('continuity-refresh').addEventListener('click',()=>run(refreshContinuity));
setInterval(()=>{if(token&&!busy)refreshContinuity();},5000);

$('continuity-compact').addEventListener('click',()=>{const on=document.body.classList.toggle('continuity-focus');$('continuity-compact').setAttribute('aria-pressed',String(on));$('continuity-compact').textContent=on?'Full workspace':'Compact view';});
