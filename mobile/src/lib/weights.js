/* Position weights, as the coach edits them. The engine scores each kind of evidence on
   its own, so each is edited on its own too, as whole percentages of that source that
   add up to 100 (the engine only cares about the ratios, so this loses nothing). */

export const SOURCES = [
  ['test', 'TESTS', 'Measured in a testing session, plus height and weight from their form.', m => m.source === 'test' || m.source === 'profile'],
  ['match', 'FOOTAGE', 'From tracked match clips — retune once you have footage from your own camera.', m => m.source === 'match'],
  ['card', 'CARDS', 'From the + / 0 / − tallies on finished match cards.', m => m.source === 'card'],
]

// raw weights -> whole percentages of their total that add up to exactly 100 (largest remainder)
export function shares(weights, keys) {
  const total = keys.reduce((t, k) => t + (weights[k] ?? 0), 0)
  if (!total) return Object.fromEntries(keys.map(k => [k, 0]))
  const raw = keys.map(k => ((weights[k] ?? 0) / total) * 100)
  const out = raw.map(Math.floor)
  let left = 100 - out.reduce((a, b) => a + b, 0)
  for (const [, i] of raw.map((r, i) => [r - out[i], i]).sort((a, b) => b[0] - a[0])) {
    if (left-- <= 0) break
    out[i] += 1
  }
  return Object.fromEntries(keys.map((k, i) => [k, out[i]]))
}

// { position: { source: { key: percent } } } for every position and source the sport has
export function toDraft(weights, metrics) {
  return Object.fromEntries(Object.entries(weights).map(([pos, w]) => [pos, Object.fromEntries(SOURCES
    .map(([src, , , match]) => [src, metrics.filter(match).map(m => m.key)])
    .filter(([, keys]) => keys.length)
    .map(([src, keys]) => [src, shares(w, keys)]))]))
}

export const sum = group => Object.values(group).reduce((a, b) => a + b, 0)

// what changed, as the API takes it: { position: { key: weight 0–1 } }, changed groups only
export function changes(draft, base) {
  const out = {}
  for (const [pos, groups] of Object.entries(draft)) {
    for (const [src, group] of Object.entries(groups)) {
      if (JSON.stringify(group) === JSON.stringify(base[pos][src])) continue
      out[pos] = { ...out[pos], ...Object.fromEntries(Object.entries(group).map(([k, v]) => [k, v / 100])) }
    }
  }
  return out
}

// the changed groups that don't add up to 100 yet: [[position, source, total]]
export function unfinished(draft, base) {
  return Object.entries(draft).flatMap(([pos, groups]) => Object.entries(groups)
    .filter(([src, g]) => JSON.stringify(g) !== JSON.stringify(base[pos][src]) && sum(g) !== 100)
    .map(([src, g]) => [pos, src, sum(g)]))
}
