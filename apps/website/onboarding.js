import {steps,paths,sources,modes,initial,advance,back,summary} from './wizard-state.js';
let state=initial();
const $=id=>document.getElementById(id);
const descriptions=[
 'Your knowledge already has a home. Explore how a new model could learn its way around. This is a demonstration, not an installation.',
 'Choose a starting path. Skeptic should adapt to your tools, not ask you to abandon them.',
 'Choose the kind of knowledge you already have. No filesystem permission is requested and no files are opened.',
 'Choose explicitly. Full brain is the project owner’s personal design default, not an assumed default for every user.',
 'Examples: “Keep updates concise” (explicit), “often asks for examples” (observed), “may prefer diagrams” (tentative). Only approved explicit rules should become permanent.',
 'A future adapter would supply applicable rules, relevant project state and source references. No provider is connected here.',
 'A checkpoint preserves verified outcomes, unknowns and the exact next action. Current files outrank a stale handoff.',
 'Walkthrough complete. No installation, scan or configuration change has occurred. Production adapters and release packaging remain future work.'
];
function render(focus=true){
 $('wizard-step').textContent=`STEP ${state.step+1} OF 8`;
 $('wizard-title').textContent=steps[state.step];$('wizard-description').textContent=descriptions[state.step];
 $('wizard-options').replaceChildren();
 const key={1:'model',2:'source',3:'mode'}[state.step];
 if(key){const label=document.createElement('label');label.htmlFor='wizard-choice';label.textContent={model:'Your starting point',source:'Knowledge source',mode:'Access policy'}[key];const select=document.createElement('select');select.id='wizard-choice';const placeholder=document.createElement('option');placeholder.value='';placeholder.textContent='Choose an option';select.append(placeholder);const values=key==='model'?Object.keys(paths):key==='source'?sources:Object.keys(modes);for(const value of values){const option=document.createElement('option');option.value=value;option.textContent=key==='mode'?value.replaceAll('_',' ').toLowerCase().replace(/^./,c=>c.toUpperCase()):value;select.append(option);}select.value=state[key];select.addEventListener('change',()=>{state[key]=select.value;render(false);$('wizard-choice').focus()});$('wizard-options').append(label,select);}
 let example='DEMO / Your files stay yours. Nothing leaves this browser.';
 if(state.step===1)example=paths[state.model]||'Claude Code · Codex · Local models · Starting fresh';
 if(state.step===2)example=state.source?`${state.source}: synthetic example only. Other integrations are coming later.`:'Obsidian and ordinary Markdown first. Other integrations are coming later.';
 if(state.step===3)example=modes[state.mode]||'No policy selected. Read access never grants write or upload permission.';
 if(state.step===4)example='PROPOSAL → evidence → your approval → canonical update. No automatic preference promotion.';
 if(state.step===5)example=`${paths[state.model]}\nSample references: principles.md · preferences.md · projects/atlas/status.md. ${modes[state.mode]}`;
 if(state.step===6)example=`${state.model==='Codex'?'Codex → Local model':'Claude Code → Codex'}\nDONE: outlined milestone. VERIFIED: reviewed synthetic checkpoint. NOT VERIFIED: real provider behavior. NEXT: review scope before editing.`;
 if(state.step===7)example=`${summary(state)}\nNext: explore the introductory docs or restart with another path. Real setup will require a released adapter and explicit permissions.`;
 $('wizard-example').textContent=example;$('wizard-error').textContent='';$('wizard-back').disabled=state.step===0;
 $('wizard-next').textContent=state.step===7?'Try another path ↺':state.step===0?'Let’s begin →':'Continue →';
 [...$('wizard-progress').children].forEach((item,index)=>{if(index===state.step)item.setAttribute('aria-current','step');else item.removeAttribute('aria-current');item.classList.toggle('complete',index<state.step)});
 if(focus)$('wizard-title').focus();
}
$('wizard-next').addEventListener('click',()=>{if(state.step===7){state=initial();render();return;}const result=advance(state);if(result.error){$('wizard-error').textContent=result.error;return;}state=result.state;render();});
$('wizard-back').addEventListener('click',()=>{state=back(state);render();});
$('early-form').addEventListener('submit',event=>{event.preventDefault();$('early-status').textContent='Preview complete. You have not joined a waitlist; nothing was submitted or saved.';});
render(false);
