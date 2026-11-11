/* GSAP, set up once for the whole site. Motion here answers something the visitor did
   (scrolled, pointed, arrived) and nothing moves for anyone who asked for less. */
import { gsap } from 'gsap'
import { useGSAP } from '@gsap/react'
import { CustomEase } from 'gsap/CustomEase'
import { DrawSVGPlugin } from 'gsap/DrawSVGPlugin'
import { ScrambleTextPlugin } from 'gsap/ScrambleTextPlugin'
import { ScrollTrigger } from 'gsap/ScrollTrigger'
import { SplitText } from 'gsap/SplitText'

gsap.registerPlugin(useGSAP, CustomEase, DrawSVGPlugin, ScrambleTextPlugin, ScrollTrigger, SplitText)

// the house curves: `out` settles quickly, `io` is the slow-fast-slow of a wipe
CustomEase.create('out', '.2,.8,.2,1')
CustomEase.create('io', '.65,0,.15,1')
gsap.defaults({ ease: 'out', duration: 0.8 })
// a section that isn't on this page (a court with no spots, say) is not a mistake
gsap.config({ nullTargetWarn: false })

export const calm = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
export const MOTION = '(prefers-reduced-motion: no-preference)'
// room for a whole scene to hold still on screen while it plays
export const DESKTOP = '(min-width: 1081px) and (min-height: 800px)'
export const COMPACT = '(max-width: 1080px), (max-height: 799px)'
export const SCRAMBLE = '0123456789'

export { gsap, useGSAP, ScrollTrigger, SplitText }
