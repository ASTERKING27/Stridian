import { useRef, useState } from 'react'
import { Pressable, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import Animated, { cubicBezier } from 'react-native-reanimated'
import { BlurView } from 'expo-blur'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { Icon, T } from './index'

// The design's curves (TabBar board): tabs 440 ms, the ink pill's leading edge 320 ms
// fast-out, its trailing edge 500 ms slow-in, 40 ms behind.
const EASE = cubicBezier(0.5, 0, 0.2, 1)
const FAST = cubicBezier(0.2, 0.8, 0.2, 1)
const SLOW = cubicBezier(0.6, 0, 0.2, 1)

/* The glass tab bar: the chosen tab widens to show its name and the ink pill stretches
   to it — leading edge first, trailing edge catching up. `blurTarget` is the view behind
   it (Android blurs only what it is pointed at). */
export default function TabBar({ tabs, active, onChange, blurTarget, reduced }) {
  const { c, name } = useTheme()
  const inset = useSafeAreaInsets()
  const [barW, setBarW] = useState(0)
  const dir = useRef(1)
  const last = useRef(active)
  if (last.current !== active) { dir.current = active > last.current ? 1 : -1; last.current = active }

  const pw = barW - 2                      // inside the 1 px border
  const inner = pw - 8                     // 4 px either side
  const n = tabs.length
  const aw = Math.round(tabs[active].short.length * 7 + 46)
  const iw = (inner - aw) / (n - 1)
  let x = 4
  const layout = tabs.map((_, i) => { const w = i === active ? aw : iw; const o = { l: x, w }; x += w; return o })
  const act = layout[active]
  const lead = dir.current >= 0 ? 'right' : 'left'
  const t = ms => (reduced ? 0 : ms)

  return (
    <View
      onLayout={e => setBarW(e.nativeEvent.layout.width)}
      style={{ position: 'absolute', left: 10, right: 10, bottom: Math.max(18, inset.bottom - 8), height: 60,
               borderRadius: 30, boxShadow: `0 14px 34px ${c.shadow}` }}>
    <View accessibilityRole="tablist"
          style={{ flex: 1, borderRadius: 30, borderWidth: 1, borderColor: c.glassEdge, overflow: 'hidden' }}>
      <BlurView intensity={40} tint={name === 'dark' ? 'dark' : 'light'} blurTarget={blurTarget}
                blurMethod="dimezisBlurViewSdk31Plus"
                style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, backgroundColor: c.glass }} />
      <View pointerEvents="none" style={{ position: 'absolute', left: 30, right: 30, top: 0, height: 1, backgroundColor: c.hi }} />
      {barW > 0 && (
        <>
          <Animated.View
            style={{ position: 'absolute', top: 3, height: 52, borderRadius: 26, backgroundColor: c.ink,
                     left: act.l, right: pw - act.l - act.w,
                     transitionProperty: [lead, lead === 'right' ? 'left' : 'right'],
                     transitionDuration: [t(320), t(500)], transitionTimingFunction: [FAST, SLOW],
                     transitionDelay: [0, t(40)] }} />
          {tabs.map((tab, i) => {
            const on = i === active
            return (
              <Animated.View key={tab.key}
                style={{ position: 'absolute', top: 3, height: 52, left: layout[i].l, width: layout[i].w,
                         transitionProperty: ['left', 'width'], transitionDuration: t(440), transitionTimingFunction: EASE }}>
                <Pressable
                  accessibilityRole="tab" accessibilityLabel={tab.label} accessibilityState={{ selected: on }}
                  onPressIn={() => { if (!on) haptic.tick() }}
                  onPress={() => { if (!on) onChange(i) }}
                  style={{ flex: 1, flexDirection: 'row', alignItems: 'center', justifyContent: 'center' }}>
                  <View style={{ width: 20, height: 20 }}>
                    <Animated.View style={{ position: 'absolute', opacity: on ? 0 : 1, transitionProperty: 'opacity',
                                            transitionDuration: t(220), transitionDelay: on ? t(120) : 0 }}>
                      <Icon d={tab.icon} size={20} color={c.ink} />
                    </Animated.View>
                    <Animated.View style={{ position: 'absolute', opacity: on ? 1 : 0, transitionProperty: 'opacity',
                                            transitionDuration: t(220), transitionDelay: on ? t(120) : 0 }}>
                      <Icon d={tab.icon} size={20} color={c.bg} />
                    </Animated.View>
                  </View>
                  <Animated.View
                    style={{ overflow: 'hidden', maxWidth: on ? 110 : 0, marginLeft: on ? 7 : 0, opacity: on ? 1 : 0,
                             transitionProperty: ['maxWidth', 'marginLeft', 'opacity'],
                             transitionDuration: [t(440), t(440), on ? t(260) : t(120)],
                             transitionTimingFunction: [EASE, EASE, 'linear'],
                             transitionDelay: [0, 0, on ? t(160) : 0] }}>
                    <T font="semi" size={12.5} color={c.bg} numberOfLines={1}>{tab.short}</T>
                  </Animated.View>
                </Pressable>
              </Animated.View>
            )
          })}
        </>
      )}
    </View>
    </View>
  )
}
