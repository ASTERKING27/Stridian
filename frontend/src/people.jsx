import { useEffect, useMemo, useState } from 'react'
import { api, authedImage, initials, openAuthed, utc } from './api'

/* The pieces the student portal, the enrol form and the coach's Profile tab share:
   photos, the details form, the read-only details, and achievements. */

export const LEVELS = [
  ['university', 'University'], ['zonal', 'Zonal'], ['state', 'State'],
  ['national', 'National'], ['international', 'International'],
]
export const levelWord = key => LEVELS.find(([k]) => k === key)?.[1] ?? ''

const BLOOD = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']
const DIETS = [['nonveg', 'Non-veg'], ['egg', 'Eggetarian'], ['veg', 'Vegetarian'], ['vegan', 'Vegan']]
export const DIET_WORDS = Object.fromEntries(DIETS)
const ALLERGEN_LABELS = {
  milk: 'Milk / dairy', egg: 'Egg', peanut: 'Peanut', treenut: 'Tree nuts',
  gluten: 'Gluten / wheat', soy: 'Soy', fish: 'Fish', shellfish: 'Shellfish',
}

// every text field of the form; allergies is a list and handled on its own
const TEXT_FIELDS = [
  'name', 'ra_number', 'dob', 'phone', 'personal_email', 'blood_group', 'id_mark',
  'father_name', 'father_phone', 'mother_name', 'mother_phone', 'aadhaar', 'passport',
  'highest_level', 'highest_level_details', 'height_cm', 'weight_kg', 'declared_position',
  'training_hours_per_day', 'diet_preference', 'student_notes',
]

export const spacedAadhaar = a => (a ? a.replace(/(\d{4})(?=\d)/g, '$1 ') : '')

/* ------------------------------------------------------------------ photos */

/* Shrink a picture in the browser before it goes up: a phone photo is 3–8 MB, the
   server takes 4 MB at most, and nobody needs 4000 pixels of a certificate. */
export async function shrinkImage(file, maxSide = 1600, quality = 0.85) {
  let bitmap
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  } catch {
    throw new Error("Couldn't open that picture — try a JPEG or PNG.")
  }
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
  const canvas = document.createElement('canvas')
  canvas.width = Math.round(bitmap.width * scale)
  canvas.height = Math.round(bitmap.height * scale)
  const ctx = canvas.getContext('2d')
  ctx.fillStyle = '#fff'                 // transparent PNGs would turn black as JPEG
  ctx.fillRect(0, 0, canvas.width, canvas.height)
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
  bitmap.close?.()
  return new Promise((resolve, reject) => canvas.toBlob(
    b => (b ? resolve(b) : reject(new Error("Couldn't read that picture."))), 'image/jpeg', quality))
}

/* A signed-in image. `version` changes with every new photo, so an old one is never
   shown from the browser's cache. */
function useAuthedImage(url, version) {
  const [src, setSrc] = useState(null)
  useEffect(() => {
    if (!url || !version) { setSrc(null); return undefined }
    let live = true
    let made = null
    authedImage(`${url}?v=${encodeURIComponent(version)}`)
      .then(u => { made = u; if (live) setSrc(u); else URL.revokeObjectURL(u) })
      .catch(() => live && setSrc(null))
    return () => { live = false; if (made) URL.revokeObjectURL(made) }
  }, [url, version])
  return src
}

export function Photo({ url, version, name, size = 64 }) {
  const src = useAuthedImage(url, version)
  const box = { width: size, height: size }
  return src
    ? <img className="photo" src={src} alt={`Photo of ${name}`} style={box} />
    : <span className="avatar photo" style={{ ...box, fontSize: Math.round(size * 0.34) }}
            aria-hidden="true">{initials(name)}</span>
}

