import { useState } from 'react'
import { View } from 'react-native'
import Svg, { Line, Polygon, Rect } from 'react-native-svg'
import { breakdown, focusPosition } from '../../../lib/report'
import { useTheme } from '../../../lib/theme'
import { Mono, Seg, T, Title } from '../../../ui'
import Page, { useReportPage } from '../../../report/Page'

// Results board, 03: the attributes that matter for the position, against what it leans on.
export default function Shape() {
  const { data, error, id } = useReportPage()
  const { c } = useTheme()
  const [view, setView] = useState('radar')
  const pos = data && focusPosition(data)
  // the six measures this position weighs most
  const rows = data ? breakdown(pos, data.metrics).sort((a, b) => b.share - a.share).slice(0, 6) : []
  const maxShare = Math.max(...rows.map(r => r.share), 0.0001)
  const items = rows.map(r => ({ ...r, ideal: Math.max(12, (r.share / maxShare) * 100) }))

  return (
    <Page data={data} error={error}>
      {pos && (
        <>
          <Title eyebrow="ATTRIBUTES · 0–100">{id ? 'Their shape' : 'Your shape'}</Title>
          <Seg options={[['radar', 'RADAR'], ['bars', 'BARS']]} value={view} onChange={setView} />
          {items.length < 3 && view === 'radar'
            ? <T size={13.5} color="ink2">A radar needs at least three measured attributes — the bars show what there is.</T>
            : null}
          {view === 'radar' && items.length >= 3 ? <Radar items={items} /> : (
            <View style={{ gap: 16, paddingTop: 6, paddingBottom: 12 }}>
              {items.map(b => (
                <View key={b.key} style={{ gap: 7 }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                    <T size={14}>{b.label}</T><Mono size={14}>{Math.round(b.score)}</Mono>
                  </View>
                  <View style={{ height: 10, backgroundColor: c.line }}>
                    <View style={{ height: 10, width: `${b.score}%`, backgroundColor: c.ink }} />
                    <View style={{ position: 'absolute', top: -4, width: 2, height: 18, backgroundColor: c.ink2, left: `${b.ideal}%` }} />
                  </View>
                </View>
              ))}
            </View>
          )}
          <View style={{ flexDirection: 'row', gap: 20, alignItems: 'center', flexWrap: 'wrap' }}>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={{ width: 18, height: 2, backgroundColor: c.ink }} />
              <Mono size={10.5} style={{ letterSpacing: 0.84 }}>{id ? 'THEM' : 'YOU'}</Mono>
            </View>
            <View style={{ flexDirection: 'row', alignItems: 'center', gap: 8 }}>
              <View style={{ width: 18, height: 0, borderTopWidth: 2, borderColor: c.ink2, borderStyle: 'dashed' }} />
              <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84 }}>WHAT {a(pos.position)} {pos.position.toUpperCase()} LEANS ON</Mono>
            </View>
          </View>
        </>
      )}
    </Page>
  )
}

const a = w => (/^[aeiou]/i.test(w) ? 'AN' : 'A')

function Radar({ items }) {
  const { c } = useTheme()
  const [W, setW] = useState(0)
  const H = W * 318 / 346
  const cx = W / 2, cy = H * 164 / 318, RR = W * 112 / 346
  const n = items.length
  const ang = i => -Math.PI / 2 + i * 2 * Math.PI / n
  const pt = (i, v) => [cx + Math.cos(ang(i)) * RR * v / 100, cy + Math.sin(ang(i)) * RR * v / 100]
  const poly = vals => vals.map((v, i) => pt(i, v).join(',')).join(' ')
  return (
    <View onLayout={e => setW(e.nativeEvent.layout.width)} style={{ width: '100%', height: H || 1 }}
          accessible accessibilityLabel={items.map(i => `${i.label} ${Math.round(i.score)}`).join(', ')}>
      {W > 0 && (
        <>
          <Svg width={W} height={H}>
            {[25, 50, 75, 100].map(v => <Polygon key={v} points={poly(Array(n).fill(v))} fill="none" stroke={c.line} strokeWidth={1} />)}
            {items.map((_, i) => { const [x, y] = pt(i, 100); return <Line key={i} x1={cx} y1={cy} x2={x} y2={y} stroke={c.line} strokeWidth={1} /> })}
            <Polygon points={poly(items.map(i => i.ideal))} fill="none" stroke={c.ink2} strokeWidth={1.5} strokeDasharray={[5, 4]} strokeLinejoin="miter" />
            <Polygon points={poly(items.map(i => i.score))} fill={c.soft} stroke={c.ink} strokeWidth={2} strokeLinejoin="miter" />
            {items.map((it, i) => {
              const [x, y] = pt(i, it.score)
              return <Rect key={it.key} x={x - 3.5} y={y - 3.5} width={7} height={7} fill={c.ink} rotation={45} origin={`${x}, ${y}`} />
            })}
          </Svg>
          {items.map((it, i) => {
            const [x, y] = pt(i, 122)
            const cos = Math.cos(ang(i))
            const side = cos > 0.3 ? 'right' : cos < -0.3 ? 'left' : 'center'
            const top = Math.max(12, Math.min(H - 12, y)) - 16
            const pos = side === 'right' ? { right: 8, alignItems: 'flex-end' }
              : side === 'left' ? { left: 8, alignItems: 'flex-start' }
                : { left: x - 70, width: 140, alignItems: 'center' }
            return (
              <View key={it.key} pointerEvents="none" style={{ position: 'absolute', top, gap: 2, maxWidth: W * 0.42, ...pos }}>
                <T size={12} numberOfLines={2} style={{ textAlign: side === 'right' ? 'right' : side === 'left' ? 'left' : 'center' }}>{it.label}</T>
                <Mono size={12} font="monoMedium">{Math.round(it.score)}</Mono>
              </View>
            )
          })}
        </>
      )}
    </View>
  )
}
