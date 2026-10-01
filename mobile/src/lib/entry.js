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

/* What's wrong with one typed result, if anything (Coach board, 07): blank (needed, or
   marked not tested), not a number, or outside what anyone could post — with the likely
   slip of the decimal point offered as the fix. `kept` accepts an outlier as typed.
   The plausible range is the sport's poor → elite span, 0.6× below and 1.6× above. */
export function check(metric, text, { skipped, kept } = {}) {
  if (skipped) return null
  const v = parseValue(text)
  if (v === null) return { kind: 'blank', text: 'Needed — or mark it as not tested today.' }
  if (Number.isNaN(v)) return { kind: 'nan', text: metric.key === 'timeTrial2km' ? 'Type minutes and seconds, like 8:30.' : 'That isn’t a number.' }
  const lo = Math.min(metric.poor, metric.elite) * 0.6
  const hi = Math.max(metric.poor, metric.elite) * 1.6
  if ((v >= lo && v <= hi) || kept) return null
  const fix = [v / 10, v * 10, v / 100, v * 100].map(r2).find(x => x >= lo && x <= hi)
  const show = x => (metric.key === 'timeTrial2km' ? formatValue(x, metric) : String(r2(x)))
  return { kind: 'range', text: `Between ${show(lo)} and ${show(hi)} ${unitOf(metric.unit)}.${fix != null ? ` Did you mean ${show(fix)}?` : ''}`,
           fix: fix != null ? show(fix) : null }
}
