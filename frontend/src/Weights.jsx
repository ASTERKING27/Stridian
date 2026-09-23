import { useEffect, useState } from 'react'
import { api } from './api'

const slugify = name => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

// The two kinds of evidence are scored separately, so they are edited separately too.
const GROUPS = [
  {
    key: 'test',
    title: 'Test battery & physique',
    hint: 'Measured in a testing session, plus height and weight from the student’s own form.',
    match: m => m.source !== 'match',
  },
  {
    key: 'match',
    title: 'Match footage',
    hint: 'Derived from tracked match clips. Retune these once you have footage from your own camera setup — framing shifts the numbers more than the players do.',
    match: m => m.source === 'match',
  },
]

export default function Weights({ coach, onSaved }) {
  const slug = slugify(coach.sport)
  const [data, setData] = useState(null)
  const [draft, setDraft] = useState(null)
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.weights(slug)
      .then(d => { setData(d); setDraft(structuredClone(d.weights)) })
      .catch(e => setStatus({ ok: false, text: e.message }))
  }, [slug])

  if (!data || !draft) {
    return status ? <div className="banner bad">{status.text}</div> : <div className="skeleton">Loading weights…</div>
  }

  const dirty = JSON.stringify(draft) !== JSON.stringify(data.weights)
  const setWeight = (position, key, value) =>
    setDraft(d => ({ ...d, [position]: { ...d[position], [key]: value } }))

  async function save() {
    setBusy(true)
    setStatus(null)
    try {
      const res = await api.saveWeights(slug, draft)
      setData({ ...data, weights: res.weights })
      setDraft(structuredClone(res.weights))
      setStatus({ ok: true, text: 'Saved. Every report now uses these weights.' })
      onSaved()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  async function reset() {
    setBusy(true)
    try {
      const res = await api.resetWeights(slug)
      setData({ ...data, weights: res.weights })
      setDraft(structuredClone(res.weights))
      setStatus({ ok: true, text: 'Back to the built-in defaults.' })
      onSaved()
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div className="pagehead">
        <h1>Scoring weights</h1>
        <p className="lede">
          How much each measurement counts towards each {coach.sport} position. Raise what
          your programme cares about, drop what it doesn&apos;t — every report recalculates
          from these. They need not add up to 1; the engine divides by the total it used.
        </p>
      </div>

      <div className="card">
        <div className="row">
          <button className="btn" onClick={save} disabled={busy || !dirty}>
            {busy ? 'Saving…' : dirty ? 'Save changes' : 'No changes'}
          </button>
          <button className="btn sec" onClick={reset} disabled={busy}>Reset to defaults</button>
        </div>
        {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
      </div>

      {Object.entries(draft).map(([position, weights]) => {
        const total = Object.values(weights).reduce((a, b) => a + b, 0)
        const changed = JSON.stringify(weights) !== JSON.stringify(data.defaults[position])
        return (
          <div className="card" key={position}>
            <div className="card-head">
              <div><h2>{position}</h2></div>
              {changed && <span className="pill warn"><i className="dot" />edited</span>}
            </div>
            {GROUPS.map(group => {
              const metrics = data.metrics.filter(group.match)
              if (metrics.length === 0) return null
              const groupTotal = metrics.reduce((a, m) => a + (weights[m.key] ?? 0), 0)
              return (
                <div key={group.key} style={{ marginTop: 14 }}>
                  <h3>{group.title}</h3>
                  <p className="muted" style={{ marginTop: -4, marginBottom: 10 }}>{group.hint}</p>
                  {metrics.map(m => {
                    const w = weights[m.key] ?? 0
                    return (
                      <div className="wrow" key={m.key}>
                        <label htmlFor={`${position}-${m.key}`}>
                          {m.label}
                          {groupTotal > 0 && w > 0 && (
                            <em> — {Math.round((w / groupTotal) * 100)}% of this source</em>
                          )}
                        </label>
                        <input id={`${position}-${m.key}`} type="range" min="0" max="1" step="0.05"
                               value={w}
                               onChange={e => setWeight(position, m.key, Number(e.target.value))} />
                        <span className="wv">{w.toFixed(2)}</span>
                      </div>
                    )
                  })}
                </div>
              )
            })}
            <p className="muted" style={{ marginTop: 10 }}>
              Total weight on this role: {total.toFixed(2)}.
            </p>
          </div>
        )
      })}
    </>
  )
}
