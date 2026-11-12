import { View } from 'react-native'
import Svg, { Path } from 'react-native-svg'
import Animated, { Easing, useAnimatedProps, useAnimatedStyle } from 'react-native-reanimated'

const AnimatedPath = Animated.createAnimatedComponent(Path)

/* The design's sweep (TabSwitch and Achievement boards): ink lines cross on a 50° slant
   and what's new is uncovered behind the leading one. `p` runs 0 → 1, linearly.

   The uncovering is a half-plane: a huge box turned 50° with overflow hidden, its content
   turned back, so only what lies on one side of the leading line shows. At rest every
   transform is the identity, so content draws exactly as it would unwrapped — and the
   wrapping never changes, so nothing inside is ever remounted by a sweep. */

export const SWEEP_MS = 820
const PHI = (50 * Math.PI) / 180
const NX = Math.cos(PHI), NY = Math.sin(PHI), UX = -Math.sin(PHI), UY = Math.cos(PHI)
// the tab change's six lines, and the level card's four
export const TAB_LINES = { maxlag: 0.175, ease: Easing.bezierFn(0.4, 0.3, 0.2, 1), lines: [
  { th: 18, off: 0, a: 0.02, b: 0.98, lag: 0 }, { th: 15, off: 30, a: 0.16, b: 0.88, lag: 0.035 },
  { th: 13, off: 57, a: 0.07, b: 0.7, lag: 0.07 }, { th: 12, off: 82, a: 0.3, b: 0.96, lag: 0.105 },
  { th: 10, off: 104, a: 0.12, b: 0.62, lag: 0.14 }, { th: 8, off: 124, a: 0.42, b: 0.86, lag: 0.175 }] }
export const CARD_LINES = { maxlag: 0.12, lines: [
  { th: 14, off: 0, a: 0.02, b: 0.98, lag: 0 }, { th: 12, off: 24, a: 0.15, b: 0.85, lag: 0.04 },
  { th: 10, off: 44, a: 0.06, b: 0.68, lag: 0.08 }, { th: 8, off: 62, a: 0.35, b: 0.95, lag: 0.12 }] }

const ID3 = [{ translateX: 0 }, { translateY: 0 }, { rotate: '0deg' }]
const ID5 = [...ID3, { translateX: 0 }, { translateY: 0 }]
export const cl = v => { 'worklet'; return v < 0 ? 0 : v > 1 ? 1 : v }
export const eIO = t => { 'worklet'; return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2 }
export const eOut = t => { 'worklet'; return 1 - Math.pow(1 - t, 3) }
/* how far a line has swept (distance along the slant), and its eased progress. The level
   card eases in and out; a tab change can't wait that long to show it heard the tap (eased
   in, the line is still off the screen 100 ms in), so its curve gets going at once. */
const sweep = (tau, L, set, w, h) => {
  'worklet'
  const ti = cl((tau - L.lag) / (1 - set.maxlag))
  const e = (set.ease ?? eIO)(ti)
  return { ti, e, c: -20 - L.off + (w * NX + h * NY + 40 + L.off) * e }
}

/* Content uncovered by a sweep. side: 'behind' shows what the leading line has passed
   (coming in), 'ahead' what it hasn't reached yet (going away), null: all of it — or a
   shared value holding one, so it can change in the same frame as `p`. Until it's measured
   (w) a masked sweep shows nothing, so it can't flash before it starts. drift:
   px the content moves along the slant — in from up-left while uncovered, away down-right
   (positive) otherwise. autoHeight: the content sets its own height (measure it, pass h). */
export function SweepMask({ p, w, h, side, drift = 0, set = TAB_LINES, autoHeight, style, children }) {
  const S = 2 * (w + h)
  const outer = useAnimatedStyle(() => {
    const s = side && typeof side === 'object' ? side.value : side
    if (!s || !w) return { opacity: s ? 0 : 1, transform: ID3 }
    const { c } = sweep(p.value, set.lines[0], set, w, h)
    const n = s === 'behind' ? c - S : c                      // where the visible strip starts, along the slant
    return { opacity: 1, transform: [{ translateX: n * NX - (S / 2) * UX }, { translateY: n * NY - (S / 2) * UY }, { rotate: '50deg' }] }
  }, [side, w, h, set])
  const inner = useAnimatedStyle(() => {
    const s = side && typeof side === 'object' ? side.value : side
    if (!w || (!s && !drift)) return { transform: ID5 }
    const { e, c } = sweep(p.value, set.lines[0], set, w, h)
    const d = s === 'behind' ? drift * (1 - e) : drift * e
    if (!s) return { transform: [{ translateX: NX * d }, { translateY: NY * d }, { rotate: '0deg' }, { translateX: 0 }, { translateY: 0 }] }
    return { transform: [{ translateX: s === 'behind' ? S - c : -c }, { translateY: S / 2 }, { rotate: '-50deg' },
                         { translateX: NX * d }, { translateY: NY * d }] }
  }, [side, drift, w, h, set])
  return (
    <View style={[{ overflow: 'hidden' }, style]}>
      <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: w ? S : '100%', height: w ? S : '100%',
                               overflow: 'hidden', transformOrigin: 'left top' }, outer]}>
        <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: w || '100%', height: autoHeight ? undefined : h || '100%',
                                 transformOrigin: 'left top' }, inner]}>
          {children}
        </Animated.View>
      </Animated.View>
    </View>
  )
}

