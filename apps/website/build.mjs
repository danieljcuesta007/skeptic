import { mkdir, copyFile } from 'node:fs/promises';
await mkdir('dist', { recursive: true });
for (const file of ['index.html','guide.html','style.css','app.js','favicon.svg','onboarding.js','wizard-state.js','_headers']) await copyFile(file, `dist/${file}`);
console.log('Production static build: dist/ (8 files). No dependencies or network.');
