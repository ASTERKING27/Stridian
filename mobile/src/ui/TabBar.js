import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import { Pressable, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import Animated, { Easing, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated'
import { BlurView } from 'expo-blur'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { useLaunchBar } from './Launch'
import { Icon, T } from './index'

// The design's curves (TabBar board): tabs 440 ms, the ink pill's leading edge 320 ms
// fast-out, its trailing edge 500 ms slow-in, 40 ms behind.
const EASE = Easing.bezier(0.5, 0, 0.2, 1)
const FAST = Easing.bezier(0.2, 0.8, 0.2, 1)
const SLOW = Easing.bezier(0.6, 0, 0.2, 1)
const CAP = 52                                   // the pill's height, so its round ends

// Where each tab sits for a given chosen one: the chosen widens to fit its name.
function place(barW, tabs, at) {
  const inner = barW - 2 - 8                     // inside the 1 px border, 4 px either side
  const aw = Math.round(tabs[at].short.length * 7 + 46)
  const iw = (inner - aw) / (tabs.length - 1)
  let x = 4
  return tabs.map((_, i) => { const w = i === at ? aw : iw; const o = { l: x, w }; x += w; return o })
}

/* The glass tab bar: the chosen tab widens to show its name and the ink pill stretches
   to it — leading edge first, trailing edge catching up. Everything that moves is a
   transform or an opacity, run on the UI thread from the moment of the tap, so a page
   being drawn at the same time can't make it stutter. `blurTarget` is the view behind it
   (Android blurs only what it is pointed at). */
export default function TabBar({ tabs, active, onChange, blurTarget, reduced }) {
  const { c, name } = useTheme()
  const inset = useSafeAreaInsets()
  const [barW, setBarW] = useState(0)
  const [shown, setShown] = useState(active)      // what the bar shows: changes on the tap itself
  const rise = useLaunchBar()                       // below the screen until the launch brings it up
  const n = tabs.length
  const L = useSharedValue(0), R = useSharedValue(0)          // the pill's edges
  const centre = useSharedValue(Array(n).fill(0))             // each tab's middle
  const open = useSharedValue(tabs.map((_, i) => (i === active ? 1 : 0)))   // how far each tab has widened
  const iconIn = useSharedValue(1), iconOut = useSharedValue(0)
  const labelIn = useSharedValue(1), labelOut = useSharedValue(0)
  const inAt = useSharedValue(active), outAt = useSharedValue(-1)
  const labelW = useSharedValue(tabs.map(t => t.short.length * 7))
  const last = useRef(active)
  const ready = useRef(false)

  // move everything to tab `to` (instantly before the bar has a width or with reduced motion)
  function moveTo(to) {
    if (!barW) return
    const from = last.current
    last.current = to
    const slots = place(barW, tabs, to)
    const edgeL = slots[to].l, edgeR = slots[to].l + slots[to].w
    const mids = slots.map(s => s.l + s.w / 2)
    const widths = tabs.map((_, i) => (i === to ? 1 : 0))
    if (reduced || !ready.current || to === from) {
      ready.current = true
      L.value = edgeL; R.value = edgeR; centre.value = mids; open.value = widths
      inAt.value = to; outAt.value = -1; iconIn.value = 1; labelIn.value = 1
      return
    }
    const right = to > from
    L.value = right ? withDelay(40, withTiming(edgeL, { duration: 500, easing: SLOW })) : withTiming(edgeL, { duration: 320, easing: FAST })
    R.value = right ? withTiming(edgeR, { duration: 320, easing: FAST }) : withDelay(40, withTiming(edgeR, { duration: 500, easing: SLOW }))
    centre.value = withTiming(mids, { duration: 440, easing: EASE })
    open.value = withTiming(widths, { duration: 440, easing: EASE })
    outAt.value = from; inAt.value = to
    iconOut.value = 1; iconOut.value = withTiming(0, { duration: 220 })
    iconIn.value = 0; iconIn.value = withDelay(120, withTiming(1, { duration: 220 }))
    labelOut.value = 1; labelOut.value = withTiming(0, { duration: 120, easing: Easing.linear })
    labelIn.value = 0; labelIn.value = withDelay(160, withTiming(1, { duration: 260, easing: Easing.linear }))
  }

  useLayoutEffect(() => { moveTo(last.current) }, [barW])                  // first layout: in place, before it's drawn
  useEffect(() => { if (active !== last.current) { setShown(active); moveTo(active) } }, [active])  // sent from a page

  const tap = i => {
    if (i === last.current) return
    setShown(i)
    moveTo(i)
    onChange(i)
  }

  const pillL = useAnimatedStyle(() => ({ transform: [{ translateX: L.value }] }))
  const pillR = useAnimatedStyle(() => ({ transform: [{ translateX: R.value - CAP }] }))
  const pillM = useAnimatedStyle(() => ({
    transform: [{ translateX: L.value + CAP / 2 }, { scaleX: Math.max(0, R.value - L.value - CAP) / 100 }],
  }))
  const slots = barW ? place(barW, tabs, shown) : []

  return (
    <Animated.View
      onLayout={e => setBarW(e.nativeEvent.layout.width)}
      style={[{ position: 'absolute', left: 10, right: 10, bottom: Math.max(18, inset.bottom - 8), height: 60,
                borderRadius: 30, boxShadow: `0 14px 34px ${c.shadow}` }, rise]}>
      <View accessibilityRole="tablist"
            style={{ flex: 1, borderRadius: 30, borderWidth: 1, borderColor: c.glassEdge, overflow: 'hidden' }}>
        <BlurView intensity={40} tint={name === 'dark' ? 'dark' : 'light'} blurTarget={blurTarget}
                  blurMethod="dimezisBlurViewSdk31Plus"
                  style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, backgroundColor: c.glass }} />
        <View pointerEvents="none" style={{ position: 'absolute', left: 30, right: 30, top: 0, height: 1, backgroundColor: c.hi }} />
        {barW > 0 && (
          <>
            {/* the ink pill: two round ends and the stretch between them */}
            <Animated.View pointerEvents="none" style={[{ position: 'absolute', top: 3, left: 0, width: CAP, height: CAP, borderRadius: CAP / 2, backgroundColor: c.ink }, pillL]} />
            <Animated.View pointerEvents="none" style={[{ position: 'absolute', top: 3, left: 0, width: CAP, height: CAP, borderRadius: CAP / 2, backgroundColor: c.ink }, pillR]} />
            <Animated.View pointerEvents="none" style={[{ position: 'absolute', top: 3, left: 0, width: 100, height: CAP, backgroundColor: c.ink, transformOrigin: 'left center' }, pillM]} />
            {tabs.map((tab, i) => (
              <Item key={tab.key} tab={tab} i={i} c={c} centre={centre} open={open} labelW={labelW}
                    iconIn={iconIn} iconOut={iconOut} labelIn={labelIn} labelOut={labelOut} inAt={inAt} outAt={outAt} />
            ))}
            {/* where to tap: the tabs as they are now (they move instantly; only the drawing animates) */}
            {tabs.map((tab, i) => (
              <Pressable key={tab.key} accessibilityRole="tab" accessibilityLabel={tab.label} accessibilityState={{ selected: i === shown }}
                         onPressIn={() => { if (i !== last.current) haptic.tick() }} onPress={() => tap(i)}
                         style={{ position: 'absolute', top: 3, height: CAP, left: slots[i].l, width: slots[i].w }} />
            ))}
          </>
        )}
      </View>
    </Animated.View>
  )
}

