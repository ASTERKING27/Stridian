import { useEffect, useMemo, useState } from 'react'
import { View } from 'react-native'
import { api } from '../lib/api'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { Btn, Choice, Eyebrow, Field, Note, T } from './index'
import { SportPicker, Toggles } from './pickers'

export const LEVELS = [['university', 'University'], ['zonal', 'Zonal'], ['state', 'State'],
                       ['national', 'National'], ['international', 'International']]
export const levelWord = key => LEVELS.find(([k]) => k === key)?.[1] ?? ''
export const TEAMS = [['M', 'Men’s team'], ['W', 'Women’s team']]
const BLOOD = ['A+', 'A-', 'B+', 'B-', 'O+', 'O-', 'AB+', 'AB-'].map(b => [b, b])
const DIETS = [['nonveg', 'Non-veg'], ['egg', 'Eggetarian'], ['veg', 'Vegetarian'], ['vegan', 'Vegan']]
const ALLERGEN_LABELS = {
  milk: 'Milk / dairy', egg: 'Egg', peanut: 'Peanut', treenut: 'Tree nuts',
  gluten: 'Gluten / wheat', soy: 'Soy', fish: 'Fish', shellfish: 'Shellfish',
}
const TEXT_FIELDS = [
  'name', 'ra_number', 'dob', 'phone', 'personal_email', 'blood_group', 'id_mark',
  'father_name', 'father_phone', 'mother_name', 'mother_phone', 'aadhaar', 'passport',
  'category', 'highest_level', 'highest_level_details', 'height_cm', 'weight_kg', 'declared_position',
  'training_hours_per_day', 'diet_preference', 'student_notes',
]

// the API speaks 2005-03-14; people type 14/03/2005
export const toDMY = iso => (iso ? iso.split('-').reverse().join('/') : '')
export function toISO(dmy) {
  const m = dmy.trim().match(/^(\d{1,2})[/.\- ]+(\d{1,2})[/.\- ]+(\d{4})$/)
  return m ? `${m[3]}-${m[2].padStart(2, '0')}-${m[1].padStart(2, '0')}` : dmy.trim()
}
// typing 14032005 lays itself out as 14/03/2005
export const dmyMask = t => {
  const d = t.replace(/\D/g, '').slice(0, 8)
  return [d.slice(0, 2), d.slice(2, 4), d.slice(4)].filter(Boolean).join('/')
}

const blank = student => {
  const s = student ?? {}
  const out = Object.fromEntries(TEXT_FIELDS.map(k => [k, s[k] == null ? '' : String(s[k])]))
  out.dob = toDMY(s.dob)
  out.diet_preference = s.diet_preference || 'nonveg'
  return out
}
const allergyList = s => (s?.allergies ? s.allergies.split(',').filter(Boolean) : [])

