/* Inline-SVG charts. No chart library: these are three shapes and some maths,
   and shipping 90 kB of Recharts to draw them would be the wrong trade.

   Conventions that hold across all three: thin marks, solid hairline grid one
   shade off the surface, values always readable as text (never colour alone),
   and a <title> on every mark so hovering gives the number natively. Colours come
   from the CSS custom properties in styles.css, so light and dark just work. */

import { utc } from './api'

const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v))

/* ---------------------------------------------------------------- radar ----
   One athlete's profile across every metric of their sport. Single series, so
   no legend — the card title names it. The measurements table underneath is the
   table-view twin, which is also where unmeasured metrics are visible. */
export function Radar({ points, size = 300 }) {
  const n = points.length
  if (n < 3) return null

  const pad = 62
  const r = (size - pad * 2) / 2
  const c = size / 2
  const at = (i, radius) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / n
    return [c + Math.cos(a) * radius, c + Math.sin(a) * radius]
  }
  const ring = radius => points.map((_, i) => at(i, radius).join(',')).join(' ')
  const shape = points.map((p, i) => at(i, (clamp(p.score ?? 0, 0, 100) / 100) * r).join(',')).join(' ')

  return (
    <div className="chartwrap">
      <svg viewBox={`0 0 ${size} ${size}`} role="img"
           aria-label={`Profile radar: ${points.map(p => `${p.label} ${p.score ?? 'not measured'}`).join(', ')}`}>
        {[25, 50, 75, 100].map(pct => (
          <polygon key={pct} className="gridline" points={ring((pct / 100) * r)} />
        ))}
        {points.map((_, i) => {
          const [x, y] = at(i, r)
          return <line key={i} className="gridline" x1={c} y1={c} x2={x} y2={y} />
        })}

        <polygon points={shape} fill="var(--s1)" fillOpacity="0.16"
                 stroke="var(--s1)" strokeWidth="2" strokeLinejoin="round" />

        {points.map((p, i) => {
          const [x, y] = at(i, (clamp(p.score ?? 0, 0, 100) / 100) * r)
          return (
            <circle key={i} cx={x} cy={y} r="4.5" fill="var(--s1)"
                    stroke="var(--surface)" strokeWidth="2">
              <title>{`${p.label}: ${p.score ?? 'not measured'}${p.score != null ? '/100' : ''}`}</title>
            </circle>
          )
        })}

        {points.map((p, i) => {
          const [x, y] = at(i, r + 16)
          const cos = Math.cos(-Math.PI / 2 + (i * 2 * Math.PI) / n)
          const anchor = cos > 0.25 ? 'start' : cos < -0.25 ? 'end' : 'middle'
          const lines = p.lines ?? [p.short ?? p.label]
          return (
            <text key={i} x={x} y={y} className="axis" textAnchor={anchor}
                  dominantBaseline="middle" dy={lines.length > 1 ? '-0.4em' : 0}>
              {lines.map((line, li) => (
                <tspan key={li} x={x} dy={li === 0 ? 0 : '1.15em'}>{line}</tspan>
              ))}
            </text>
          )
        })}
      </svg>
    </div>
  )
}

/* ------------------------------------------------------------ sparkline ----
   One metric over time. 2px line, the endpoint gets a marker and a direct label;
   every other point carries its value in a <title>. */
export function Sparkline({ series, unit = '', lowerIsBetter = false, width = 300, height = 76 }) {
  if (!series || series.length < 2) return null

  const padL = 6, padR = 46, padY = 12
  const values = series.map(p => p.v)
  const lo = Math.min(...values), hi = Math.max(...values)
  const span = hi - lo || 1
  const x = i => padL + (i / (series.length - 1)) * (width - padL - padR)
  const y = v => padY + (1 - (v - lo) / span) * (height - padY * 2)

  const path = series.map((p, i) => `${i ? 'L' : 'M'}${x(i)},${y(p.v)}`).join(' ')
  const last = series[series.length - 1]
  const first = series[0]
  const improved = lowerIsBetter ? last.v < first.v : last.v > first.v
  const changed = last.v !== first.v

  return (
    <div className="chartwrap">
      <svg viewBox={`0 0 ${width} ${height}`} role="img"
           aria-label={`${series.length} readings from ${first.v} to ${last.v} ${unit}`}>
        <line className="gridline" x1={padL} y1={height - padY} x2={width - padR} y2={height - padY} />
        <path d={path} fill="none" stroke="var(--s1)" strokeWidth="2"
              strokeLinecap="round" strokeLinejoin="round" />
        {series.map((p, i) => (
          <circle key={i} cx={x(i)} cy={y(p.v)} r={i === series.length - 1 ? 4.5 : 3}
                  fill={i === series.length - 1 ? 'var(--s1)' : 'var(--surface)'}
                  stroke="var(--s1)" strokeWidth="2">
            <title>{`${utc(p.t).toLocaleDateString()}: ${p.v} ${unit}`}</title>
          </circle>
        ))}
        <text x={width - padR + 8} y={y(last.v)} className="marklabel" dominantBaseline="middle">
          {last.v}
        </text>
      </svg>
      <p className="muted" style={{ margin: '2px 0 0' }}>
        {series.length} readings ·{' '}
        {changed
          ? <span style={{ color: improved ? 'var(--good)' : 'var(--serious)' }}>
              {improved ? '▲ improving' : '▼ slipping'} ({first.v} → {last.v} {unit})
            </span>
          : <>no change ({last.v} {unit})</>}
      </p>
    </div>
  )
}

/* ------------------------------------------------------------ macro bar ----
   Part-to-whole across three fixed categories, so a stacked bar rather than a
   pie: three segments, 2px surface gaps, legend plus direct labels. */
export function MacroBar({ parts, height = 26 }) {
  const total = parts.reduce((a, p) => a + p.value, 0) || 1
  let offset = 0
  const gap = 0.6 // percentage points, rendered as a surface-coloured gap

  return (
    <div className="chartwrap">
      <svg viewBox={`0 0 100 ${height}`} preserveAspectRatio="none"
           style={{ height, width: '100%' }} role="img"
           aria-label={parts.map(p => `${p.label} ${Math.round((p.value / total) * 100)}%`).join(', ')}>
        {parts.map((p, i) => {
          const w = (p.value / total) * 100
          const x = offset
          offset += w
          const inner = Math.max(w - (i < parts.length - 1 ? gap : 0), 0.5)
          return (
            <rect key={p.label} x={x} y="0" width={inner} height={height} rx="1.5" fill={p.color}>
              <title>{`${p.label}: ${p.display} (${Math.round(w)}%)`}</title>
            </rect>
          )
        })}
      </svg>
      <div className="legend">
        {parts.map(p => (
          <span key={p.label}>
            <i style={{ background: p.color }} />
            {p.label} <b>{p.display}</b>{' '}
            <span className="muted">{Math.round((p.value / total) * 100)}%</span>
          </span>
        ))}
      </div>
    </div>
  )
}
