import { useMemo, useRef } from 'react'
import { SPORTKIT, kitLayers } from './sportkit'
import { calm, gsap, useGSAP } from './motion'

/* A sport's court, drawn to scale from the sport kit, the lines chalked in whenever the
   sport changes. `spots` marks where each position plays; `players` (one per kit spot,
   null for an open one) puts names on them instead. `view` picks a kit view box
   ('squadView', 'crop'), 'full' for the whole ground, or is a view box string of its own.
   `pace` stretches the chalking-in and `delay` holds it back, for a page that is still
   arriving. */
export default function Court({ sport, spots = false, players, view = 'squadView', onSpot, className = '', pace = 1, delay = 0 }) {
  const kit = SPORTKIT[sport]
  const box = useRef(null)
  const layers = useMemo(() => (kit ? kitLayers(kit) : []), [kit])
  const vb = ((view === 'full' ? kit?.court.viewBox : kit?.[view] ?? view) ?? '0 0 1 1').split(' ').map(Number)

  useGSAP(() => {
    if (!kit || calm()) return
    const svg = box.current.querySelector('svg')
    const ppu = svg.clientWidth / vb[2]          // screen pixels per metre: the strokes don't scale
    const strokes = [...svg.querySelectorAll('.kl, .ks, .kk')]
    strokes.forEach(p => {
      const len = p.getTotalLength() * ppu + 2
      gsap.fromTo(p, { strokeDasharray: len, strokeDashoffset: len },
        { strokeDashoffset: 0, duration: 0.85 * pace, ease: 'io', delay: delay + Math.min(0.5, strokes.indexOf(p) * 0.02) * pace, clearProps: 'strokeDasharray,strokeDashoffset' })
    })
    gsap.from(svg.querySelectorAll('.kt, .ktl, .kf, .kd, .km, .kkm'), { opacity: 0, duration: 0.6 * pace, delay: delay + 0.35 * pace, ease: 'power1.out' })
    gsap.from(box.current.querySelectorAll('.spot'), { opacity: 0, scale: 0.5, duration: 0.45, stagger: 0.035, delay: delay + 0.5 * pace, ease: 'back.out(2)' })
  }, { scope: box, dependencies: [sport], revertOnUpdate: true })

  if (!kit) return null
  const marks = players ?? (spots ? kit.spots.map(s => ({ pos: s.pos })) : [])
  const order = [...new Set(kit.spots.map(s => s.pos))]      // each position's number, for a key under a small drawing
  return (
    <div className={`court ${className}`} ref={box} style={{ aspectRatio: `${vb[2]} / ${vb[3]}`, '--aspect': vb[2] / vb[3] }}>
      <svg viewBox={vb.join(' ')} fill="none" aria-hidden="true">
        {layers.map((l, i) => <path key={i} className={l.c} d={l.d} vectorEffect="non-scaling-stroke" />)}
      </svg>
      {marks.map((m, i) => {
        const s = kit.spots[i]
        if (!s) return null
        const open = players && !m?.name
        const Tag = onSpot ? 'button' : 'span'
        return (
          <Tag key={i} className={`spot lab-${s.lab ?? 'b'}${open ? ' open' : ''}${s.active ? ' active' : ''}`}
               data-n={order.indexOf(s.pos) + 1}
               style={{ left: `${((s.x - vb[0]) / vb[2]) * 100}%`, top: `${((s.y - vb[1]) / vb[3]) * 100}%` }}
               {...(onSpot && { type: 'button', onClick: () => onSpot(m, s) })}>
            <i />
            <span>
              {players && <b>{m?.name ?? 'Open'}</b>}
              <small>{s.pos}</small>
            </span>
          </Tag>
        )
      })}
    </div>
  )
}
