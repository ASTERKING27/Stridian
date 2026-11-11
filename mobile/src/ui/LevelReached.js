import { useEffect, useState } from 'react'
import { Modal, Pressable, StyleSheet, View } from 'react-native'
import { BlurView } from 'expo-blur'
import Animated, { cancelAnimation, Easing, runOnJS, useAnimatedReaction, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated'
import { formatValue, shortUnits } from '../lib/api'
import { useTheme } from '../lib/theme'
import { haptic, play } from '../lib/haptics'
import { Logo, Mono, T } from './index'
import { CARD_LINES, cl, eIO, eOut, SweepLines, SweepMask } from './Sweep'
import Burst from './Burst'

const SHORT = ['UNI', 'ZONAL', 'STATE', 'NATIONAL', 'INTL']
// the card is the theme turned inside out (Achievement board)
const CARD = {
  white: { bg: '#121211', fg: '#F3F2EE', fg2: '#A8A7A1', line: 'rgba(243,242,238,0.2)', scrim: 'rgba(18,18,17,0.22)' },
  dark: { bg: '#EEEDE8', fg: '#0F0F0E', fg2: '#55544F', line: 'rgba(15,15,14,0.18)', scrim: 'rgba(0,0,0,0.45)' },
}
// the board's timeline, ms from the moment the card is called up
const T_IN = 180, SWEEP = 720, T_LOGO = 760, T_SPK = 820, T_LET = 900, T_CNT = 1400, T_LAD = 1750, T_REST = 2050, T_DONE = 2470, EXIT = 640
const eBack = t => { 'worklet'; const c = 1.7; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2) }

/* A level reached goes on record (Achievement board): the card sweeps in on the slant,
   the logo pops with a burst of sparks, the level's letters rise one by one, the count
   ticks up, the ladder fills to the new rung (more sparks), then the details settle in.
   "Keep going" sweeps it away. With reduced motion it fades in already complete.
   `party` is the dashboard's `celebrate`; `rings` its rings. */
