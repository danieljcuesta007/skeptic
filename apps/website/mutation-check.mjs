// Verify new UX regressions reject faults without altering source files.
import { mkdtemp, cp, readFile, writeFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { spawnSync } from 'node:child_process';
const cases = [
 ['colored favicon','website ships only monochrome colors with contrasting secondary controls','favicon.svg', s=>s.replace('fill="#000000"','fill="#ff2800"')],
 ['invisible primary CTA','monochrome primary CTA meets AAA contrast and preserves interaction states','style.css', s=>s.replace('color:#fff; border-color:var(--black); font-size:19px','color:#000; border-color:var(--black); font-size:19px')],
 ['missing architecture icon','homepage architecture has decorative inline icons and responsive cards','index.html', s=>s.replace(/<svg class="architecture-icon"[\s\S]*?<\/svg>/,'')],
 ['external tracking asset','production package contains only reviewed local assets and inert signup','guide.html', s=>s.replace('</head>','<script src="https://analytics.example/tracker.js"></script></head>')],
 ['unlabeled architecture','architecture diagrams retain accessible descriptions and truthful capability status','index.html', s=>s.replace('aria-labelledby="architecture-caption"','')],
 ['false learning status','architecture diagrams retain accessible descriptions and truthful capability status','index.html', s=>s.replace('Preference learning</strong><span>Planned','Preference learning</strong><span>Implemented')],
 ['broken guide destination','all page and fragment links resolve with unique IDs per page','index.html', s=>s.replace('guide.html#onboarding','guide.html#missing-step43')],
 ['repeated homepage section','homepage keeps six focused sections and full previews remain on the guide','index.html', s=>s.replace('</main>','<section id="repeated"><h2>Repeat</h2></section></main>')],
 ['overflow concealed','compact CTA and responsive shrink rules never mask overflow','style.css', s=>s+'\nbody { overflow-x:hidden; }\n'],
 ['extra primary heading','each page has one primary heading and a labeled navigation and skip link','guide.html', s=>s.replace('</main>','<h1>Repeated title</h1></main>')],
 ['oversized mobile CTA','compact CTA and responsive shrink rules never mask overflow','style.css', s=>s.replace('.cta-actions .button { width:fit-content; }','.cta-actions .button { width:100%; }')]
];
for (const [name,expected,file,mutate] of cases) {
 const scratch=await mkdtemp(join(tmpdir(),'skeptic-ux-'));
 try {
  await cp(new URL('.',import.meta.url),scratch,{recursive:true,filter:src=>!src.split('/').includes('dist')});
  const target=join(scratch,file); const before=await readFile(target,'utf8');
  const after=mutate(before); if(after===before) throw Error(`Fault not planted: ${name}`);
  await writeFile(target,after);
  const build=spawnSync(process.execPath,['build.mjs'],{cwd:scratch,encoding:'utf8'});
  if(build.status!==0) throw Error(`Scratch build failed: ${name}`);
  const result=spawnSync(process.execPath,['--test','--test-reporter=tap','test.mjs'],{cwd:scratch,encoding:'utf8'});
  if(result.error||result.status===null) throw result.error||Error('Runner failed');
  if(result.status===0 || !result.stdout.split("\n").some(line=>line.startsWith("not ok ") && line.endsWith(expected))) throw Error(`Expected regression did not reject fault: ${name}`);
  console.log(`Caught UX fault: ${name}`);
 } finally { await rm(scratch,{recursive:true,force:true}); }
}
console.log(`${cases.length}/${cases.length} UX mutations caught; source files unchanged.`);
