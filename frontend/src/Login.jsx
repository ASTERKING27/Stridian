import { useState } from 'react'
import { api, token } from './api'
import Icon from './Icon'

export default function Login({ sports, onAuthed, onCancel, theme, onTheme }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', email: '', password: '', sport: sports[0].name, signup_code: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const signup = mode === 'signup'

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      const res = signup
        ? await api.signup(form)
        : await api.login({ email: form.email, password: form.password })
      token.set(res.token)
      onAuthed(res.coach)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

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
            <b>Stridian<span>Coach access</span></b>
          </div>

          <div className="seg" role="group" aria-label="Sign in or create an account">
            <button type="button" aria-pressed={!signup} onClick={() => { setMode('login'); setError('') }}>
              Sign in
            </button>
            <button type="button" aria-pressed={signup} onClick={() => { setMode('signup'); setError('') }}>
              Create account
            </button>
          </div>

          <form onSubmit={submit}>
            {signup && (
              <>
                <div className="field">
                  <label htmlFor="cname">Your name</label>
                  <input id="cname" required value={form.name} onChange={e => set('name', e.target.value)}
                         autoComplete="name" />
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
              </>
            )}

            <div className="field">
              <label htmlFor="cemail">Email</label>
              <input id="cemail" type="email" required value={form.email}
                     onChange={e => set('email', e.target.value)} autoComplete="email" />
            </div>

            <div className="field">
              <label htmlFor="cpass">Password</label>
              <input id="cpass" type="password" required minLength={signup ? 8 : undefined}
                     value={form.password} onChange={e => set('password', e.target.value)}
                     autoComplete={signup ? 'new-password' : 'current-password'} />
              {signup && <p className="muted" style={{ marginTop: 6 }}>At least 8 characters.</p>}
            </div>

            <button className="btn wide" disabled={busy}>
              {busy ? 'Working…' : signup ? 'Create account' : 'Sign in'}
            </button>
            {error && <div className="note err">{error}</div>}
          </form>
        </div>

        <div style={{ textAlign: 'center' }}>
          <button className="linkbtn" onClick={onCancel}>← I'm a student, take me back</button>
        </div>
      </div>
    </div>
  )
}
