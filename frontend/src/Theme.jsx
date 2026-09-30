import { useEffect, useId, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { calm } from './fx'
import Icon from './Icon'

/* Looks: whole designs, not just light and dark. Each is a data-theme value that
   styles.css gives its own colours, type and surfaces. More can be added here. The
   choice is a per-browser convenience, kept in localStorage. */
export const LOOKS = [
  { key: 'neon', name: 'Neon', note: 'Deep navy, cyan-to-violet glow', swatch: ['#070b1a', '#22d3ee', '#a78bfa', '#f472b6'] },
  { key: 'light', name: 'Classic light', note: 'Calm and plain', swatch: ['#f9f9f7', '#2a78d6', '#1baf7a', '#eb6834'] },
  { key: 'dark', name: 'Classic dark', note: 'Calm and plain, at night', swatch: ['#0d0d0d', '#3987e5', '#199e70', '#d95926'] },
  { key: 'system', name: 'Classic auto', note: 'Follows your device', swatch: ['#f9f9f7', '#0d0d0d', '#2a78d6', '#3987e5'] },
]
const KEY = 'stridian.look'     // index.html reads it too, to paint the right look first

function apply(look) {
  const root = document.documentElement
  if (look === 'system') root.removeAttribute('data-theme')
  else root.setAttribute('data-theme', look)
  try { localStorage.setItem(KEY, look) } catch { /* private mode */ }
}

export function useLook() {
  const [look, setLook] = useState(() => {
    let saved = null
    try { saved = localStorage.getItem(KEY) } catch { /* private mode */ }
    return LOOKS.some(l => l.key === saved) ? saved : 'neon'
  })
  useEffect(() => apply(look), [look])

  /* A new look spreads out in a circle from `at` (the picker), where the browser can
     animate a whole-page change; elsewhere, or with reduced motion, it just changes. */
  const change = (next, at) => {
    const swap = () => { apply(next); setLook(next) }
    if (!document.startViewTransition || calm()) { swap(); return }
    const root = document.documentElement
    root.style.setProperty('--vt-x', `${Math.round(at?.x ?? innerWidth / 2)}px`)
    root.style.setProperty('--vt-y', `${Math.round(at?.y ?? 0)}px`)
    const t = document.startViewTransition(() => flushSync(swap))
    t.ready.catch(() => {})     // cut short by another change: not an error
  }
  return [look, change]
}

export function LookPicker({ look, onLook }) {
  const [open, setOpen] = useState(false)
  const box = useRef(null)
  const trigger = useRef(null)
  const menu = useId()

  useEffect(() => {
    if (!open) return undefined
    const close = e => { if (!box.current?.contains(e.target)) setOpen(false) }
    const esc = e => { if (e.key === 'Escape') { setOpen(false); trigger.current?.focus() } }
    document.addEventListener('pointerdown', close)
    document.addEventListener('keydown', esc)
    return () => { document.removeEventListener('pointerdown', close); document.removeEventListener('keydown', esc) }
  }, [open])

  const current = LOOKS.find(l => l.key === look) ?? LOOKS[0]
  // a disclosure: the button opens a short list of buttons, Tab moves through them
  return (
    <div className="lookpick" ref={box}>
      <button ref={trigger} className="iconbtn" aria-expanded={open} aria-controls={menu}
              aria-label={`Look: ${current.name}. Change it.`} title={`Look: ${current.name}`}
              onClick={() => setOpen(o => !o)}>
        <Icon name="palette" size={16} />
      </button>
      {open && (
        <div className="lookmenu" id={menu} role="group" aria-label="Choose a look">
          <div className="lookmenu-head" aria-hidden="true">Look</div>
          {LOOKS.map(l => (
            <button key={l.key} aria-pressed={l.key === look}
                    onClick={() => {
                      const r = box.current.getBoundingClientRect()
                      setOpen(false)
                      trigger.current?.focus()
                      if (l.key !== look) onLook(l.key, { x: r.left + r.width / 2, y: r.top + r.height / 2 })
                    }}>
              <span className="swatch" aria-hidden="true">
                {l.swatch.map(c => <i key={c} style={{ background: c }} />)}
              </span>
              <span><b>{l.name}</b><small>{l.note}</small></span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
