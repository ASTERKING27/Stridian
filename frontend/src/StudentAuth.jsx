import { useEffect, useState } from 'react'
import { api, token } from './api'
import Icon from './Icon'

/* Students sign in with their university email and a password they choose for
   Stridian. Creating an account and resetting a forgotten password are the same two
   steps: get a code by email, then type it with the password you want. */
export default function StudentAuth({ onAuthed, onCoach, theme, onTheme }) {
  const [mode, setMode] = useState('login')   // login | email | code
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [code, setCode] = useState('')
  const [domain, setDomain] = useState('')
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.health().then(h => setDomain(h.studentDomain || '')).catch(() => {})
  }, [])

  function go(next) {
    setMode(next)
    setError('')
    setInfo('')
    setPassword('')
  }

  async function run(action) {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const signedIn = res => {
    token.set(res.token, 'student')
    onAuthed(res.me)
  }

  const signIn = e => {
    e.preventDefault()
    run(async () => signedIn(await api.studentLogin({ email, password })))
  }

  const sendCode = e => {
    e?.preventDefault()
    run(async () => {
      const res = await api.studentCode(email)
      setEmail(res.email)
      setCode('')
      setMode('code')
      setInfo(`We've emailed a 6-digit code to ${res.email}. It can take a minute — check spam too.`)
    })
  }

  const finish = e => {
    e.preventDefault()
    run(async () => signedIn(await api.studentVerify({ email, code, password })))
  }

  const emailField = (
    <div className="field">
      <label htmlFor="semail">University email</label>
      <input id="semail" type="email" required value={email} autoComplete="email"
             placeholder={domain ? `you@${domain}` : ''}
             onChange={e => setEmail(e.target.value)} />
    </div>
  )

  return (
    <div className="authpage">
      <div className="authcard">
        <div className="row" style={{ justifyContent: 'flex-end', marginBottom: 6 }}>
          <button className="iconbtn" onClick={onTheme} aria-label={`Theme: ${theme}. Click to change.`}
                  title={`Theme: ${theme}`}>
            <Icon name={theme === 'system' ? 'laptop' : theme === 'dark' ? 'moon' : 'sun'} size={16} />
          </button>
        </div>

        <div className="card">
          <div className="brand">
            <span className="mark" aria-hidden="true">S</span>
            <b>Stridian<span>Student access</span></b>
          </div>

          {mode !== 'code' && (
            <div className="seg" role="group" aria-label="Sign in or create an account">
              <button type="button" aria-pressed={mode === 'login'} onClick={() => go('login')}>
                Sign in
              </button>
              <button type="button" aria-pressed={mode === 'email'} onClick={() => go('email')}>
                New here
              </button>
            </div>
          )}

          {mode === 'login' && (
            <form onSubmit={signIn}>
              {emailField}
              <div className="field">
                <label htmlFor="spass">Stridian password</label>
                <input id="spass" type="password" required value={password}
                       autoComplete="current-password" onChange={e => setPassword(e.target.value)} />
              </div>
              <button className="btn wide" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
              {error && <div className="note err">{error}</div>}
              <p style={{ textAlign: 'center', marginTop: 12 }}>
                <button type="button" className="linkbtn" onClick={() => go('email')}>
                  Forgot your password?
                </button>
              </p>
            </form>
          )}

          {mode === 'email' && (
            <form onSubmit={sendCode}>
              <p className="muted" style={{ marginTop: 0 }}>
                We&apos;ll email a code to your university inbox to check it&apos;s yours,
                then you choose a password for Stridian. The same steps reset a forgotten
                password.
              </p>
              {emailField}
              <button className="btn wide" disabled={busy}>{busy ? 'Sending…' : 'Email me a code'}</button>
              {error && <div className="note err">{error}</div>}
            </form>
          )}

          {mode === 'code' && (
            <form onSubmit={finish}>
              {info && <p className="muted" style={{ marginTop: 0 }}>{info}</p>}
              <div className="field">
                <label htmlFor="scode">6-digit code</label>
                {/* no maxLength: a pasted "246 810" would be cut before the space is dropped */}
                <input id="scode" required inputMode="numeric" autoComplete="one-time-code" value={code}
                       onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />
              </div>
              <div className="field">
                <label htmlFor="snew">Choose a Stridian password</label>
                <input id="snew" type="password" required minLength={8} value={password}
                       autoComplete="new-password" onChange={e => setPassword(e.target.value)} />
                <p className="muted" style={{ marginTop: 6 }}>
                  At least 8 characters. Don&apos;t reuse your university email password.
                </p>
              </div>
              <button className="btn wide" disabled={busy || code.length !== 6}>
                {busy ? 'Checking…' : 'Continue'}
              </button>
              {error && <div className="note err">{error}</div>}
              <p className="row" style={{ justifyContent: 'space-between', marginTop: 12 }}>
                <button type="button" className="linkbtn" disabled={busy} onClick={() => sendCode()}>
                  Send a new code
                </button>
                <button type="button" className="linkbtn" onClick={() => go('email')}>
                  Use a different email
                </button>
              </p>
            </form>
          )}
        </div>

        <div style={{ textAlign: 'center' }}>
          <button className="linkbtn" onClick={onCoach}>I&apos;m a coach →</button>
        </div>
        <footer className="sitefoot" style={{ textAlign: 'center' }}>
          <a href="/privacy.html">Privacy policy</a>
        </footer>
      </div>
    </div>
  )
}
