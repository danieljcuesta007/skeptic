import * as React from "react"
import { renderToString } from "react-dom/server"
import { Masthead, LandingFooter } from "./landing"
export const masthead = renderToString(<Masthead />)
export const footer = renderToString(<LandingFooter />)
