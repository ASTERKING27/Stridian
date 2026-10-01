import { useEffect, useRef, useState } from 'react'
import { Pressable, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import Animated, { Easing, useAnimatedStyle, useSharedValue, withTiming } from 'react-native-reanimated'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { I, Icon, Mono, T } from './index'

/* The confirmation toast (Feedback board): ink, from the top, 3 s, with Undo when the
   thing can be taken back. Call toast({ title, sub, undo, icon }) from anywhere. */
let push = () => {}
export const toast = t => push(t)

export default function ToastHost() {
  const { c, reduced } = useTheme()
  const inset = useSafeAreaInsets()
  const [queue, setQueue] = useState([])
  const y = useSharedValue(-160)
  const left = useSharedValue(1)
  const timer = useRef(null)
  const now = queue[0]

  useEffect(() => { push = t => setQueue(q => [...q, { ms: 3000, ...t, id: Math.random() }]) }, [])

  useEffect(() => {
    if (!now) return undefined
    y.value = reduced ? 0 : -160
    y.value = withTiming(0, { duration: reduced ? 0 : 320, easing: Easing.out(Easing.cubic) })
    left.value = 1
    left.value = withTiming(0, { duration: now.ms, easing: Easing.linear })
    timer.current = setTimeout(close, now.ms)
    return () => clearTimeout(timer.current)
  }, [now?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  function close() {
    clearTimeout(timer.current)
    const done = () => setQueue(q => q.slice(1))
    if (reduced) return done()
    y.value = withTiming(-160, { duration: 280, easing: Easing.in(Easing.cubic) })
    setTimeout(done, 290)
  }

  const slide = useAnimatedStyle(() => ({ transform: [{ translateY: y.value }] }))
  const line = useAnimatedStyle(() => ({ width: `${left.value * 100}%` }))
  if (!now) return null
  return (
    <Animated.View accessibilityRole="alert" accessibilityLiveRegion="polite"
                   style={[{ position: 'absolute', left: 12, right: 12, top: inset.top + 8, zIndex: 50,
                             backgroundColor: c.ink, paddingVertical: 14, paddingHorizontal: 16, overflow: 'hidden',
                             flexDirection: 'row', alignItems: 'center', gap: 12 }, slide]}>
      <Icon d={now.icon ?? I.check} size={18} sw={2} color={c.bg} />
      <Pressable onPress={close} style={{ flex: 1, gap: 3 }}>
        <T font="semi" size={14.5} color={c.bg}>{now.title}</T>
        {!!now.sub && <Mono size={10} color={c.bg} style={{ letterSpacing: 0.6, opacity: 0.75 }}>{now.sub}</Mono>}
      </Pressable>
      {!!now.undo && (
        <Pressable hitSlop={10} onPress={() => { haptic.tap(); now.undo(); close() }} accessibilityRole="button">
          <Mono size={10.5} color={c.bg} style={{ letterSpacing: 1.26, textDecorationLine: 'underline' }}>UNDO</Mono>
        </Pressable>
      )}
      <View style={{ position: 'absolute', left: 0, bottom: 0, right: 0, height: 2 }}>
        <Animated.View style={[{ height: 2, backgroundColor: c.bg }, line]} />
      </View>
    </Animated.View>
  )
}