/* One tab's page. Whether it shows, comes in or goes out is worked out on the UI thread
   from `cur` (the tab chosen), `from` (the one being left) and `p` — so a sweep starts the
   moment those are set, however busy React is, and a page can never show before its
   sweep does. Coming in, it's uncovered behind the leading line; going out it's covered
   ahead of it (and dims), so the two never overlap and their order doesn't matter. With
   reduced motion the new tab fades in over 150 ms. `live`: it's the chosen tab (touches,
   screen readers). */
const roleOf = (i, cur, from, p) => {
  'worklet'
  if (i === cur) return from >= 0 && from !== cur && p < 1 ? 1 : 0          // 1 coming in, 0 showing
  return i === from && p < 1 ? 2 : 3                                        // 2 going out, 3 hidden
}
export function TabLayer({ i, cur, from, p, w, h, reduced, dim = 0.12, live, children }) {
  const S = 2 * (w + h)
  const L0 = TAB_LINES.lines[0]
  const outer = useAnimatedStyle(() => {
    const r = roleOf(i, cur.value, from.value, p.value)
    if (r === 3 || (r === 2 && reduced)) return { opacity: 0, transform: ID3 }
    if (r === 0 || !w) return { opacity: 1, transform: ID3 }
    if (reduced) return { opacity: p.value, transform: ID3 }
    const { c } = sweep(p.value, L0, TAB_LINES, w, h)
    const n = r === 1 ? c - S : c
    return { opacity: 1, transform: [{ translateX: n * NX - (S / 2) * UX }, { translateY: n * NY - (S / 2) * UY }, { rotate: '50deg' }] }
  }, [i, reduced, w, h])
  const inner = useAnimatedStyle(() => {
    const r = roleOf(i, cur.value, from.value, p.value)
    if (reduced || !w || r === 0 || r === 3) return { transform: ID5 }
    const { e, c } = sweep(p.value, L0, TAB_LINES, w, h)
    const d = r === 1 ? -40 * (1 - e) : 26 * e                // in from up-left, away down-right
    return { transform: [{ translateX: r === 1 ? S - c : -c }, { translateY: S / 2 }, { rotate: '-50deg' }, { translateX: NX * d }, { translateY: NY * d }] }
  }, [i, reduced, w, h])
  const shade = useAnimatedStyle(() => {
    const r = roleOf(i, cur.value, from.value, p.value)
    if (r !== 2 || reduced || !w) return { opacity: 0 }
    return { opacity: dim * sweep(p.value, L0, TAB_LINES, w, h).e }
  }, [i, reduced, w, h, dim])
  return (
    <View pointerEvents={live ? 'auto' : 'none'} importantForAccessibility={live ? 'auto' : 'no-hide-descendants'}
          accessibilityElementsHidden={!live} style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, overflow: 'hidden' }}>
      <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: w ? S : '100%', height: w ? S : '100%',
                               overflow: 'hidden', transformOrigin: 'left top' }, outer]}>
        <Animated.View style={[{ position: 'absolute', left: 0, top: 0, width: w || '100%', height: h || '100%',
                                 transformOrigin: 'left top' }, inner]}>
          {children}
          <Animated.View pointerEvents="none" style={[{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, backgroundColor: '#000' }, shade]} />
        </Animated.View>
      </Animated.View>
    </View>
  )
}

/* The lines, over what's being swept, while `p` runs (hidden at 0 and 1). Drawn as round-
   capped strokes, so only their ends move each frame. `shadow`: a soft offset copy under
   each line, for depth on paper. */
export function SweepLines({ p, w, h, color, shadow, set = TAB_LINES }) {
  return (
    <Svg pointerEvents="none" width={w} height={h} style={{ position: 'absolute', left: 0, top: 0, zIndex: 3 }}>
      {!!shadow && set.lines.map(L => <Line key={`s${L.off}`} L={L} set={set} p={p} w={w} h={h} color={shadow} dx={3} dy={7} grow={5} />)}
      {set.lines.map(L => <Line key={L.off} L={L} set={set} p={p} w={w} h={h} color={color} />)}
    </Svg>
  )
}

function Line({ L, set, p, w, h, color, dx = 0, dy = 0, grow = 0 }) {
  const props = useAnimatedProps(() => {
    const { ti, c } = sweep(p.value, L, set, w, h)
    // where the line N·x = c crosses the box, measured along the line
    const x0 = NX * c, y0 = NY * c
    const lo = Math.max((x0 - w) / -UX, -y0 / UY)
    const hi = Math.min(x0 / -UX, (h - y0) / UY)
    const ch = hi - lo
    if (ch <= 0 || p.value <= 0 || p.value >= 1) return { d: 'M-50 -50' }
    const bEff = L.a + (L.b - L.a) * eOut(cl(ti / 0.45))
    const t1 = lo + L.a * ch, t2 = lo + bEff * ch
    const ax = NX * c + UX * t1 + dx, ay = NY * c + UY * t1 + dy
    const bx = NX * c + UX * t2 + dx, by = NY * c + UY * t2 + dy
    return { d: `M${ax.toFixed(1)} ${ay.toFixed(1)}L${bx.toFixed(1)} ${by.toFixed(1)}` }
  }, [w, h, set, dx, dy])
  return <AnimatedPath animatedProps={props} stroke={color} strokeWidth={L.th + grow} strokeLinecap="round" fill="none" />
}
