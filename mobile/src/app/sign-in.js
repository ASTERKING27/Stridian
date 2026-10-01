import { useState } from 'react'
import { Linking, Text, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api, BASE } from '../lib/api'
import { useSession } from '../lib/session'
import { haptic } from '../lib/haptics'
import { Back, Btn, Divider, Field, Note, Screen, T, Title } from '../ui'

// Onboarding 12: sign in, as a student (university email) or a coach.
export default function SignIn() {
  const { role = 'student' } = useLocalSearchParams()
  const session = useSession()
  const student = role === 'student'
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function signIn() {
    setBusy(true)
    setError('')
    try {
      const body = { email: email.trim(), password }
      if (student) session.signedInStudent(await api.studentLogin(body))
      else session.signedInCoach(await api.login(body))
      haptic.success()
    } catch (err) {
      haptic.error()
      setError(err.message)
      setBusy(false)
    }
  }

  const code = mode => router.push({ pathname: '/code', params: { role, mode, email: email.trim() } })
  return (
    <Screen fill>
      <Back onPress={() => router.back()} />
      <Title eyebrow={student ? 'STUDENT' : 'COACH'}>Sign in</Title>
      <Field label={student ? 'UNIVERSITY EMAIL' : 'EMAIL'} placeholder={student ? 'name@srmist.edu.in' : 'you@example.com'}
             value={email} onChangeText={setEmail} autoCapitalize="none" autoCorrect={false}
             keyboardType="email-address" autoComplete="email" textContentType="username" />
      <Field label="STRIDIAN PASSWORD" value={password} onChangeText={setPassword} secureTextEntry
             autoComplete="current-password" textContentType="password" returnKeyType="go" onSubmitEditing={signIn}
             hint={student ? 'Your password for Stridian — not your university one. Stridian never sees that.'
               : 'Coaches pick their sport once, when they sign up.'} />
      <Note>{error}</Note>
      <View style={{ gap: 6 }}>
        <Btn label="Sign in" busy={busy} busyLabel="Signing in" disabled={!email.trim() || !password} onPress={signIn} />
        <Btn kind="text" label="Forgot your password?" onPress={() => code('reset')} />
      </View>
      <Divider label="NEW HERE" />
      <Btn kind="secondary" label={student ? 'Sign up with a code' : 'Create a coach account'}
           onPress={() => (student ? code('new') : router.push('/coach-signup'))} />
      <View style={{ flex: 1, justifyContent: 'flex-end' }}>
        <T size={12} color="ink2" style={{ textAlign: 'center', lineHeight: 18 }}>
          By continuing you agree to the{' '}
          <Text style={{ textDecorationLine: 'underline' }} onPress={() => Linking.openURL(`${BASE}/terms.html`)}>Terms of use</Text>
          {' '}and{' '}
          <Text style={{ textDecorationLine: 'underline' }} onPress={() => Linking.openURL(`${BASE}/privacy.html`)}>Privacy policy</Text>.
        </T>
      </View>
    </Screen>
  )
}
