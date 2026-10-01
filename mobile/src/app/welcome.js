import { useState } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { Btn, Eyebrow, I, Icon, Logo, Screen, T, Wordmark } from '../ui'

const ROLES = [
  ['student', 'Student', 'Sign in with your university email', I.student],
  ['coach', 'Coach', 'For coaches and admins of a sport', I.whistle],
]

// Onboarding 11: who's signing in?
export default function Welcome() {
  const { c } = useTheme()
  const [role, setRole] = useState('student')
  return (
    <Screen fill>
      <View style={{ alignItems: 'flex-start', gap: 18, paddingTop: 40 }}>
        <Logo size={96} />
        <Wordmark size={26} />
        <T size={20} color="ink2" style={{ lineHeight: 26 }}>
          Sport-specific talent profiling — and a second coach in your pocket.
        </T>
      </View>
      <Eyebrow style={{ paddingTop: 18 }}>WHO’S SIGNING IN?</Eyebrow>
      <View accessibilityRole="radiogroup" style={{ gap: 10 }}>
        {ROLES.map(([k, label, sub, icon]) => {
          const on = role === k
          const fg = on ? c.bg : c.ink
          return (
            <Pressable key={k} accessibilityRole="radio" accessibilityState={{ checked: on }}
                       onPress={() => { if (!on) { haptic.tick(); setRole(k) } }}
                       style={{ flexDirection: 'row', alignItems: 'center', gap: 16, paddingVertical: 18, paddingHorizontal: 16,
                                borderWidth: 1, borderColor: c.ink, backgroundColor: on ? c.ink : 'transparent' }}>
              <Icon d={icon} size={28} sw={1.4} color={fg} />
              <View style={{ flex: 1, gap: 4 }}>
                <T font="semi" size={18} color={fg}>{label}</T>
                <T size={12.5} color={fg} style={{ opacity: 0.75 }}>{sub}</T>
              </View>
              <View style={{ width: 16, height: 16, borderWidth: 1.5, borderColor: fg, transform: [{ rotate: '45deg' }],
                             alignItems: 'center', justifyContent: 'center' }}>
                {on && <View style={{ width: 6, height: 6, backgroundColor: fg }} />}
              </View>
            </Pressable>
          )
        })}
      </View>
      <View style={{ flex: 1, justifyContent: 'flex-end' }}>
        <Btn label={`Continue as ${role}`} onPress={() => router.push({ pathname: '/sign-in', params: { role } })} />
      </View>
    </Screen>
  )
}
