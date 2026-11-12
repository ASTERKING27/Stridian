import { useEffect, useState } from 'react'
import { StyleSheet } from 'react-native'
import * as SplashScreen from 'expo-splash-screen'
import Svg, { Path } from 'react-native-svg'
import Animated, { Easing, makeMutable, runOnJS, useAnimatedProps, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated'
import { useTheme } from '../lib/theme'
import { buzz } from '../lib/haptics'
import { PATTERNS, launchWave } from '../lib/patterns'
import { LOGO_D } from './icons'

/* Launch (Launch board), picking up where the phone's splash leaves off — the logo, 120 px,
   in the middle. Sparks fly off it as it charges and shudders, it squashes, and fires:
   a runner-shaped window in the shape of the logo opens and races out until the app fills
   the screen, settling from 1.14× as the tab bar rises. With reduced motion the logo
   simply gives way to the app with a fade. Times are the board's, in ms from the icon
   tap; the splash covers the first 360. */

const T_START = 360, T_CHG = 820, T_SQ = 1380, T_IG = 1520, T_ZEND = 2420, T_END = 2800
const AX = 47.6, AY = 49.4                    // where the window opens from, in the logo
const K0 = 1.2 * 0.9, K1 = 120                // the window's scale, from the squashed logo to past the screen
const AnimatedPath = Animated.createAnimatedComponent(Path)

// The launch clock. At rest it reads the end, so the tab bar and the app sit where they belong.
export const launchClock = makeMutable(T_END)

const cl = v => { 'worklet'; return v < 0 ? 0 : v > 1 ? 1 : v }
const lerp = (a, b, t) => { 'worklet'; return a + (b - a) * t }
const eIO = t => { 'worklet'; return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2 }
const eOut = t => { 'worklet'; return 1 - Math.pow(1 - t, 3) }

// the logo's two outlines as point lists (it is straight lines only)
const POLYS = LOGO_D.split('M').filter(Boolean).map(sub => sub.replace('Z', '').split('L').map(p => p.trim().split(' ').map(Number)))
const outline = (sx, sy, k, ax, ay) => {
  'worklet'
  let d = ''
  for (const poly of POLYS) {
    for (let i = 0; i < poly.length; i++) d += `${i ? 'L' : 'M'}${(sx + k * (poly[i][0] - ax)).toFixed(1)} ${(sy + k * (poly[i][1] - ay)).toFixed(1)}`
    d += 'Z'
  }
  return d
}

// The sparks: along the logo's spine while it charges, then a ring of them at ignition.
const SKEL = [[88.8, 26.4], [83.9, 10.7], [27.1, 18.6], [18.3, 46.0], [77.0, 52.8], [28.5, 88.7], [3.0, 78.5]]
function rng(seed) {
  return () => {
    seed |= 0; seed = (seed + 0x6d2b79f5) | 0
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed)
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296
  }
}
function makeSparks() {
  const R = rng(11)
  const segs = []
  let total = 0
  for (let i = 0; i < SKEL.length - 1; i++) {
    const [x1, y1] = SKEL[i], [x2, y2] = SKEL[i + 1]
    const len = Math.hypot(x2 - x1, y2 - y1)
    segs.push({ x1, y1, x2, y2, len, at: total })
    total += len
  }
  const out = []
  for (let i = 0; i < 46; i++) {
    const d = R() * total
    const s = segs.find(g => d >= g.at && d <= g.at + g.len) ?? segs[segs.length - 1]
    const f = (d - s.at) / s.len
    const px = s.x1 + (s.x2 - s.x1) * f, py = s.y1 + (s.y2 - s.y1) * f
    const a = Math.atan2(py - 50, px - 50) + (R() - 0.5)
    const dot = R() < 0.22
    out.push({ ox: (px - 50) * 1.2, oy: (py - 50) * 1.2, a, dist: 44 + R() * 120, birth: 400 + (i / 46) * 900 + R() * 60,
               life: 440 + R() * 340, len: dot ? 3 : 7 + R() * 11, h: dot ? 3 : R() < 0.3 ? 3 : 2, dot })
  }
  for (let i = 0; i < 24; i++) {
    const a = R() * Math.PI * 2
    out.push({ ox: (R() - 0.5) * 30, oy: (R() - 0.5) * 30, a, dist: 170 + R() * 230, birth: T_IG + R() * 60,
               life: 480 + R() * 280, len: 16 + R() * 18, h: 2.5, dot: false })
  }
  return out
}
const SPARKS = makeSparks()
// its haptics, a ms at a time from T_START: a tick per spark, the dive's buzz, the dot as it lands
const WAVE = launchWave(SPARKS.map(s => s.birth - T_START), T_IG - T_START, T_ZEND - T_START)

