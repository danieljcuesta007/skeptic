// Preview the production build with the same CSP as Cloudflare Pages.
import { createServer } from 'node:http';
import { readFile, readdir } from 'node:fs/promises';
const files = new Set(await readdir('dist'));
const headers = await readFile('dist/_headers', 'utf8');
const shared = Object.fromEntries([...headers.matchAll(/^  ([\w-]+): (.+)$/gm)].map(([,k,v]) => [k,v]).filter(([k]) => k !== 'Content-Type'));
const types = { '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8', '.js':'text/javascript; charset=utf-8', '.svg':'image/svg+xml', '.sh':'text/plain; charset=utf-8' };
const port = Number(process.env.PORT || 4173);
createServer(async (req,res) => {
  const name = new URL(req.url, 'http://localhost').pathname.slice(1) || 'index.html';
  if (!files.has(name) || name.startsWith('_') || !['GET','HEAD'].includes(req.method)) { res.writeHead(404, shared); res.end(); return; }
  try {
    const body = await readFile(`dist/${name}`);
    res.writeHead(200, { ...shared, 'Content-Type':types[name.slice(name.lastIndexOf('.'))] || 'application/octet-stream' });
    res.end(req.method === 'HEAD' ? undefined : body);
  } catch { res.writeHead(404, shared); res.end(); }
}).listen(port, '127.0.0.1', () => console.log(`Skeptic preview: http://127.0.0.1:${port}`));
