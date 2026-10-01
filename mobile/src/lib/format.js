/* Formatting shared by every screen. Nothing here imports the app, so Node can run it
   (scripts/check.mjs). */

export const LEVEL_NAMES = ['University', 'Zonal', 'State', 'National', 'International']

// The API stores UTC without a zone marker, which JS would read as local time.
export const utc = s => new Date(/(Z|[+-]\d\d:?\d\d)$/.test(s) ? s : `${s}Z`)

// "4.38 sec" -> "4.38 s": the design writes seconds short
const UNIT = { sec: 's' }
export const unitOf = u => UNIT[u] ?? u ?? ''

export function formatValue(value, metric) {
  if (value === null || value === undefined) return '—'
  if (metric?.key === 'timeTrial2km') {
    const t = Math.round(value)            // whole seconds first, so 599.6 reads 10:00, not 9:60
    return `${Math.floor(t / 60)}:${String(t % 60).padStart(2, '0')}`
  }
  if (metric?.unit === 'level') return String(value)
  const u = unitOf(metric?.unit)
  return `${value}${u ? (u === '%' ? '' : ' ') + u : ''}`
}

// "0.05 sec" (the words the server writes) -> "0.05 s"
export const shortUnits = text => (text ? text.replace(/(\d) sec\b/g, '$1 s') : text)

export const initials = name =>
  (name || '?').trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
