import { mkdir, copyFile, rm, readFile, writeFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
import { build } from 'esbuild';
import postcss from 'postcss';
import tailwind from '@tailwindcss/postcss';
export const files = ['index.html','guide.html','legal.html','style.css','site.js','favicon.svg','install.sh','_headers'];
await rm('dist', { recursive: true, force: true });
await mkdir('dist', { recursive: true });
for (const file of files) await copyFile(file, `dist/${file}`);
await mkdir('.build', { recursive: true });
try {
  await build({ entryPoints: ['render.tsx'], bundle: true, platform: 'node', format: 'cjs', outfile: '.build/render.cjs', loader: { '.css': 'empty' } });
  const { masthead, footer } = createRequire(import.meta.url)('./.build/render.cjs');
  const source = await readFile('index.html', 'utf8');
  await writeFile('dist/index.html', source.replace('<!-- HALFTONE_MASTHEAD -->', masthead).replace('<!-- HALFTONE_FOOTER -->', footer));
  await build({ entryPoints: ['client.tsx'], bundle: true, minify: true, format: 'esm', target: ['es2022'], outfile: 'dist/landing.js' });
  const utilities = await postcss([tailwind({ base: process.cwd() })]).process(await readFile('styles/globals.css', 'utf8'), { from: 'styles/globals.css' });
  await writeFile('dist/utilities.css', utilities.css);
} finally {
  await rm('.build', { recursive: true, force: true });
}
console.log('Production build: static HTML with hydrated React wordmarks, local CSS and JS.');
