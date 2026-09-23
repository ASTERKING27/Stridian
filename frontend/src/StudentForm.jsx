import { useEffect, useMemo, useState } from 'react'
import { api } from './api'

const BLOOD = ['', 'A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-']

const DIETS = [
  ['nonveg', 'Non-veg'],
  ['egg', 'Eggetarian'],
  ['veg', 'Vegetarian'],
  ['vegan', 'Vegan'],
]

const ALLERGEN_LABELS = {
  milk: 'Milk / dairy', egg: 'Egg', peanut: 'Peanut', treenut: 'Tree nuts',
  gluten: 'Gluten / wheat', soy: 'Soy', fish: 'Fish', shellfish: 'Shellfish',
}

const EMPTY = {
  name: '', age: '', height_cm: '', weight_kg: '', blood_group: '',
  declared_position: '', student_notes: '', diet_preference: 'nonveg',
  training_hours_per_day: '',
}

export default function StudentForm({ sports, coach, onSaved }) {
  const [sport, setSport] = useState(coach?.sport ?? sports[0].name)
  const [form, setForm] = useState(EMPTY)
  const [allergies, setAllergies] = useState([])
  const [allergens, setAllergens] = useState(Object.keys(ALLERGEN_LABELS))
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.nutritionOptions().then(o => setAllergens(o.allergens)).catch(() => {})
  }, [])

  const positions = useMemo(
    () => sports.find(s => s.name === sport)?.positions ?? [], [sports, sport]
  )

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))
  const num = v => (v === '' ? null : Number(v))
  const toggleAllergy = key =>
    setAllergies(a => (a.includes(key) ? a.filter(x => x !== key) : [...a, key]))

  async function submit(e) {
    e.preventDefault()
    setBusy(true)
    setStatus(null)
    try {
      await api.createStudent({
        name: form.name.trim(),
        sport,
        age: num(form.age),
        height_cm: num(form.height_cm),
        weight_kg: num(form.weight_kg),
        blood_group: form.blood_group || null,
        declared_position: form.declared_position || null,
        student_notes: form.student_notes.trim() || null,
        diet_preference: form.diet_preference,
        allergies: allergies.join(',') || null,
        training_hours_per_day: num(form.training_hours_per_day),
      })
      setStatus({ ok: true, text: `Thanks, ${form.name.trim()} — your ${sport} coach can now add your test results.` })
      setForm({ ...EMPTY, diet_preference: form.diet_preference })
      setAllergies([])
      onSaved()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <form onSubmit={submit}>
      <div className="pagehead">
        <h1>Student entry</h1>
        <p className="lede">
          Fill this in once. It goes straight to the coach for your sport — nobody else
          sees it — and they add the test results afterwards.
        </p>
      </div>

      <div className="card">
        <div className="card-head"><div><h2>About you</h2></div></div>

        <div className="field">
          <label htmlFor="sport">Sport</label>
          <select id="sport" value={sport}
                  onChange={e => { setSport(e.target.value); set('declared_position', '') }}>
            {sports.map(s => <option key={s.slug} value={s.name}>{s.name}</option>)}
          </select>
        </div>

        <div className="grid2">
          <div className="field">
            <label htmlFor="name">Full name *</label>
            <input id="name" required value={form.name} onChange={e => set('name', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="age">Age (years)</label>
            <input id="age" type="number" min="8" max="60" value={form.age}
                   onChange={e => set('age', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="height">Height (cm)</label>
            <input id="height" type="number" min="100" max="250" step="0.5" value={form.height_cm}
                   onChange={e => set('height_cm', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="weight">Weight (kg)</label>
            <input id="weight" type="number" min="20" max="200" step="0.5" value={form.weight_kg}
                   onChange={e => set('weight_kg', e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="blood">Blood group</label>
            <select id="blood" value={form.blood_group} onChange={e => set('blood_group', e.target.value)}>
              {BLOOD.map(b => <option key={b} value={b}>{b || 'Prefer not to say'}</option>)}
            </select>
          </div>
          <div className="field">
            <label htmlFor="pos">Position you usually play</label>
            <select id="pos" value={form.declared_position}
                    onChange={e => set('declared_position', e.target.value)}>
              <option value="">Not sure yet</option>
              {positions.map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
        </div>

        <p className="muted">
          Height and weight are used by the prediction and by the diet plan — roles like
          goalkeeper, centre-back and centre weigh height heavily, and weight sets the
          calorie and macro targets.
        </p>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Training &amp; diet</h2>
            <p className="muted">So the plan matches what you actually eat and train.</p>
          </div>
        </div>

        <div className="field" style={{ maxWidth: 260 }}>
          <label htmlFor="hours">Training hours per day</label>
          <input id="hours" type="number" min="0" max="8" step="0.5" placeholder="1.5"
                 value={form.training_hours_per_day}
                 onChange={e => set('training_hours_per_day', e.target.value)} />
        </div>

        <div className="field">
          <label id="dietlbl">Diet preference</label>
          <div className="toggles" role="group" aria-labelledby="dietlbl">
            {DIETS.map(([key, label]) => (
              <button key={key} type="button" aria-pressed={form.diet_preference === key}
                      onClick={() => set('diet_preference', key)}>
                {label}
              </button>
            ))}
          </div>
        </div>

        <div className="field">
          <label id="allglbl">Allergies / foods to avoid</label>
          <div className="toggles" role="group" aria-labelledby="allglbl">
            {allergens.map(key => (
              <button key={key} type="button" aria-pressed={allergies.includes(key)}
                      onClick={() => toggleAllergy(key)}>
                {ALLERGEN_LABELS[key] ?? key}
              </button>
            ))}
          </div>
          <p className="muted" style={{ marginTop: 8 }}>
            Anything selected is removed from every meal suggestion.
          </p>
        </div>

        <div className="field">
          <label htmlFor="notes">Anything your coach should know</label>
          <textarea id="notes" placeholder="Injury history, preferred foot, availability…"
                    value={form.student_notes} onChange={e => set('student_notes', e.target.value)} />
        </div>

        <button className="btn" disabled={busy || !form.name.trim()}>
          {busy ? 'Saving…' : 'Submit my details'}
        </button>
        {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
      </div>
    </form>
  )
}
