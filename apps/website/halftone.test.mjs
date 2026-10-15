import test from 'node:test';
import assert from 'node:assert/strict';
import { build } from 'esbuild';
import { readFile } from 'node:fs/promises';
import { createRequire } from 'node:module';
// Run the actual typed component helpers, without copying their implementation.
const compiled = await build({ entryPoints: ['components/ui/halftone-wordmark-footer.tsx'], bundle: true, platform: 'node', format: 'cjs', write: false, loader: { '.css': 'empty' } });
const mod = { exports: {} };
new Function('module', 'exports', 'require', compiled.outputFiles[0].text)(mod, mod.exports, createRequire(import.meta.url));
const { hwfHex, hwfRadius, hwfStep, hwfWarmth, hwfFitSize } = mod.exports;

test('dot coverage preserves area and clamps empty/full cells', () => {
  assert.equal(hwfRadius(-1, 6), 0);
  assert.equal(hwfRadius(2, 6), hwfRadius(1, 6));
  assert.ok(Math.abs(hwfRadius(0.25, 6) ** 2 / hwfRadius(1, 6) ** 2 - 0.25) < 1e-8);
});
test('pointer displaces dots and springs converge back to the exact home', () => {
  const pushed = hwfStep(10, 0, 0, 0, 10, 0, 0, 0, 80);
  assert.ok(pushed[0] > 10);
  let [x,y,vx,vy] = pushed;
  for (let i = 0; i < 240; i++) [x,y,vx,vy] = hwfStep(x,y,vx,vy,10,0,-1e5,-1e5,80);
  assert.ok(Math.abs(x - 10) + Math.abs(y) + Math.abs(vx) + Math.abs(vy) < 1e-6);
  assert.deepEqual(hwfStep(10,0,0,0,10,0,0,0,0), [10,0,0,0]);
});
test('mask sizing, colour parsing and warmth handle empty and displaced inputs', () => {
  assert.deepEqual(hwfHex('#abc'), [170,187,204]);
  assert.equal(hwfHex('transparent'), null);
  assert.equal(hwfFitSize(200, 1200), 600);
  assert.equal(hwfFitSize(0, 1200), 0);
  assert.equal(hwfWarmth(28,0,0,0,28), 1);
  assert.equal(hwfWarmth(0,0,0,0,28), 0);
});
test('landing is rendered without JavaScript, with correct landmarks and real links', async () => {
  const home = await readFile('dist/index.html','utf8');
  assert.match(home, /<section[^>]+skeptic-masthead/);
  assert.match(home, /<footer[^>]+skeptic-footer/);
  assert.equal((home.match(/<canvas/g) || []).length, 2);
  assert.match(home, /class="hwf-fallback" aria-hidden="true">skeptic/);
  assert.doesNotMatch(home, /halden|Oslo|Lisbon|href="#"|<style|\sstyle="/i);
  const compiledCss = await readFile('dist/landing.css','utf8');
  assert.match(compiledCss, /min-height:\s*44px/);
});

const lifecycleBundle = await build({ entryPoints: ['components/ui/halftone-wordmark-footer.tsx'], bundle: true, platform: 'node', format: 'cjs', write: false, external: ['react', 'react/jsx-runtime'], loader: { '.css': 'empty' } });
function mount({ reduced = false, interactive = true, crop = 0.2, scrollReveal = false } = {}) {
  const baselines = []; const properties = new Map(); let top = 100;
  const effects = [], frames = new Map(), listeners = new Map(), observers = [];
  let ref = 0, frameId = 0;
  const noop = () => {};
  const ctx = { setTransform:noop, fillRect:noop, fillText:(_word,_x,y)=>baselines.push(y), beginPath:noop, arc:noop, fill:noop, putImageData:noop,
    measureText:()=>({width:100, actualBoundingBoxAscent:10}),
    getImageData:()=>({data:new Uint8ClampedArray(30*30*4).fill(255)}), createImageData:()=>({data:new Uint8ClampedArray(256*256*4)}), createPattern:()=>null };
  const canvas = { getContext:()=>ctx, getBoundingClientRect:()=>({left:0,top:0}) };
  const callbacks = new Map();
  const target = prefix => ({
    addEventListener:(type,fn)=>{ const key=prefix+type; if(!callbacks.has(key)) callbacks.set(key,new Set()); callbacks.get(key).add(fn); listeners.set(key,event=>callbacks.get(key)?.forEach(f=>f(event))); },
    removeEventListener:(type,fn)=>{const key=prefix+type; callbacks.get(key)?.delete(fn); if(!callbacks.get(key)?.size) listeners.delete(key);}
  });
  const root = { ...target('root:'), style:{setProperty:(key,value)=>properties.set(key,value),removeProperty:key=>properties.delete(key)}, getBoundingClientRect:()=>({width:30,height:30,top}) };
  const motion = { ...target('motion:'), matches:reduced };
  const document = { ...target('doc:'), hidden:false, createElement:()=>({...canvas}) };
  const window = { ...target('window:'), innerHeight:100, matchMedia:()=>motion, devicePixelRatio:1 };
  const react = { ...createRequire(import.meta.url)('react'), useRef:value=>({current:ref++===0?root:ref===2?canvas:value}), useEffect:fn=>effects.push(fn) };
  const require = name => name === 'react' ? react : createRequire(import.meta.url)(name);
  class Observer { constructor(callback) { this.callback=callback; observers.push(this); } observe() {} disconnect() { this.disconnected=true; } }
  const module = { exports:{} };
  new Function('module','exports','require','window','document','ResizeObserver','IntersectionObserver','requestAnimationFrame','cancelAnimationFrame','performance', lifecycleBundle.outputFiles[0].text)(
    module,module.exports,require,window,document,Observer,Observer,fn=>{frames.set(++frameId,fn);return frameId;},id=>frames.delete(id),{now:()=>0});
  module.exports.default({interactive,grain:0,crop,scrollReveal});
  const cleanup = effects.map(fn=>fn()).filter(Boolean);
  const flush = now => { const pending=[...frames.values()];frames.clear();pending.forEach(fn=>fn(now)); };
  return {setTop:value=>{top=value},properties,baselines,frames,listeners,motion,document,observers,flush,unmount:()=>cleanup.forEach(fn=>fn())};
}
test('canvas sleeps at rest, ignores reduced-motion input, and releases listeners on unmount', () => {
  for (const options of [{reduced:true},{interactive:false}]) {
    const env = mount(options); env.flush(1000); assert.equal(env.frames.size,0);
    env.listeners.get('root:pointermove')({clientX:10,clientY:10,pointerType:'mouse'});
    env.listeners.get('root:pointerdown')({target:{closest:()=>null},clientX:10,clientY:10});
    assert.equal(env.frames.size,0,'disabled input does not start an animation');
    env.unmount(); assert.equal(env.listeners.size,0); assert.ok(env.observers.every(o=>o.disconnected));
  }
});
test('interactive canvas wakes, settles, responds to changed motion preferences and pauses offscreen', () => {
  const env = mount();env.flush(1000);assert.equal(env.frames.size,0);
  env.listeners.get('root:pointermove')({clientX:10,clientY:10,pointerType:'mouse'});
  assert.equal(env.frames.size,1);env.flush(1016);assert.equal(env.frames.size,1);
  env.listeners.get('root:pointerleave')();
  for(let i=0;i<300;i++) env.flush(1032+i*16);
  assert.equal(env.frames.size,0,'displaced dots settle and stop rendering');
  env.listeners.get('root:pointerdown')({target:{closest:()=>({})},clientX:10,clientY:10});
  assert.equal(env.frames.size,0,'links do not trigger shock rings');
  env.listeners.get('root:pointerdown')({target:{closest:()=>null},clientX:10,clientY:10});
  assert.equal(env.frames.size,1);
  env.motion.matches=true;env.listeners.get('motion:change')();env.flush(2000);assert.equal(env.frames.size,0);
  env.motion.matches=false;env.listeners.get('motion:change')();
  env.observers[1].callback([{isIntersecting:false}]);assert.equal(env.frames.size,0);
  env.observers[1].callback([{isIntersecting:true}]);assert.equal(env.frames.size,1);
  env.document.hidden=true;env.listeners.get('doc:visibilitychange')();assert.equal(env.frames.size,0);
  env.unmount();assert.equal(env.listeners.size,0);
});

test('negative crop lifts the baseline so lowercase descenders remain visible', () => {
  const env = mount({crop:-0.22});
  assert.ok(env.baselines.length > 0);
  assert.ok(env.baselines.every(y => y < 30), 'baseline must sit above the canvas bottom');
  env.unmount();
});

test('footer scroll reveal swallows on scroll up, coalesces work and respects reduced motion', () => {
  const env = mount({scrollReveal:true}); env.flush(1000);
  assert.equal(env.properties.get('--hwf-scroll-shift'),'9px');
  env.setTop(70); env.listeners.get('window:scroll')(); env.flush(1016);
  assert.equal(env.properties.get('--hwf-scroll-shift'),'0px');
  env.setTop(85); env.listeners.get('window:scroll')(); env.listeners.get('window:scroll')();
  assert.equal(env.frames.size,1,'one update for a burst of scroll events'); env.flush(1032);
  assert.equal(env.properties.get('--hwf-scroll-shift'),'4.5px','scrolling up pushes the wordmark below its clipping edge');
  env.motion.matches=true; env.listeners.get('motion:change')(); env.flush(1048);
  assert.equal(env.properties.get('--hwf-scroll-shift'),'0px','live reduced-motion setting removes scroll movement');
  env.unmount(); assert.equal(env.listeners.size,0); assert.equal(env.frames.size,0);
  assert.equal(env.properties.has('--hwf-scroll-shift'),false);
});
