import { useState } from 'react'
import { Alert, View } from 'react-native'
import { router } from 'expo-router'
import { api } from '../../lib/api'
import { useSession } from '../../lib/session'
import { haptic } from '../../lib/haptics'
import { Back, Btn, Field, Note, Screen, T, Title } from '../../ui'

// Settings › Delete account — what the app stores require: gone for good, from the phone.
export default function DeleteAccount() {
  const s = useSession()
  const student = s.role === 'student'
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const go = () => Alert.alert('Delete your account?', 'This can’t be undone.', [
    { text: 'Keep it', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: remove },
  ])
  async function remove() {
    setBusy(true)
    setError('')
    try {
      await (student ? api.deleteMyStudentAccount(password) : api.deleteMyCoachAccount(password))
      haptic.success()
      s.forget()
    } catch (err) {
      haptic.error()
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <Back label="Settings" onPress={() => router.back()} />
      <Title eyebrow="ACCOUNT">Delete your account</Title>
      <View style={{ gap: 10 }}>
        {student ? (
          <>
            <T size={15} style={{ lineHeight: 22 }}>This deletes your Stridian login and your record in your sport:</T>
            <T size={14} color="ink2" style={{ lineHeight: 21 }}>
              Your details and photo, your test results and report, your certificates, your drill videos and your focus
              streak. Your coach will no longer see you in the squad.
            </T>
          </>
        ) : (
          <>
            <T size={15} style={{ lineHeight: 22 }}>This deletes your coach login and your details.</T>
            <T size={14} color="ink2" style={{ lineHeight: 21 }}>
              Your squad stays: the students, their results and the cards you finished belong to your sport, and other
              coaches and admins keep working with them.
            </T>
          </>
        )}
        <T size={14} color="ink2" style={{ lineHeight: 21 }}>You can make a new account later, but nothing deleted comes back.</T>
      </View>
      <Field label="YOUR STRIDIAN PASSWORD" value={password} onChangeText={setPassword} secureTextEntry autoComplete="current-password" />
      <Note>{error}</Note>
      <Btn label="Delete my account" busy={busy} busyLabel="Deleting" disabled={!password} onPress={go} />
    </Screen>
  )
}
