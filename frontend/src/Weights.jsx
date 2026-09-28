import { useEffect, useState } from 'react'
import { api } from './api'

const slugify = name => name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

// The three kinds of evidence are scored separately, so they are edited separately too.
const GROUPS = [
  {
    key: 'test',
    title: 'Test battery & physique',
    hint: 'Measured in a testing session, plus height and weight from the student’s own form.',
    match: m => m.source === 'test' || m.source === 'profile',
  },
  {
    key: 'match',
    title: 'Match footage',
    hint: 'Derived from tracked match clips. Retune these once you have footage from your own camera setup — framing shifts the numbers more than the players do.',
    match: m => m.source === 'match',
  },
  {
    key: 'card',
    title: 'Match cards',
    hint: 'Worked out from the + / 0 / − tallies on finished match cards. The “share of actions” ones describe what a player does in a match, which is what sets the roles apart.',
    match: m => m.source === 'card',
  },
]

export default function Weights({ coach, onSaved }) {
  const [view, setView] = useState('weights')
  return (
    <>
      <div className="seg" role="group" aria-label="What to tune" style={{ maxWidth: 420 }}>
        <button aria-pressed={view === 'weights'} onClick={() => setView('weights')}>Position weights</button>
        <button aria-pressed={view === 'levels'} onClick={() => setView('levels')}>Level targets</button>
      </div>
      {view === 'weights' ? <PositionWeights coach={coach} onSaved={onSaved} /> : <LevelTargets coach={coach} />}
    </>
  )
}

