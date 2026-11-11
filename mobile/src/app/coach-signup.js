import { useEffect, useState } from 'react'
import { View } from 'react-native'
import { router } from 'expo-router'
import { api, getSports } from '../lib/api'
import { useSession } from '../lib/session'
import { haptic } from '../lib/haptics'
import { Back, Btn, Eyebrow, Field, Note, Screen, T, Title } from '../ui'
import { SportPicker } from '../ui/pickers'

// A coach account: their details, the one sport they coach, and the sign-up code.
export default function CoachSignup() {
  const session = useSession()
  const [sports, setSports] = useState([])
  const [f, setF] = useState({ name: '', employee_id: '', phone: '', designation: '', sport: '', signup_code: '',
                               email: '', password: '', email_code: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [codeSent, setCodeSent] = useState('')
  const set = k => v => setF(x => ({ ...x, [k]: v }))

  useEffect(() => {
    getSports().then(list => { setSports(list); setF(x => ({ ...x, sport: x.sport || list[0]?.name })) },
                     err => setError(err.message))
  }, [])

  async function create() {
    setBusy(true)
    setError('')
    try {
      session.signedInCoach(await api.signup({ ...f, email: f.email.trim() }))
      haptic.success()
    } catch (err) {
      if (err.status === 428) setCodeSent(err.message)   // an admin address: a code has gone to it
      else { haptic.error(); setError(err.message) }
      setBusy(false)
    }
  }

  const ready = f.name && f.employee_id && f.phone && f.sport && f.email && f.password.length >= 8
  return (
    <Screen>
      <Back onPress={() => router.back()} />
      <Title eyebrow="COACH">Create a coach account</Title>
      <Field label="YOUR NAME" value={f.name} onChangeText={set('name')} autoComplete="name" />
      <Field label="EMPLOYEE ID" value={f.employee_id} onChangeText={set('employee_id')} autoCapitalize="characters" />
      <Field label="MOBILE" value={f.phone} onChangeText={set('phone')} keyboardType="phone-pad" autoComplete="tel"
             hint="Any common format works — we store ten digits." />
      <Field label="DESIGNATION · OPTIONAL" value={f.designation} onChangeText={set('designation')}
             placeholder="e.g. Assistant Professor, Physical Education" />
      <View style={{ gap: 10 }}>
        <Eyebrow>SPORT YOU COACH</Eyebrow>
        <SportPicker sports={sports} value={f.sport} onChange={set('sport')} />
        <T size={12.5} color="ink2">You’ll only ever see students, results and weights for this sport.</T>
      </View>
      <Field label="COACH SIGN-UP CODE" value={f.signup_code} onChangeText={set('signup_code')} autoCapitalize="none"
             autoCorrect={false} hint="Ask whoever runs Stridian — it keeps student details to real coaches." />
      <Field label="EMAIL" value={f.email} onChangeText={set('email')} autoCapitalize="none" autoCorrect={false}
             keyboardType="email-address" autoComplete="email" />
      <Field label="CHOOSE A PASSWORD" value={f.password} onChangeText={set('password')} secureTextEntry
             autoComplete="new-password" placeholder="At least 8 characters" />
      {!!codeSent && (
        <>
          <Note tone="ok">{codeSent}</Note>
          <Field label="CODE FROM THE EMAIL" value={f.email_code} keyboardType="number-pad" autoComplete="one-time-code"
                 onChangeText={v => set('email_code')(v.replace(/\D/g, '').slice(0, 6))} />
        </>
      )}
      <Note>{error}</Note>
      <Btn label="Create account" busy={busy} busyLabel="Creating" disabled={!ready} onPress={create} />
    </Screen>
  )
}
