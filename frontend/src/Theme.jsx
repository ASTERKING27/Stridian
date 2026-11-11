import { useEffect, useId, useRef, useState } from 'react'
import { flushSync } from 'react-dom'
import { calm } from './fx'
import Icon from './Icon'

/* Two looks, Floodlit (dark) and Daylight (light), and three accents. Each is an
   attribute on <html> that styles.css gives its own values. The choice is a per-browser
   convenience, kept in localStorage; index.html reads it too, to paint the right look
   first. */
export const LOOKS = [
  { key: 'floodlit', name: 'Floodlit', note: 'Graphite, for the evening session' },
  { key: 'daylight', name: 'Daylight', note: 'Chalk, for the morning one' },
  { key: 'system', name: 'Auto', note: 'Follows your device' },
]
export const ACCENTS = [['volt', 'Volt', '#CDF24A'], ['blaze', 'Blaze', '#FF6A2B'], ['sky', 'Sky', '#7FD3FF']]
const KEY = 'stridian.look'
const ACCENT_KEY = 'stridian.accent'
const OLD = { neon: 'floodlit', dark: 'floodlit', light: 'daylight' }   // looks this site used to have

const prefersLight = () => window.matchMedia?.('(prefers-color-scheme: light)').matches
const themeOf = look => (look === 'daylight' || (look === 'system' && prefersLight()) ? 'daylight' : 'floodlit')

function apply(look) {
  document.documentElement.setAttribute('data-theme', themeOf(look))
  try { localStorage.setItem(KEY, look) } catch { /* private mode */ }
}

function applyAccent(accent) {
  const root = document.documentElement
  if (accent === 'volt') root.removeAttribute('data-accent')
  else root.setAttribute('data-accent', accent)
  try { localStorage.setItem(ACCENT_KEY, accent) } catch { /* private mode */ }
}

export function useLook() {
  const [look, setLook] = useState(() => {
    let saved = null
    try { saved = localStorage.getItem(KEY) } catch { /* private mode */ }
    saved = OLD[saved] ?? saved
    return LOOKS.some(l => l.key === saved) ? saved : 'floodlit'
  })
  useEffect(() => {
    apply(look)
    if (look !== 'system') return undefined
    const mq = window.matchMedia('(prefers-color-scheme: light)')
    const follow = () => apply('system')
    mq.addEventListener('change', follow)
    return () => mq.removeEventListener('change', follow)
  }, [look])

  /* A new look spreads out in a circle from `at` (the picker), where the browser can
     animate a whole-page change; elsewhere, or with reduced motion, it just changes. */
  const change = (next, at) => {
    const swap = () => { apply(next); setLook(next) }
    if (!document.startViewTransition || calm() || themeOf(next) === themeOf(look)) { swap(); return }
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
  const [accent, setAccent] = useState(() => document.documentElement.getAttribute('data-accent') ?? 'volt')
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
        <Icon name="contrast" size={16} />
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
              <span className={`swatch ${l.key}`} aria-hidden="true"><i /><i /></span>
              <span><b>{l.name}</b><small>{l.note}</small></span>
            </button>
          ))}
          <div className="lookmenu-head" aria-hidden="true">Accent</div>
          <div className="accents" role="group" aria-label="Accent colour">
            {ACCENTS.map(([key, name, hex]) => (
              <button key={key} aria-pressed={key === accent} aria-label={name} title={name}
                      onClick={() => { applyAccent(key); setAccent(key) }}>
                <i style={{ background: hex }} />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
