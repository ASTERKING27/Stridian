import { useCallback, useEffect, useState } from 'react'
import { api, initials, setUnauthorizedHandler, token } from './api'
import Icon from './Icon'
import Logo, { Mark } from './Logo'
import StudentForm from './StudentForm'
import CoachEntry from './CoachEntry'
import Matches from './Matches'
import MatchCards from './MatchCards'
import Dashboard, { MyDetails } from './Dashboard'
import Portal from './Portal'
import Weights from './Weights'
import Training from './Training'
import Home from './site/Home'
import SignIn from './site/SignIn'
import { SPORTKIT } from './site/sportkit'
import { Switcher, Toaster, calm, useIndicator } from './fx'
import { LookPicker, useLook } from './Theme'

// the public pages keep their place in the address bar, so Back works between them
const HASH = { signin: '#signin', login: '#coach' }
const fromHash = () => (window.location.hash === '#coach' ? 'login' : window.location.hash === '#signin' ? 'signin' : 'home')
const STUDENT_NAV = [
  { key: 'Dashboard', label: 'Dashboard', short: 'Home', icon: 'chart' },
  { key: 'My report', label: 'My report', short: 'Report', icon: 'clipboard' },
  { key: 'Achievements', label: 'Achievements', short: 'Awards', icon: 'medal' },
  { key: 'Profile', label: 'Profile', short: 'Profile', icon: 'student' },
]
const WIPE_MS = 460   // when the sheet covers the whole window (system.css .wipe)

