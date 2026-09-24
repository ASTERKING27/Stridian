import { useCallback, useEffect, useState } from 'react'
import { Analytics } from '@vercel/analytics/react'
import { api, initials, setUnauthorizedHandler, token } from './api'
import Icon from './Icon'
import Login from './Login'
import StudentAuth from './StudentAuth'
import StudentForm from './StudentForm'
import CoachEntry from './CoachEntry'
import Matches from './Matches'
import Dashboard from './Dashboard'
import Report from './Report'
import Weights from './Weights'
import Training from './Training'

const THEMES = ['system', 'light', 'dark']

function useTheme() {
  const [theme, setTheme] = useState(() => {
    try { return localStorage.getItem('stridian.theme') || 'system' } catch { return 'system' }
  })
  useEffect(() => {
    const root = document.documentElement
    if (theme === 'system') root.removeAttribute('data-theme')
    else root.setAttribute('data-theme', theme)
    try { localStorage.setItem('stridian.theme', theme) } catch { /* private mode */ }
  }, [theme])
  const cycle = () => setTheme(t => THEMES[(THEMES.indexOf(t) + 1) % THEMES.length])
  return [theme, cycle]
}

function ThemeButton({ theme, onClick }) {
  const icon = theme === 'system' ? 'laptop' : theme === 'dark' ? 'moon' : 'sun'
  return (
    <button className="iconbtn" onClick={onClick} title={`Theme: ${theme} — click to change`}
            aria-label={`Theme: ${theme}. Click to change.`}>
      <Icon name={icon} size={16} />
    </button>
  )
}

const Brand = () => (
  <div className="brand">
    <span className="mark" aria-hidden="true">S</span>
    <b>Stridian<span>Sports talent intelligence</span></b>
  </div>
)

const DIET_WORDS = { nonveg: 'Non-veg', egg: 'Eggetarian', veg: 'Vegetarian', vegan: 'Vegan' }

