import { useEffect, useMemo, useState } from 'react'
import { api, utc } from './api'
import Report from './Report'
import StudentForm from './StudentForm'
import {
  Achievement, CertificateUpload, DetailsForm, DetailsView, levelWord, Photo, PhotoButton,
} from './people'

const TABS = ['Dashboard', 'My report', 'Achievements', 'Profile']
const PHOTO_URL = '/api/student/photo'
const certUrl = id => `/api/student/achievements/${id}/certificate`

/* A signed-in student's own space: enrol first, then a dashboard, their report once the
   coach has verified them, their achievements, and their details. */
export default function Portal({ me, sports, onChange }) {
  const [tab, setTab] = useState('Dashboard')
  const [achievements, setAchievements] = useState(null)
  const [aiOn, setAiOn] = useState(false)
  const s = me.student

  const loadAchievements = () => api.myAchievements().then(setAchievements).catch(() => setAchievements(a => a ?? []))
  useEffect(() => {
    if (!s) return
    loadAchievements()
    api.health().then(h => setAiOn(!!h.documentAI)).catch(() => {})
  }, [s?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!s) return <StudentForm sports={sports} onSaved={m => { onChange(m); setTab('Dashboard') }} />

  const replace = item => setAchievements(list => list.map(a => (a.id === item.id ? item : a)))
  const remove = id => setAchievements(list => list.filter(a => a.id !== id))
  const setStudent = student => onChange({ ...me, student })

  return (
    <>
      <div className="pagehead row noprint" style={{ gap: 16, flexWrap: 'nowrap' }}>
        <Photo url={PHOTO_URL} version={s.photo_version} name={s.name} size={64} />
        <div style={{ minWidth: 0 }}>
          <h1>Hi, {s.name.split(' ')[0]}</h1>
          <p className="muted" style={{ margin: 0 }}>
            {s.sport}{s.ra_number ? ` · ${s.ra_number}` : ''} · {me.email}
          </p>
        </div>
      </div>

      <div className="seg noprint" role="tablist" style={{ maxWidth: 560 }}>
        {TABS.map(t => (
          <button key={t} role="tab" aria-pressed={tab === t} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === 'Dashboard' && (
        <Home me={me} achievements={achievements} onGo={setTab}
              onRefresh={m => { onChange(m); loadAchievements() }} />
      )}
      {tab === 'My report' && (s.status === 'verified'
        ? <Report readOnly />
        : (
          <div className="card empty">
            <b>Your report isn&apos;t ready yet</b>
            It appears here once your coach has recorded your tests and verified your position.
          </div>
        ))}
      {tab === 'Achievements' && (
        <Achievements student={s} list={achievements} aiOn={aiOn}
                      onAdd={a => setAchievements(list => [a, ...(list ?? [])])}
                      onChange={replace} onDelete={remove} />
      )}
      {tab === 'Profile' && (
        <Profile student={s} sports={sports} achievements={achievements} onStudent={setStudent} />
      )}
    </>
  )
}

/* -------------------------------------------------------------- dashboard */

function Home({ me, achievements, onGo, onRefresh }) {
  const s = me.student
  const [busy, setBusy] = useState(false)
  const list = achievements ?? []
  const count = st => list.filter(a => a.status === st).length

  const todo = [
    ['A profile photo', !!s.photo_version, 'Profile'],
    ['Your RA number and date of birth', !!(s.ra_number && s.dob), 'Profile'],
    ['Your mobile and a parent’s mobile', !!(s.phone && (s.father_phone || s.mother_phone)), 'Profile'],
    ['Your Aadhaar number', !!s.aadhaar, 'Profile'],
    ['Your blood group', !!s.blood_group, 'Profile'],
    ['Your height and weight', !!(s.height_cm && s.weight_kg), 'Profile'],
    ...(s.highest_level
      ? [[`Proof of your ${levelWord(s.highest_level).toLowerCase()}-level achievement`,
          list.some(a => a.status !== 'draft'), 'Achievements']]
      : []),
  ]
  const done = todo.filter(t => t[1]).length

  // what has happened lately, newest first
  const updates = useMemo(() => [
    ...(s.status === 'verified' && s.verified_at
      ? [{ at: s.verified_at, tone: 'good', text: `${s.verified_by_name ?? 'Your coach'} verified you as ${s.verified_position}. Your report is ready.` }]
      : []),
    ...list.filter(a => a.reviewed_at && (a.status === 'verified' || a.status === 'rejected')).map(a => ({
      at: a.reviewed_at,
      tone: a.status === 'verified' ? 'good' : 'bad',
      text: a.status === 'verified'
        ? `“${a.title}” was verified${a.reviewed_by_name ? ` by ${a.reviewed_by_name}` : ''}.`
        : `“${a.title}” needs fixing: ${a.review_note}`,
    })),
  ].sort((x, y) => utc(y.at) - utc(x.at)).slice(0, 6), [s, list])

  async function refresh() {
    setBusy(true)
    try { onRefresh(await api.studentMe()) } catch { /* stays as it was */ }
    setBusy(false)
  }

  return (
    <>
      <div className="card">
        {s.status === 'verified' ? (
          <div className="verify">
            <span className="pill good"><i className="dot" />Verified</span>
            <span>Your coach confirmed you play <b>{s.verified_position}</b>.</span>
            <button className="btn sm" onClick={() => onGo('My report')}>Open my report</button>
          </div>
        ) : (
          <div className="verify">
            <span className="pill warn"><i className="dot" />Waiting for your coach</span>
            <span>Your best position, training plan and diet plan appear once your coach has recorded your tests and verified you.</span>
            <button className="btn sec sm" disabled={busy} onClick={refresh}>{busy ? 'Checking…' : 'Check again'}</button>
          </div>
        )}
      </div>

      <div className="tiles">
        <div className="tile">
          <div className="k">Profile</div>
          <div className="v">{Math.round((done / todo.length) * 100)}%</div>
          <div className="s">{done} of {todo.length} done</div>
        </div>
        <div className="tile">
          <div className="k">Verified achievements</div>
          <div className="v">{count('verified')}</div>
          <div className="s">{s.top_verified_level ? `highest: ${levelWord(s.top_verified_level)}` : 'none yet'}</div>
        </div>
        <div className="tile">
          <div className="k">Waiting for check</div>
          <div className="v">{count('pending')}</div>
          <div className="s">sent to your coach</div>
        </div>
        <div className="tile">
          <div className="k">Need your attention</div>
          <div className="v">{count('rejected') + count('draft')}</div>
          <div className="s">to fix or send</div>
        </div>
      </div>

      <div className="split">
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Your profile</h2>
              <p className="muted">What the sports directorate needs from you.</p>
            </div>
          </div>
          <div className="progress" style={{ marginTop: 0, marginBottom: 10 }}>
            <span style={{ width: `${(done / todo.length) * 100}%` }} />
          </div>
          <ul className="checklist">
            {todo.map(([text, ok, where]) => (
              <li key={text} className={ok ? 'done' : ''}>
                {ok ? text : <button className="linkbtn" onClick={() => onGo(where)}>{text}</button>}
              </li>
            ))}
          </ul>
        </div>

        <div className="card">
          <div className="card-head"><div><h2>Updates</h2></div></div>
          {updates.length === 0 ? (
            <p className="muted">
              Nothing yet. When your coach verifies you or checks an achievement, it shows up here.
            </p>
          ) : (
            <ul className="updates">
              {updates.map((u, i) => (
                <li key={i}>
                  <span className={`pill ${u.tone}`}><i className="dot" /></span>
                  <span>{u.text}<small className="muted">{utc(u.at).toLocaleDateString()}</small></span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </>
  )
}

/* ------------------------------------------------------------ achievements */

function Achievements({ student, list, aiOn, onAdd, onChange, onDelete }) {
  if (!list) return <div className="skeleton">Loading…</div>
  return (
    <>
      <div className="card">
        <div className="card-head">
          <div>
            <h2>Add proof of an achievement</h2>
            <p className="muted">
              A photo or PDF of a certificate, medal record or selection letter.
              {aiOn ? ' The details are read off it for you — check them, then send it to your coach.'
                : ' Fill in its details, then send it to your coach.'}
              {' '}Your coach looks at the certificate and verifies it.
            </p>
          </div>
        </div>
        <CertificateUpload aiOn={aiOn} upload={api.addMyAchievement} onUploaded={onAdd} />
      </div>

      {list.length === 0 ? (
        <div className="card empty">
          <b>No achievements yet</b>
          Every certificate you add shows here, with whether your coach has verified it.
        </div>
      ) : (
        <div className="card">
          {list.map(a => (
            <Achievement key={a.id} item={a} as="student" studentName={student.name}
                         certUrl={certUrl(a.id)} onChange={onChange} onDelete={() => onDelete(a.id)} />
          ))}
        </div>
      )}
    </>
  )
}

/* ----------------------------------------------------------------- profile */

function Profile({ student, sports, achievements, onStudent }) {
  const [editing, setEditing] = useState(false)
  const verified = (achievements ?? []).filter(a => a.status === 'verified')

  if (editing) {
    return (
      <DetailsForm mode="self" student={student} sports={sports} submitLabel="Save changes"
                   onCancel={() => setEditing(false)}
                   onSubmit={async body => {
                     onStudent((await api.updateMyProfile(body)).student)
                     setEditing(false)
                     return null
                   }} />
    )
  }

  return (
    <div className="card printable">
      <div className="card-head">
        <div className="row" style={{ gap: 16, flexWrap: 'nowrap' }}>
          <Photo url={PHOTO_URL} version={student.photo_version} name={student.name} size={96} />
          <div>
            <h2>{student.name}</h2>
            <p className="muted">{student.sport}{student.ra_number ? ` · ${student.ra_number}` : ''}</p>
          </div>
        </div>
        <div className="row noprint">
          <PhotoButton label={student.photo_version ? 'Change photo' : 'Add photo'}
                       onPhoto={async blob => onStudent({ ...student, ...(await api.setMyPhoto(blob)) })} />
          <button className="btn sec sm" onClick={() => setEditing(true)}>Edit details</button>
          <button className="btn sec sm" onClick={() => window.print()}>Print / save as PDF</button>
        </div>
      </div>
      <DetailsView student={student} />
      <h3 style={{ marginTop: 18 }}>Verified achievements</h3>
      {verified.length === 0 ? <p className="muted">None yet.</p> : (
        <table className="data">
          <thead><tr><th>Event</th><th>Level</th><th>Year</th><th>Result</th></tr></thead>
          <tbody>
            {verified.map(a => (
              <tr key={a.id}><td>{a.title}</td><td>{levelWord(a.level)}</td><td>{a.year ?? '—'}</td><td>{a.result ?? '—'}</td></tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
