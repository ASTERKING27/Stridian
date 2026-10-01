import { useEffect, useRef, useState } from 'react'
import { Pressable, TextInput, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api } from '../lib/api'
import { useSession } from '../lib/session'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { Back, Btn, Field, Mono, Note, Screen, T, Title } from '../ui'
import { toast } from '../ui/Toast'

const RESEND = 60   // the server sends at most one code a minute

/* Onboarding 13. A student signing up or resetting (the same two steps: a code to their
   university inbox, then that code with the password they choose), or a coach resetting
   a forgotten password. */
export default function CodeFlow() {
  const p = useLocalSearchParams()
  const fixed = !!p.fixed       // changing the password while signed in: their own email only
  const student = p.role !== 'coach'
  const session = useSession()
  const { c } = useTheme()
  const [email, setEmail] = useState(p.email ?? '')
  const [sentTo, setSentTo] = useState(null)
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [wait, setWait] = useState(0)
  const box = useRef(null)

  useEffect(() => {
    if (wait <= 0) return undefined
    const t = setTimeout(() => setWait(w => w - 1), 1000)
    return () => clearTimeout(t)
  }, [wait])

  async function send() {
    setBusy(true)
    setError('')
    try {
      const res = await (student ? api.studentCode(email.trim()) : api.resetCode(email.trim()))
      setSentTo(res.email)
      setCode('')
      setWait(RESEND)
      setTimeout(() => box.current?.focus(), 300)
    } catch (err) {
      haptic.error()
      setError(err.message)
    }
    setBusy(false)
  }

  async function finish() {
    setBusy(true)
    setError('')
    try {
      const body = { email: sentTo, code, password }
      if (student) session.signedInStudent(await api.studentVerify(body))
      else session.signedInCoach(await api.reset(body))
      haptic.success()
      if (fixed) { toast({ title: 'Password changed', sub: 'EVERY OTHER DEVICE IS SIGNED OUT' }); router.back() }
    } catch (err) {
      haptic.error()
      setError(err.message)
      setBusy(false)
    }
  }

  if (!sentTo) {
    return (
      <Screen fill>
        <Back onPress={() => router.back()} />
        <Title eyebrow={fixed ? 'ACCOUNT' : student ? (p.mode === 'reset' ? 'FORGOT YOUR PASSWORD' : 'NEW TO STRIDIAN') : 'COACH · FORGOT YOUR PASSWORD'}>
          {fixed ? 'Change your password' : student ? 'Get a code' : 'Reset your password'}
        </Title>
        <T size={15} color="ink2" style={{ lineHeight: 22 }}>
          {student
            ? 'We’ll email a 6-digit code to your university inbox. With it you choose your Stridian password.'
            : 'Type your account’s email. We’ll send a 6-digit code to it, then you choose a new password.'}
        </T>
        <Field label={student ? 'UNIVERSITY EMAIL' : 'EMAIL'} placeholder={student ? 'name@srmist.edu.in' : 'you@example.com'}
               value={email} onChangeText={setEmail} autoCapitalize="none" autoCorrect={false} editable={!fixed}
               keyboardType="email-address" autoComplete="email" returnKeyType="send" onSubmitEditing={send} />
        <Note>{error}</Note>
        <Btn label="Email me a code" busy={busy} busyLabel="Sending" disabled={!email.trim()} onPress={send} />
      </Screen>
    )
  }

  const ready = code.length === 6 && password.length >= 8
  return (
    <Screen fill gap={22}>
      <Back onPress={() => setSentTo(null)} />
      <Title eyebrow="PROVE IT’S YOUR EMAIL">{student ? 'Check your university inbox' : 'Check your inbox'}</Title>
      <T size={15} color="ink2" style={{ lineHeight: 22 }}>
        {student ? 'We sent a 6-digit code to ' : 'If a coach account uses '}
        <T font="semi" size={15}>{sentTo}</T>
        {student ? '. It works for 15 minutes.' : ', a 6-digit code is on its way. It works for 15 minutes — check spam too.'}
      </T>

      <Pressable onPress={() => box.current?.focus()} accessibilityLabel={`6-digit code, ${code.length} typed`}
                 style={{ flexDirection: 'row', gap: 8 }}>
        {Array.from({ length: 6 }, (_, i) => (
          <View key={i} style={{ flex: 1, height: 62, borderWidth: 1, borderBottomWidth: i === code.length ? 3 : 1,
                                 borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
            <Mono size={26} font="monoMedium">{code[i] ?? ''}</Mono>
          </View>
        ))}
        {/* one real input under the six boxes: paste and the SMS/email autofill both work */}
        <TextInput ref={box} value={code} onChangeText={t => setCode(t.replace(/\D/g, '').slice(0, 6))}
                   keyboardType="number-pad" textContentType="oneTimeCode" autoComplete="one-time-code"
                   caretHidden style={{ position: 'absolute', opacity: 0, width: '100%', height: '100%' }} />
      </Pressable>

      <Field label={student ? 'NEW STRIDIAN PASSWORD' : 'NEW PASSWORD'} placeholder="At least 8 characters"
             value={password} onChangeText={setPassword} secureTextEntry autoComplete="new-password"
             textContentType="newPassword" hint={student ? undefined : 'Anywhere else you’re signed in will be signed out.'} />
      <Note>{error}</Note>
      <Btn label="Set password and sign in" busy={busy} busyLabel="Checking" disabled={!ready} onPress={finish} />
      {wait > 0
        ? <Mono size={11} color="ink2" style={{ textAlign: 'center', letterSpacing: 0.9 }}>
            SEND AGAIN IN 0:{String(wait).padStart(2, '0')}
          </Mono>
        : <Btn kind="text" label="Send a new code" onPress={send} />}
      <View style={{ flex: 1, justifyContent: 'flex-end' }}>
        <T size={12.5} color="ink2" style={{ lineHeight: 19 }}>
          Five wrong tries and the code stops working — just ask for a new one.
        </T>
      </View>
    </Screen>
  )
}