// One tab's icon and name, drawn where the tab is heading.
function Item({ tab, i, c, centre, open, labelW, iconIn, iconOut, labelIn, labelOut, inAt, outAt }) {
  const box = useAnimatedStyle(() => {
    const o = open.value[i] ?? 0
    const w = 20 + o * (7 + labelW.value[i])
    return { transform: [{ translateX: (centre.value[i] ?? 0) - w / 2 }] }
  })
  // the icon crossfades from ink to paper as the pill arrives under it
  const paper = useAnimatedStyle(() => ({ opacity: i === inAt.value ? iconIn.value : i === outAt.value ? iconOut.value : 0 }))
  const ink = useAnimatedStyle(() => ({ opacity: 1 - (i === inAt.value ? iconIn.value : i === outAt.value ? iconOut.value : 0) }))
  const label = useAnimatedStyle(() => ({ opacity: i === inAt.value ? labelIn.value : i === outAt.value ? labelOut.value : 0 }))
  return (
    <Animated.View pointerEvents="none" style={[{ position: 'absolute', top: 3, left: 0, height: CAP, flexDirection: 'row', alignItems: 'center' }, box]}>
      <View style={{ width: 20, height: 20 }}>
        <Animated.View style={ink}><Icon d={tab.icon} size={20} color={c.ink} /></Animated.View>
        <Animated.View style={[{ position: 'absolute', left: 0, top: 0 }, paper]}>
          <Icon d={tab.icon} size={20} color={c.bg} />
        </Animated.View>
      </View>
      <Animated.View style={[{ marginLeft: 7 }, label]}
                     onLayout={e => { const w = e.nativeEvent.layout.width; if (Math.abs(w - labelW.value[i]) > 0.5) { const next = [...labelW.value]; next[i] = w; labelW.value = next } }}>
        <T font="semi" size={12.5} color={c.bg} numberOfLines={1}>{tab.short}</T>
      </Animated.View>
    </Animated.View>
  )
}
