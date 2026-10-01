import { Modal, Pressable, View } from 'react-native'
import { BlurView } from 'expo-blur'
import { formatValue, shortUnits } from '../lib/api'
import { useTheme } from '../lib/theme'
import { Logo, Mono, T } from './index'

const SHORT = ['UNI', 'ZONAL', 'STATE', 'NATIONAL', 'INTL']
// the card is the theme turned inside out (Achievement board)
const CARD = {
  white: { bg: '#121211', fg: '#F3F2EE', fg2: '#A8A7A1', line: 'rgba(243,242,238,0.2)', scrim: 'rgba(18,18,17,0.22)' },
  dark: { bg: '#EEEDE8', fg: '#0F0F0E', fg2: '#55544F', line: 'rgba(15,15,14,0.18)', scrim: 'rgba(0,0,0,0.45)' },
}

/* A level reached goes on record (Achievement board): the level, what it rests on, the
   date and the next target. `party` is the dashboard's `celebrate`; `rings` its rings.
   ponytail: the card appears whole — the sweep, rising letters and count-up come with
   the motion build. */
export default function LevelReached({ party, rings, onClose }) {
  const { name, reduced } = useTheme()
  const k = CARD[name]
  const L = party.level
  const up = !L && party.levelUps[0]
  const ring = up && rings.find(r => r.key === up.key)
  const level = L ? L.level : ring?.level ?? 0
  const word = (L ? L.word : up.level).toUpperCase()
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()

  return (
    <Modal transparent visible animationType={reduced ? 'none' : 'fade'} onRequestClose={onClose} statusBarTranslucent>
      <BlurView intensity={20} tint={name === 'dark' ? 'dark' : 'light'} blurMethod="dimezisBlurViewSdk31Plus"
                style={{ flex: 1, backgroundColor: k.scrim, justifyContent: 'center', paddingHorizontal: 22 }}>
        <View accessibilityRole="alert" accessibilityLabel={`New level: ${word}`}
              style={{ backgroundColor: k.bg, paddingTop: 26, paddingHorizontal: 26, paddingBottom: 24, minHeight: 500 }}>
          <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
            <Logo size={34} color={k.fg} />
            <Mono size={10.5} color={k.fg2} style={{ letterSpacing: 1.26 }}>{today}</Mono>
          </View>
          <Mono size={10.5} color={k.fg2} style={{ letterSpacing: 1.47, paddingTop: 26 }}>
            {L ? (L.first ? 'YOUR LEVEL' : 'NEW LEVEL') : `NEW LEVEL · ${up.label.toUpperCase()}`}
          </Mono>
          <T font="display" size={word.length > 8 ? 44 : 62} color={k.fg} style={{ lineHeight: 70, letterSpacing: 2.5, paddingTop: 6 }}
             adjustsFontSizeToFit numberOfLines={1}>{word}</T>
          <T size={14} color={k.fg2} style={{ lineHeight: 20, paddingTop: 6 }}>
            {L ? `${L.met} of your ${L.of} key numbers now sit at ${L.word}${L.position && L.position !== 'your position' ? `, weighed for ${L.position}` : ''}.`
              : `${up.label} crossed into ${up.level}.`}
          </T>

          <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', paddingTop: 22 }}>
            <Mono size={38} font="monoMedium" color={k.fg} style={{ lineHeight: 40 }}>
              {L ? `${L.met}/${L.of}` : ring ? formatValue(ring.value, ring) : ''}
            </Mono>
            <Mono size={11} color={k.fg2} style={{ paddingBottom: 4 }}>{L ? `MEASURES AT ${word}` : ''}</Mono>
          </View>

          <View style={{ gap: 8, paddingTop: 24 }}>
            <View style={{ flexDirection: 'row', gap: 4 }}>
              {SHORT.map((_, i) => (
                <View key={i} style={{ flex: 1, height: 8, borderWidth: 1, borderColor: k.fg, backgroundColor: i <= level ? k.fg : 'transparent' }} />
              ))}
            </View>
            <View style={{ flexDirection: 'row', gap: 4 }}>
              {SHORT.map((s, i) => (
                <Mono key={s} size={9.5} color={i === level ? k.fg : k.fg2} style={{ flex: 1, letterSpacing: 0.95 }}>{s}</Mono>
              ))}
            </View>
          </View>

          <View style={{ marginTop: 'auto', gap: 16, paddingTop: 24 }}>
            {(L?.next || ring?.next) && (
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 14,
                             borderTopWidth: 1, borderTopColor: k.line }}>
                <Mono size={10.5} color={k.fg2} style={{ letterSpacing: 1.47 }}>NEXT · {(L ? L.next : ring.next).toUpperCase()}</Mono>
                <Mono size={12} color={k.fg}>
                  {L ? `${L.need} more measure${L.need === 1 ? '' : 's'} to go` : `${shortUnits(ring.gap)} to go`}
                </Mono>
              </View>
            )}
            <Pressable onPress={onClose} accessibilityRole="button"
                       style={({ pressed }) => ({ height: 48, alignItems: 'center', justifyContent: 'center', backgroundColor: k.fg,
                                                  transform: [{ scale: pressed ? 0.97 : 1 }] })}>
              <T font="semi" size={14} color={k.bg} style={{ letterSpacing: 0.28 }}>Keep going</T>
            </Pressable>
          </View>
        </View>
      </BlurView>
    </Modal>
  )
}