export default function LevelReached({ party, rings, onClose }) {
  const { name, reduced } = useTheme()
  const k = CARD[name]
  const L = party.level
  const up = !L && party.levelUps[0]
  const ring = up && rings.find(r => r.key === up.key)
  const level = L ? L.level : ring?.level ?? 0
  const word = (L ? L.word : up.level).toUpperCase()
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()

  const [w, setW] = useState(0)
  const [h, setH] = useState(0)
  const [rowW, setRowW] = useState(0)          // the letters' natural width, to fit them
  const [ladderY, setLadderY] = useState(0)
  const [phase, setPhase] = useState('in')     // in → rest → out
  const [count, setCount] = useState(reduced || !L ? L?.met ?? 0 : 0)
  const t = useSharedValue(reduced ? T_DONE : 0)   // the card's clock, ms
  const sw = useSharedValue(0)                     // the sweep in, then the sweep out
  const back = useSharedValue(0)                   // the blurred backdrop
  const show = useSharedValue(reduced ? 0 : 1)     // reduced motion: the whole card fades

  useEffect(() => {
    back.value = withTiming(1, { duration: 320, easing: Easing.out(Easing.cubic) })
    if (reduced) {
      show.value = withTiming(1, { duration: 200 })
      haptic.success()
      return
    }
    play('level')
    t.value = withTiming(T_DONE, { duration: T_DONE, easing: Easing.linear })
    sw.value = withDelay(T_IN, withTiming(1, { duration: SWEEP, easing: Easing.linear }, done => { if (done) runOnJS(setPhase)('rest') }))
  }, [])

  // the count: 0 → how many measures sit at the level, a step at a time
  useAnimatedReaction(() => (L ? Math.round(L.met * eOut(cl((t.value - T_CNT) / 700))) : 0), (n, was) => {
    if (L && n !== was) runOnJS(setCount)(n)
  })

  function leave() {
    if (phase === 'out' || (!reduced && t.value < T_REST)) return
    if (reduced) {
      back.value = withTiming(0, { duration: 150 })
      show.value = withTiming(0, { duration: 150 }, () => runOnJS(onClose)())
      return
    }
    setPhase('out')
    cancelAnimation(t)
    t.value = T_DONE
    sw.value = 0
    sw.value = withTiming(1, { duration: EXIT, easing: Easing.linear }, done => { if (done) runOnJS(onClose)() })
    back.value = withDelay(260, withTiming(0, { duration: 380 }))
  }

  const backdrop = useAnimatedStyle(() => ({ opacity: back.value }))
  const card = useAnimatedStyle(() => ({ opacity: show.value }))
  const logo = useAnimatedStyle(() => ({
    opacity: cl((t.value - T_LOGO) / 120),
    transform: [{ scale: t.value < T_LOGO ? 0.6 : 0.6 + 0.4 * eBack(cl((t.value - T_LOGO) / 360)) }],
  }))
  const rest = useAnimatedStyle(() => ({ opacity: eOut(cl((t.value - T_REST) / 420)) }))
  const settle = useAnimatedStyle(() => {
    const u = eOut(cl((t.value - T_REST) / 420))
    return { opacity: u, transform: [{ translateY: 14 * (1 - u) }] }
  })
  const fill = useAnimatedStyle(() => ({ transform: [{ scaleX: eIO(cl((t.value - T_LAD) / 320)) }] }))

  const big = word.length > 8 ? 44 : 62
  const fit = rowW && w ? Math.min(1, (w - 52) / rowW) : 1
  const seg = (w - 52 - 16) / 5                   // one rung of the ladder

  return (
    <Modal transparent visible animationType="none" onRequestClose={leave} statusBarTranslucent>
      <Animated.View style={[StyleSheet.absoluteFill, backdrop]}>
        <BlurView intensity={20} tint={name === 'dark' ? 'dark' : 'light'} blurMethod="dimezisBlurViewSdk31Plus"
                  style={{ flex: 1, backgroundColor: k.scrim }} />
      </Animated.View>
      <View pointerEvents="box-none" style={{ flex: 1, justifyContent: 'center', paddingHorizontal: 22 }}>
        <Animated.View onLayout={e => setW(e.nativeEvent.layout.width)} style={[{ height: h || 500, overflow: 'hidden' }, card]}>
          <SweepMask p={sw} w={w} h={h || 500} side={reduced ? null : phase === 'in' ? 'behind' : phase === 'out' ? 'ahead' : null} set={CARD_LINES}
                     autoHeight style={{ flex: 1 }}>
            <View onLayout={e => setH(e.nativeEvent.layout.height)} accessibilityRole="alert" accessibilityLabel={`New level: ${word}`}
                  style={{ backgroundColor: k.bg, paddingTop: 26, paddingHorizontal: 26, paddingBottom: 24, minHeight: 500 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                <Animated.View style={logo}><Logo size={34} color={k.fg} /></Animated.View>
                <Mono size={10.5} color={k.fg2} style={{ letterSpacing: 1.26 }}>{today}</Mono>
              </View>
              <Mono size={10.5} color={k.fg2} style={{ letterSpacing: 1.47, paddingTop: 26 }}>
                {L ? (L.first ? 'YOUR LEVEL' : 'NEW LEVEL') : `NEW LEVEL · ${up.label.toUpperCase()}`}
              </Mono>
              {/* the level's letters, each rising into place */}
              <View style={{ height: 76, paddingTop: 6, overflow: 'hidden' }}>
                <View onLayout={e => setRowW(e.nativeEvent.layout.width)}
                      style={{ flexDirection: 'row', alignSelf: 'flex-start', transformOrigin: 'left top', transform: [{ scale: fit }] }}>
                  {[...word].map((ch, i) => <Letter key={i} ch={ch} i={i} t={t} size={big} color={k.fg} />)}
                </View>
              </View>
              <Animated.View style={rest}>
                <T size={14} color={k.fg2} style={{ lineHeight: 20, paddingTop: 6 }}>
                  {L ? `${L.met} of your ${L.of} key numbers now sit at ${L.word}${L.position && L.position !== 'your position' ? `, weighed for ${L.position}` : ''}.`
                    : `${up.label} crossed into ${up.level}.`}
                </T>
              </Animated.View>

              <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between', paddingTop: 22 }}>
                <Mono size={38} font="monoMedium" color={k.fg} style={{ lineHeight: 40 }}>
                  {L ? `${count}/${L.of}` : ring ? formatValue(ring.value, ring) : ''}
                </Mono>
                <Animated.View style={rest}>
                  <Mono size={11} color={k.fg2} style={{ paddingBottom: 4 }}>{L ? `MEASURES AT ${word}` : ''}</Mono>
                </Animated.View>
              </View>

              <View onLayout={e => setLadderY(e.nativeEvent.layout.y)} style={{ gap: 8, paddingTop: 24 }}>
                <View style={{ flexDirection: 'row', gap: 4 }}>
                  {SHORT.map((_, i) => (
                    <View key={i} style={{ flex: 1, height: 8, borderWidth: 1, borderColor: k.fg, overflow: 'hidden' }}>
                      {i < level && <View style={{ flex: 1, backgroundColor: k.fg }} />}
                      {i === level && <Animated.View style={[{ flex: 1, backgroundColor: k.fg, transformOrigin: 'left center' }, fill]} />}
                    </View>
                  ))}
                </View>
                <View style={{ flexDirection: 'row', gap: 4 }}>
                  {SHORT.map((s, i) => (
                    <Mono key={s} size={9.5} color={i === level ? k.fg : k.fg2} style={{ flex: 1, letterSpacing: 0.95 }}>{s}</Mono>
                  ))}
                </View>
              </View>

              <Animated.View style={[{ marginTop: 'auto', gap: 16, paddingTop: 24 }, settle]}>
                {(L?.next || ring?.next) && (
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingTop: 14,
                                 borderTopWidth: 1, borderTopColor: k.line }}>
                    <Mono size={10.5} color={k.fg2} style={{ letterSpacing: 1.47 }}>NEXT · {(L ? L.next : ring.next).toUpperCase()}</Mono>
                    <Mono size={12} color={k.fg}>
                      {L ? `${L.need} more measure${L.need === 1 ? '' : 's'} to go` : `${shortUnits(ring.gap)} to go`}
                    </Mono>
                  </View>
                )}
                <Pressable onPress={leave} accessibilityRole="button"
                           style={({ pressed }) => ({ height: 48, alignItems: 'center', justifyContent: 'center', backgroundColor: k.fg,
                                                      transform: [{ scale: pressed ? 0.97 : 1 }] })}>
                  <T font="semi" size={14} color={k.bg} style={{ letterSpacing: 0.28 }}>Keep going</T>
                </Pressable>
              </Animated.View>
            </View>
          </SweepMask>
          {phase !== 'rest' && !reduced && w > 0 && <SweepLines p={sw} w={w} h={h || 500} color={k.bg} set={CARD_LINES} />}
          {!reduced && w > 0 && (
            <>
              <Burst t={t} at={T_SPK} x={43} y={43} n={16} dist={46} wobble={0.18} step={10} base={9} color={k.fg} />
              <Burst t={t} at={T_LAD + 320} x={26 + level * (seg + 4) + seg / 2} y={ladderY + 28} n={12} dist={34} seed={0.3}
                     wobble={0.18} step={10} base={9} color={k.fg} />
            </>
          )}
        </Animated.View>
      </View>
    </Modal>
  )
}

// One letter of the level, rising 72 px into place, 55 ms after the one before.
function Letter({ ch, i, t, size, color }) {
  const style = useAnimatedStyle(() => {
    const u = cl((t.value - T_LET - i * 55) / 380)
    return { opacity: u > 0 ? 1 : 0, transform: [{ translateY: 72 * (1 - eOut(u)) }] }
  })
  return (
    <Animated.View style={style}>
      <T font="display" size={size} color={color} style={{ lineHeight: 70, letterSpacing: 2.5 }}>{ch === ' ' ? ' ' : ch}</T>
    </Animated.View>
  )
}
