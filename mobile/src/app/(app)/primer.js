import { View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import * as SecureStore from 'expo-secure-store'
import * as ImagePicker from 'expo-image-picker'
import Svg, { Path } from 'react-native-svg'
import { registerPush } from '../../lib/notifications'
import { useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { Btn, I, Icon, Mono, Screen, T, TILE_D } from '../../ui'

// Onboarding 14 and 16: why the app asks, before the phone's own permission prompt.
const KINDS = {
  camera: { step: 0, icon: I.camera, title: 'Record drills right here', allow: 'Allow camera',
    reasons: ['Film a drill and send it straight for pose analysis.', 'The camera is only on while you’re recording.',
              'Your clips are seen by you and your sport’s coaches.'] },
  notifications: { step: 1, icon: I.bell, title: 'Know when it’s ready', allow: 'Turn on notifications',
    reasons: { student: ['Analysis runs on the coach’s computer — we’ll tell you when a video is done.',
                         'Hear when your coach verifies you or an achievement.',
                         'A nudge for this week’s focus, so the streak keeps going.'],
               coach: ['Hear when a student enrols or sends a certificate to check.',
                       'Know when a drill clip has been analysed.',
                       'Nothing else — no marketing, ever.'] } },
}

export default function Primer() {
  const { kind = 'notifications' } = useLocalSearchParams()
  const s = useSession()
  const { c } = useTheme()
  const k = KINDS[kind] ?? KINDS.notifications
  const reasons = Array.isArray(k.reasons) ? k.reasons : k.reasons[s.role === 'student' ? 'student' : 'coach']
  const done = async allow => {
    await SecureStore.setItemAsync(`stridian.primed.${kind}`, '1').catch(() => {})
    if (allow) await (kind === 'camera' ? ImagePicker.requestCameraPermissionsAsync().catch(() => {}) : registerPush(true))
    router.back()
  }
  const total = Object.keys(KINDS).length
  return (
    <Screen fill gap={22}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14, height: 44 }}>
        <View style={{ flexDirection: 'row', gap: 4, width: 60 }}>
          {Array.from({ length: total }, (_, i) => <View key={i} style={{ flex: 1, height: 3, backgroundColor: i <= k.step ? c.ink : c.line }} />)}
        </View>
        <Mono size={10.5} color="ink2" style={{ letterSpacing: 1.26 }}>{k.step + 1} OF {total}</Mono>
        <View style={{ flex: 1 }} />
        <Btn kind="text" label="Skip" onPress={() => done(false)} />
      </View>
      <View style={{ height: 200, justifyContent: 'center' }}>
        <View style={{ width: 150, height: 167, alignItems: 'center', justifyContent: 'center' }}>
          <Svg width={150} height={167} viewBox="0 0 72 80" style={{ position: 'absolute' }}><Path d={TILE_D} fill={c.ink} /></Svg>
          <Icon d={k.icon} size={64} sw={1.3} color={c.bg} />
        </View>
        {[[176, 58, 150, 10], [206, 96, 110, 8], [236, 128, 70, 6]].map(([x, y, w, h]) => (
          <View key={x} style={{ position: 'absolute', left: x, top: y, width: w, height: h, borderRadius: h / 2, backgroundColor: c.ink,
                                 transform: [{ rotate: '140deg' }] }} />
        ))}
      </View>
      <T font="title" size={32} style={{ lineHeight: 35 }}>{k.title}</T>
      <View>
        {reasons.map((r, i) => (
          <View key={r} style={{ flexDirection: 'row', gap: 14, paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.line }}>
            <Mono size={11} color="ink2" style={{ paddingTop: 3 }}>0{i + 1}</Mono>
            <T size={15} style={{ flex: 1, lineHeight: 21 }}>{r}</T>
          </View>
        ))}
      </View>
      <View style={{ flex: 1, justifyContent: 'flex-end', gap: 8 }}>
        <Mono size={10} color="ink2" style={{ textAlign: 'center', letterSpacing: 0.8, paddingBottom: 6 }}>YOU CAN CHANGE THIS LATER IN SETTINGS</Mono>
        <Btn label={k.allow} onPress={() => done(true)} />
        <Btn kind="text" label="Not now" onPress={() => done(false)} />
      </View>
    </Screen>
  )
}
