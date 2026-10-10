import {spawnSync} from 'node:child_process';
const faults={filter:'picker filters',units:'two Hermes',remaining:'Codex displays',expired:'expired manual'};
for(const [fault,pattern] of Object.entries(faults)){
  const result=spawnSync(process.execPath,['--test','--test-name-pattern',pattern,'test_usage_ui.mjs'],{cwd:new URL('.',import.meta.url),env:{...process.env,SKEPTIC_UI_FAULT:fault},encoding:'utf8'});
  if(result.error||result.status===null)throw result.error||new Error('Mutation runner failed');
  if(result.status===0)throw new Error(`Fault survived: ${fault}`);
}
console.log('4 planted UI usage faults caught; production source unchanged.');
