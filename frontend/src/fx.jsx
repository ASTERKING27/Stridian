import { useEffect, useLayoutEffect, useRef, useState } from 'react'

/* Motion, written by hand rather than pulled in as a library: a ring that fills, a number
   that counts up, quiet toasts, the marker that slides under the chosen tab, and the
   switch between one page (or tab) and the next. Motion answers something the person did
   or marks something that changed; nothing moves on its own. Everything sits still for
   anyone whose device asks for reduced motion. */

export const calm = () => window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

// rings draw themselves in while the app first opens (or when asked to), so moving
// between tabs doesn't set every ring spinning again
const OPENED = performance.now()
const opening = () => performance.now() - OPENED < 2500

export function useCountUp(target, ms = 900) {
  const [shown, setShown] = useState(calm() || !opening() ? target : 0)
  useEffect(() => {
    if (target == null || calm() || !opening()) { setShown(target); return undefined }
    let frame
    const start = performance.now()
    const step = now => {
      const t = Math.min(1, (now - start) / ms)
      setShown(target * (1 - (1 - t) ** 3))
      if (t < 1) frame = requestAnimationFrame(step)
    }
    frame = requestAnimationFrame(step)
    return () => cancelAnimationFrame(frame)
  }, [target, ms])
  return shown
}

export function CountUp({ value, decimals = 0, suffix = '' }) {
  const shown = useCountUp(value)
  if (value == null) return '—'
  return `${Number(shown).toFixed(decimals)}${suffix}`
}

/* A ring that fills to `value` (0 → 1). `draw` makes it draw in slowly whenever it
   appears — the achievement record does that. */
export function Ring({ value = 0, size = 88, stroke = 9, children, label, draw = false }) {
  const animate = (draw || opening()) && !calm()
  const [shown, setShown] = useState(animate ? 0 : value)
  useEffect(() => {
    if (!animate) { setShown(value); return undefined }
    const t = setTimeout(() => setShown(value), draw ? 250 : 60)
    return () => clearTimeout(t)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps
  const r = (size - stroke) / 2
  const c = 2 * Math.PI * r
  const id = useRef(`g${Math.random().toString(36).slice(2, 8)}`).current
  return (
    <div className={`ring${draw ? ' slow' : ''}`} style={{ width: size, height: size }} role="img"
         aria-label={label ?? `${Math.round(value * 100)}%`}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} aria-hidden="true">
        <defs>
          <linearGradient id={id} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" className="ring-a" />
            <stop offset="100%" className="ring-b" />
          </linearGradient>
        </defs>
        <circle className="ring-track" cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} fill="none" />
        <circle className="ring-fill" cx={size / 2} cy={size / 2} r={r} strokeWidth={stroke} fill="none"
                stroke={`url(#${id})`} strokeLinecap="round"
                strokeDasharray={c} strokeDashoffset={c * (1 - Math.max(0, Math.min(1, shown)))}
                transform={`rotate(-90 ${size / 2} ${size / 2})`} />
      </svg>
      <div className="ring-in">{children}</div>
    </div>
  )
}

/* ---------------------------------------------------------------- toasts ---- */

const listeners = new Set()
export function toast(t) {
  const item = { id: Math.random().toString(36).slice(2), ...t }
  listeners.forEach(fn => fn(item))
}

export function Toaster() {
  const [items, setItems] = useState([])
  useEffect(() => {
    const add = item => {
      setItems(list => [...list, item])
      setTimeout(() => setItems(list => list.filter(i => i.id !== item.id)), item.ms ?? 5000)
    }
    listeners.add(add)
    return () => listeners.delete(add)
  }, [])
  return (
    <div className="toaster" aria-live="polite">
      {items.map(t => (
        <div key={t.id} className="toast" style={{ '--ms': `${t.ms ?? 5000}ms` }}>
          {t.icon && <span className="toast-ico">{t.icon}</span>}
          <span><b>{t.title}</b>{t.body && <small>{t.body}</small>}</span>
        </div>
      ))}
    </div>
  )
}

/* ------------------------------------------------------- slide indicator ----
   A marker behind (or under) whichever child of `ref` matches `selector`, moved when
   that changes. */
