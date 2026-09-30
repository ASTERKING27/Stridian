import { useCallback, useEffect, useState } from 'react'
import { api, initials, setUnauthorizedHandler, token } from './api'
import Icon from './Icon'
import Login from './Login'
import StudentAuth from './StudentAuth'
import StudentForm from './StudentForm'
import CoachEntry from './CoachEntry'
import Matches from './Matches'
import MatchCards from './MatchCards'
import Dashboard, { MyDetails } from './Dashboard'
import Portal from './Portal'
import Weights from './Weights'
import Training from './Training'
import { Switcher, Toaster, useIndicator } from './fx'
import { LookPicker, useLook } from './Theme'

const Brand = ({ sub }) => (
  <div className="brand">
    <span className="mark" aria-hidden="true">S</span>
    <b>Stridian<span>{sub}</span></b>
  </div>
)

export default function App() {
  const [coach, setCoach] = useState(null)
  const [me, setMe] = useState(null)        // a signed-in student: { email, student }
  const [booted, setBooted] = useState(false)
  const [sports, setSports] = useState(null)
  const [error, setError] = useState('')
  const [view, setView] = useState('home')
  const [look, setLook] = useLook()
  const go = key => {
    setView(key)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }
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
               onCancel={() => go('home')} look={look} onLook={setLook} />
      : <StudentAuth onAuthed={m => { setMe(m); setView('mine') }} onCoach={() => go('login')}
                     look={look} onLook={setLook} />
  }

  const nav = coach ? [
    // adding students by hand is for admins; everyone else enrols themselves
    ...(coach.is_admin ? [{ key: 'student', label: 'Add Student', short: 'Add', icon: 'student' }] : []),
    { key: 'coach', label: 'Coach Entry', short: 'Entry', icon: 'clipboard' },
    { key: 'matches', label: 'Match Footage', short: 'Footage', icon: 'film' },
    { key: 'cards', label: 'Match Cards', short: 'Cards', icon: 'card' },
    { key: 'dashboard', label: 'Dashboard', short: 'Squad', icon: 'chart' },
    { key: 'weights', label: 'Weights', short: 'Weights', icon: 'sliders' },
    { key: 'training', label: 'AI Training', short: 'AI', icon: 'cpu' },
  ] : [
    { key: 'mine', label: 'My space', short: 'Me', icon: 'student' },
  ]
  const who = coach
    ? { name: coach.name, sub: coach.is_admin ? `Admin · viewing ${coach.sport}` : `${coach.sport} coach` }
    : { name: me.student?.name ?? me.email, sub: me.student ? `${me.student.sport} · student` : 'Student' }

  async function switchSport(sport) {
    try {
      setCoach(await api.switchSport(sport))
      bump()
    } catch (err) {
      alert(err.message)
    }
  }
  const sportPicker = coach?.is_admin && (
    <select className="sportpick" aria-label="Sport you are viewing" value={coach.sport}
            onChange={e => switchSport(e.target.value)}>
      {sports.map(s => <option key={s.slug} value={s.name}>{s.name}</option>)}
    </select>
  )

  // keyed by sport: an admin switching sport gets every page fresh; within a sport the
  // Switcher slides one page out and the next in
  const body = (
    <div key={coach?.sport ?? 'student'}>
      <Switcher value={view} order={[...nav.map(n => n.key), 'me']}>
        {v => (
          <>
            {v === 'mine' && me && <Portal me={me} sports={sports} onChange={setMe} />}
            {v === 'me' && coach && <MyDetails coach={coach} onSaved={setCoach} />}
            {v === 'student' && coach?.is_admin && <StudentForm sports={sports} coach={coach} onSaved={bump} />}
            {v === 'coach' && coach && (
              <CoachEntry coach={coach} sports={sports} version={version} onSaved={bump} />
            )}
            {v === 'matches' && coach && (
              <Matches version={version} onChanged={bump} />
            )}
            {v === 'cards' && coach && <MatchCards coach={coach} version={version} onChanged={bump} />}
            {v === 'dashboard' && coach && (
              <Dashboard coach={coach} sports={sports} version={version} onChanged={bump} onCoach={setCoach}
                         onGo={go} />
            )}
            {v === 'weights' && coach && <Weights coach={coach} onSaved={bump} />}
            {v === 'training' && coach && <Training coach={coach} />}
          </>
        )}
      </Switcher>
    </div>
  )

  return (
    <div className="shell">
      <aside className="rail">
        <Brand sub={coach ? 'Coach console' : 'Your second coach'} />
        <Nav items={nav} view={view} onGo={go} />

        <div className="spacer" />

        {sportPicker}
        <button className="whoami" disabled={!coach} onClick={() => go('me')}
                title={coach ? 'Your details' : undefined}>
          <span className="avatar" aria-hidden="true">{initials(who.name)}</span>
          <span style={{ minWidth: 0 }}>
            <b>{who.name}</b>
            <small>{who.sub}</small>
          </span>
        </button>
        <div className="row" style={{ gap: 8 }}>
          <button className="navitem" onClick={signOut} style={{ flex: 1 }}>
            <Icon name="logout" /> Sign out
          </button>
          <LookPicker look={look} onLook={setLook} />
        </div>
      </aside>

      <div>
        <header className="topbar">
          <Brand sub={coach ? 'Coach console' : 'Your second coach'} />
          <div className="row" style={{ gap: 8, flexWrap: 'nowrap' }}>
            {sportPicker}
            {coach && <button className="btn sec sm" onClick={() => go('me')}>Me</button>}
            <button className="btn sec sm" onClick={signOut}>Sign out</button>
            <LookPicker look={look} onLook={setLook} />
          </div>
        </header>

        <main>
          {body}
          <footer className="sitefoot"><a href="/privacy.html">Privacy policy</a> · <a href="/terms.html">Terms of use</a></footer>
        </main>

        {nav.length > 1 && <TabBar items={nav} view={view} onGo={go} />}
      </div>
      <Toaster />
    </div>
  )
}

/* The side menu, with a marker that slides to the page you are on. */
function Nav({ items, view, onGo }) {
  const [ref, style] = useIndicator('[aria-current="page"]', [view, items.length])
  return (
    <nav className="navlist" ref={ref} aria-label="Sections">
      <i className="nav-ind" style={style} aria-hidden="true" />
      {items.map(item => (
        <button key={item.key} className="navitem" onClick={() => onGo(item.key)}
                aria-current={view === item.key ? 'page' : undefined}>
          <Icon name={item.icon} />
          {item.label}
        </button>
      ))}
    </nav>
  )
}

/* The phone's bottom bar, same idea. */
function TabBar({ items, view, onGo }) {
  const [ref, style] = useIndicator('[aria-current="page"]', [view, items.length])
  return (
    <nav className="tabbar" aria-label="Sections" ref={ref}>
      <i className="tab-ind" style={style} aria-hidden="true" />
      {items.map(item => (
        <button key={item.key} onClick={() => onGo(item.key)}
                aria-current={view === item.key ? 'page' : undefined}>
          <Icon name={item.icon} size={19} />
          {item.short}
        </button>
      ))}
    </nav>
  )
}
