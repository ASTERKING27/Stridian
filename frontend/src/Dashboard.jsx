import { useEffect, useMemo, useState } from 'react'
import { api, download, initials } from './api'
import { Seg, Switcher } from './fx'
import Icon from './Icon'
import { levelWord } from './people'
import Report from './Report'
import Court from './site/Court'
import { SPORTKIT } from './site/sportkit'

export default function Dashboard({ coach, sports, version, onChanged, onCoach, onGo }) {
  const [students, setStudents] = useState(null)
  const [waiting, setWaiting] = useState([])
  const [open, setOpen] = useState(null)          // { id, tab }
  const [lastOpen, setLastOpen] = useState(null)  // so closing a report slides back the way it came
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

  const openReport = o => {
    setLastOpen(`r${o.id}`)
    setOpen(o)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }
  const close = () => { setOpen(null); onChanged() }

  return (
    <Switcher value={open ? `r${open.id}` : 'list'} order={['list', lastOpen]}>
      {k => (k === 'list' ? squad() : (
        <Report id={Number(k.slice(1))} initialTab={open?.tab} isAdmin={coach.is_admin} sports={sports}
                onBack={close} onChanged={onChanged} onDeleted={close} />
      ))}
    </Switcher>
  )

  function squad() {
    if (!students) return <div className="skeleton">Loading your squad…</div>
    return (
    <>
      <header className="band">
        <div className="band-copy">
          <div className="band-title">
            <i className="band-ico" aria-hidden="true"><Icon path={SPORTKIT[coach.sport]?.icon} name="chart" size={34} /></i>
            <h1>{coach.sport} squad</h1>
          </div>
          <p className="lede">
            Everyone who registered for {coach.sport}. Open a student for their details and
            achievements, position prediction, training priorities and diet plan.
          </p>
          <div className="row">
            <button className="btn sec" disabled={!!busy} onClick={() => save('sport')}>
              <Icon name="download" size={18} />{busy === 'sport' ? 'Preparing' : 'Download Excel'}
            </button>
            {coach.is_admin && (
              <button className="btn sec" disabled={!!busy} onClick={() => save('all')}>
                {busy === 'all' ? 'Preparing' : 'All sports (Excel)'}
              </button>
            )}
          </div>
        </div>
        {SPORTKIT[coach.sport] && <div className="band-art" aria-hidden="true"><Court sport={coach.sport} /></div>}
      </header>

      <div className="tiles strip">
        {[['Students', stats.total, `registered for ${coach.sport}`], ['Analysed', stats.analysed, 'have test results'],
          ['Verified', stats.verified, 'position confirmed'], ['Pending', stats.pending, 'position not confirmed yet']].map(([k, v, note]) => (
          <div className="tile" key={k}>
            <div className="k">{k}</div>
            <div className="v">{v}</div>
            <div className="s">{note}</div>
          </div>
        ))}
      </div>

      {(!coach.employee_id || !coach.phone) && <MyDetails coach={coach} onSaved={onCoach} missing />}

      <div className="deck">
        <CoachCorner version={version} onOpen={openReport} onGo={onGo} />
        <div className="deck-side">
          <EnrolCode sport={coach.sport} />
          {waiting.length > 0 && (
            <div className="card flush">
              <div style={{ padding: '22px 22px 8px' }}>
                <h2>Achievements to check</h2>
                <p className="muted">Look at each certificate, then verify it or say what&apos;s wrong.</p>
              </div>
              <div className="rows">
                {waiting.map(a => (
                  <button key={a.id} className="rowitem" onClick={() => openReport({ id: a.student_id, tab: 'Profile' })}>
                    <span className="who">
                      <b>{a.title}</b>
                      <span>{a.student_name}, {[levelWord(a.level), a.year, a.result].filter(Boolean).join(', ')}</span>
                    </span>
                    <span className="pill accent">Check</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      <Lineup students={students} sport={coach.sport} onOpen={openReport} />

      <div className="card flush">
        <div className="row" style={{ padding: '14px 18px', borderBottom: '1px solid var(--line)', gap: 10 }}>
          <input placeholder="Search by name or RA number…" aria-label="Search students" style={{ flex: '1 1 200px' }}
                 value={search} onChange={e => setSearch(e.target.value)} />
          <Seg options={[['all', 'All'], ['pending', 'Pending'], ['verified', 'Verified']]} value={show}
               onChange={setShow} label="Show" style={{ marginBottom: 0 }} />
        </div>

        {visible.length === 0 ? (
          <p className="empty">
            <b>{students.length === 0 ? 'Nobody here yet' : 'Nobody matches'}</b>
            {students.length === 0
              ? `Students enrol themselves on this site with their university email and the enrolment code above.`
              : 'Try a different name or filter.'}
          </p>
        ) : (
          <div className="rows swap" key={show}>
            {visible.map(s => (
              <button key={s.id} className="rowitem" onClick={() => openReport({ id: s.id })}>
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
}

/* The second coach, for coaches: what needs them today and who to talk to, from the
   squad's own numbers (backend/coach.py coach_feed). Each name opens that player. */
const FEED = {
  verify: ['shield', 'Overview'], certs: ['card', 'Profile'], team: ['student', 'Profile'],
  near: ['target', 'Levels'], movers: ['trend', 'Levels'], drops: ['down', 'Levels'],
  untested: ['clipboard', 'Overview'], stale: ['clipboard', 'Overview'], streaks: ['flame', 'Overview'],
  clear: ['check', 'Overview'],
}

function CoachCorner({ version, onOpen, onGo }) {
  const [feed, setFeed] = useState(null)
  useEffect(() => {
    api.coachFeed().then(r => setFeed(r.feed)).catch(() => setFeed([]))
  }, [version])
  if (!feed?.length) {
    return (
      <section className="card corner">
        <h2>Today&apos;s brief</h2>
        <p className="muted">{feed ? 'Nothing needs you right now. It fills in as results and certificates arrive.' : 'Reading your squad'}</p>
      </section>
    )
  }
  return (
    <section className="card corner swap">
      <div className="card-head">
        <div>
          <h2>Today&apos;s brief</h2>
        </div>
      </div>
      <div className="feed">
        {feed.map(f => {
          const [icon, tab] = FEED[f.kind] ?? ['chart', 'Overview']
          return (
            <article key={f.kind} className={`feeditem ${f.kind}`}>
              <span className="say-ico"><Icon name={icon} size={16} /></span>
              <div style={{ minWidth: 0 }}>
                <h3>{f.title}</h3>
                <p>{f.body}</p>
                {f.people.length > 0 && (
                  <div className="people">
                    {f.people.slice(0, 6).map(p => (
                      <button key={p.id} className="person" onClick={() => onOpen({ id: p.id, tab })}>
                        <b>{p.name}</b>{p.text && <small>{p.text}</small>}
                      </button>
                    ))}
                    {f.people.length > 6 && <span className="muted">+{f.people.length - 6} more</span>}
                  </div>
                )}
                {f.tab === 'coach' && onGo && (
                  <button className="linkbtn" onClick={() => onGo('coach')}>Open Coach Entry</button>
                )}
              </div>
            </article>
          )
        })}
      </div>
    </section>
  )
}

/* The squad on its own court: every verified player where their position plays, the open
   positions left dashed. Each sport names its list its own way. */
const LINEUP = {
  Football: ['Starting XI', 'pitch'], Basketball: ['Starting five', 'court'], Volleyball: ['Rotation', 'court'],
  Cricket: ['Batting order', 'field'], Badminton: ['Playing styles', 'court'], Tennis: ['Playing styles', 'court'],
  'Kho-Kho': ['Chasing order', 'field'],
}
const shortName = name => { const [first, ...rest] = name.trim().split(/\s+/); return rest.length ? `${first} ${rest.at(-1)[0]}.` : first }

function Lineup({ students, sport, onOpen }) {
  const kit = SPORTKIT[sport]
  const verified = students.filter(s => s.status === 'verified')
  const teams = ['M', 'W'].filter(t => verified.some(s => s.category === t))
  const [team, setTeam] = useState(null)
  if (!kit) return null
  const shown = teams.includes(team) ? team : teams[0]
  const pool = teams.length > 1 ? verified.filter(s => s.category === shown) : verified
  const taken = new Set()
  const players = kit.spots.map(spot => {
    const p = pool.find(s => s.verified_position === spot.pos && !taken.has(s.id))
    if (p) taken.add(p.id)
    return p ? { id: p.id, name: shortName(p.name), full: p.name } : null
  })
  const held = players.filter(Boolean).length
  const [title, ground] = LINEUP[sport] ?? ['Line-up', 'court']
  return (
    <section className="card lineup">
      <div className="card-head">
        <div>
          <h2>Squad on the {ground}</h2>
          <p className="muted">
            {shown ? `${shown === 'W' ? 'Women’s' : 'Men’s'} team. ` : ''}{held} of {kit.spots.length} positions held by verified players.
          </p>
        </div>
        {teams.length > 1 && (
          <Seg options={[['M', 'Men'], ['W', 'Women']]} value={shown} onChange={setTeam} label="Team" style={{ marginBottom: 0 }} />
        )}
      </div>
      <div className="lineup-grid">
        <div className="lineup-court" key={shown}>
          <Court sport={sport} players={players} onSpot={m => m?.id && onOpen({ id: m.id })} />
        </div>
        <ol className="lineup-list">
          <li className="lineup-head"><span className="k">{title}</span><span className="mono">{held} of {kit.spots.length}</span></li>
          {kit.spots.map((spot, i) => (
            <li key={i} className={players[i] ? '' : 'open'}>
              <span className="mono">{String(i + 1).padStart(2, '0')}</span>
              {players[i]
                ? <button className="linkbtn" onClick={() => onOpen({ id: players[i].id })}>{players[i].full}</button>
                : <span>Open</span>}
              <small>{spot.pos}</small>
            </li>
          ))}
        </ol>
      </div>
    </section>
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
    <div className="codecell">
      <span className="k">{sport} enrolment code</span>
      <code className="enrolcode">{code ?? '······'}</code>
      <p>
        Give this to your students. They sign in with their university email, pick {sport} and
        type this code to enrol. Make a new one if it has been shared too widely.
      </p>
      <button className="linkbtn" onClick={renew} disabled={!code}>Make a new code</button>
      {error && <div className="note err">{error}</div>}
    </div>
  )
}
