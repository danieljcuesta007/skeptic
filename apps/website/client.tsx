import * as React from "react"
import { hydrateRoot } from "react-dom/client"
import { Masthead, LandingFooter } from "./landing"
for (const [id, Component] of [["landing-masthead", Masthead], ["landing-footer", LandingFooter]] as const) {
  const root = document.getElementById(id)
  if (root) hydrateRoot(root, <Component />)
}
