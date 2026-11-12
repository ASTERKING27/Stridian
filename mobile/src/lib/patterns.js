/* The haptic patterns of the design's big moments (code/haptics_data.py), as data —
   played by lib/haptics.js. Nothing here imports the app, so scripts/check.mjs runs it. */

export const PRIM = { CLICK: 0, THUD: 1, SPIN: 2, QUICK_RISE: 3, SLOW_RISE: 4, QUICK_FALL: 5, TICK: 6, LOW_TICK: 7 }

/* Each pattern, ms from its own start: rich — [primitive, at, scale]; budget — [at, ms,
   strength 0–1] pulses (gaps are still); fallback — [at, system haptic] without the module. */
export const PATTERNS = {
  // the diagonal lines crossing on a tab change (rich only: the tap already ticked)
  sweep: { rich: [['TICK', 0, 0.3], ['TICK', 60, 0.2], ['TICK', 120, 0.12]] },
  // launch: drawn per ms by launchWave below; this is only for phones without a vibrator we drive
  launch: { fallback: [[70, 'tick'], [320, 'tick'], [540, 'tick'], [730, 'tick'], [1160, 'snap'], [2060, 'tap']] },
  // level reached (Achievement board): sweep, pop and sparks, a stamp per letter, a tick per
  // count step, the ladder rising, success
  level: {
    rich: [['TICK', 480, 0.3], ['TICK', 540, 0.2], ['TICK', 600, 0.12], ['CLICK', 820, 0.6], ['TICK', 850, 0.45], ['TICK', 885, 0.35],
      ...[0, 1, 2, 3, 4].map(i => ['TICK', 1100 + i * 55, 0.35 + i * 0.05]), ...[1424, 1478, 1544, 1631, 1775].map(at => ['TICK', at, 0.28]),
      ['SLOW_RISE', 1790, 0.45], ['CLICK', 2070, 0.45], ['CLICK', 2180, 0.75], ['TICK', 2240, 0.4], ['TICK', 2280, 0.3]],
    budget: [[820, 12, 0.5], [2070, 25, 0.55], [2185, 45, 0.86]],
    fallback: [[480, 'tick'], [820, 'tap'], [2070, 'success']],
  },
  // a badge earned (Badges board): the outline draws, the ink rises, the glyph pops, sparks
  badge: {
    rich: [['LOW_TICK', 0, 0.3], ['SLOW_RISE', 300, 0.45], ['CLICK', 600, 0.6], ['TICK', 700, 0.5], ['TICK', 760, 0.4], ['TICK', 820, 0.3]],
    budget: [[600, 25, 0.55], [715, 45, 0.86]],
    fallback: [[600, 'success']],
  },
  // the streak back on (Streaks board): the missed week fills, the count rolls up, success
  streakUp: {
    rich: [['SLOW_RISE', 600, 0.45], ['CLICK', 1900, 0.5], ['CLICK', 2010, 0.45], ['CLICK', 2120, 0.75]],
    budget: [[2010, 25, 0.55], [2125, 45, 0.86]],
    fallback: [[1900, 'tap'], [2060, 'success']],
  },
  // the streak broken: the count drops to 0 — soft, never harsh
  streakDown: { rich: [['QUICK_FALL', 700, 0.5]] },
}

// budget pulses → [ms, amplitude, …] segments, stillness filling the gaps
export function waveform(pulses) {
  const out = []
  let t = 0
  for (const [at, ms, a] of [...pulses].sort((x, y) => x[0] - y[0])) {
    const from = Math.max(at, t), len = at + ms - from
    if (len <= 0) continue
    if (from > t) out.push(from - t, 0)
    out.push(len, Math.round(Math.min(1, Math.max(0, a)) * 255))
    t = from + len
  }
  return out
}

/* Launch, ms from its start: a tick for every spark that flies off the logo, harder as it
   charges; still while it squashes; the ignition sparks as one kick; then the dive — a buzz
   building as the window races out ("bzzzZZZZ"), a breath, and the dot as the app lands.
   One strength (0–1) per ms. */
export function launchWave(births, ignite, land) {
  const a = new Array(land + 26).fill(0)
  const put = (from, to, v) => { for (let t = Math.max(0, Math.round(from)); t < Math.min(a.length, Math.round(to)); t++) a[t] = Math.max(a[t], v) }
  for (const b of births) put(b, b + 10, b >= ignite ? 1 : 0.35 + 0.35 * Math.min(1, b / ignite))
  const z0 = ignite + 70, z1 = land - 60
  for (let t = z0; t < z1; t++) a[t] = Math.max(a[t], 0.12 + 0.88 * ((Math.floor((t - z0) / 10) * 10) / (z1 - z0)) ** 2)   // 10 ms steps
  put(land, land + 26, 1)
  return a
}

// strength per ms → [ms, amplitude 0–255, …] segments, for a motor that can set its strength
export function levels(a) {
  const out = []
  for (const v of a) {
    const amp = Math.round(Math.min(1, Math.max(0, v)) * 255)
    if (out.length && out[out.length - 1] === amp) out[out.length - 2]++
    else out.push(1, amp)
  }
  return out
}

/* strength per ms → [off, on, off, on, …] ms, for a motor that can only switch: each 20 ms
   is on for as many ms as its strength adds up to, from its first moment that isn't still,
   so a weak buzz is short taps and a strong one is unbroken. */
export function onOff(a, period = 20) {
  const out = [0]
  let on = false
  const push = (state, ms) => {
    if (ms <= 0) return
    if (state === on) out[out.length - 1] += ms
    else { out.push(ms); on = state }
  }
  for (let w = 0; w < a.length; w += period) {
    const win = a.slice(w, w + period)
    const first = win.findIndex(v => v > 0)
    if (first < 0) { push(false, win.length); continue }
    const len = Math.min(win.length - first, Math.round(win.reduce((s, v) => s + v, 0)))
    push(false, first); push(true, len); push(false, win.length - first - len)
  }
  return out
}