export function useIndicator(selector, deps) {
  const ref = useRef(null)
  const placed = useRef(false)
  const [style, setStyle] = useState({ opacity: 0 })
  useLayoutEffect(() => {
    const box = ref.current
    if (!box) return undefined
    const place = () => {
      const el = box.querySelector(selector)
      if (!el) { setStyle(s => ({ ...s, opacity: 0 })); return }
      // the first time it just appears in place; after that it slides
      setStyle({ opacity: 1, width: el.offsetWidth, height: el.offsetHeight,
                 transform: `translate(${el.offsetLeft}px, ${el.offsetTop}px)`,
                 transition: placed.current ? undefined : 'none' })
      placed.current = true
      // keep the chosen tab in view in a strip that scrolls sideways
      if (box.scrollWidth > box.clientWidth) {
        box.scrollTo?.({ left: el.offsetLeft - (box.clientWidth - el.offsetWidth) / 2,
                         behavior: calm() ? 'auto' : 'smooth' })
      }
    }
    place()
    const ro = new ResizeObserver(place)
    ro.observe(box)
    document.fonts?.ready.then(place)      // the look's own typeface changes every width
    return () => ro.disconnect()
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps
  return [ref, style]
}

/* Tabs on a hairline, with the underline sliding to the chosen one. Keyboard as a tab
   list should be: Tab lands on the chosen tab, the arrow keys (and Home / End) move.
   `id` ties each tab to the panel a Switcher with the same `id` shows. */
export function Tabs({ tabs, value, onChange, label, id, className = '' }) {
  const [ref, style] = useIndicator('[aria-selected="true"]', [value, tabs.length])
  const at = tabs.indexOf(value)
  const move = e => {
    const to = { ArrowRight: at + 1, ArrowLeft: at - 1, Home: 0, End: tabs.length - 1 }[e.key]
    if (to === undefined) return
    e.preventDefault()
    const i = (to + tabs.length) % tabs.length
    onChange(tabs[i])
    ref.current.querySelector(`#${CSS.escape(`${id}-tab-${i}`)}`)?.focus()
  }
  return (
    <div className={`seg tabs ${className}`} role="tablist" aria-label={label} ref={ref} onKeyDown={move}>
      <i className="seg-ind" style={style} aria-hidden="true" />
      {tabs.map((t, i) => (
        <button key={t} role="tab" type="button" id={`${id}-tab-${i}`} aria-controls={`${id}-panel`}
                aria-selected={value === t} tabIndex={i === Math.max(0, at) ? 0 : -1}
                onClick={() => onChange(t)}>{t}</button>
      ))}
    </div>
  )
}

/* A segmented choice (Men / Women, Position weights / Level targets): a pill slides
   behind the chosen option. `options` is [[value, label], …]. */
export function Seg({ options, value, onChange, label, className = '', style }) {
  const [ref, pill] = useIndicator('[aria-pressed="true"]', [value, options.length])
  return (
    <div className={`seg slide ${className}`} role="group" aria-label={label} ref={ref} style={style}>
      <i className="seg-pill" style={pill} aria-hidden="true" />
      {options.map(([key, text]) => (
        <button key={key} type="button" aria-pressed={value === key} onClick={() => onChange(key)}>{text}</button>
      ))}
    </div>
  )
}

/* ------------------------------------------------------------- switcher ----
   Moving between pages or tabs: the old panel fades and drifts away while the new one
   slides in from the side of the tab that was chosen (from `order`). The old panel keeps
   its key while it leaves, so it stays the same mounted component — nothing reloads —
   and the page keeps its height until it has gone, so nothing below jumps.
   `children` is a function: value => the panel for it. */
const EXIT_MS = 240

export function Switcher({ value, order = [], id, children }) {
  const [panes, setPanes] = useState([{ key: value }])
  const [dir, setDir] = useState(1)
  const [hold, setHold] = useState(null)
  const box = useRef(null)
  const last = useRef(value)

  // before the browser paints, so the new panel never shows without its entrance
  useLayoutEffect(() => {
    if (value === last.current) return undefined
    const from = order.indexOf(last.current)
    const to = order.indexOf(value)
    setDir(from < 0 || to < 0 || to > from ? 1 : -1)
    const leaving = last.current
    last.current = value
    if (calm()) { setPanes([{ key: value }]); return undefined }
    setHold(box.current?.offsetHeight ?? null)
    setPanes([{ key: leaving, leaving: true }, { key: value, fresh: true }])
    const t = setTimeout(() => {
      setPanes(list => list.filter(p => !p.leaving))
      setHold(null)
    }, EXIT_MS)
    return () => clearTimeout(t)
  }, [value]) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="switch" ref={box} style={{ '--dir': dir, minHeight: hold ?? undefined }}
         {...(id && { role: 'tabpanel', id: `${id}-panel`, 'aria-labelledby': `${id}-tab-${Math.max(0, order.indexOf(value))}` })}>
      {panes.map(p => (
        <div key={p.key} className={`pane${p.leaving ? ' out' : p.fresh ? ' in' : ''}`}
             aria-hidden={p.leaving || undefined} inert={p.leaving || undefined}>
          {children(p.key)}
        </div>
      ))}
    </div>
  )
}