/* A signed-in student's one page: enrol, then wait for the coach, then their report. */
function StudentHome({ me, sports, onChange }) {
  const [busy, setBusy] = useState(false)
  const s = me.student

  if (!s) return <StudentForm sports={sports} onSaved={onChange} />
  if (s.status === 'verified') return <Report readOnly />

  async function refresh() {
    setBusy(true)
    try { onChange(await api.studentMe()) } catch { /* the banner stays as it was */ }
    setBusy(false)
  }

  const details = [
    ['Sport', s.sport], ['Age', s.age && `${s.age} yrs`], ['Height', s.height_cm && `${s.height_cm} cm`],
    ['Weight', s.weight_kg && `${s.weight_kg} kg`], ['Blood group', s.blood_group],
    ['Position you play', s.declared_position], ['Diet', DIET_WORDS[s.diet_preference]],
    ['Allergies', s.allergies?.replaceAll(',', ', ')], ['Training per day', s.training_hours_per_day && `${s.training_hours_per_day} h`],
    ['Notes for your coach', s.student_notes],
  ]
  return (
    <>
      <div className="pagehead">
        <h1>Hi, {s.name.split(' ')[0]}</h1>
        <p className="lede">You&apos;re enrolled in {s.sport}.</p>
      </div>
      <div className="card">
        <div className="verify">
          <span className="pill warn"><i className="dot" />Waiting for your coach</span>
          <span>
            Your best position, the reasons for it, your training plan and your diet plan appear
            here once your coach has recorded your tests and verified you.
          </span>
          <button className="btn sec sm" disabled={busy} onClick={refresh}>
            {busy ? 'Checking…' : 'Check again'}
          </button>
        </div>
      </div>
      <div className="card">
        <div className="card-head">
          <div>
            <h2>What you sent</h2>
            <p className="muted">If something is wrong, tell your coach.</p>
          </div>
        </div>
        <table className="data">
          <tbody>
            {details.map(([k, v]) => (
              <tr key={k}><td className="muted">{k}</td><td>{v || '—'}</td></tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

export default function App() {
  const [coach, setCoach] = useState(null)
  const [me, setMe] = useState(null)        // a signed-in student: { email, student }
  const [booted, setBooted] = useState(false)
  const [sports, setSports] = useState(null)
  const [error, setError] = useState('')
  const [view, setView] = useState('home')
  const [theme, cycleTheme] = useTheme()
  const [version, setVersion] = useState(0)
  const bump = useCallback(() => setVersion(v => v + 1), [])

  useEffect(() => {
    setUnauthorizedHandler(role => {
      if (!role) return   // a wrong password on a sign-in form, not a lost session
      setCoach(null)
      setMe(null)
      setView(role === 'student' ? 'home' : 'login')
    })
  }, [])

  useEffect(() => {
    api.sports()
      .then(setSports)
      .catch(e => setError(`Can't reach the API — is the backend running? (${e.message})`))

    if (token.get()) {
      const load = token.role() === 'student'
        ? api.studentMe().then(m => { setMe(m); setView('mine') })
        : api.me().then(c => { setCoach(c); setView('dashboard') })
      // a 401 has already cleared the token; anything else (server down, database waking)
      // mustn't sign anyone out
      load.catch(e => token.get() && setError(`Can't reach the API right now — try again in a minute. (${e.message})`))
        .finally(() => setBooted(true))
    } else {
      setBooted(true)
    }
  }, [])

  async function signOut() {
    try { await (me ? api.studentLogout() : api.logout()) } catch { /* token already dead */ }
    token.set(null)
    setCoach(null)
    setMe(null)
    setView('home')
  }

  if (error) return <main><div className="banner bad" style={{ marginTop: 24 }}>{error}</div></main>
  if (!sports || !booted) return <div className="skeleton">Loading…</div>

  if (!coach && !me) {
    return view === 'login'
      ? <Login sports={sports} onAuthed={c => { setCoach(c); setView('dashboard') }}
               onCancel={() => setView('home')} theme={theme} onTheme={cycleTheme} />
      : <StudentAuth onAuthed={m => { setMe(m); setView('mine') }} onCoach={() => setView('login')}
                     theme={theme} onTheme={cycleTheme} />
  }

  const nav = coach ? [
    { key: 'student', label: 'Add Student', short: 'Add', icon: 'student' },
    { key: 'coach', label: 'Coach Entry', short: 'Entry', icon: 'clipboard' },
    { key: 'matches', label: 'Match Footage', short: 'Match', icon: 'film' },
    { key: 'dashboard', label: 'Dashboard', short: 'Squad', icon: 'chart' },
    { key: 'weights', label: 'Weights', short: 'Weights', icon: 'sliders' },
    { key: 'training', label: 'AI Training', short: 'AI', icon: 'cpu' },
  ] : [
    { key: 'mine', label: 'My profile', short: 'Me', icon: 'student' },
  ]
  const who = coach
    ? { name: coach.name, sub: `${coach.sport} coach` }
    : { name: me.student?.name ?? me.email, sub: me.student ? `${me.student.sport} · student` : 'Student' }

  const body = (
    <>
      {view === 'mine' && me && <StudentHome me={me} sports={sports} onChange={setMe} />}
      {view === 'student' && coach && <StudentForm sports={sports} coach={coach} onSaved={bump} />}
      {view === 'coach' && coach && (
        <CoachEntry coach={coach} sports={sports} version={version} onSaved={bump} />
      )}
      {view === 'matches' && coach && (
        <Matches version={version} onChanged={bump} />
      )}
      {view === 'dashboard' && coach && (
        <Dashboard coach={coach} sports={sports} version={version} onChanged={bump} />
      )}
      {view === 'weights' && coach && <Weights coach={coach} onSaved={bump} />}
      {view === 'training' && coach && <Training coach={coach} />}
    </>
  )

  return (
    <div className="shell">
      <aside className="rail">
        <Brand />
        {nav.map(item => (
          <button key={item.key} className="navitem" onClick={() => setView(item.key)}
                  aria-current={view === item.key ? 'page' : undefined}>
            <Icon name={item.icon} />
            {item.label}
          </button>
        ))}

        <div className="spacer" />

        <div className="whoami">
          <span className="avatar" aria-hidden="true">{initials(who.name)}</span>
          <span style={{ minWidth: 0 }}>
            <b>{who.name}</b>
            <small>{who.sub}</small>
          </span>
        </div>
        <div className="row" style={{ gap: 8 }}>
          <button className="navitem" onClick={signOut} style={{ flex: 1 }}>
            <Icon name="logout" /> Sign out
          </button>
          <ThemeButton theme={theme} onClick={cycleTheme} />
        </div>
      </aside>

      <div>
        <header className="topbar">
          <Brand />
          <div className="row" style={{ gap: 8 }}>
            <button className="btn sec sm" onClick={signOut}>Sign out</button>
            <ThemeButton theme={theme} onClick={cycleTheme} />
          </div>
        </header>

        <main>
          {body}
          <footer className="sitefoot"><a href="/privacy.html">Privacy policy</a></footer>
        </main>

        {nav.length > 1 && (
          <nav className="tabbar" aria-label="Sections">
            {nav.map(item => (
              <button key={item.key} onClick={() => setView(item.key)}
                      aria-current={view === item.key ? 'page' : undefined}>
                <Icon name={item.icon} size={19} />
                {item.short}
              </button>
            ))}
          </nav>
        )}
      </div>
      <Analytics />
    </div>
  )
}