export default function App() {
  const [coach, setCoach] = useState(null)
  const [me, setMe] = useState(null)        // a signed-in student: { email, student }
  const [booted, setBooted] = useState(false)
  const [sports, setSports] = useState(null)
  const [error, setError] = useState('')
  const [view, setView] = useState(fromHash)
  const [wipe, setWipe] = useState(0)       // counts changes of scene: each plays the sheet once
  const [look, setLook] = useLook()
  const go = key => {
    setView(key)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }
  const [version, setVersion] = useState(0)
  const bump = useCallback(() => setVersion(v => v + 1), [])

  /* A change of scene (home, sign in, the app itself): a sheet sweeps across the window
     and the scene changes under it. */
  const scene = useCallback(change => {
    const land = () => { change(); window.scrollTo({ top: 0, behavior: 'instant' }) }
    if (calm()) { land(); return }
    setWipe(n => n + 1)
    setTimeout(land, WIPE_MS)
  }, [])
  const visit = key => scene(() => {
    setView(key)
    window.history.pushState(null, '', HASH[key] ?? window.location.pathname)
  })
  const settle = () => window.history.replaceState(null, '', window.location.pathname)

  useEffect(() => {
    setUnauthorizedHandler(role => {
      if (!role) return   // a wrong password on a sign-in form, not a lost session
      setCoach(null)
      setMe(null)
      setView(role === 'student' ? 'signin' : 'login')
    })
    const back = () => { if (!token.get()) setView(fromHash()) }
    window.addEventListener('popstate', back)
    return () => window.removeEventListener('popstate', back)
  }, [])

  useEffect(() => {
    api.sports()
      .then(setSports)
      .catch(e => setError(`Can't reach the API. Is the backend running? (${e.message})`))

    if (token.get()) {
      const load = token.role() === 'student'
        ? api.studentMe().then(m => { setMe(m); setView('Dashboard') })
        : api.me().then(c => { setCoach(c); setView('dashboard') })
      // a 401 has already cleared the token; anything else (server down, database waking)
      // mustn't sign anyone out
      load.catch(e => token.get() && setError(`Can't reach the API right now. Try again in a minute. (${e.message})`))
        .finally(() => setBooted(true))
    } else {
      setBooted(true)
    }
  }, [])

  async function signOut() {
    try { await (me ? api.studentLogout() : api.logout()) } catch { /* token already dead */ }
    scene(() => {
      token.set(null)
      setCoach(null)
      setMe(null)
      setView('home')
    })
  }

  const sheet = wipe > 0 && <div className="wipe" key={wipe} aria-hidden="true"><i /><i /></div>
  const signedOut = !coach && !me

  // the home page needs nothing from the server, so a visitor sees it at once
  if (signedOut && !token.get() && view === 'home') {
    return <>{sheet}<Home onSignIn={who => visit(who === 'coach' ? 'login' : 'signin')} look={look} onLook={setLook} /></>
  }
  if (error) return <main><div className="banner bad" style={{ marginTop: 24 }}>{error}</div></main>
  if (!sports || !booted) return <>{sheet}<div className="skeleton" style={{ textAlign: 'center' }}>Loading</div></>

  if (signedOut) {
    return (
      <>
        {sheet}
        <SignIn role={view === 'login' ? 'coach' : 'athlete'} sports={sports} look={look} onLook={setLook}
                onHome={() => visit('home')}
                onRole={r => { const v = r === 'coach' ? 'login' : 'signin'; setView(v); window.history.replaceState(null, '', HASH[v]) }}
                onAthlete={m => scene(() => { setMe(m); setView('Dashboard'); settle() })}
                onCoach={c => scene(() => { setCoach(c); setView('dashboard'); settle() })} />
      </>
    )
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
  ] : me.student ? STUDENT_NAV : []

  async function switchSport(sport) {
    try {
      setCoach(await api.switchSport(sport))
      bump()
    } catch (err) {
      alert(err.message)
    }
  }
  const sportName = coach?.sport ?? me?.student?.sport
  const sportIcon = <i><Icon path={SPORTKIT[sportName]?.icon} name="chart" size={22} /></i>
  const signOutButton = (
    <button className="navitem signout" onClick={signOut}><Icon name="logout" /><span>Sign out</span></button>
  )

  /* ---------------------------------------------------------------- an athlete's space */
  if (me) {
    const s = me.student
    return (
      <div className="ashell">
        {sheet}
        <header className="abar">
          <Logo size={28} />
          {s && (
            <div className="sportchip">
              {sportIcon}
              <span><b>{s.sport}</b><small>{s.category === 'W' ? 'Women’s team' : s.category === 'M' ? 'Men’s team' : 'Athlete'}</small></span>
            </div>
          )}
          {nav.length > 0 && <BarTabs items={nav} view={view} onGo={go} />}
          <div className="abar-who" style={{ marginLeft: nav.length ? 0 : 'auto' }}>
            <span className="avatar" aria-hidden="true">{initials(s?.name ?? me.email)}</span>
            <span style={{ minWidth: 0 }}>
              <b>{s?.name ?? me.email}</b>
              <small>{s?.ra_number ?? (s ? me.email : 'Not enrolled yet')}</small>
            </span>
          </div>
          <LookPicker look={look} onLook={setLook} />
          {signOutButton}
        </header>
        <main>
          <Portal me={me} sports={sports} onChange={setMe} tab={nav.length ? view : 'Dashboard'} onTab={go} />
          <footer className="sitefoot"><a href="/privacy.html">Privacy policy</a> · <a href="/terms.html">Terms of use</a></footer>
        </main>
        {nav.length > 1 && <TabBar items={nav} view={view} onGo={go} />}
        <Toaster />
      </div>
    )
  }

  /* ---------------------------------------------------------------- the coach console */
  const sportPicker = coach.is_admin && (
    <select className="sportpick" aria-label="Sport you are viewing" value={coach.sport}
            onChange={e => switchSport(e.target.value)}>
      {sports.map(s => <option key={s.slug} value={s.name}>{s.name}</option>)}
    </select>
  )

  // keyed by sport: an admin switching sport gets every page fresh; within a sport the
  // Switcher slides one page out and the next in
  const body = (
    <div key={coach.sport}>
      <Switcher value={view} order={[...nav.map(n => n.key), 'me']}>
        {v => (
          <>
            {v === 'me' && <MyDetails coach={coach} onSaved={setCoach} />}
            {v === 'student' && coach.is_admin && <StudentForm sports={sports} coach={coach} onSaved={bump} />}
            {v === 'coach' && <CoachEntry coach={coach} sports={sports} version={version} onSaved={bump} />}
            {v === 'matches' && <Matches version={version} onChanged={bump} />}
            {v === 'cards' && <MatchCards coach={coach} version={version} onChanged={bump} />}
            {v === 'dashboard' && (
              <Dashboard coach={coach} sports={sports} version={version} onChanged={bump} onCoach={setCoach}
                         onGo={go} />
            )}
            {v === 'weights' && <Weights coach={coach} onSaved={bump} />}
            {v === 'training' && <Training coach={coach} />}
          </>
        )}
      </Switcher>
    </div>
  )

  return (
    <div className="shell">
      {sheet}
      <aside className="rail">
        <Logo size={28} />
        <div className="sportchip">
          {sportIcon}
          <span>
            {coach.is_admin ? sportPicker : <b>{coach.sport}</b>}
            <small>{coach.is_admin ? 'Admin console' : 'Coach console'}</small>
          </span>
        </div>
        <Nav items={nav} view={view} onGo={go} />

        <div className="spacer" />

        <button className="whoami" onClick={() => go('me')} title="Your details">
          <span className="avatar" aria-hidden="true">{initials(coach.name)}</span>
          <span style={{ minWidth: 0 }}>
            <b>{coach.name}</b>
            <small>{coach.designation || (coach.is_admin ? 'Admin' : `${coach.sport} coach`)}</small>
          </span>
        </button>
        <div className="row" style={{ gap: 8 }}>
          {signOutButton}
          <LookPicker look={look} onLook={setLook} />
        </div>
      </aside>

      <div>
        <header className="topbar">
          <span className="logo"><Mark size={28} /></span>
          <div className="row" style={{ gap: 8, flexWrap: 'nowrap' }}>
            {sportPicker}
            <button className="btn sec sm" onClick={() => go('me')}>Me</button>
            <button className="btn sec sm" onClick={signOut}>Sign out</button>
            <LookPicker look={look} onLook={setLook} />
          </div>
        </header>

        <main>
          {body}
          <footer className="sitefoot"><a href="/privacy.html">Privacy policy</a> · <a href="/terms.html">Terms of use</a></footer>
        </main>

        <TabBar items={nav} view={view} onGo={go} />
      </div>
      <Toaster />
    </div>
  )
}

/* The side menu, with a block of ink that slides to the page you are on. */
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

/* An athlete's pages, along the top bar. */
function BarTabs({ items, view, onGo }) {
  const [ref, style] = useIndicator('[aria-current="page"]', [view, items.length])
  return (
    <nav className="abar-tabs" ref={ref} aria-label="Your space">
      <i className="nav-ind" style={style} aria-hidden="true" />
      {items.map(item => (
        <button key={item.key} onClick={() => onGo(item.key)} aria-current={view === item.key ? 'page' : undefined}>
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
