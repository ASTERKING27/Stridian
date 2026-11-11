import { useEffect, useState } from 'react'
import { api, token } from './api'
import { Seg } from './fx'
import Icon from './Icon'

/* Students sign in with their university email and a password they choose for
   Stridian. Creating an account and resetting a forgotten password are the same two
   steps: get a code by email, then type it with the password you want. */
export default function StudentAuth({ onAuthed }) {
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
      setInfo(`We've emailed a 6-digit code to ${res.email}. It can take a minute, so check spam too.`)
    })
  }

  const finish = e => {
    e.preventDefault()
    run(async () => signedIn(await api.studentVerify({ email, code, password })))
  }

  const emailField = (
    <div className="field">
      <label htmlFor="semail">University email</label>
      <input id="semail" name="email" type="email" required value={email} autoComplete="username"
             placeholder={domain ? `you@${domain}` : ''}
             onChange={e => setEmail(e.target.value)} />
    </div>
  )

  const title = { login: 'Welcome back.', email: 'Join your squad.', code: 'Check your inbox.' }[mode]
  return (
        <>
          <h1 className="auth-h" key={mode}>{title}</h1>

          {mode !== 'code' && (
            <Seg options={[['login', 'Sign in'], ['email', 'New here']]} value={mode} onChange={go}
                 label="Sign in or create an account" />
          )}

          {mode === 'login' && (
            <form onSubmit={signIn}>
              {emailField}
              <div className="field">
                <label htmlFor="spass">Stridian password</label>
                <input id="spass" name="password" type="password" required value={password}
                       autoComplete="current-password" onChange={e => setPassword(e.target.value)} />
              </div>
              <button className="btn wide" disabled={busy}>{busy ? 'Signing in' : 'Sign in'}<Icon name="next" size={18} /></button>
              {error && <div className="note err">{error}</div>}
              <p className="auth-alt">
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
              <button className="btn wide" disabled={busy}>{busy ? 'Sending' : 'Email me a code'}<Icon name="next" size={18} /></button>
              {error && <div className="note err">{error}</div>}
            </form>
          )}

          {mode === 'code' && (
            <form onSubmit={finish}>
              {info && <p className="muted" style={{ marginTop: 0 }}>{info}</p>}
              {/* not shown: tells the password manager which account the new password is for,
                  so it doesn't save the code as the username */}
              <input type="text" name="email" autoComplete="username" defaultValue={email} hidden />
              <div className="field">
                <label htmlFor="scode">6-digit code</label>
                {/* no maxLength: a pasted "246 810" would be cut before the space is dropped */}
                <input id="scode" required inputMode="numeric" autoComplete="one-time-code" value={code}
                       onChange={e => setCode(e.target.value.replace(/\D/g, '').slice(0, 6))} />
              </div>
              <div className="field">
                <label htmlFor="snew">Choose a Stridian password</label>
                <input id="snew" name="new-password" type="password" required minLength={8} value={password}
                       autoComplete="new-password" onChange={e => setPassword(e.target.value)} />
                <p className="muted" style={{ marginTop: 6 }}>
                  At least 8 characters. Don&apos;t reuse your university email password.
                </p>
              </div>
              <button className="btn wide" disabled={busy || code.length !== 6}>
                {busy ? 'Checking' : 'Continue'}<Icon name="next" size={18} />
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
        </>
  )
}
