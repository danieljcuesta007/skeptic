import * as React from "react"
import HalftoneWordmarkFooter from "@/components/ui/halftone-wordmark-footer"

const brand = { background: "#0b0b0b", ink: "#f7f7f7", warm: "#8c8c8c" }
export function Masthead() {
  return <HalftoneWordmarkFooter scrollReveal as="section" wordmark="skeptic" label="Your work. Your memory. Any AI."
    meta="Not everything is black and white." palette={brand} crop={-0.1} dotGap={5} grain={0.5}
    height="clamp(300px,39vw,630px)" className="skeptic-masthead" backToTop={false}
    columns={[{ title: "Start here", links: [{ label: "Install Skeptic ↗", href: "#install" }] }]} />
}
export function LandingFooter() {
  return <HalftoneWordmarkFooter wordmark="skeptic" label="Skeptic / DC Labs" meta="© 2026 · Built by Daniel Cuesta"
    palette={brand} fontWeight={800} crop={-0.1} dotGap={5} height="clamp(560px,43vw,680px)" className="skeptic-footer"
    columns={[
      { title: "Product", links: [{ label: "How it works", href: "#how" }, { label: "Compare", href: "guide.html#compare" }, { label: "Install", href: "#install" }] },
      { title: "Project", links: [{ label: "Creator", href: "#creator" }, { label: "Source", href: "https://github.com/danieljcuesta007/skeptic" }, { label: "Privacy & legal", href: "legal.html" }] },
    ]} />
}
