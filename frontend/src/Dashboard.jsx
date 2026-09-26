import { useEffect, useMemo, useState } from 'react'
import { api, download, initials } from './api'
import { levelWord } from './people'
import Report from './Report'

export default function Dashboard({ coach, sports, version, onChanged, onCoach }) {
  const [students, setStudents] = useState(null)
  const [waiting, setWaiting] = useState([])
  const [open, setOpen] = useState(null)          // { id, tab }
  const [search, setSearch] = useState('')
  const [show, setShow] = useState('all')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState('')

  useEffect(() => {
    api.students().then(setStudents).catch(e => setError(e.message))
    api.achievements('pending').then(setWaiting).catch(() => {})
  }, [version])

  async function save(scope) {
    setBusy(scope)
    try {
      await download(`/api/export/squad${scope === 'all' ? '?scope=all' : ''}`)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy('')
    }
  }

  const stats = useMemo(() => {
    if (!students) return null
    const verified = students.filter(s => s.status === 'verified').length
    return {
      total: students.length,
      analysed: students.filter(s => s.has_results).length,
      verified,
      pending: students.length - verified,
    }
  }, [students])

  const visible = useMemo(() => {
    if (!students) return []
    const q = search.trim().toLowerCase()
    return students
      .filter(s => show === 'all' || (show === 'verified') === (s.status === 'verified'))
      .filter(s => !q || s.name.toLowerCase().includes(q) || (s.ra_number ?? '').toLowerCase().includes(q))
  }, [students, search, show])

  if (error) return <div className="banner bad">{error}</div>

  if (open) {
    return (
      <Report id={open.id} initialTab={open.tab} isAdmin={coach.is_admin} sports={sports}
              onBack={() => { setOpen(null); onChanged() }} onChanged={onChanged}
              onDeleted={() => { setOpen(null); onChanged() }} />
    )
  }

  if (!students) return <div className="skeleton">Loading your squad…</div>

  return (
    <>
      <div className="pagehead row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1>{coach.sport} squad</h1>
          <p className="lede" style={{ marginBottom: 0 }}>
            Everyone who registered for {coach.sport}. Open a student for their details and
            achievements, position prediction, training priorities and diet plan.
          </p>
        </div>
        <div className="row">
          <button className="btn sec sm" disabled={!!busy} onClick={() => save('sport')}>
            {busy === 'sport' ? 'Preparing…' : 'Download Excel'}
          </button>
          {coach.is_admin && (
            <button className="btn sec sm" disabled={!!busy} onClick={() => save('all')}>
              {busy === 'all' ? 'Preparing…' : 'All sports (Excel)'}
            </button>
          )}
        </div>
      </div>

      {(!coach.employee_id || !coach.phone) && <MyDetails coach={coach} onSaved={onCoach} missing />}

      <div className="tiles">
        <div className="tile">
          <div className="k">Students</div>
          <div className="v">{stats.total}</div>
          <div className="s">registered for {coach.sport}</div>
        </div>
        <div className="tile">
          <div className="k">Analysed</div>
          <div className="v">{stats.analysed}</div>
          <div className="s">have test results</div>
        </div>
        <div className="tile">
          <div className="k">Verified</div>
          <div className="v">{stats.verified}</div>
          <div className="s">position confirmed</div>
        </div>
        <div className="tile">
          <div className="k">Pending</div>
          <div className="v">{stats.pending}</div>
          <div className="s">awaiting your verification</div>
        </div>
      </div>

      {waiting.length > 0 && (
        <div className="card flush">
          <div style={{ padding: '16px 18px 4px' }}>
            <h2>Achievements to check</h2>
            <p className="muted">Look at each certificate, then verify it or say what&apos;s wrong.</p>
          </div>
          <div className="rows">
            {waiting.map(a => (
              <button key={a.id} className="rowitem" onClick={() => setOpen({ id: a.student_id, tab: 'Profile' })}>
                <span className="who">
                  <b>{a.title}</b>
                  <span>{a.student_name} · {[levelWord(a.level), a.year, a.result].filter(Boolean).join(' · ')}</span>
                </span>
                <span className="pill warn"><i className="dot" />Check</span>
              </button>
            ))}
          </div>
        </div>
      )}

      <EnrolCode sport={coach.sport} />

      <div className="card flush">
        <div className="row" style={{ padding: '14px 18px', borderBottom: '1px solid var(--line)', gap: 10 }}>
          <input placeholder="Search by name or RA number…" aria-label="Search students" style={{ flex: '1 1 200px' }}
                 value={search} onChange={e => setSearch(e.target.value)} />
          <div className="toggles" role="group" aria-label="Show">
            {['all', 'pending', 'verified'].map(k => (
              <button key={k} type="button" aria-pressed={show === k} onClick={() => setShow(k)}>
                {k[0].toUpperCase() + k.slice(1)}
              </button>
            ))}
          </div>
        </div>

        {visible.length === 0 ? (
          <p className="empty">
            <b>{students.length === 0 ? 'Nobody here yet' : 'Nobody matches'}</b>
            {students.length === 0
              ? `Students enrol themselves on this site with their university email and the enrolment code above.`
              : 'Try a different name or filter.'}
          </p>
        ) : (
          <div className="rows">
            {visible.map(s => (
              <button key={s.id} className="rowitem" onClick={() => setOpen({ id: s.id })}>
                <span className="avatar" aria-hidden="true">{initials(s.name)}</span>
                <span className="who">
                  <b>{s.name}</b>
                  <span>
                    {s.ra_number ? `${s.ra_number} · ` : ''}
                    {s.age ? `${s.age} yrs` : 'age not set'} · {s.declared_position || 'role not set'}
                    {s.achievements_verified
                      ? ` · ${s.achievements_verified} achievement${s.achievements_verified > 1 ? 's' : ''} (best: ${levelWord(s.top_verified_level)})`
                      : ''}
                    {s.video_count ? ` · ${s.video_count} clip${s.video_count > 1 ? 's' : ''}` : ''}
                  </span>
                </span>
                {s.achievements_pending > 0 && (
                  <span className="pill accent" title="Achievements waiting for you to check">
                    {s.achievements_pending} to check
                  </span>
                )}
                {s.status === 'verified' ? (
                  <span className="pill good"><i className="dot" />{s.verified_position}</span>
                ) : (
                  <span className={`pill ${s.has_results ? 'accent' : 'warn'}`}>
                    <i className="dot" />{s.has_results ? 'Ready to verify' : 'Awaiting results'}
                  </span>
                )}
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

/* A coach's own details. Accounts from before sign-up asked for them see this on the
   dashboard until they are filled in; anyone can open it from their name in the menu. */
export function MyDetails({ coach, onSaved, missing = false }) {
  const [f, setF] = useState({
    name: coach.name ?? '', employee_id: coach.employee_id ?? '', phone: coach.phone ?? '',
    designation: coach.designation ?? '',
  })
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)
  const [coaches, setCoaches] = useState(null)
  const set = (k, v) => setF(x => ({ ...x, [k]: v }))

  useEffect(() => {
    if (coach.is_admin && !missing) api.coaches().then(setCoaches).catch(() => {})
  }, [coach.is_admin, missing])

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setStatus(null)
    try {
      const saved = await api.updateMe(f)
      setStatus({ ok: true, text: 'Saved.' })
      onSaved(saved)
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {!missing && (
        <div className="pagehead">
          <h1>Your details</h1>
          <p className="lede">{coach.email} · {coach.is_admin ? 'Admin' : `${coach.sport} coach`}</p>
        </div>
      )}
      <form className="card" onSubmit={submit}>
        {missing && (
          <div className="card-head">
            <div>
              <h2>Add your employee ID and mobile</h2>
              <p className="muted">The sports directorate keeps these for every coach.</p>
            </div>
          </div>
        )}
        <div className="grid2">
          <div className="field">
            <label htmlFor="md-name">Name *</label>
            <input id="md-name" required value={f.name} onChange={e => set('name', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="md-emp">Employee ID *</label>
            <input id="md-emp" required value={f.employee_id} onChange={e => set('employee_id', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="md-phone">Mobile *</label>
            <input id="md-phone" type="tel" inputMode="tel" required value={f.phone}
                   onChange={e => set('phone', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="md-des">Designation</label>
            <input id="md-des" value={f.designation} placeholder="e.g. Assistant Professor, Physical Education"
                   onChange={e => set('designation', e.target.value)} />
          </div>
        </div>
        <button className="btn" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
        {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
      </form>

      {coaches && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Every coach</h2>
              <p className="muted">Only admins see this list. Admins are set on the server (ADMIN_EMAILS).</p>
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data">
              <thead>
                <tr><th>Name</th><th>Sport</th><th>Employee ID</th><th>Mobile</th><th>Email</th><th>Designation</th></tr>
              </thead>
              <tbody>
                {coaches.map(c => (
                  <tr key={c.id}>
                    <td>{c.name}{c.is_admin ? ' (admin)' : ''}</td><td>{c.sport}</td>
                    <td>{c.employee_id || '—'}</td><td>{c.phone || '—'}</td><td>{c.email}</td>
                    <td>{c.designation || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}

/* The code students type to enrol in this sport. Only people who have it (and a
   university email) can add themselves to the squad. */
function EnrolCode({ sport }) {
  const [code, setCode] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.enrolCode().then(r => setCode(r.code)).catch(e => setError(e.message))
  }, [])

  async function renew() {
    if (!confirm('Make a new enrolment code? The current one stops working for anyone who '
                 + "hasn't enrolled yet. Students already enrolled aren't affected.")) return
    setError('')
    try {
      setCode((await api.newEnrolCode()).code)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div className="card">
      <div className="verify">
        <span>{sport} enrolment code</span>
        <code className="enrolcode">{code ?? '······'}</code>
        <button className="linkbtn" onClick={renew} disabled={!code}>Make a new code</button>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        Give this to your students. They sign in with their university email, pick {sport} and
        type this code to enrol. Make a new one if it has been shared too widely.
      </p>
      {error && <div className="note err">{error}</div>}
    </div>
  )
}
