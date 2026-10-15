"use client"

import * as React from "react"
import "./halftone-wordmark-footer.css"

export interface HalftonePalette { background: string; ink: string; warm: string }
export type HalftonePreset = "night" | "paper" | "ember" | "cobalt"
export interface FooterLink { label: string; href?: string }
export interface FooterColumn { title: string; links: FooterLink[] }
export interface HalftoneWordmarkFooterProps {
  wordmark?: string; label?: string; meta?: string; columns?: FooterColumn[];
  scrollReveal?: boolean; backToTop?: boolean; preset?: HalftonePreset; palette?: Partial<HalftonePalette>;
  dotGap?: number; radius?: number; crop?: number; grain?: number; interactive?: boolean;
  fontFamily?: string; fontWeight?: number; monoFamily?: string; height?: string; className?: string;
  /** Use a section when the wordmark introduces a page. The default is a footer. */
  as?: "footer" | "section";
}
const PRESETS: Record<HalftonePreset, HalftonePalette> = {
  night: { background: "#0c0c0b", ink: "#e9e4da", warm: "#e9762b" },
  paper: { background: "#efebe3", ink: "#17150f", warm: "#c2361c" },
  ember: { background: "#160a06", ink: "#f2c48c", warm: "#ff5a1f" },
  cobalt: { background: "#0d1b4d", ink: "#dfe7ff", warm: "#ffcd3c" },
}
const DEFAULT_COLUMNS: FooterColumn[] = [
  { title: "Work", links: [{ label: "Index" }, { label: "Archive" }, { label: "Journal" }] },
  { title: "Studio", links: [{ label: "About" }, { label: "Process" }, { label: "Careers" }] },
  { title: "Contact", links: [{ label: "hello@halden.co" }, { label: "+47 22 00 41 00" }] },
]
const SANS_STACK = '"Inter Tight", "Inter Variable", "Inter", "Helvetica Neue", Arial, system-ui, sans-serif'
const MONO_STACK = '"JetBrains Mono", "SF Mono", ui-monospace, Menlo, Consolas, monospace'

export function hwfHex(hex: string) {
  const m = /^#?([0-9a-f]{3}|[0-9a-f]{6})$/i.exec((hex || "").trim())
  if (!m) return null
  const h = m[1].length === 3 ? m[1].split("").map(c => c + c).join("") : m[1]
  return [parseInt(h.slice(0, 2), 16), parseInt(h.slice(2, 4), 16), parseInt(h.slice(4, 6), 16)]
}
export function hwfRadius(coverage: number, gap: number) {
  const c = coverage < 0 ? 0 : coverage > 1 ? 1 : coverage
  return Math.sqrt(c) * gap * 0.56
}
export function hwfStep(x: number, y: number, vx: number, vy: number, hx: number, hy: number, px: number, py: number, r: number) {
  const dx = x - px, dy = y - py, d2 = dx * dx + dy * dy
  if (r > 0 && d2 < r * r) {
    const d = Math.sqrt(d2) + 0.001, f = (1 - d / r) * 2.6
    vx += (dx / d) * f; vy += (dy / d) * f
  }
  vx = (vx + (hx - x) * 0.05) * 0.84
  vy = (vy + (hy - y) * 0.05) * 0.84
  return [x + vx, y + vy, vx, vy]
}
export function hwfWarmth(x: number, y: number, hx: number, hy: number, span: number) {
  const d = Math.hypot(x - hx, y - hy)
  return span > 0 ? Math.min(1, d / span) : 0
}
export function hwfFitSize(measured: number, width: number) {
  return measured > 0 ? (width / measured) * 100 : 0
}

