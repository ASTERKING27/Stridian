import { useEffect, useMemo, useState } from 'react'
import { api, initials } from './api'
import Report from './Report'

export default function Dashboard({ coach, version, onChanged }) {
  const [students, setStudents] = useState(null)
  const [openId, setOpenId] = useState(null)
  const [search, setSearch] = useState('')
  const [show, setShow] = useState('all')
  const [error, setError] = useState('')

  useEffect(() => {
    api.students().then(setStudents).catch(e => setError(e.message))
  }, [version])

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
      .filter(s => !q || s.name.toLowerCase().includes(q))
  }, [students, search, show])

  if (error) return <div className="banner bad">{error}</div>

  if (openId) {
    return (
      <Report id={openId} onBack={() => setOpenId(null)} onChanged={onChanged}
              onDeleted={() => { setOpenId(null); onChanged() }} />
    )
  }

  if (!students) return <div className="skeleton">Loading your squad…</div>

  return (
    <>
      <div className="pagehead">
        <h1>{coach.sport} squad</h1>
        <p className="lede">
          Everyone who registered for {coach.sport}. Open a student for their position
          prediction, training priorities and diet plan.
        </p>
      </div>

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

      <EnrolCode sport={coach.sport} />

      <div className="card flush">
        <div className="row" style={{ padding: '14px 18px', borderBottom: '1px solid var(--line)', gap: 10 }}>
          <input placeholder="Search by name…" aria-label="Search students" style={{ flex: '1 1 200px' }}
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
              <button key={s.id} className="rowitem" onClick={() => setOpenId(s.id)}>
                <span className="avatar" aria-hidden="true">{initials(s.name)}</span>
                <span className="who">
                  <b>{s.name}</b>
                  <span>
                    {s.age ? `${s.age} yrs` : 'age not set'} · {s.declared_position || 'role not set'}
                    {s.video_count ? ` · ${s.video_count} clip${s.video_count > 1 ? 's' : ''}` : ''}
                  </span>
                </span>
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