/*
  One form for a student's details (the website's people.jsx), in four situations:
    enrol   a student joining (everything the university needs is required)
    create  an admin adding someone by hand (only the name is required)
    self    a student correcting their details (RA number, DOB and team only if still empty)
    admin   an admin editing anyone's details, sport included
  Edits send only what changed.
*/
export default function DetailsForm({ student, mode, sports, sport: fixedSport, onSubmit, submitLabel, busyLabel = 'Saving', children }) {
  const { c } = useTheme()
  const [form, setForm] = useState(() => blank(student))
  const [allergies, setAllergies] = useState(() => allergyList(student))
  const [allergens, setAllergens] = useState(Object.keys(ALLERGEN_LABELS))
  const [sport, setSport] = useState(student?.sport ?? fixedSport ?? sports?.[0]?.name ?? '')
  const [busy, setBusy] = useState(false)
  const [status, setStatus] = useState(null)

  useEffect(() => { api.nutritionOptions().then(o => setAllergens(o.allergens)).catch(() => {}) }, [])
  useEffect(() => { if (!sport && sports?.length) setSport(sports[0].name) }, [sports, sport])

  const editing = mode === 'self' || mode === 'admin'
  const staff = mode === 'create' || mode === 'admin'
  const strict = mode === 'enrol' || mode === 'self'
  const locked = key => mode === 'self' && !!student?.[key]
  const positions = useMemo(() => sports?.find(s => s.name === sport)?.positions ?? [], [sports, sport])
  const set = k => v => setForm(f => ({ ...f, [k]: v }))
  const star = on => (on ? ' *' : '')
  const you = staff ? 'they' : 'you'

  function body() {
    const all = { ...form, dob: toISO(form.dob), allergies: allergies.join(',') }
    if (!editing) return { ...all, sport }
    const before = { ...blank(student), allergies: allergyList(student).join(',') }
    before.dob = toISO(before.dob)
    const changed = Object.fromEntries(Object.entries(all).filter(([k, v]) => v !== before[k]))
    if (mode === 'admin' && sport !== student.sport) changed.sport = sport
    return changed
  }

  async function submit() {
    const payload = body()
    if (editing && Object.keys(payload).length === 0) return setStatus({ ok: true, text: 'Nothing changed.' })
    setBusy(true)
    setStatus(null)
    try {
      const done = await onSubmit(payload)
      haptic.success()
      if (done) setStatus({ ok: true, text: done })
    } catch (err) {
      haptic.error()
      setStatus({ ok: false, text: err.message })
    }
    setBusy(false)
  }

  const lockHint = key => (locked(key) ? 'Only an admin can change this — ask your coach.' : undefined)
  const section = (title, note) => (
    <View style={{ gap: 6, paddingTop: 14, borderTopWidth: 1, borderTopColor: c.line }}>
      <Eyebrow color="ink">{title}</Eyebrow>
      {!!note && <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>{note}</T>}
    </View>
  )

  return (
    <View style={{ gap: 20 }}>
      {children}

      {section(staff ? 'ABOUT THE STUDENT' : 'ABOUT YOU')}
      {(mode === 'enrol' || staff) && (
        <View style={{ gap: 10 }}>
          <Eyebrow>SPORT</Eyebrow>
          <SportPicker sports={sports ?? []} value={sport}
                       onChange={v => { setSport(v); set('declared_position')('') }} />
          {mode === 'admin' && sport !== student?.sport && (
            <T size={12.5} color="ink2">Moving sport sends them back to Pending — positions differ between sports.</T>
          )}
        </View>
      )}
      <Field label={`FULL NAME (AS IN UNIVERSITY RECORDS)${star(true)}`} value={form.name} onChangeText={set('name')} autoComplete="name" />
      <Field label={`RA NUMBER${star(mode === 'enrol')}`} value={form.ra_number} placeholder="RA2311003010123"
             onChangeText={v => set('ra_number')(v.toUpperCase())} autoCapitalize="characters" autoCorrect={false}
             editable={!locked('ra_number')} hint={lockHint('ra_number')} />
      <Field label={`DATE OF BIRTH${star(mode === 'enrol')}`} value={form.dob} placeholder="DD / MM / YYYY"
             onChangeText={v => set('dob')(dmyMask(v))} keyboardType="number-pad" maxLength={10}
             editable={!locked('dob')} hint={lockHint('dob')} />
      <Field label={`MOBILE${star(strict)}`} value={form.phone} onChangeText={set('phone')} keyboardType="phone-pad"
             autoComplete="tel" placeholder="98765 43210" hint="Any common format works — we store ten digits." />
      <Field label="PERSONAL EMAIL" value={form.personal_email} onChangeText={set('personal_email')} autoCapitalize="none"
             keyboardType="email-address" hint="Besides the university email." />
      <View style={{ gap: 10 }}>
        <Eyebrow>{`BLOOD GROUP${star(strict)}`}</Eyebrow>
        <Choice options={BLOOD} value={form.blood_group} onChange={set('blood_group')} />
      </View>
      <Field label="IDENTIFICATION MARK" value={form.id_mark} onChangeText={set('id_mark')} placeholder="e.g. Mole on the left cheek" />

      {section('FAMILY', 'At least one parent’s mobile number, for emergencies and travel consent.')}
      <Field label={`FATHER’S NAME${star(strict)}`} value={form.father_name} onChangeText={set('father_name')} />
      <Field label="FATHER’S MOBILE" value={form.father_phone} onChangeText={set('father_phone')} keyboardType="phone-pad" />
      <Field label={`MOTHER’S NAME${star(strict)}`} value={form.mother_name} onChangeText={set('mother_name')} />
      <Field label="MOTHER’S MOBILE" value={form.mother_phone} onChangeText={set('mother_phone')} keyboardType="phone-pad" />

      {section('IDENTITY DOCUMENTS', `Needed to register ${staff ? 'them' : 'you'} for university, zonal and national events.`)}
      <Field label={`AADHAAR NUMBER${star(strict)}`} value={form.aadhaar} onChangeText={set('aadhaar')}
             keyboardType="number-pad" placeholder="1234 5678 9012" maxLength={14} />
      <Field label="PASSPORT NUMBER" value={form.passport} onChangeText={v => set('passport')(v.toUpperCase())}
             autoCapitalize="characters" placeholder="If you have one" />

      {section(staff ? 'THEIR SPORT' : 'YOUR SPORT', 'Height and weight feed the position match and the diet plan.')}
      <View style={{ gap: 10 }}>
        <Eyebrow>{`TEAM${star(strict)}`}</Eyebrow>
        <Choice options={TEAMS} value={form.category} onChange={set('category')} disabled={locked('category')} />
        <T size={12.5} color="ink2">
          {locked('category') ? 'Only your coach can change this.' : `Which level targets ${staff ? 'their' : 'your'} results are compared with.`}
        </T>
      </View>
      <View style={{ gap: 10 }}>
        <Eyebrow>{`HIGHEST LEVEL ${you === 'you' ? 'YOU HAVE PLAYED' : 'PLAYED'} AT`}</Eyebrow>
        <Choice options={[['', 'Not yet'], ...LEVELS]} value={form.highest_level} onChange={set('highest_level')} />
      </View>
      {!!form.highest_level && (
        <Field label="ABOUT THAT LEVEL" value={form.highest_level_details} onChangeText={set('highest_level_details')} multiline
               placeholder="Event, year and result — e.g. TN State U-19 Championship 2023, Silver" />
      )}
      {positions.length > 0 && (
        <View style={{ gap: 10 }}>
          <Eyebrow>{`POSITION ${you.toUpperCase()} USUALLY PLAY`}</Eyebrow>
          <Choice options={[['', 'Not sure yet'], ...positions.map(p => [p, p])]} value={form.declared_position}
                  onChange={set('declared_position')} />
        </View>
      )}
      <View style={{ flexDirection: 'row', gap: 16 }}>
        <Field style={{ flex: 1 }} label="HEIGHT · CM" value={form.height_cm} onChangeText={set('height_cm')} keyboardType="decimal-pad" />
        <Field style={{ flex: 1 }} label="WEIGHT · KG" value={form.weight_kg} onChangeText={set('weight_kg')} keyboardType="decimal-pad" />
      </View>
      <Field label="TRAINING HOURS A DAY" value={form.training_hours_per_day} onChangeText={set('training_hours_per_day')}
             keyboardType="decimal-pad" />
      <View style={{ gap: 10 }}>
        <Eyebrow>DIET</Eyebrow>
        <Choice options={DIETS} value={form.diet_preference} onChange={set('diet_preference')} />
      </View>
      <View style={{ gap: 10 }}>
        <Eyebrow>ALLERGIES · FOODS TO AVOID</Eyebrow>
        <Toggles options={allergens.map(k => [k, ALLERGEN_LABELS[k] ?? k])} value={allergies} onChange={setAllergies} />
      </View>
      <Field label="ANYTHING THE COACH SHOULD KNOW" value={form.student_notes} onChangeText={set('student_notes')} multiline
             placeholder="Injury history, preferred foot, availability…" />

      {status && <Note tone={status.ok ? 'ok' : 'bad'}>{status.text}</Note>}
      <Btn label={submitLabel} busy={busy} busyLabel={busyLabel} onPress={submit} />
    </View>
  )
}
