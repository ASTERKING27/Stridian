import { formatValue, unitOf } from './format.js'

const r2 = v => Math.round(v * 100) / 100

// Coaches type "8:30" or "510" for a time trial; both land as seconds. Blank is null,
// anything unreadable NaN.
export function parseValue(text) {
  const s = String(text ?? '').trim().replace(',', '.')
  if (!s) return null
  if (s.includes(':')) {
    const [m, sec] = s.split(':').map(x => (x.trim() === '' ? NaN : Number(x)))
    return Number.isNaN(m) || Number.isNaN(sec) || sec >= 60 ? NaN : m * 60 + sec
  }
  return Number(s)
}

/* What the app accepts for a test: the sport's poor → elite span, 0.6× below and 1.6×
   above — and which way is better. Shown under the field before anything is typed. */
export function rangeOf(metric) {
  const lo = Math.min(metric.poor, metric.elite) * 0.6
  const hi = Math.max(metric.poor, metric.elite) * 1.6
  const show = x => (metric.key === 'timeTrial2km' ? formatValue(x, metric) : String(r2(x)))
  // 8:30 says its own unit, and the field's label already says LEVEL
  const unit = metric.key === 'timeTrial2km' || metric.unit === 'level' ? '' : unitOf(metric.unit)
  const lower = metric.direction ? metric.direction === 'lower' : metric.elite < metric.poor
  return { lo, hi, show, unit, text: `${show(lo)}–${show(hi)} ${unit}`.trim(), better: lower ? 'LOWER IS BETTER' : 'HIGHER IS BETTER', lower }
}

/* What's wrong with one typed result, if anything (Coach board, 07): blank (needed, or
   marked not tested), not a number, or outside the range above — with the likely slip of
   the decimal point offered as the fix. `kept` accepts an outlier as typed. */
export function check(metric, text, { skipped, kept } = {}) {
  if (skipped) return null
  const v = parseValue(text)
  if (v === null) return { kind: 'blank', text: 'Needed — or mark it as not tested today.' }
  if (Number.isNaN(v)) return { kind: 'nan', text: metric.key === 'timeTrial2km' ? 'Type minutes and seconds, like 8:30.' : 'That isn’t a number.' }
  const { lo, hi, show, unit } = rangeOf(metric)
  if ((v >= lo && v <= hi) || kept) return null
  const fix = [v / 10, v * 10, v / 100, v * 100].map(r2).find(x => x >= lo && x <= hi)
  return { kind: 'range', text: `Between ${show(lo)} and ${show(hi)}${unit ? ` ${unit}` : ''}.${fix != null ? ` Did you mean ${show(fix)}?` : ''}`,
           fix: fix != null ? show(fix) : null }
}
