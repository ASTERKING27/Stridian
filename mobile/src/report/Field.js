import { useState } from 'react'
import { View } from 'react-native'
import Svg, { Circle, Defs, Ellipse, Line, Path, Pattern, Polygon, Rect } from 'react-native-svg'
import { useTheme } from '../lib/theme'
import { Mono } from '../ui'

// The pitches and courts, landscape on a 100 × 64 grid, and where each position plays
// (design: Results.tpl.html). Racket sports mark a zone instead of a spot.
const R = (x, y, w, h, sw) => ({ t: 'rect', x, y, w, h, sw })
const L = (x1, y1, x2, y2, sw) => ({ t: 'line', x1, y1, x2, y2, sw })
const C = (cx, cy, r) => ({ t: 'circle', cx, cy, r })
const E = (cx, cy, rx, ry, dash) => ({ t: 'ellipse', cx, cy, rx, ry, dash })
const P = d => ({ t: 'path', d })
const KHO = Array.from({ length: 8 }, (_, i) => R(17.5 + i * 9.3, 30.5, 3, 3))

export const FIELDS = {
  Football: { prims: [R(2, 2, 96, 60, 0.7), L(50, 2, 50, 62), C(50, 32, 8), R(2, 17, 15, 30), R(83, 17, 15, 30), R(2, 25, 5, 14), R(93, 25, 5, 14)],
    pos: { Goalkeeper: [6, 32], 'Centre-back': [21, 32], 'Full-back': [27, 10], 'Central Midfielder': [43, 32], Winger: [73, 9], Striker: [86, 32] } },
  Basketball: { prims: [R(2, 2, 96, 60, 0.7), C(90, 32, 1.6), L(93, 28, 93, 36, 0.7), R(74, 24, 24, 16), C(74, 32, 6), P('M98 8H88A24 24 0 0 0 88 56H98'), P('M2 26A6 6 0 0 1 2 38')],
    pos: { 'Point Guard': [38, 32], 'Shooting Guard': [60, 9], 'Small Forward': [58, 55], 'Power Forward': [80, 50], Centre: [84, 20] } },
  Volleyball: { prims: [R(2, 8, 96, 48, 0.7), L(50, 5, 50, 59, 1.2), L(34, 8, 34, 56), L(66, 8, 66, 56)],
    pos: { Setter: [44, 18], Libero: [12, 32], 'Outside Hitter': [42, 48], 'Middle Blocker': [45, 33], 'Opposite / Server': [22, 14] } },
  Cricket: { prims: [E(50, 32, 47, 29), E(50, 32, 28, 18, [1.5, 1.2]), R(40, 30, 20, 4), L(42.5, 29, 42.5, 35), L(57.5, 29, 57.5, 35)],
    pos: { 'Opening Batsman': [58, 25], 'Middle-order Batsman': [58, 40], 'Fast Bowler': [22, 32], 'Spin Bowler': [35, 22], Wicketkeeper: [66, 32], 'All-rounder': [46, 44] } },
  Badminton: { prims: [R(2, 10, 96, 44, 0.7), L(50, 7, 50, 57, 1.2), L(39, 10, 39, 54), L(61, 10, 61, 54), L(6, 10, 6, 54), L(94, 10, 94, 54), L(2, 13.5, 98, 13.5), L(2, 50.5, 98, 50.5), L(6, 32, 39, 32), L(61, 32, 94, 32)],
    zones: { 'Attacking / Power player': [38, 10, 12, 44], 'All-court / Balanced': [18, 10, 20, 44], 'Defensive / Counter player': [2, 10, 16, 44] } },
  Tennis: { prims: [R(2, 10, 96, 44, 0.7), L(2, 15, 98, 15), L(2, 49, 98, 49), L(50, 7, 50, 57, 1.2), L(27, 15, 27, 49), L(73, 15, 73, 49), L(27, 32, 73, 32)],
    zones: { 'Attacking / Power player': [34, 10, 16, 44], 'All-court / Balanced': [14, 10, 20, 44], 'Defensive / Counter player': [2, 10, 12, 44] } },
  'Kho-Kho': { prims: [R(2, 12, 96, 40, 0.7), L(10, 32, 90, 32), R(9, 30.5, 2, 3), R(89, 30.5, 2, 3), L(10, 12, 10, 52), L(90, 12, 90, 52), ...KHO],
    pos: { Chaser: [47.1, 32], 'Runner / Dodger': [64, 20] } },
}

const diamond = (x, y, s) => `${x},${y - s} ${x + s},${y} ${x},${y + s} ${x - s},${y}`

/* The pitch with every position marked and the chosen one in ink, labelled.
   `positions` are the sport's position names; `best` is the one to mark; `labelled` the
   ones whose names are written. */
