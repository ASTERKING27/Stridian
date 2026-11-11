import { useEffect, useRef, useState } from 'react'
import { Modal, Pressable, StyleSheet, View } from 'react-native'
import { BlurView } from 'expo-blur'
import Animated, { Easing, runOnJS, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated'
import { Inverted, useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { Btn, H1, I, Icon, Logo, T } from './index'
import { CARD_LINES, cl, eOut, SweepLines, SweepMask } from './Sweep'

/* The app's questions, in place of the phone's alert: the level card's look — the theme
   turned inside out over the blurred page — sweeping in on the slant, its logo popping and
   its buttons settling as the lines pass, and sweeping away the way it reads. Called like
   Alert.alert, from anywhere: dialog(title, message, [{ text, style, onPress }]).
   The first button that isn't 'cancel' leads (filled), any others are outlined, the cancel
   is the quiet one at the bottom; no buttons is a single OK. Tapping outside or Back is the
   cancel (or the OK). A 'destructive' question is marked and warns with a buzz. A button's
   onPress runs the moment it's tapped, as the card leaves; one that asks again queues. */
let push = () => {}
export const dialog = (title, message, buttons) => push({ title, message, buttons })

export default function DialogHost() {
  const [queue, setQueue] = useState([])
  useEffect(() => { push = d => setQueue(q => [...q, { ...d, id: Math.random() }]) }, [])
  const now = queue[0]
  return now ? <Card key={now.id} d={now} onGone={() => setQueue(q => q.slice(1))} /> : null
}

const IN = 560, OUT = 440
const eBack = t => { 'worklet'; const c = 1.7; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2) }

function Card({ d, onGone }) {
  const { name, c, reduced } = useTheme()
  const buttons = d.buttons?.length ? d.buttons : [{ text: 'OK' }]
  const cancel = buttons.find(b => b.style === 'cancel')
  const rest = buttons.filter(b => b !== cancel)
  const danger = rest.some(b => b.style === 'destructive')
  const dismiss = cancel ?? (buttons.length === 1 ? buttons[0] : null)    // what a tap outside or Back means
  const [w, setW] = useState(0)
  const [h, setH] = useState(0)
  const ready = w > 0 && h > 0
  const side = useSharedValue(reduced ? null : 'behind')     // coming in: shown behind the line; going: ahead of it
  const sw = useSharedValue(0)
  const back = useSharedValue(0)
  const show = useSharedValue(reduced ? 0 : 1)              // reduced motion: the card fades instead
  const gone = useRef(false)

  // in once it's measured, so the sweep plays from its first frame
  useEffect(() => {
    if (!ready) return
    back.value = withTiming(1, { duration: 280, easing: Easing.out(Easing.cubic) })
    if (danger) haptic.warning(); else haptic.sweep()
    if (reduced) show.value = withTiming(1, { duration: 150 })
    else sw.value = withTiming(1, { duration: IN, easing: Easing.linear })
  }, [ready]) // eslint-disable-line react-hooks/exhaustive-deps

  function leave(b) {
    if (gone.current) return
    gone.current = true
    const done = () => { 'worklet'; runOnJS(onGone)() }
    back.value = withDelay(reduced ? 0 : 140, withTiming(0, { duration: reduced ? 150 : 300 }))
    if (reduced || !ready) show.value = withTiming(0, { duration: 150 }, done)
    else if (sw.value < 1) sw.value = withTiming(0, { duration: Math.max(140, OUT * sw.value), easing: Easing.linear }, done)  // still coming in: back the way it came
    else { side.value = 'ahead'; sw.value = 0; sw.value = withTiming(1, { duration: OUT, easing: Easing.linear }, done) }
    b?.onPress?.()
  }
  const outside = () => (dismiss ? leave(dismiss) : haptic.nope())

  const backdrop = useAnimatedStyle(() => ({ opacity: back.value }))
  const card = useAnimatedStyle(() => ({ opacity: show.value }))
  // the logo pops and the buttons settle as the lines pass over them (only on the way in;
  // sw and side are read right here, so the style follows them)
  const logo = useAnimatedStyle(() => {
    const u = side.value === 'behind' ? cl((sw.value - 0.25) / 0.47) : 1
    return { opacity: cl(u * 3), transform: [{ scale: 0.6 + 0.4 * eBack(u) }] }
  })
  const settle = useAnimatedStyle(() => {
    const u = side.value === 'behind' ? eOut(cl((sw.value - 0.45) / 0.55)) : 1
    return { opacity: u, transform: [{ translateY: 12 * (1 - u) }] }
  })

  return (
    <Modal transparent visible animationType="none" onRequestClose={outside} statusBarTranslucent>
      <Animated.View style={[StyleSheet.absoluteFill, backdrop]}>
        <Pressable onPress={outside} accessible={false} style={{ flex: 1 }}>
          <BlurView intensity={20} tint={name === 'dark' ? 'dark' : 'light'} blurMethod="dimezisBlurViewSdk31Plus"
                    style={{ flex: 1, backgroundColor: name === 'dark' ? 'rgba(0,0,0,0.45)' : 'rgba(18,18,17,0.22)' }} />
        </Pressable>
      </Animated.View>
      <View pointerEvents="box-none" style={{ flex: 1, justifyContent: 'center', paddingHorizontal: 22 }}>
        <Animated.View onLayout={e => setW(e.nativeEvent.layout.width)}
                       style={[{ width: '100%', maxWidth: 420, alignSelf: 'center', height: h || 1, overflow: 'hidden' }, card]}>
          <SweepMask p={sw} w={ready ? w : 0} h={h} side={side} set={CARD_LINES} autoHeight style={{ flex: 1 }}>
            <Inverted>
              <View onLayout={e => setH(e.nativeEvent.layout.height)} accessibilityViewIsModal
                    style={{ backgroundColor: c.ink, padding: 24, paddingBottom: cancel ? 12 : 24 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                  <Animated.View style={logo}><Logo size={26} /></Animated.View>
                  {danger && <Icon d={I.warning} size={20} sw={1.8} />}
                </View>
                <H1 size={23} style={{ paddingTop: 22 }}>{d.title}</H1>
                {!!d.message && <T size={14} color="ink2" style={{ lineHeight: 20, paddingTop: 8 }}>{d.message}</T>}
                <Animated.View style={[{ gap: 10, paddingTop: 24 }, settle]}>
                  {rest.map((b, i) => (
                    <Btn key={b.text} small kind={i === 0 ? 'primary' : 'secondary'} label={b.text} haptics onPress={() => leave(b)} />
                  ))}
                  {cancel && <Btn kind="text" label={cancel.text} onPress={() => { haptic.tick(); leave(cancel) }} />}
                </Animated.View>
              </View>
            </Inverted>
          </SweepMask>
          {ready && !reduced && <SweepLines p={sw} w={w} h={h} color={c.ink} set={CARD_LINES} />}
        </Animated.View>
      </View>
    </Modal>
  )
}
