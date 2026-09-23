import { useCallback, useEffect, useState } from 'react'
import { api, initials, setUnauthorizedHandler, token } from './api'
import Icon from './Icon'
import Login from './Login'
import StudentForm from './StudentForm'
import CoachEntry from './CoachEntry'
import Matches from './Matches'
import Dashboard from './Dashboard'
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

export default function App() {
  const [coach, setCoach] = useState(null)
  const [booted, setBooted] = useState(false)
  const [sports, setSports] = useState(null)
  const [error, setError] = useState('')
  const [view, setView] = useState('student')
  const [theme, cycleTheme] = useTheme()
  const [version, setVersion] = useState(0)
  const bump = useCallback(() => setVersion(v => v + 1), [])

  useEffect(() => {
    setUnauthorizedHandler(() => { setCoach(null); setView('login') })
  }, [])

  useEffect(() => {
    api.sports()
      .then(setSports)
      .catch(e => setError(`Can't reach the API — is the backend running? (${e.message})`))

    if (token.get()) {
      api.me()
        .then(c => { setCoach(c); setView('dashboard') })
        .catch(() => token.set(null))
        .finally(() => setBooted(true))
    } else {
      setBooted(true)
    }
  }, [])

  async function signOut() {
    try { await api.logout() } catch { /* token already dead */ }
    token.set(null)
    setCoach(null)
    setView('student')
  }

  function onAuthed(c) {
    setCoach(c)
    setView('dashboard')
  }

  if (error) return <main><div className="banner bad" style={{ marginTop: 24 }}>{error}</div></main>
  if (!sports || !booted) return <div className="skeleton">Loading…</div>

  const nav = [
    { key: 'student', label: 'Student Entry', short: 'Student', icon: 'student' },
    ...(coach ? [
      { key: 'coach', label: 'Coach Entry', short: 'Entry', icon: 'clipboard' },
      { key: 'matches', label: 'Match Footage', short: 'Match', icon: 'film' },
      { key: 'dashboard', label: 'Dashboard', short: 'Squad', icon: 'chart' },
      { key: 'weights', label: 'Weights', short: 'Weights', icon: 'sliders' },
      { key: 'training', label: 'AI Training', short: 'AI', icon: 'cpu' },
    ] : []),
  ]

  if (view === 'login' && !coach) {
    return (
      <Login sports={sports} onAuthed={onAuthed} onCancel={() => setView('student')}
             theme={theme} onTheme={cycleTheme} />
    )
  }

  const body = (
    <>
      {view === 'student' && <StudentForm sports={sports} coach={coach} onSaved={bump} />}
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

        {coach ? (
          <>
            <div className="whoami">
              <span className="avatar" aria-hidden="true">{initials(coach.name)}</span>
              <span style={{ minWidth: 0 }}>
                <b>{coach.name}</b>
                <small>{coach.sport} coach</small>
              </span>
            </div>
            <div className="row" style={{ gap: 8 }}>
              <button className="navitem" onClick={signOut} style={{ flex: 1 }}>
                <Icon name="logout" /> Sign out
              </button>
              <ThemeButton theme={theme} onClick={cycleTheme} />
            </div>
          </>
        ) : (
          <div className="row" style={{ gap: 8 }}>
            <button className="btn sec sm" style={{ flex: 1 }} onClick={() => setView('login')}>
              Coach sign in
            </button>
            <ThemeButton theme={theme} onClick={cycleTheme} />
          </div>
        )}
      </aside>

      <div>
        <header className="topbar">
          <Brand />
          <div className="row" style={{ gap: 8 }}>
            {coach
              ? <button className="btn sec sm" onClick={signOut}>Sign out</button>
              : <button className="btn sec sm" onClick={() => setView('login')}>Coach sign in</button>}
            <ThemeButton theme={theme} onClick={cycleTheme} />
          </div>
        </header>

        <main>{body}</main>

        <nav className="tabbar" aria-label="Sections">
          {nav.map(item => (
            <button key={item.key} onClick={() => setView(item.key)}
                    aria-current={view === item.key ? 'page' : undefined}>
              <Icon name={item.icon} size={19} />
              {item.short}
            </button>
          ))}
        </nav>
      </div>
    </div>
  )
}