export default function Field({ sport, positions, best, labelled = positions }) {
  const { c } = useTheme()
  const [w, setW] = useState(0)
  const f = FIELDS[sport]
  if (!f) return null
  const S = w / 100
  const h = w * 0.64
  const stroke = { stroke: c.ink2, fill: 'none' }
  // the chosen one is named first; another name is left off if it would cover a mark or a name already placed
  const placed = f.pos ? positions.filter(p => f.pos[p]).map(p => [f.pos[p][0] * S - 7, f.pos[p][1] * S - 7, f.pos[p][0] * S + 7, f.pos[p][1] * S + 7]) : []
  const named = (f.zones ? positions.filter(p => f.zones[p])
    : [best, ...labelled.filter(p => p !== best)].filter(p => positions.includes(p) && f.pos[p])).filter(p => {
    if (f.zones) return true
    const [px, py] = f.pos[p]
    const on = p === best
    const wide = p.length * (on ? 10.5 : 9.5) * 0.68 + (on ? 14 : 2)
    const x0 = px > 66 ? (px - 4.5) * S - wide : (px + 4.5) * S
    const box = [x0, py * S - 10, x0 + wide, py * S + 10]
    if (!on && placed.some(b => box[0] < b[2] && b[0] < box[2] && box[1] < b[3] && b[1] < box[3])) return false
    placed.push(box)
    return true
  })
  return (
    <View onLayout={e => setW(e.nativeEvent.layout.width)} style={{ width: '100%', height: h || 1 }}
          accessible accessibilityLabel={`${sport} pitch, ${best} marked`}>
      {w > 0 && (
        <>
          <Svg width={w} height={h} viewBox="0 0 100 64">
            <Defs>
              <Pattern id="fhatch" width="2.2" height="2.2" patternUnits="userSpaceOnUse" patternTransform="rotate(40)">
                <Line x1="0" y1="0" x2="0" y2="2.2" stroke={c.ink} strokeWidth={0.7} />
              </Pattern>
            </Defs>
            <Rect x={0} y={0} width={100} height={64} fill={c.soft} />
            {f.prims.map((g, i) => {
              const sw = g.sw ?? 0.45
              if (g.t === 'rect') return <Rect key={i} x={g.x} y={g.y} width={g.w} height={g.h} strokeWidth={sw} {...stroke} />
              if (g.t === 'line') return <Line key={i} x1={g.x1} y1={g.y1} x2={g.x2} y2={g.y2} strokeWidth={sw} stroke={c.ink2} />
              if (g.t === 'circle') return <Circle key={i} cx={g.cx} cy={g.cy} r={g.r} strokeWidth={sw} {...stroke} />
              if (g.t === 'ellipse') return <Ellipse key={i} cx={g.cx} cy={g.cy} rx={g.rx} ry={g.ry} strokeWidth={sw} strokeDasharray={g.dash} {...stroke} />
              return <Path key={i} d={g.d} strokeWidth={sw} {...stroke} />
            })}
            {f.zones && positions.filter(p => f.zones[p]).map(p => {
              const [x, y, zw, zh] = f.zones[p]
              const on = p === best
              return <Rect key={p} x={x} y={y} width={zw} height={zh} fill={on ? 'url(#fhatch)' : 'none'} stroke={c.ink}
                           strokeWidth={on ? 0.7 : 0.35} strokeDasharray={on ? undefined : [1.2, 1]} />
            })}
            {f.pos && positions.filter(p => f.pos[p]).map(p => {
              const [x, y] = f.pos[p]
              const on = p === best
              return <Polygon key={p} points={diamond(x, y, on ? 3 : 1.7)} strokeWidth={0.5}
                              fill={on ? c.ink : c.bg} stroke={on ? c.ink : c.ink2} />
            })}
          </Svg>
          {/* every position gets its mark; names only for the ones in the running, and never on top of each other */}
          {named.map(p => {
            const on = p === best
            let x, y, anchor
            if (f.pos) {
              const [px, py] = f.pos[p]
              const right = px > 66
              x = (right ? px - 4.5 : px + 4.5) * S
              y = py * S
              anchor = right ? 'right' : 'left'
            } else {
              const [zx, , zw] = f.zones[p]
              x = (zx + zw / 2) * S
              y = (on ? 32 : 58.5) * S
              anchor = 'center'
            }
            const text = f.pos ? p : p.split(' /')[0]
            return (
              <View key={p} pointerEvents="none"
                    style={{ position: 'absolute', top: y - 10, height: 20, justifyContent: 'center',
                             ...(anchor === 'right' ? { right: w - x } : anchor === 'left' ? { left: x } : { left: x - 80, width: 160, alignItems: 'center' }) }}>
                <View style={on ? { backgroundColor: c.ink, paddingVertical: 4, paddingHorizontal: 7 } : null}>
                  <Mono size={on ? 10.5 : 9.5} color={on ? c.bg : c.ink2} style={{ letterSpacing: 0.6 }}>
                    {on ? text.toUpperCase() : text}
                  </Mono>
                </View>
              </View>
            )
          })}
        </>
      )}
    </View>
  )
}
