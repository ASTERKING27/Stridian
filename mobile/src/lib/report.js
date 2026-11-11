import { useCallback, useEffect, useState } from 'react'
import { api } from './api'

/* A report, fetched once and shared by the report tab and the pages pushed from it.
   No id: the signed-in student's own (read-only, once verified). An id: a coach's view
   of one of their students. */
const cache = new Map()
const keyOf = id => (id ? String(id) : 'me')      // a route param ('3') and a list's id (3) are one student
export const forgetReport = id => cache.delete(keyOf(id))

export function useReport(id) {
  const key = keyOf(id)
  const [data, setData] = useState(() => cache.get(key) ?? null)
  const [error, setError] = useState(null)
  const load = useCallback(async () => {
    try {
      const d = await (id ? api.analysis(id) : api.myReport())
      cache.set(key, d)
      setData(d)
      setError(null)
    } catch (err) { setError(err) }
  }, [id, key])
  useEffect(() => { if (!cache.has(key)) load(); else setData(cache.get(key)) }, [key, load])
  return { data, error, reload: load }
}

// The position the report is about: the one the coach confirmed, else the best fit.
export function focusPosition(data) {
  const s = data.student
  const name = (s.status === 'verified' && s.verified_position) || data.recommended?.position
  return data.positions.find(p => p.position === name) ?? data.recommended ?? data.positions[0]
}

/* Every measure behind a position's fit: its share of the weight and the points it adds
   (score × share), which sum to the fit. Uses the full breakdown when the server sends
   it, else the top strengths and weak points it always sends. */
export function breakdown(pos, metrics) {
  const rows = pos.contributions ?? [...(pos.drivers ?? []), ...(pos.drags ?? [])]
  const total = rows.reduce((t, r) => t + r.weight, 0) || 1
  const byKey = Object.fromEntries((metrics ?? []).map(m => [m.key, m]))
  return rows
    .map(r => ({ ...r, metric: byKey[r.key], share: r.weight / total, adds: (r.score * r.weight) / total }))
    .sort((a, b) => b.adds - a.adds)
}