export default function Launch() {
  const { c, reduced } = useTheme()
  const [{ W, H }, setSize] = useState({ W: 0, H: 0 })      // the whole screen, edge to edge
  const [done, setDone] = useState(false)
  const fade = useSharedValue(1)
  const t = launchClock
  const CX = W / 2, CY = H / 2

  useEffect(() => {
    SplashScreen.hideAsync().catch(() => {})
    const end = () => { 'worklet'; runOnJS(setDone)(true) }
    if (reduced) {                 // the logo holds a moment, then the app fades in under it
      t.value = T_END
      fade.value = withDelay(400, withTiming(0, { duration: 200 }, end))
      return
    }
    buzz(WAVE, PATTERNS.launch.fallback)
    t.value = T_START
    t.value = withTiming(T_END, { duration: T_END - T_START, easing: Easing.linear }, end)
  }, [])

  // the paper over the app, with the runner-shaped window cut out of it
  const veil = useAnimatedProps(() => {
    let d = `M0 0H${W}V${H}H0Z`
    if (t.value >= T_IG && !reduced) {
      const z = cl((t.value - T_IG) / (T_ZEND - T_IG))
      const k = K0 * Math.pow(K1 / K0, z * z)
      const e = eOut(z)
      d += outline(lerp(CX + (AX - 50) * K0, CX, e), lerp(CY + (AY - 50) * K0, CY, e), k, AX, AY)
    }
    return { d: d || 'M0 0' }
  })
  // the window's rim and its two echoes
  const useRim = m => useAnimatedProps(() => {
    if (t.value < T_IG || reduced) return { d: 'M0 0', strokeWidth: 0, opacity: 0 }
    const z = cl((t.value - T_IG) / (T_ZEND - T_IG))
    const k = K0 * Math.pow(K1 / K0, z * z) * m
    const e = eOut(z)
    return { d: outline(lerp(CX + (AX - 50) * K0, CX, e), lerp(CY + (AY - 50) * K0, CY, e), k, AX, AY),
             strokeWidth: m === 1 ? lerp(2.5, 7, z) : m < 1.2 ? 2 : 1,
             opacity: m === 1 ? 1 : (m < 1.2 ? 0.55 : 0.28) * (1 - z * 0.4) }
  })
  const ring = useRim(1), echo1 = useRim(1.12), echo2 = useRim(1.28)
  // the logo itself: charging (a 6% swell and a shudder), squashing, gone at ignition
  const logo = useAnimatedProps(() => {
    const now = t.value
    if (now >= T_IG && !reduced) return { d: 'M0 0' }
    let m = 1, jx = 0, jy = 0
    if (now >= T_CHG && now < T_SQ) m = 1 + 0.06 * eOut((now - T_CHG) / (T_SQ - T_CHG))
    if (now >= T_SQ) m = lerp(1.06, 0.9, eIO(cl((now - T_SQ) / (T_IG - T_SQ))))
    if (now >= T_CHG && now < T_IG) {
      const a = 0.9 * cl((now - T_CHG) / (T_SQ - T_CHG))
      jx = a * Math.sin(now * 0.09); jy = a * Math.cos(now * 0.117)
    }
    const s = reduced ? 1.2 : 1.2 * m
    return { d: outline(CX + jx, CY + jy, s, 50, 50) }
  })
  // every spark alive now, as one shape: a kite pointing where it flies (dots are squares)
  const sparks = useAnimatedProps(() => {
    let d = ''
    const now = t.value
    if (reduced || now > T_END) return { d: d || 'M0 0' }
    for (const s of SPARKS) {
      const u = (now - s.birth) / s.life
      if (u < 0 || u > 1) continue
      const fly = s.dist * eOut(u)
      const o = u < 0.6 ? 1 : 1 - (u - 0.6) / 0.4                // fading out: shrinking with it
      const x = CX + s.ox + Math.cos(s.a) * fly, y = CY + s.oy + Math.sin(s.a) * fly
      const w = (s.dot ? s.len : s.len * (1 - 0.55 * u)) * o, h = s.h * o
      const ca = Math.cos(s.a), sa = Math.sin(s.a)
      const pt = (lx, ly) => `${(x + lx * ca - ly * sa).toFixed(1)} ${(y + lx * sa + ly * ca).toFixed(1)}`
      d += s.dot ? `M${pt(-w / 2, -h / 2)}L${pt(w / 2, -h / 2)}L${pt(w / 2, h / 2)}L${pt(-w / 2, h / 2)}Z`
        : `M${pt(-w / 2, 0)}L${pt(0.2 * w, -h / 2)}L${pt(w / 2, 0)}L${pt(0.2 * w, h / 2)}Z`
    }
    return { d: d || 'M0 0' }
  })
  const whole = useAnimatedStyle(() => ({ opacity: fade.value }))

  if (done) return null
  return (
    <Animated.View pointerEvents="none" onLayout={e => setSize({ W: e.nativeEvent.layout.width, H: e.nativeEvent.layout.height })}
                   style={[StyleSheet.absoluteFill, { zIndex: 100, backgroundColor: W ? 'transparent' : c.bg }, whole]}>
      {W > 0 && <Svg width={W} height={H}>
        <AnimatedPath animatedProps={veil} fill={c.bg} fillRule="evenodd" />
        <AnimatedPath animatedProps={echo2} fill="none" stroke={c.ink} strokeLinejoin="miter" strokeMiterlimit={12} />
        <AnimatedPath animatedProps={echo1} fill="none" stroke={c.ink} strokeLinejoin="miter" strokeMiterlimit={12} />
        <AnimatedPath animatedProps={ring} fill="none" stroke={c.ink} strokeLinejoin="miter" strokeMiterlimit={12} />
        <AnimatedPath animatedProps={logo} fill={c.ink} />
        <AnimatedPath animatedProps={sparks} fill={c.ink} />
      </Svg>}
    </Animated.View>
  )
}

/* The app under the launch: 1.14× until the window opens, settling to 1× (2650 ms). */
export function useLaunchScale() {
  return useAnimatedStyle(() => {
    const now = launchClock.value
    if (now >= T_END) return { transform: [{ scale: 1 }] }
    return { transform: [{ scale: now < T_IG ? 1.14 : lerp(1.14, 1, eOut(cl((now - T_IG) / (2650 - T_IG)))) }] }
  })
}
// The tab bar under the launch: below the screen until 2200 ms, rising over 520.
export function useLaunchBar() {
  return useAnimatedStyle(() => {
    const now = launchClock.value
    return { transform: [{ translateY: now < 2200 ? 100 : lerp(100, 0, eOut(cl((now - 2200) / 520))) }] }
  })
}
