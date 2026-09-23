import { useEffect, useMemo, useState } from 'react'
import { api, formatValue, inFlight, initials, parseValue, usePoll } from './api'
import VideoCard, { VideoUploader } from './VideoCard'

export default function CoachEntry({ coach, sports, version, onSaved }) {
  const [students, setStudents] = useState(null)
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.students().then(setStudents).catch(e => setError(e.message))
  }, [version])

  const selected = students?.find(s => s.id === selectedId) ?? null

  const visible = useMemo(() => {
    if (!students) return []
    const q = search.trim().toLowerCase()
    return q ? students.filter(s => s.name.toLowerCase().includes(q)) : students
  }, [students, search])

  if (error) return <div className="banner bad">{error}</div>
  if (!students) return <div className="skeleton">Loading your squad…</div>

  return (
    <>
      <div className="pagehead">
        <h1>Coach entry</h1>
        <p className="lede">
          Your {coach.sport} squad only. Pick a student, record their test results, and
          upload clips for movement analysis.
        </p>
      </div>

      <div className="card flush">
        <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--line)' }}>
          <input placeholder="Search by name…" aria-label="Search students"
                 value={search} onChange={e => setSearch(e.target.value)} />
        </div>

        {visible.length === 0 ? (
          <p className="empty">
            <b>{students.length === 0 ? 'No students yet' : 'Nobody matches that search'}</b>
            {students.length === 0
              ? `Students register themselves from the Student Entry tab — anyone who picks ${coach.sport} appears here.`
              : 'Try a different name.'}
          </p>
        ) : (
          <div className="rows">
            {visible.map(s => (
              <button key={s.id} className="rowitem" aria-selected={selectedId === s.id}
                      onClick={() => setSelectedId(s.id === selectedId ? null : s.id)}>
                <span className="avatar" aria-hidden="true">{initials(s.name)}</span>
                <span className="who">
                  <b>{s.name}</b>
                  <span>
                    {s.age ? `${s.age} yrs` : 'age not set'}
                    {s.declared_position ? ` · ${s.declared_position}` : ''}
                    {s.video_count ? ` · ${s.video_count} clip${s.video_count > 1 ? 's' : ''}` : ''}
                  </span>
                </span>
                <span className={`pill ${s.has_results ? 'good' : 'warn'}`}>
                  <i className="dot" />{s.has_results ? 'Results in' : 'Awaiting results'}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selected && (
        <ResultsPanel key={selected.id} student={selected} sports={sports}
                      onSaved={onSaved} />
      )}
    </>
  )
}

function ResultsPanel({ student, sports, onSaved }) {
  const sport = sports.find(s => s.name === student.sport)
  const tests = sport.metrics.filter(m => m.source === 'test')

  const [values, setValues] = useState({})
  const [position, setPosition] = useState(student.declared_position ?? '')
  const [notes, setNotes] = useState(student.coach_notes ?? '')
  const [sessions, setSessions] = useState(student.sessions_observed ?? '')
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [videos, setVideos] = useState([])

  const loadVideos = () => api.videos(student.id).then(setVideos).catch(() => {})
  usePoll(videos.some(v => inFlight(v.status)), loadVideos)

  useEffect(() => {
    api.results(student.id)
      .then(r => setValues(Object.fromEntries(
        Object.entries(r.results).map(([k, v]) => {
          const metric = tests.find(t => t.key === k)
          return [k, metric?.key === 'timeTrial2km' ? formatValue(v, metric) : String(v)]
        })
      )))
      .catch(() => {})
    loadVideos()
  }, [student.id]) // eslint-disable-line react-hooks/exhaustive-deps

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setStatus(null)
    try {
      const results = {}
      for (const t of tests) {
        const parsed = parseValue(values[t.key])
        if (parsed !== null) results[t.key] = parsed
      }
      const res = await api.saveResults(student.id, {
        results,
        declared_position: position,
        coach_notes: notes,
        sessions_observed: sessions === '' ? null : Number(sessions),
      })
      setStatus({
        ok: true,
        text: `Saved ${res.saved} measurement${res.saved === 1 ? '' : 's'} for ${student.name}. Open the Dashboard for the full report.`,
      })
      onSaved()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  async function removeVideo(id) {
    await api.deleteVideo(id)
    await loadVideos()
    onSaved()
  }

  return (
    <>
      <form className="card" onSubmit={submit}>
        <div className="card-head">
          <div>
            <h2>{student.name}</h2>
            <p className="muted">{sport.note}</p>
          </div>
        </div>

        <div className="field" style={{ maxWidth: 320 }}>
          <label htmlFor="cpos">Position / role</label>
          <select id="cpos" value={position} onChange={e => setPosition(e.target.value)}>
            <option value="">Not assigned</option>
            {sport.positions.map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>

        <h3 style={{ marginTop: 20 }}>Test results</h3>
        <div className="grid3">
          {tests.map(t => (
            <div className="field" key={t.key}>
              <label htmlFor={t.key}>
                {t.label} ({t.unit}) <em style={{ color: 'var(--ink-3)', fontStyle: 'normal' }}>
                  {t.direction === 'lower' ? '↓ better' : '↑ better'}
                </em>
              </label>
              <input id={t.key} inputMode="decimal"
                     placeholder={t.key === 'timeTrial2km' ? 'e.g. 8:30' : `${t.poor} → ${t.elite}`}
                     value={values[t.key] ?? ''}
                     onChange={e => setValues(v => ({ ...v, [t.key]: e.target.value }))} />
            </div>
          ))}
        </div>
        <p className="muted">
          Placeholders show the poor → elite range each score is measured against. Leave a
          field blank if it wasn't tested — the prediction just reports lower confidence.
        </p>

        <div className="grid2" style={{ marginTop: 14 }}>
          <div className="field">
            <label htmlFor="sess">Sessions observed</label>
            <input id="sess" type="number" min="0" value={sessions}
                   onChange={e => setSessions(e.target.value)} />
          </div>
        </div>

        <div className="field">
          <label htmlFor="cnotes">Coach notes</label>
          <textarea id="cnotes" value={notes} onChange={e => setNotes(e.target.value)}
                    placeholder="What you saw in training…" />
        </div>

        <button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save results'}</button>
        {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
      </form>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Drill video</h2>
            <p className="muted">
              One player only — MediaPipe measures their technique frame by frame.
              Side-on, whole body in frame, steady camera. mp4, mov, avi, mkv, webm or
              m4v up to 200 MB. For footage with the whole squad in it, use the Match
              Footage tab instead.
            </p>
          </div>
        </div>

        <VideoUploader studentId={student.id}
                       onUploaded={() => { loadVideos(); onSaved() }} />

        <div style={{ marginTop: 16 }}>
          {videos.map(v => (
            <VideoCard key={v.id} video={v} onDelete={() => removeVideo(v.id)} />
          ))}
        </div>
      </div>
    </>
  )
}