/* A button that picks a picture, shrinks it and hands back a JPEG blob. */
export function PhotoButton({ label = 'Change photo', onPhoto, disabled }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function pick(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setBusy(true)
    setError('')
    try {
      await onPhoto(await shrinkImage(file, 800, 0.88))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }
  return (
    <span>
      <label className={`btn sec sm${busy || disabled ? ' disabled' : ''}`} style={{ margin: 0 }}>
        {busy ? 'Uploading…' : label}
        <input type="file" accept="image/*" hidden disabled={busy || disabled} onChange={pick} />
      </label>
      {error && <span className="note err" style={{ display: 'block' }}>{error}</span>}
    </span>
  )
}

/* ----------------------------------------------------------- details form */

const blankForm = student => {
  const s = student ?? {}
  const out = Object.fromEntries(TEXT_FIELDS.map(k => [k, s[k] == null ? '' : String(s[k])]))
  out.diet_preference = s.diet_preference || 'nonveg'
  return out
}
const allergyList = s => (s?.allergies ? s.allergies.split(',').filter(Boolean) : [])

/*
  One form for a student's details, in four situations:
    enrol   a student joining (everything the university needs is required)
    create  an admin adding someone by hand (only the name is required)
    self    a student correcting their details (RA number and DOB only if still empty)
    admin   an admin editing anyone's details, sport included
  Edits send only what changed.
*/
export function DetailsForm({ student, mode, sports, sport: fixedSport, sportLocked = false, onSubmit,
                              submitLabel, onCancel, children }) {
  const [form, setForm] = useState(() => blankForm(student))
  const [allergies, setAllergies] = useState(() => allergyList(student))
  const [allergens, setAllergens] = useState(Object.keys(ALLERGEN_LABELS))
  const [sport, setSport] = useState(student?.sport ?? fixedSport ?? sports?.[0]?.name ?? '')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => {
    api.nutritionOptions().then(o => setAllergens(o.allergens)).catch(() => {})
  }, [])

  const editing = mode === 'self' || mode === 'admin'
  const staff = mode === 'create' || mode === 'admin'       // someone filling it in for a student
  const strict = mode === 'enrol' || mode === 'self'        // what the university needs
  const needed = strict ? { required: true } : {}
  const onceLocked = key => mode === 'self' && !!student?.[key]
  const positions = useMemo(() => sports?.find(s => s.name === sport)?.positions ?? [], [sports, sport])
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const toggleAllergy = key => setAllergies(a => (a.includes(key) ? a.filter(x => x !== key) : [...a, key]))

  // built by hand: toISOString() would give yesterday's date before 5:30 am in India
  const today = new Date()
  const pad = n => String(n).padStart(2, '0')
  const yearsAgo = n => `${today.getFullYear() - n}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}`

  function body() {
    const all = { ...form, allergies: allergies.join(',') }
    if (!editing) return { ...all, sport }
    const before = { ...blankForm(student), allergies: allergyList(student).join(',') }
    const changed = Object.fromEntries(Object.entries(all).filter(([k, v]) => v !== before[k]))
    if (mode === 'admin' && sport !== student.sport) changed.sport = sport
    return changed
  }

  async function submit(e) {
    e.preventDefault()
    const payload = body()
    if (editing && Object.keys(payload).length === 0) {
      setStatus({ ok: true, text: 'Nothing changed.' })
      return
    }
    setBusy(true)
    setStatus(null)
    try {
      const done = await onSubmit(payload)
      if (done) setStatus({ ok: true, text: done })
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  const fieldOf = (key, label, props = {}) => {
    const { hint, ...rest } = props
    return (
      <div className="field">
        <label htmlFor={`f-${key}`}>{label}{rest.required ? ' *' : ''}</label>
        <input id={`f-${key}`} value={form[key]} onChange={e => set(key, e.target.value)} {...rest} />
        {hint && <p className="muted" style={{ marginTop: 5 }}>{hint}</p>}
      </div>
    )
  }
  const lockedHint = key => (onceLocked(key) ? 'Only an admin can change this — ask your coach.' : undefined)

  return (
    <form onSubmit={submit}>
      {children}

      <div className="card">
        <div className="card-head"><div><h2>{staff ? 'About the student' : 'About you'}</h2></div></div>
        <div className="grid2">
          {(mode === 'enrol' || mode === 'create' || mode === 'admin') && (
            <div className="field">
              <label htmlFor="f-sport">Sport</label>
              <select id="f-sport" value={sport} disabled={sportLocked}
                      onChange={e => { setSport(e.target.value); set('declared_position', '') }}>
                {sports.map(s => (
                  <option key={s.slug} value={s.name}>{s.name}</option>
                ))}
              </select>
              {mode === 'admin' && sport !== student?.sport && (
                <p className="muted" style={{ marginTop: 5 }}>
                  Moving sport sends them back to Pending — positions differ between sports.
                </p>
              )}
            </div>
          )}
          {fieldOf('name', 'Full name (as in university records)', { required: true, autoComplete: 'name' })}
          {fieldOf('ra_number', 'RA number', {
            ...(mode === 'enrol' ? { required: true } : {}), disabled: onceLocked('ra_number'),
            placeholder: 'RA2311003010123', autoComplete: 'off',
            style: { textTransform: 'uppercase' }, hint: lockedHint('ra_number'),
          })}
          {fieldOf('dob', 'Date of birth', {
            ...(mode === 'enrol' ? { required: true } : {}), type: 'date', disabled: onceLocked('dob'),
            min: yearsAgo(60), max: yearsAgo(14), hint: lockedHint('dob'),
          })}
          {fieldOf('phone', 'Mobile', { ...needed, type: 'tel', inputMode: 'tel', autoComplete: 'tel',
                                        placeholder: '98765 43210' })}
          {fieldOf('personal_email', 'Personal email', { type: 'email', autoComplete: 'email',
                                                          hint: 'Besides the university email.' })}
          <div className="field">
            <label htmlFor="f-blood">Blood group{strict ? ' *' : ''}</label>
            <select id="f-blood" value={form.blood_group} {...needed}
                    onChange={e => set('blood_group', e.target.value)}>
              <option value="">Choose…</option>
              {BLOOD.map(b => <option key={b} value={b}>{b}</option>)}
            </select>
          </div>
          {fieldOf('id_mark', 'Identification mark', { placeholder: 'e.g. Mole on the left cheek' })}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Family</h2>
            <p className="muted">At least one parent&apos;s mobile number, for emergencies and travel consent.</p>
          </div>
        </div>
        <div className="grid2">
          {fieldOf('father_name', "Father's name", needed)}
          {fieldOf('father_phone', "Father's mobile", { type: 'tel', inputMode: 'tel' })}
          {fieldOf('mother_name', "Mother's name", needed)}
          {fieldOf('mother_phone', "Mother's mobile", { type: 'tel', inputMode: 'tel' })}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Identity documents</h2>
            <p className="muted">Needed to register {staff ? 'them' : 'you'} for university, zonal and national events.</p>
          </div>
        </div>
        <div className="grid2">
          {fieldOf('aadhaar', 'Aadhaar number', { ...needed, inputMode: 'numeric', autoComplete: 'off',
                                                  placeholder: '1234 5678 9012', maxLength: 14 })}
          {fieldOf('passport', 'Passport number', { autoComplete: 'off', placeholder: 'If you have one',
                                                     style: { textTransform: 'uppercase' } })}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>{staff ? 'Their sport' : 'Your sport'}</h2>
            <p className="muted">
              {mode === 'create' || mode === 'admin'
                ? 'Measurements are used by the prediction and the diet plan.'
                : 'Height and weight feed the position prediction and your diet plan. Add proof of your achievements from the Achievements tab.'}
            </p>
          </div>
        </div>
        <div className="grid2">
          <div className="field">
            <label htmlFor="f-level">Highest level {staff ? 'played' : 'you have played'} at</label>
            <select id="f-level" value={form.highest_level} onChange={e => set('highest_level', e.target.value)}>
              <option value="">Not yet competed</option>
              {LEVELS.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="f-pos">Position {staff ? 'they usually play' : 'you usually play'}</label>
            <select id="f-pos" value={form.declared_position}
                    onChange={e => set('declared_position', e.target.value)}>
              <option value="">Not sure yet</option>
              {positions.map(p => <option key={p} value={p}>{p}</option>)}
              {form.declared_position && !positions.includes(form.declared_position) && (
                <option value={form.declared_position}>{form.declared_position}</option>
              )}
            </select>
          </div>
        </div>
        {form.highest_level && (
          <div className="field">
            <label htmlFor="f-leveld">About that level</label>
            <textarea id="f-leveld" value={form.highest_level_details}
                      placeholder="Event, year and result — e.g. TN State U-19 Championship 2023, Silver"
                      onChange={e => set('highest_level_details', e.target.value)} />
          </div>
        )}
        <div className="grid3">
          {fieldOf('height_cm', 'Height (cm)', { type: 'number', min: 100, max: 250, step: 0.5 })}
          {fieldOf('weight_kg', 'Weight (kg)', { type: 'number', min: 20, max: 200, step: 0.5 })}
          {fieldOf('training_hours_per_day', 'Training hours / day', { type: 'number', min: 0, max: 8, step: 0.5 })}
        </div>
        <div className="field">
          <label id="dietlbl">Diet preference</label>
          <div className="toggles" role="group" aria-labelledby="dietlbl">
            {DIETS.map(([key, label]) => (
              <button key={key} type="button" aria-pressed={form.diet_preference === key}
                      onClick={() => set('diet_preference', key)}>{label}</button>
            ))}
          </div>
        </div>
        <div className="field">
          <label id="allglbl">Allergies / foods to avoid</label>
          <div className="toggles" role="group" aria-labelledby="allglbl">
            {allergens.map(key => (
              <button key={key} type="button" aria-pressed={allergies.includes(key)}
                      onClick={() => toggleAllergy(key)}>{ALLERGEN_LABELS[key] ?? key}</button>
            ))}
          </div>
        </div>
        <div className="field">
          <label htmlFor="f-notes">Anything the coach should know</label>
          <textarea id="f-notes" value={form.student_notes} placeholder="Injury history, preferred foot, availability…"
                    onChange={e => set('student_notes', e.target.value)} />
        </div>

        <div className="row">
          <button className="btn" disabled={busy}>{busy ? 'Saving…' : submitLabel}</button>
          {onCancel && <button type="button" className="btn sec" onClick={onCancel}>Cancel</button>}
        </div>
        {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
      </div>
    </form>
  )
}

/* ---------------------------------------------------------- details, read */

export function DetailsView({ student: s }) {
  const age = s.age ? ` (${s.age} yrs)` : ''
  const dob = s.dob ? new Date(`${s.dob}T00:00`).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' }) : ''
  const groups = [
    ['Personal', [
      ['RA number', s.ra_number], ['Date of birth', dob && dob + age], ['Mobile', s.phone],
      ['University email', s.email], ['Personal email', s.personal_email],
      ['Blood group', s.blood_group], ['Identification mark', s.id_mark],
    ]],
    ['Family', [
      ["Father's name", s.father_name], ["Father's mobile", s.father_phone],
      ["Mother's name", s.mother_name], ["Mother's mobile", s.mother_phone],
    ]],
    ['Identity documents', [['Aadhaar', spacedAadhaar(s.aadhaar)], ['Passport', s.passport]]],
    ['Sport', [
      ['Sport', s.sport],
      ['Highest level (their word)', [levelWord(s.highest_level), s.highest_level_details].filter(Boolean).join(' — ')],
      ['Highest verified level', levelWord(s.top_verified_level)],
      ['Height', s.height_cm && `${s.height_cm} cm`], ['Weight', s.weight_kg && `${s.weight_kg} kg`],
      ['Position they play', s.declared_position],
      ['Training per day', s.training_hours_per_day && `${s.training_hours_per_day} h`],
      ['Diet', DIET_WORDS[s.diet_preference]], ['Allergies', s.allergies?.replaceAll(',', ', ')],
      ['Notes', s.student_notes],
    ]],
  ]
  return (
    <div className="detailgrid">
      {groups.map(([title, rows]) => (
        <div key={title}>
          <h3>{title}</h3>
          <table className="data details">
            <tbody>
              {rows.map(([k, v]) => (
                <tr key={k}><td className="muted">{k}</td><td>{v || '—'}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

/* ----------------------------------------------------------- achievements */

const STATUS = {
  draft: ['Not sent', ''], pending: ['Waiting for check', 'warn'],
  verified: ['Verified', 'good'], rejected: ['Needs fixing', 'bad'],
}

/* Pick a certificate (photo or PDF), shrink a photo, and upload it. */
export function CertificateUpload({ upload, onUploaded, aiOn, label = 'Add a certificate' }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function pick(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    setError('')
    const pdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
    if (pdf && file.size > 4 * 1024 * 1024) {
      setError('That PDF is over 4 MB — take a photo of the certificate instead.')
      return
    }
    setBusy(true)
    try {
      const blob = pdf ? file : await shrinkImage(file, 2000, 0.85)
      onUploaded(await upload(blob, file.name))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <label className={`btn${busy ? ' disabled' : ''}`} style={{ margin: 0 }}>
        {busy ? (aiOn ? 'Reading the certificate…' : 'Uploading…') : label}
        <input type="file" accept="image/*,application/pdf" hidden disabled={busy} onChange={pick} />
      </label>
      {error && <div className="note err">{error}</div>}
    </div>
  )
}

function AchievementForm({ item, canSend, onSave, onCancel }) {
  const [f, setF] = useState({
    title: item.title ?? '', level: item.level ?? '', year: item.year ?? '',
    result: item.result ?? '', details: item.details ?? '',
  })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = (k, v) => setF(x => ({ ...x, [k]: v }))

  async function save(submit) {
    setBusy(true)
    setError('')
    try {
      await onSave({ ...f, submit })
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <div className="achform">
      <div className="grid2">
        <div className="field">
          <label htmlFor={`t-${item.id}`}>Event / tournament *</label>
          <input id={`t-${item.id}`} value={f.title} maxLength={200} onChange={e => set('title', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor={`l-${item.id}`}>Level *</label>
          <select id={`l-${item.id}`} value={f.level} onChange={e => set('level', e.target.value)}>
            <option value="">Choose…</option>
            {LEVELS.map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor={`y-${item.id}`}>Year</label>
          <input id={`y-${item.id}`} type="number" min="1990" max="2100" value={f.year}
                 onChange={e => set('year', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor={`r-${item.id}`}>Result</label>
          <input id={`r-${item.id}`} value={f.result} maxLength={80} placeholder="Gold, Runners-up, Participation…"
                 onChange={e => set('result', e.target.value)} />
        </div>
      </div>
      <div className="field">
        <label htmlFor={`d-${item.id}`}>Details</label>
        <textarea id={`d-${item.id}`} value={f.details} maxLength={2000} onChange={e => set('details', e.target.value)} />
      </div>
      <div className="row">
        {canSend && (
          <button className="btn sm" disabled={busy || !f.title.trim() || !f.level} onClick={() => save(true)}>
            Send to coach
          </button>
        )}
        <button className={`btn sm${canSend ? ' sec' : ''}`} disabled={busy} onClick={() => save(false)}
                title={canSend && item.status === 'pending' ? 'Takes it back from your coach until you send it again' : undefined}>
          {canSend ? 'Save, send later' : 'Save'}
        </button>
        <button className="linkbtn" disabled={busy} onClick={onCancel}>Cancel</button>
      </div>
      {error && <div className="note err">{error}</div>}
    </div>
  )
}

/*
  One achievement. `as` decides what can be done with it:
    student  edit and send (until it is verified), delete (unless verified)
    coach    verify or reject, with a reason
    admin    all a coach can, plus edit its details
*/
export function Achievement({ item, as, studentName, certUrl, onChange, onDelete }) {
  const [editing, setEditing] = useState(as === 'student' && item.status === 'draft' && !item.title)
  const [rejecting, setRejecting] = useState(false)
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [label, tone] = STATUS[item.status] ?? [item.status, '']
  const ai = item.ai_read
  const nameOnIt = ai?.name_on_certificate
  const nameDiffers = nameOnIt && studentName &&
    !nameOnIt.toLowerCase().split(/\s+/).some(w => w.length > 2 && studentName.toLowerCase().includes(w))
  const student = as === 'student'
  const reviewer = as === 'coach' || as === 'admin'

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

  const save = async body => {
    const saved = await (student ? api.editMyAchievement(item.id, body) : api.editAchievement(item.id, body))
    setEditing(false)
    onChange(saved)
  }
  const review = (decision, why) => run(async () => {
    onChange(await api.reviewAchievement(item.id, decision, why || null, item.version))
    setRejecting(false)
    setNote('')
  })

  return (
    <div className="ach">
      <div className="achhead">
        <div style={{ minWidth: 0 }}>
          <b>{item.title || 'Certificate — details not filled in yet'}</b>
          <div className="muted">
            {[levelWord(item.level), item.year, item.result].filter(Boolean).join(' · ') || 'No level or year yet'}
          </div>
        </div>
        <span className={`pill ${tone}`}><i className="dot" />{label}</span>
      </div>

      {item.details && <p className="achdetails">{item.details}</p>}
      {(item.status === 'rejected' || item.status === 'draft') && item.review_note && (
        <div className="banner bad" style={{ margin: '8px 0 0' }}>
          <b>{item.reviewed_by_name ?? 'Your coach'}:</b> {item.review_note}
        </div>
      )}
      {item.status === 'verified' && (
        <p className="muted" style={{ margin: '6px 0 0' }}>
          Verified{item.reviewed_by_name ? ` by ${item.reviewed_by_name}` : ''}
          {item.reviewed_at ? ` on ${utc(item.reviewed_at).toLocaleDateString()}` : ''}.
        </p>
      )}
      {ai && ai.is_certificate === false && (
        <p className="note err">The AI reader doesn&apos;t think this is a sports certificate — check it&apos;s the right file.</p>
      )}
      {reviewer && nameOnIt && (
        <p className={`note ${nameDiffers ? 'err' : ''}`}>
          Name on the certificate (as the AI read it): <b>{nameOnIt}</b>{nameDiffers ? ' — doesn’t match the student' : ''}
        </p>
      )}

      {editing ? (
        <AchievementForm item={item} canSend={student} onSave={save} onCancel={() => setEditing(false)} />
      ) : (
        <div className="row achactions">
          <button className="linkbtn" onClick={() => run(() => openAuthed(certUrl))}>
            View {item.cert_mime === 'application/pdf' ? 'PDF' : 'certificate'}
          </button>
          {student && item.status !== 'verified' && (
            <>
              <button className="linkbtn" onClick={() => setEditing(true)}>Edit details</button>
              {(item.status === 'draft' || item.status === 'rejected') && item.title && item.level && (
                <button className="btn sm" disabled={busy}
                        onClick={() => run(() => save({ submit: true }))}>Send to coach</button>
              )}
              <button className="linkbtn danger" disabled={busy} onClick={() => {
                if (confirm('Delete this certificate?')) run(async () => { await api.deleteMyAchievement(item.id); onDelete() })
              }}>Delete</button>
            </>
          )}
          {as === 'admin' && <button className="linkbtn" onClick={() => setEditing(true)}>Edit details</button>}
          {reviewer && item.status !== 'verified' && (
            <button className="btn sm" disabled={busy || !item.title || !item.level}
                    title={!item.title || !item.level ? 'It needs an event and a level first' : undefined}
                    onClick={() => review('verified')}>Verify</button>
          )}
          {reviewer && item.status !== 'rejected' && !rejecting && (
            <button className="btn sm sec" disabled={busy} onClick={() => setRejecting(true)}>Reject</button>
          )}
        </div>
      )}

      {rejecting && (
        <div className="row" style={{ marginTop: 8 }}>
          <input aria-label="Why it's rejected" placeholder="Why? The student sees this — e.g. photo is blurry"
                 value={note} maxLength={500} onChange={e => setNote(e.target.value)} style={{ flex: '1 1 240px' }} />
          <button className="btn sm" disabled={busy || !note.trim()} onClick={() => review('rejected', note.trim())}>
            Reject
          </button>
          <button className="linkbtn" onClick={() => setRejecting(false)}>Cancel</button>
        </div>
      )}
      {error && <div className="note err">{error}</div>}
    </div>
  )
}
