import { useState } from 'react'
import { api, token } from './api'
import { Seg } from './fx'
import { LookPicker } from './Theme'

/* Each step is its own <form>, with the autocomplete words password managers look for:
   "username" + "current-password" is a sign-in, "username" + "new-password" is a new
   account or a reset. One form flipping between them made browsers offer a new password
   on sign-in. */
export default function Login({ sports, onAuthed, onCancel, look, onLook }) {
  const [mode, setMode] = useState('login')   // login | signup | forgot | reset
  const [form, setForm] = useState({
    name: '', email: '', password: '', sport: sports[0].name, signup_code: '',
    employee_id: '', phone: '', designation: '', email_code: '',
  })
  const [error, setError] = useState('')
  const [codeSent, setCodeSent] = useState('')   // a code has gone out: what to tell them
  const [busy, setBusy] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  function go(next) {
    setMode(next)
    setError('')
    setCodeSent('')
    setForm(f => ({ ...f, password: '', email_code: '' }))
  }

  async function run(action) {
    setBusy(true)
    setError('')
    try {
      await action()
    } catch (err) {
      if (err.status === 428) {
        setCodeSent(err.message)   // an admin address: the code has gone out
      } else {
        setError(err.message)
      }
    } finally {
      setBusy(false)
    }
  }

  const signedIn = res => {
    token.set(res.token)
    onAuthed(res.coach)
  }

  const signIn = e => {
    e.preventDefault()
    run(async () => signedIn(await api.login({ email: form.email, password: form.password })))
  }

  const signUp = e => {
    e.preventDefault()
    run(async () => signedIn(await api.signup(form)))
  }

  const sendReset = e => {
    e?.preventDefault()
    run(async () => {
      const res = await api.resetCode(form.email)
      setForm(f => ({ ...f, email: res.email, email_code: '' }))
      setMode('reset')
      setCodeSent(`If a coach account uses ${res.email}, a 6-digit code is on its way to it. ` +
                  'It can take a minute — check spam too.')
    })
  }

  const finishReset = e => {
    e.preventDefault()
    run(async () => signedIn(await api.reset({
      email: form.email, code: form.email_code, password: form.password,
    })))
  }

  const emailField = (
    <div className="field">
      <label htmlFor="cemail">Email</label>
      <input id="cemail" name="email" type="email" required value={form.email}
             onChange={e => set('email', e.target.value)} autoComplete="username" />
    </div>
  )
  const errorNote = error && <div className="note err">{error}</div>

  return (
    <div className="authpage">
      <div className="authcard">
        <div className="row" style={{ justifyContent: 'flex-end', marginBottom: 6 }}>
          <LookPicker look={look} onLook={onLook} />
        </div>

        <div className="authhero">
          <span className="eyebrow">Stridian for coaches</span>
          <h1>Your squad, read for you.</h1>
          <p>Who is close to a level-up, who needs a check-in, and what needs you today.</p>
        </div>

        <div className="card">
          <div className="brand">
            <span className="mark" aria-hidden="true">S</span>
            <b>Stridian<span>Coach access</span></b>
          </div>

          {(mode === 'login' || mode === 'signup') && (
            <Seg options={[['login', 'Sign in'], ['signup', 'Create account']]} value={mode} onChange={go}
                 label="Sign in or create an account" />
          )}

          {mode === 'login' && (
            <form id="signin" name="signin" onSubmit={signIn}>
              {emailField}
              <div className="field">
                <label htmlFor="cpass">Password</label>
                <input id="cpass" name="password" type="password" required value={form.password}
                       onChange={e => set('password', e.target.value)} autoComplete="current-password" />
              </div>
              <button className="btn wide" disabled={busy}>{busy ? 'Signing in…' : 'Sign in'}</button>
              {errorNote}
              <p style={{ textAlign: 'center', marginTop: 12 }}>
                <button type="button" className="linkbtn" onClick={() => go('forgot')}>
                  Forgot your password?
                </button>
              </p>
            </form>
          )}

          {mode === 'signup' && (
            <form id="signup" name="signup" onSubmit={signUp}>
              <div className="field">
                <label htmlFor="cname">Your name</label>
                <input id="cname" required value={form.name} onChange={e => set('name', e.target.value)}
                       autoComplete="name" />
              </div>
              <div className="grid2" style={{ gap: 10 }}>
                <div className="field">
                  <label htmlFor="cemp">Employee ID</label>
                  <input id="cemp" required value={form.employee_id} autoComplete="off"
                         onChange={e => set('employee_id', e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="cphone">Mobile</label>
                  <input id="cphone" type="tel" inputMode="tel" required value={form.phone}
                         autoComplete="tel" onChange={e => set('phone', e.target.value)} />
                </div>
              </div>
              <div className="field">
                <label htmlFor="cdes">Designation <span className="muted">(optional)</span></label>
                <input id="cdes" value={form.designation} placeholder="e.g. Assistant Professor, Physical Education"
                       onChange={e => set('designation', e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="csport">Sport you coach</label>
                <select id="csport" value={form.sport} onChange={e => set('sport', e.target.value)}>
                  {sports.map(s => <option key={s.slug} value={s.name}>{s.name}</option>)}
                </select>
                <p className="muted" style={{ marginTop: 6 }}>
                  You'll only ever see students, results and weights for this sport.
                </p>
              </div>
              <div className="field">
                <label htmlFor="ccode">Coach sign-up code</label>
                <input id="ccode" value={form.signup_code} autoComplete="off"
                       onChange={e => set('signup_code', e.target.value)} />
                <p className="muted" style={{ marginTop: 6 }}>
                  Ask whoever runs this site — it keeps student details to real coaches.
                </p>
              </div>
              {emailField}
              <div className="field">
                <label htmlFor="cpass">Choose a password</label>
                <input id="cpass" name="new-password" type="password" required minLength={8}
                       value={form.password} onChange={e => set('password', e.target.value)}
                       autoComplete="new-password" />
                <p className="muted" style={{ marginTop: 6 }}>At least 8 characters.</p>
              </div>
              {codeSent && (
                <div className="field">
                  <p className="note ok" style={{ marginTop: 0 }}>{codeSent}</p>
                  <label htmlFor="cecode">Code from the email</label>
                  <input id="cecode" inputMode="numeric" autoComplete="one-time-code" value={form.email_code}
                         onChange={e => set('email_code', e.target.value.replace(/\D/g, '').slice(0, 6))} />
                </div>
              )}
              <button className="btn wide" disabled={busy}>{busy ? 'Working…' : 'Create account'}</button>
              {errorNote}
            </form>
          )}

          {mode === 'forgot' && (
            <form id="forgot" name="forgot" onSubmit={sendReset}>
              <h2 style={{ marginTop: 0 }}>Reset your password</h2>
              <p className="muted" style={{ marginTop: 0 }}>
                Type your account&apos;s email. We&apos;ll send a 6-digit code to it, then you
                choose a new password.
              </p>
              {emailField}
              <button className="btn wide" disabled={busy}>{busy ? 'Sending…' : 'Email me a code'}</button>
              {errorNote}
              <p style={{ textAlign: 'center', marginTop: 12 }}>
                <button type="button" className="linkbtn" onClick={() => go('login')}>
                  ← Back to sign in
                </button>
              </p>
            </form>
          )}

          {mode === 'reset' && (
            <form id="reset" name="reset" onSubmit={finishReset}>
              <h2 style={{ marginTop: 0 }}>Reset your password</h2>
              {codeSent && <p className="muted" style={{ marginTop: 0 }}>{codeSent}</p>}
              {/* not shown: tells the password manager which account the new password is for */}
              <input type="text" name="email" autoComplete="username" defaultValue={form.email} hidden />
              <div className="field">
                <label htmlFor="crcode">6-digit code</label>
                {/* no maxLength: a pasted "246 810" would be cut before the space is dropped */}
                <input id="crcode" required inputMode="numeric" autoComplete="one-time-code"
                       value={form.email_code}
                       onChange={e => set('email_code', e.target.value.replace(/\D/g, '').slice(0, 6))} />
              </div>
              <div className="field">
                <label htmlFor="cnew">New password</label>
                <input id="cnew" name="new-password" type="password" required minLength={8}
                       value={form.password} onChange={e => set('password', e.target.value)}
                       autoComplete="new-password" />
                <p className="muted" style={{ marginTop: 6 }}>
                  At least 8 characters. Anywhere else you&apos;re signed in will be signed out.
                </p>
              </div>
              <button className="btn wide" disabled={busy || form.email_code.length !== 6}>
                {busy ? 'Checking…' : 'Set password and sign in'}
              </button>
              {errorNote}
              <p className="row" style={{ justifyContent: 'space-between', marginTop: 12 }}>
                <button type="button" className="linkbtn" disabled={busy} onClick={() => sendReset()}>
                  Send a new code
                </button>
                <button type="button" className="linkbtn" onClick={() => go('forgot')}>
                  Use a different email
                </button>
              </p>
            </form>
          )}
        </div>

        <div style={{ textAlign: 'center' }}>
          <button className="linkbtn" onClick={onCancel}>← I'm a student, take me back</button>
        </div>
      </div>
    </div>
  )
}
