import { useEffect, useState } from 'react'
import { Alert, Linking, Pressable, View } from 'react-native'
import { router } from 'expo-router'
import Constants from 'expo-constants'
import * as SecureStore from 'expo-secure-store'
import { BASE } from '../../lib/api'
import { useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { NOTIFY_DEFAULT, NOTIFY_KEY, registerPush } from '../../lib/notifications'
import { Back, Eyebrow, I, Icon, Mono, Screen, Seg, Switch, T, Title } from '../../ui'


// Profile board, 03: appearance, notifications, account.
export default function Settings() {
  const s = useSession()
  const { c, choice, setChoice, motion, setMotion } = useTheme()
  const [n, setN] = useState(NOTIFY_DEFAULT)
  useEffect(() => { SecureStore.getItemAsync(NOTIFY_KEY).then(v => v && setN({ ...NOTIFY_DEFAULT, ...JSON.parse(v) })).catch(() => {}) }, [])
  const flip = k => v => {
    const next = { ...n, [k]: v }
    setN(next)
    // saved on the phone, then sent with its push token so the server only sends what's on
    SecureStore.setItemAsync(NOTIFY_KEY, JSON.stringify(next)).then(() => registerPush(v)).catch(() => {})
  }
  const student = s.role === 'student'
  const email = student ? s.me?.email : s.coach?.email

  const row = { flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 13, borderTopWidth: 1, borderTopColor: c.line }
  const toggle = (title, sub, k) => (
    <View style={row}>
      <View style={{ flex: 1, gap: 3 }}><T size={15}>{title}</T><T size={12} color="ink2">{sub}</T></View>
      <Switch value={n[k]} onChange={flip(k)} label={title} />
    </View>
  )
  const action = (icon, label, onPress, chevron) => (
    <Pressable onPress={onPress} accessibilityRole="button"
               style={({ pressed }) => [row, { backgroundColor: pressed ? c.soft : 'transparent' }]}>
      <Icon d={icon} size={20} />
      <T size={15} style={{ flex: 1 }}>{label}</T>
      {chevron && <Icon d={I.next} size={18} />}
    </Pressable>
  )

  return (
    <Screen gap={14}>
      <Back label={student ? 'Profile' : 'Back'} onPress={() => router.back()} />
      <Title eyebrow="SETTINGS">Settings</Title>
      <View>
        <Eyebrow style={{ paddingVertical: 4 }}>APPEARANCE</Eyebrow>
        <View style={{ gap: 8, paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.line }}>
          <T size={15}>Theme</T>
          <Seg options={[['white', 'WHITE'], ['dark', 'DARK'], ['auto', 'SYSTEM']]} value={choice}
               onChange={v => { haptic.tap(); setChoice(v) }} />
        </View>
        <View style={{ gap: 8, paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.line }}>
          <T size={15}>Motion</T>
          <Seg options={[['system', 'SYSTEM'], ['full', 'FULL'], ['reduced', 'REDUCED']]} value={motion} onChange={setMotion} />
        </View>
      </View>
      <View>
        <Eyebrow style={{ paddingTop: 8, paddingBottom: 4 }}>NOTIFICATIONS</Eyebrow>
        {toggle('Video analysed', 'When a clip is ready', 'video')}
        {toggle(student ? 'Coach updates' : 'Squad updates', student ? 'Verification and achievements' : 'New enrolments and certificates', 'coach')}
        {student && toggle('Weekly focus nudge', 'One reminder before the week ends', 'focus')}
      </View>
      <View>
        <Eyebrow style={{ paddingTop: 8, paddingBottom: 4 }}>ACCOUNT</Eyebrow>
        {action(I.lock, 'Change password', () => router.push({ pathname: '/password', params: { role: student ? 'student' : 'coach', email, fixed: '1' } }), true)}
        {action(I.signout, 'Sign out', () => Alert.alert('Sign out of Stridian?', '', [
          { text: 'Stay', style: 'cancel' }, { text: 'Sign out', onPress: s.signOut }]))}
        {action(I.delete, 'Delete account', () => router.push('/delete-account'), true)}
      </View>
      <View style={{ flexDirection: 'row', gap: 16, paddingTop: 4, alignItems: 'center' }}>
        <Pressable onPress={() => Linking.openURL(`${BASE}/privacy.html`)} hitSlop={8}>
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84, textDecorationLine: 'underline' }}>PRIVACY POLICY</Mono>
        </Pressable>
        <Pressable onPress={() => Linking.openURL(`${BASE}/terms.html`)} hitSlop={8}>
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84, textDecorationLine: 'underline' }}>TERMS OF USE</Mono>
        </Pressable>
        <View style={{ flex: 1 }} />
        <Mono size={10.5} color="ink2">V {Constants.expoConfig?.version ?? '1.0'}</Mono>
      </View>
    </Screen>
  )
}
