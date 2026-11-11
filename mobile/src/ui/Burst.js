import Svg, { Path } from 'react-native-svg'
import Animated, { useAnimatedProps } from 'react-native-reanimated'
import { eOut } from './Sweep'

const AnimatedPath = Animated.createAnimatedComponent(Path)

/* A ring of sparks flying out from a point (Achievement, Badges and Streaks boards): `n`
   kite-shaped sparks, each pointing the way it flies, slowing and shrinking as they go and
   fading over 560 ms. `t` is the clock (ms), `at` when it goes off; `step` spreads the
   sparks' distances, `base` their lengths. Draws over its parent, `pad` px past its edges
   (x, y are in the parent's coordinates); touches pass through. */
export default function Burst({ t, at, x, y, n, dist, seed = 0, wobble = 0.2, step = 8, base = 8, pad = 0, color }) {
  const props = useAnimatedProps(() => {
    const u = (t.value - at) / 560
    if (u < 0 || u > 1) return { d: 'M0 0', opacity: 0 }
    let d = ''
    for (let i = 0; i < n; i++) {
      const a = (i / n) * Math.PI * 2 + seed + (i % 2) * wobble
      const far = (dist + (i % 3) * step) * eOut(u)
      const w = (base + (i % 4) * 3) * (1 - 0.5 * u)
      const cx = pad + x + Math.cos(a) * far, cy = pad + y + Math.sin(a) * far
      const ca = Math.cos(a), sa = Math.sin(a)
      const pt = (lx, ly) => `${(cx + lx * ca - ly * sa).toFixed(1)} ${(cy + lx * sa + ly * ca).toFixed(1)}`
      d += `M${pt(-w / 2, 0)}L${pt(0.2 * w, -1)}L${pt(w / 2, 0)}L${pt(0.2 * w, 1)}Z`
    }
    return { d, opacity: 1 - u }
  })
  return (
    <Svg pointerEvents="none" style={{ position: 'absolute', left: -pad, top: -pad, right: -pad, bottom: -pad }}>
      <AnimatedPath animatedProps={props} fill={color} />
    </Svg>
  )
}