export default function HalftoneWordmarkFooter({
  wordmark = "halden", label = "Halden Studio", meta = "©2026 · Oslo / Lisbon", columns = DEFAULT_COLUMNS,
  scrollReveal = false, backToTop = true, preset = "night", palette, dotGap = 6, radius = 80, crop = 0.2, grain = 0.5,
  interactive = true, fontFamily = SANS_STACK, fontWeight = 800, monoFamily = MONO_STACK,
  height = "560px", className = "", as: Tag = "footer",
}: HalftoneWordmarkFooterProps) {
  const colors = { ...PRESETS[preset], ...palette }
  const rootRef = React.useRef<HTMLElement | null>(null)
  const canvasRef = React.useRef<HTMLCanvasElement | null>(null)
  const opts = React.useRef({ colors, dotGap, radius, crop, grain, interactive, fontFamily, fontWeight, wordmark })
  opts.current = { colors, dotGap, radius, crop, grain, interactive, fontFamily, fontWeight, wordmark }
  const key = [wordmark, dotGap, crop, grain, fontFamily, fontWeight, colors.background, colors.ink, colors.warm].join("|")

  // External CSS and CSSOM properties preserve the site's strict self-only CSP.
  React.useEffect(() => {
    const root = rootRef.current
    if (!root) return
    root.style.height = height
    root.style.setProperty("--hwf-bg", colors.background)
    root.style.setProperty("--hwf-ink", colors.ink)
    root.style.setProperty("--hwf-mono", monoFamily)
  }, [height, colors.background, colors.ink, monoFamily])

  // The footer wordmark rises out of its clipped lower edge as the footer enters.
  React.useEffect(() => {
    const root = rootRef.current
    if (!root || !scrollReveal) return
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)")
    let frame = 0
    const update = () => {
      frame = 0
      const rect = root.getBoundingClientRect()
      const progress = Math.max(0, Math.min(1, (window.innerHeight - rect.top) / Math.max(1, rect.height)))
      const shift = motion.matches ? 0 : (1 - progress) * Math.min(rect.width * 0.3, rect.height * 0.8)
      root.style.setProperty("--hwf-scroll-shift", shift + "px")
    }
    const schedule = () => { if (!frame) frame = requestAnimationFrame(update) }
    update()
    window.addEventListener("scroll", schedule, { passive: true })
    window.addEventListener("resize", schedule)
    motion.addEventListener("change", schedule)
    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener("scroll", schedule)
      window.removeEventListener("resize", schedule)
      motion.removeEventListener("change", schedule)
      root.style.removeProperty("--hwf-scroll-shift")
    }
  }, [scrollReveal])

  React.useEffect(() => {
    const root = rootRef.current, canvas = canvasRef.current
    if (!root || !canvas) return
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    const motion = window.matchMedia("(prefers-reduced-motion: reduce)")
    let reduced = motion.matches
    let w = 0, h = 0, dpr = 1, px = -1e5, py = -1e5, raf = 0
    let visible = true, awake = true, alive = true
    let ring = { x: 0, y: 0, t: -1 }
    let dots = new Float32Array(0), count = 0
    let grainTile: HTMLCanvasElement | null = null
    const ink = hwfHex(opts.current.colors.ink) || [233, 228, 218]
    const warm = hwfHex(opts.current.colors.warm) || [233, 118, 43]
    const layout = () => {
      const o = opts.current, rect = root.getBoundingClientRect()
      w = Math.max(1, Math.round(rect.width)); h = Math.max(1, Math.round(rect.height))
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      canvas.width = Math.round(w * dpr); canvas.height = Math.round(h * dpr)
      const mask = document.createElement("canvas")
      mask.width = w; mask.height = h
      const m = mask.getContext("2d", { willReadFrequently: true })
      if (!m) return
      m.font = o.fontWeight + " 100px " + o.fontFamily
      const word = o.wordmark || " ", fit = hwfFitSize(m.measureText(word).width, w * 1.02)
      m.font = o.fontWeight + " " + fit + "px " + o.fontFamily
      const box = m.measureText(word), cap = box.actualBoundingBoxAscent || fit * 0.72
      m.fillStyle = "#000"; m.textBaseline = "alphabetic"
      m.fillText(word, (w - box.width) / 2, h + cap * Math.max(-0.4, Math.min(0.6, o.crop)))
      const img = m.getImageData(0, 0, w, h).data, gap = Math.max(3, o.dotGap)
      const tmp: number[] = []
      for (let gy = 0; gy < Math.ceil(h / gap); gy++) {
        for (let gx = 0; gx < Math.ceil(w / gap); gx++) {
          let sum = 0
          for (let sy = 0; sy < 3; sy++) for (let sx = 0; sx < 3; sx++) {
            const x = Math.min(w - 1, Math.floor(gx * gap + ((sx + 0.5) * gap) / 3))
            const y = Math.min(h - 1, Math.floor(gy * gap + ((sy + 0.5) * gap) / 3))
            sum += img[(y * w + x) * 4 + 3]
          }
          const cov = sum / (9 * 255)
          if (cov < 0.06) continue
          const hx = gx * gap + gap / 2, hy = gy * gap + gap / 2
          tmp.push(hx, hy, 0, 0, hx, hy, hwfRadius(cov, gap))
        }
      }
      dots = new Float32Array(tmp); count = tmp.length / 7
      grainTile = document.createElement("canvas"); grainTile.width = 256; grainTile.height = 256
      const g = grainTile.getContext("2d")
      if (g) {
        const id = g.createImageData(256, 256)
        for (let i = 0; i < id.data.length; i += 4) {
          id.data[i] = id.data[i + 1] = id.data[i + 2] = Math.random() * 255
          id.data[i + 3] = Math.random() < 0.5 ? 0 : 255
        }
        g.putImageData(id, 0, 0)
      }
      awake = true
    }
    const draw = (now: number) => {
      const o = opts.current
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); ctx.fillStyle = o.colors.background; ctx.fillRect(0, 0, w, h)
      const r = o.interactive && !reduced ? Math.max(0, o.radius) : 0
      const ringAge = ring.t < 0 ? 1e9 : now - ring.t, ringR = ringAge * 0.9
      let moving = false
      for (let i = 0; i < count; i++) {
        const j = i * 7
        let x = dots[j], y = dots[j + 1], vx = dots[j + 2], vy = dots[j + 3]
        const hx = dots[j + 4], hy = dots[j + 5]
        if (!reduced) {
          if (o.interactive && ringAge < 900) {
            const dx = hx - ring.x, dy = hy - ring.y, d = Math.sqrt(dx * dx + dy * dy) + 0.001
            const band = 1 - Math.min(1, Math.abs(d - ringR) / 26)
            if (band > 0) {
              const f = band * 3.2 * (1 - ringAge / 900)
              vx += (dx / d) * f; vy += (dy / d) * f
            }
          }
          ;[x, y, vx, vy] = hwfStep(x, y, vx, vy, hx, hy, px, py, r)
          if (Math.abs(vx) + Math.abs(vy) > 0.02 || Math.abs(x - hx) + Math.abs(y - hy) > 0.05) moving = true
          else { x = hx; y = hy; vx = 0; vy = 0 }
        } else { x = hx; y = hy; vx = 0; vy = 0 }
        dots[j] = x; dots[j + 1] = y; dots[j + 2] = vx; dots[j + 3] = vy
        const k = hwfWarmth(x, y, hx, hy, 28)
        ctx.fillStyle = k > 0.02 ? `rgb(${Math.round(ink[0] + (warm[0] - ink[0]) * k)},${Math.round(ink[1] + (warm[1] - ink[1]) * k)},${Math.round(ink[2] + (warm[2] - ink[2]) * k)})` : o.colors.ink
        ctx.beginPath(); ctx.arc(x, y, dots[j + 6], 0, 6.2832); ctx.fill()
      }
      if (grainTile && o.grain > 0) {
        ctx.globalAlpha = Math.min(1, o.grain) * 0.09; ctx.globalCompositeOperation = "overlay"
        const pattern = ctx.createPattern(grainTile, "repeat")
        if (pattern) { ctx.fillStyle = pattern; ctx.fillRect(0, 0, w, h) }
        ctx.globalAlpha = 1; ctx.globalCompositeOperation = "source-over"
      }
      awake = !reduced && (moving || (o.interactive && (ringAge < 900 || px > -1e4)))
    }
    const loop = (now: number) => {
      raf = 0
      if (!visible || document.hidden) return
      draw(now)
      if (awake) raf = requestAnimationFrame(loop)
    }
    const wake = () => { awake = true; if (!raf && visible && !document.hidden) raf = requestAnimationFrame(loop) }
    const toLocal = (e: PointerEvent) => { const b = canvas.getBoundingClientRect(); return [e.clientX - b.left, e.clientY - b.top] }
    const onMove = (e: PointerEvent) => {
      if (!opts.current.interactive || reduced || e.pointerType === "touch") return
      ;[px, py] = toLocal(e); wake()
    }
    const onLeave = () => { px = -1e5; py = -1e5; wake() }
    const onDown = (e: PointerEvent) => {
      if (!opts.current.interactive || reduced || (e.target as HTMLElement).closest("a,button")) return
      const [x, y] = toLocal(e); ring = { x, y, t: performance.now() }; wake()
    }
    const onMotion = () => { reduced = motion.matches; px = -1e5; py = -1e5; ring.t = -1; wake() }
    const onVisibility = () => { if (document.hidden) { cancelAnimationFrame(raf); raf = 0; px = -1e5; py = -1e5 } else wake() }
    layout(); draw(performance.now()); wake()
    root.addEventListener("pointermove", onMove); root.addEventListener("pointerleave", onLeave); root.addEventListener("pointerdown", onDown)
    motion.addEventListener("change", onMotion); document.addEventListener("visibilitychange", onVisibility)
    const ro = new ResizeObserver(() => { layout(); wake() }); ro.observe(root)
    const io = new IntersectionObserver(entries => {
      visible = entries[0]?.isIntersecting ?? true
      if (visible) wake()
      else { cancelAnimationFrame(raf); raf = 0; px = -1e5; py = -1e5 }
    }); io.observe(root)
    document.fonts?.ready.then(() => { if (alive) { layout(); wake() } })
    return () => {
      alive = false; cancelAnimationFrame(raf); ro.disconnect(); io.disconnect()
      root.removeEventListener("pointermove", onMove); root.removeEventListener("pointerleave", onLeave); root.removeEventListener("pointerdown", onDown)
      motion.removeEventListener("change", onMotion); document.removeEventListener("visibilitychange", onVisibility)
    }
  }, [key])
  const toTop = () => window.scrollTo({ top: 0, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "instant" : "smooth" })
  return (
    <Tag ref={rootRef} className={"hwf-root " + className} aria-label={Tag === "section" ? label : undefined}>
      <canvas ref={canvasRef} aria-hidden="true" />
      <span className="hwf-fallback" aria-hidden="true">{wordmark}</span>
      <span className="hwf-sr">{wordmark}</span>
      <div className="hwf-top">
        <div className="hwf-brand"><strong>{label}</strong><span>{meta}</span></div>
        {columns.map(col => <nav className="hwf-col" key={col.title} aria-label={col.title}>
          <h3>{col.title}</h3><ul>{col.links.map(l => <li key={l.label}><a href={l.href || "#"}>{l.label}</a></li>)}</ul>
        </nav>)}
      </div>
      <div className="hwf-rule">{backToTop ? <button type="button" className="hwf-up" onClick={toTop}>Back to top ↑</button> : null}</div>
    </Tag>
  )
}