function PositionWeights({ coach, onSaved }) {
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

/* ---------------------------------------------------------- level targets */

const TEAMS = [['M', 'Men'], ['W', 'Women']]
const BASIS = { published: 'published', mixed: 'published + estimated', estimated: 'estimated' }

// the five numbers for one team (and format) out of a measure's targets
const ladderOf = (m, team, fmt) => (m.formats ? m.targets[fmt]?.[team] : m.targets[team]) ?? null

/* What a player typically posts at each level, per measure. Reports read every number
   against these; nothing else (scores, positions, training) does. */
function LevelTargets({ coach }) {
  const slug = slugify(coach.sport)
  const [data, setData] = useState(null)
  const [team, setTeam] = useState('M')
  const [fmt, setFmt] = useState(null)
  const [drafts, setDrafts] = useState({})
  const [notes, setNotes] = useState({})
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    // an admin switching sport starts clean: another sport's edits must not carry over
    setData(null)
    setDrafts({})
    setNotes({})
    api.levels(slug).then(d => { setData(d); setFmt(d.formats[0]?.key ?? null) }).catch(e => setError(e.message))
  }, [slug])

  if (!data) return error ? <div className="banner bad">{error}</div> : <div className="skeleton">Loading level targets…</div>

  const draftKey = m => `${m.key}|${team}|${m.formats ? fmt : ''}`
  const shown = m => drafts[draftKey(m)] ?? (ladderOf(m, team, fmt) ?? ['', '', '', '', '']).map(v => String(v))
  const dirty = m => drafts[draftKey(m)] !== undefined
  const setCell = (m, i, v) => setDrafts(d => ({ ...d, [draftKey(m)]: shown(m).map((x, j) => (j === i ? v : x)) }))
  const replace = metric => setData(d => ({ ...d, metrics: d.metrics.map(m => (m.key === metric.key ? metric : m)) }))
  // a save keeps unsaved edits to the other team's (or format's) ladder; a reset drops them
  const forget = (m, all = false) => setDrafts(d => Object.fromEntries(Object.entries(d).filter(([k]) =>
    (all ? !k.startsWith(`${m.key}|`) : k !== draftKey(m)))))

  async function save(m) {
    const cells = shown(m).map(v => v.trim())
    const blank = cells.every(v => v === '')
    if (!blank && cells.some(v => v === '' || !Number.isFinite(Number(v)))) {
      setNotes(n => ({ ...n, [m.key]: { ok: false, text: 'Fill in all five levels, or clear all five.' } }))
      return
    }
    const steps = blank ? null : cells.map(Number)
    const targets = structuredClone(m.targets)
    if (m.formats) targets[fmt] = { ...(targets[fmt] ?? { M: null, W: null }), [team]: steps }
    else targets[team] = steps
    setBusy(m.key)
    try {
      replace(await api.saveLevel(slug, m.key, targets))
      forget(m)
      setNotes(n => ({ ...n, [m.key]: { ok: true, text: 'Saved — reports use it now.' } }))
    } catch (err) {
      setNotes(n => ({ ...n, [m.key]: { ok: false, text: err.message } }))
    } finally {
      setBusy('')
    }
  }

  async function reset(m) {
    setBusy(m.key)
    try {
      replace(await api.resetLevel(slug, m.key))
      forget(m, true)
      setNotes(n => ({ ...n, [m.key]: { ok: true, text: 'Back to the built-in numbers.' } }))
    } catch (err) {
      setNotes(n => ({ ...n, [m.key]: { ok: false, text: err.message } }))
    } finally {
      setBusy('')
    }
  }

  return (
    <>
      <div className="pagehead">
        <h1>Level targets</h1>
        <p className="lede">
          What {coach.sport} players typically post at each level, University to International.
          A report reads each of a student&apos;s numbers against these and says which level it
          reaches. They start from published norms where those exist and estimates where they
          don&apos;t — retune them to what you see at your level.
        </p>
      </div>

      <div className="card">
        <div className="row">
          <div className="seg" role="group" aria-label="Team" style={{ marginBottom: 0 }}>
            {TEAMS.map(([k, label]) => (
              <button key={k} aria-pressed={team === k} onClick={() => setTeam(k)}>{label}</button>
            ))}
          </div>
          {data.formats.length > 0 && (
            <div className="seg" role="group" aria-label="Format" style={{ marginBottom: 0 }}>
              {data.formats.map(f => (
                <button key={f.key} aria-pressed={fmt === f.key} onClick={() => setFmt(f.key)}>{f.label}</button>
              ))}
            </div>
          )}
        </div>
        <p className="muted" style={{ marginTop: 10, marginBottom: 0 }}>
          Each row must never get worse going up the levels. Clear all five to stop comparing a
          measure across levels. {data.formats.length > 0 && 'The format only matters for match-card measures.'}
        </p>
      </div>

      {/* footage last: it counts least */}
      {[GROUPS[0], GROUPS[2], GROUPS[1]].map(group => {
        const metrics = data.metrics.filter(group.match)
        if (metrics.length === 0) return null
        return (
          <div className="card" key={group.key}>
            <div className="card-head">
              <div>
                <h2>{group.title}</h2>
                {group.key === 'match' && (
                  <p className="muted">Counts half as much as the tests and match cards towards a player&apos;s overall level.</p>
                )}
              </div>
            </div>
            <div className="sheetwrap">
              <table className="data ladder">
                <thead>
                  <tr>
                    <th>Measure</th>
                    {data.levels.map(l => <th key={l} className="num">{l}</th>)}
                    <th />
                  </tr>
                </thead>
                <tbody>
                  {metrics.map(m => {
                    const cells = shown(m)
                    const note = notes[m.key]
                    return (
                      <tr key={m.key}>
                        <td style={{ minWidth: 200 }}>
                          <b>{m.label}</b>{m.unit ? ` (${m.unit})` : ''}
                          <div className="muted" style={{ fontSize: '.78rem' }}>
                            {m.better === 'lower' ? 'Lower' : 'Higher'} is better · {BASIS[m.basis] ?? m.basis}
                            {m.custom && <span className="pill warn" style={{ marginLeft: 6 }}><i className="dot" />edited</span>}
                          </div>
                          <details className="sources">
                            <summary>Where these come from</summary>
                            <p style={{ margin: '4px 0 0' }}>{m.note}</p>
                            {m.sources.length > 0 && <ul>{m.sources.map((src, i) => <li key={i}>{src}</li>)}</ul>}
                          </details>
                          {note && <div className={`note ${note.ok ? 'ok' : 'err'}`}>{note.text}</div>}
                        </td>
                        {data.levels.map((l, i) => (
                          <td key={l} className="num">
                            <input aria-label={`${m.label} ${l}`} inputMode="decimal" value={cells[i]}
                                   onChange={e => setCell(m, i, e.target.value)} />
                          </td>
                        ))}
                        <td>
                          <div className="row" style={{ flexWrap: 'nowrap' }}>
                            <button className="btn sm" disabled={busy === m.key || !dirty(m)} onClick={() => save(m)}>
                              {busy === m.key ? 'Saving…' : 'Save'}
                            </button>
                            {m.custom && (
                              <button className="btn sec sm" disabled={busy === m.key} onClick={() => reset(m)}>Reset</button>
                            )}
                          </div>
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )
      })}
    </>
  )
}
