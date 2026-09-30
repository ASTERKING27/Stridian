import { useEffect, useId, useMemo, useRef, useState } from 'react'
import { api, formatValue, utc } from './api'
import { CountUp, Ring, Switcher, Tabs, toast } from './fx'
import Icon from './Icon'
import Report from './Report'
import StudentForm from './StudentForm'
import {
  Achievement, CertificateUpload, DetailsForm, DetailsView, levelWord, Photo, PhotoButton,
} from './people'

const TABS = ['Dashboard', 'My report', 'Achievements', 'Profile']
const PHOTO_URL = '/api/student/photo'
const certUrl = id => `/api/student/achievements/${id}/certificate`
const SHORT = ['Uni', 'Zonal', 'State', 'Nat’l', 'Int’l']

const greeting = () => {
  const h = new Date().getHours()
  return h < 5 ? 'Up late' : h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening'
}

/* A signed-in student's own space: enrol first, then a dashboard that talks to them (the
   second coach), their report once the coach has verified them, their achievements, and
   their details. */
export default function Portal({ me, sports, onChange }) {
  const [tab, setTab] = useState('Dashboard')
  const [reportTab, setReportTab] = useState('Overview')   // where a "See it" link lands in the report
  const [achievements, setAchievements] = useState(null)
  const [aiOn, setAiOn] = useState(false)
  const tabsId = useId()
  const s = me.student

  const loadAchievements = () => api.myAchievements().then(setAchievements).catch(() => setAchievements(a => a ?? []))
  useEffect(() => {
    if (!s) return
    loadAchievements()
    api.health().then(h => setAiOn(!!h.documentAI)).catch(() => {})
  }, [s?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  if (!s) return <StudentForm sports={sports} onSaved={m => { onChange(m); setTab('Dashboard') }} />

  const go = (next, sub = 'Overview') => { setReportTab(sub); setTab(next) }
  const replace = item => setAchievements(list => list.map(a => (a.id === item.id ? item : a)))
  const remove = id => setAchievements(list => list.filter(a => a.id !== id))
  const setStudent = student => onChange({ ...me, student })

  return (
    <>
      <div className="pagehead row noprint" style={{ gap: 16, flexWrap: 'nowrap' }}>
        <Photo url={PHOTO_URL} version={s.photo_version} name={s.name} size={64} />
        <div style={{ minWidth: 0 }}>
          <h1>{greeting()}, {s.name.split(' ')[0]}</h1>
          <p className="muted" style={{ margin: 0 }}>
            {s.sport}{s.ra_number ? ` · ${s.ra_number}` : ''} · {me.email}
          </p>
        </div>
      </div>

      <Tabs id={tabsId} tabs={TABS} value={tab} onChange={t => go(t)} label="Your space" className="noprint" />

      <Switcher id={tabsId} value={tab} order={TABS}>
        {t => (
          <>
            {t === 'Dashboard' && (
              <Home me={me} achievements={achievements} onGo={go}
                    onRefresh={m => { onChange(m); loadAchievements() }} />
            )}
            {t === 'My report' && (s.status === 'verified'
              ? <Report readOnly initialTab={reportTab} />
              : (
                <div className="card empty">
                  <b>Your report isn&apos;t ready yet</b>
                  It appears here once your coach has recorded your tests and verified your position.
                </div>
              ))}
            {t === 'Achievements' && (
              <Achievements student={s} list={achievements} aiOn={aiOn}
                            onAdd={a => setAchievements(list => [a, ...(list ?? [])])}
                            onChange={replace} onDelete={remove} />
            )}
            {t === 'Profile' && (
              <Profile student={s} sports={sports} achievements={achievements} onStudent={setStudent} />
            )}
          </>
        )}
      </Switcher>
    </>
  )
}

/* -------------------------------------------------------------- dashboard */

/* The second coach: what the numbers say today (backend/coach.py writes the words), this
   week's focus, the rings to each next level, milestones — then the profile checklist.
   A level reached is put on record for them; a new milestone is a quiet note. */
function Home({ me, achievements, onGo, onRefresh }) {
  const s = me.student
  const [coach, setCoach] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [ticking, setTicking] = useState(false)
  const [record, setRecord] = useState(null)       // { party, snapshot }: the level reached, on show
  const handled = useRef(null)
  const list = achievements ?? []
  const count = st => list.filter(a => a.status === st).length

  useEffect(() => {
    let live = true
    const load = () => api.studentCoach()
      .then(c => { if (live) { setError(''); setCoach(c) } })
      .catch(e => live && setError(e.message))
    load()
    // back on a page left open (overnight, say): today's tick and this week's focus move on
    const back = () => { if (document.visibilityState === 'visible') load() }
    document.addEventListener('visibilitychange', back)
    return () => { live = false; document.removeEventListener('visibilitychange', back) }
  }, [s.status, s.category, s.photo_version])

  // what is new since they last looked: a level first (it waits to be read), then milestones
  useEffect(() => {
    if (!coach || handled.current === coach) return
    handled.current = coach
    const party = coach.celebrate
    if (party.level || party.levelUps.length) setRecord({ party, snapshot: coach.snapshot })
    else if (party.badges.length) {
      announce(party.badges)
      // what was shown, not what is true by the time this lands; told again next time, at worst
      api.studentCoachSeen(coach.snapshot).catch(() => {})
    }
  }, [coach])

  function closeRecord() {
    announce(record.party.badges)
    api.studentCoachSeen(record.snapshot).catch(() => {})
    setRecord(null)
  }

  const todo = [
    ['A profile photo', !!s.photo_version, 'Profile'],
    ['Your RA number and date of birth', !!(s.ra_number && s.dob), 'Profile'],
    ['Your mobile and a parent’s mobile', !!(s.phone && (s.father_phone || s.mother_phone)), 'Profile'],
    ['Your Aadhaar number', !!s.aadhaar, 'Profile'],
    ['Your blood group', !!s.blood_group, 'Profile'],
    ['Your team (men’s or women’s)', !!s.category, 'Profile'],
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

  async function tick() {
    setTicking(true)
    try { setCoach(await api.focusTick()) } catch (err) { setError(err.message) }
    setTicking(false)
  }

  const c = coach
  return (
    <>
      {error && <div className="banner bad">{error}</div>}
      {!c && !error && <div className="card brief"><p className="skeleton">Your coach is reading your numbers…</p></div>}
      {c && <Brief c={c} s={s} busy={busy} onRefresh={refresh} onGo={onGo} />}
      {c && c.cards.length > 0 && <Says cards={c.cards} onGo={onGo} />}
      {c?.focus && <Focus f={c.focus} busy={ticking} onTick={tick} onGo={onGo} />}
      {c && c.rings.length > 0 && <Rings rings={c.rings} />}
      {c && <Milestones list={c.badges} />}

      <div className="split">
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Your profile</h2>
              <p className="muted">What the sports directorate needs from you — {done} of {todo.length} done.</p>
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
          <div className="card-head">
            <div><h2>Updates</h2></div>
            <div className="chips" style={{ marginTop: 0 }}>
              <span className="pill good">{count('verified')} verified</span>
              {count('pending') > 0 && <span className="pill accent">{count('pending')} with your coach</span>}
            </div>
          </div>
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

      {record && <Record party={record.party} student={s} standing={c.standing} levels={c.levels} onClose={closeRecord} />}
    </>
  )
}

// a few notes at most; the rest wait on the milestones card
function announce(badges) {
  badges.slice(0, 3).forEach((b, i) => setTimeout(() => toast({
    icon: <Icon name={b.icon} size={16} />, title: `Milestone: ${b.title}`, body: b.desc, ms: 6000,
  }), i * 400))
  if (badges.length > 3) {
    setTimeout(() => toast({ title: `And ${badges.length - 3} more`, body: 'See them under Milestones.', ms: 6000 }), 1200)
  }
}

/* The five levels as steps: how many of their measures reach each, the one they play at
   marked. `fresh` fills that step in, for the record. */
function Ladder({ levels, standing, level, fresh = false }) {
  return (
    <ol className={`lvl-ladder${fresh ? ' fresh' : ''}`} aria-label="How many of your measures reach each level">
      {levels.map((word, i) => {
        const st = standing[i]
        const state = level != null && i <= level ? (i === level ? 'reached here' : 'reached')
          : level != null && i === level + 1 ? 'next' : ''
        return (
          <li key={word} className={state} aria-current={i === level ? 'step' : undefined}
              title={st ? `${st.met} of ${st.of} of your measures reach ${word}` : undefined}>
            <span className="bar"><i style={{ width: `${Math.round((st?.share ?? 0) * 100)}%` }} /></span>
            <b data-short={SHORT[i]}><span>{word}</span></b>
            <small>{st ? `${st.met}/${st.of}` : '—'}</small>
          </li>
        )
      })}
    </ol>
  )
}

/* The headline, the level they play at as a ring, and the ladder under it. */
function Brief({ c, s, busy, onRefresh, onGo }) {
  const lv = c.level
  const next = lv == null || lv >= 4 ? null : lv + 1
  // they reach the next level once more than half their measures (by weight) do
  const progress = lv == null ? 0 : next == null ? 1 : Math.min(1, (c.standing[next]?.share ?? 0) / 0.5)
  const name = lv == null ? '—' : lv < 0 ? 'Starter' : c.levels[lv]
  return (
    <section className="card brief swap">
      <div className="brief-text">
        <span className="eyebrow">{c.verified ? 'Your second coach' : 'Getting you set up'}</span>
        <p className="headline">{c.headline}</p>
        {c.verified && c.standing.length > 0 && <Ladder levels={c.levels} standing={c.standing} level={lv} />}
        <div className="verify brief-status">
          {s.status === 'verified' ? (
            <>
              <span className="pill good"><i className="dot" />Verified · {s.verified_position}</span>
              <button className="btn sm" onClick={() => onGo('My report')}>Open my report</button>
            </>
          ) : (
            <>
              <span className="pill warn"><i className="dot" />Waiting for your coach</span>
              <button className="btn sec sm" disabled={busy} onClick={onRefresh}>{busy ? 'Checking…' : 'Check again'}</button>
            </>
          )}
        </div>
      </div>
      {c.verified && (
        <Ring value={progress} size={150} stroke={11}
              label={lv == null ? 'Level: not enough results yet'
                : `Playing at ${name} level${next != null ? `, ${Math.round(progress * 100)}% of the way to ${c.levels[next]}` : ''}`}>
          <small>Playing at</small>
          <b>{name}</b>
          <small>{lv == null ? 'needs more tests' : next != null ? `${Math.round(progress * 100)}% to ${c.levels[next]}` : 'top of the ladder'}</small>
        </Ring>
      )}
    </section>
  )
}

// each kind of message: its icon, and where its link goes in the report
const SAY = {
  levelup: ['medal', 'Levels', 'See it'],
  win: ['trend', 'Levels', 'See it'],
  drop: ['down', 'Levels', 'See it'],
  near: ['target', 'Levels', 'See how close'],
  focus: ['bolt', 'Training', 'See the drills'],
  step: ['target', 'Levels', 'See how close'],
  strength: ['star', 'Levels', 'See it'],
  missing: ['clipboard', 'Measurements', 'See your tests'],
  todo: ['check', null, 'Do it now'],
}

function Says({ cards, onGo }) {
  return (
    <section className="says" aria-label="What your coach says">
      {cards.map((card, i) => {
        const [icon, sub, cta] = SAY[card.kind] ?? ['chart', null, 'Open']
        return (
          <article key={`${card.kind}-${card.key ?? i}`} className={`say ${card.kind}`}>
            <span className="say-ico"><Icon name={icon} size={17} /></span>
            <div style={{ minWidth: 0 }}>
              <h3>{card.title}</h3>
              <p>{card.body}</p>
              {card.tab && (
                <button className="linkbtn" onClick={() => onGo(card.tab, sub ?? 'Overview')}>{cta} →</button>
              )}
            </div>
          </article>
        )
      })}
    </section>
  )
}

function Focus({ f, busy, onTick, onGo }) {
  const n = f.sessions.length
  const left = Math.max(0, f.target - n)
  return (
    <section className={`card focus swap${f.complete ? ' complete' : ''}`}>
      <div className="focus-top">
        <div style={{ minWidth: 0 }}>
          <span className="eyebrow">This week&apos;s focus</span>
          <h2>{f.label}</h2>
          {f.ring && (
            <p className="focus-gap">
              {f.ring.next ? `${f.ring.gap} to ${f.ring.next} level` : 'You’re at the top here — keep it there'}
            </p>
          )}
          <p className="muted" style={{ margin: 0 }}>{f.tip}</p>
        </div>
        <div className={`streak${f.streak ? ' on' : ''}`} title="Weeks in a row with every focus session done">
          <Icon name="flame" size={20} />
          <b><CountUp value={f.streak} /></b>
          <small>{f.streak ? 'week streak' : 'start a streak'}</small>
        </div>
      </div>
      <div className="sessions">
        {Array.from({ length: Math.max(f.target, n) }, (_, i) => (
          <i key={i} className={i < n ? 'on' : ''} aria-hidden="true">
            {i < n ? <Icon name="check" size={14} /> : i + 1}
          </i>
        ))}
        <span>{f.complete ? 'Week done. That’s how it’s done.'
          : `${n} of ${f.target} sessions · ${left} more this week`}</span>
      </div>
      <div className="row">
        <button className="btn" disabled={f.doneToday || busy} onClick={onTick}>
          {f.doneToday ? 'Done for today' : busy ? 'Saving…' : 'I trained this today'}
        </button>
        <button className="linkbtn" onClick={() => onGo('My report', 'Training')}>See the drills →</button>
      </div>
    </section>
  )
}

function Rings({ rings }) {
  const [all, setAll] = useState(false)
  const shown = all ? rings : rings.slice(0, 8)
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>Next-level rings</h2>
          <p className="muted">Each ring fills as a result climbs through its level. A full ring is the next level.</p>
        </div>
      </div>
      <div className="rings">
        {shown.map(r => (
          <div key={r.key} className="ringcard">
            <Ring value={r.next ? r.progress : 1} size={68} stroke={6}
                  label={`${r.label}: ${r.levelName} level${r.next ? `, ${Math.round(r.progress * 100)}% of the way to ${r.next}` : ''}`}>
              <b>{r.level < 0 ? 'Pre' : SHORT[r.level]}</b>
            </Ring>
            <div style={{ minWidth: 0 }}>
              <b>{r.label}</b>
              <small>{r.unit === 'level' ? `Level ${r.value}` : formatValue(r.value, r)}</small>
              <small className="next">{r.next ? `${r.gap} to ${r.next}` : 'Top level'}</small>
            </div>
          </div>
        ))}
      </div>
      {rings.length > 8 && (
        <button className="linkbtn" style={{ marginTop: 12 }} onClick={() => setAll(a => !a)}>
          {all ? 'Show fewer' : `Show all ${rings.length}`}
        </button>
      )}
    </section>
  )
}

function Milestones({ list }) {
  const got = list.filter(b => b.earned).length
  return (
    <section className="card">
      <div className="card-head">
        <div>
          <h2>Milestones</h2>
          <p className="muted">{got} of {list.length} on your record.</p>
        </div>
      </div>
      <ul className="milestones">
        {list.map(b => (
          <li key={b.id} className={`${b.earned ? 'got' : ''}${b.new ? ' new' : ''}`}>
            <span className="ms-ico"><Icon name={b.icon} size={16} /></span>
            <span className="ms-text"><b>{b.title}</b><small>{b.desc}</small></span>
            <span className="ms-state">{b.new ? 'New' : b.earned ? 'Earned' : 'Locked'}</span>
          </li>
        ))}
      </ul>
    </section>
  )
}

/* Reaching a level is a real achievement, so it gets a moment of its own — not a party,
   a record: the ring closes, the level is written down with what it rests on and the
   date, and the next target is named. A native <dialog> keeps focus inside and closes on
   Escape. */
function Record({ party, student, standing, levels, onClose }) {
  const box = useRef(null)
  useEffect(() => { if (!box.current.open) box.current.showModal() }, [])
  const L = party.level
  const ups = party.levelUps
  const title = L ? `${L.word} level` : ups.length === 1 ? `${ups[0].level} level` : `${ups.length} measures stepped up`
  const eyebrow = L ? (L.first ? 'Your level is on record' : 'Level reached')
    : ups.length === 1 ? `New level · ${ups[0].label}` : 'New levels reached'
  const also = L ? ups : ups.length > 1 ? ups : []
  return (
    <dialog ref={box} className="record" aria-labelledby="rec-title" onClose={onClose}>
      <div className="record-crest">
        <Ring value={1} size={108} stroke={4} draw label={title}>
          <Icon name={L ? 'medal' : 'trend'} size={36} />
        </Ring>
      </div>
      <span className="eyebrow">{eyebrow}</span>
      <h2 id="rec-title" className="record-title">{title}</h2>
      {L && (
        <p className="record-basis">
          You meet {L.word}-level targets in {L.met} of the {L.of} measures that count for {L.position}.
        </p>
      )}
      {also.length > 0 && (
        <ul className="record-ups">
          {also.map(u => <li key={u.key}><b>{u.label}</b> reached {u.level} level</li>)}
        </ul>
      )}
      {L && !L.first && (
        <p className="record-note">Earned through your own work. It is on your record now, and your coach sees it too.</p>
      )}
      {L && <Ladder levels={levels} standing={standing} level={L.level} fresh />}
      <dl className="record-meta">
        <div><dt>Athlete</dt><dd>{student.name}</dd></div>
        <div><dt>Sport</dt><dd>{student.sport}</dd></div>
        <div><dt>Recorded</dt><dd>{new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}</dd></div>
      </dl>
      {L?.next && (
        <p className="record-next">Next: <b>{L.next}</b> — about {L.need} more measure{L.need === 1 ? '' : 's'} to bring up.</p>
      )}
      <form method="dialog"><button className="btn">Continue</button></form>
    </dialog>
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
