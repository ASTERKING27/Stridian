import { useEffect, useState } from 'react'
import { View } from 'react-native'
import Svg, { G, Path } from 'react-native-svg'
import Animated, { Easing, useAnimatedProps, useAnimatedStyle, useSharedValue, withDelay, withTiming } from 'react-native-reanimated'
import { useTheme } from '../lib/theme'
import { play } from '../lib/haptics'
import { Mono, T, TILE_D } from './index'
import { BADGE_ICONS } from './icons'
import { cl, eOut, SweepMask } from './Sweep'
import Burst from './Burst'

const PERIMETER = 283.68           // the tile outline's length, for drawing part of it
const AnimatedPath = Animated.createAnimatedComponent(Path)
const FILL = { maxlag: 0, lines: [{ th: 0, off: 0, a: 0, b: 1, lag: 0 }] }   // a sweep with no lines: just the edge
const eBack = t => { 'worklet'; const c = 1.7; return 1 + (c + 1) * Math.pow(t - 1, 3) + c * Math.pow(t - 1, 2) }
const played = new Set()           // badges already earned on screen this session
let buzzed = 0

/* A badge (Badges board): earned is the ink tile with a paper glyph; locked is a hairline
   tile with a grey glyph, part-drawn in ink when there is progress (0–1) towards it.
   A badge that is new plays its earning once, the first time it is shown: the outline
   draws itself, ink sweeps in on the slant, the glyph flips to paper and pops, sparks
   fly, and the NEW tag lands. With reduced motion it is simply there, filled and NEW. */
export default function Badge({ badge, progress = 0, prog, size = 86, labels = true, live = true }) {
  const { c, reduced } = useTheme()
  const h = Math.round(size * 80 / 72)
  const k = size / 72
  const [earning] = useState(() => badge.earned && badge.new && !reduced && !played.has(badge.id))
  const u = useSharedValue(earning ? 0 : 1400)     // ms into the earning
  const sweep = useSharedValue(earning ? 0 : 1)

  // it plays once its page is on screen (tabs are built before they're shown)
  useEffect(() => {
    if (!earning || !live || played.has(badge.id)) return
    played.add(badge.id)
    const wait = 500                                  // let the tab's own sweep finish first
    if (Date.now() - buzzed > 400) { buzzed = Date.now(); setTimeout(() => play('badge'), wait) }     // several at once: one buzz
    u.value = withDelay(wait, withTiming(1400, { duration: 1400, easing: Easing.linear }))
    sweep.value = withDelay(wait + 300, withTiming(1, { duration: 450, easing: Easing.linear }))      // 300 → 750 ms
  }, [live])

  const outline = useAnimatedProps(() => ({ strokeDashoffset: (1 - eOut(cl(u.value / 420))) * PERIMETER }))
  const glyph = useAnimatedStyle(() => ({
    opacity: u.value >= 600 ? 1 : 0,
    transform: [{ scale: u.value < 600 ? 0.6 : 0.6 + 0.4 * eBack(cl((u.value - 600) / 320)) }],
  }))
  const tag = useAnimatedStyle(() => ({ opacity: cl((u.value - 750) / 120) }))

  const earned = badge.earned
  const icon = BADGE_ICONS[badge.icon] ?? BADGE_ICONS.target
  const glyphSvg = color => (
    <Svg width={size} height={h} viewBox="-1 -1 74 82">
      <G transform="translate(36 40) scale(1.35) translate(-12 -12)">
        <Path d={icon} fill="none" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" stroke={color} />
      </G>
    </Svg>
  )
  return (
    <View style={{ alignItems: 'center', gap: 10 }} accessible
          accessibilityLabel={`${badge.title}: ${badge.desc} ${earned ? 'Earned' : 'Locked'}${badge.new ? ', new' : ''}`}>
      <View style={{ width: size, height: h }}>
        {/* locked: the hairline tile, the grey glyph and any progress — and where an earning starts */}
        {(!earned || earning) && (
          <Svg width={size} height={h} viewBox="-1 -1 74 82" style={{ position: 'absolute' }}>
            <Path d={TILE_D} fill="none" stroke={c.line} strokeWidth={1.3} />
            {!earned && progress > 0 && (
              <Path d={TILE_D} fill="none" stroke={c.ink} strokeWidth={1.6} strokeLinejoin="miter"
                    strokeDasharray={[progress * PERIMETER, PERIMETER]} />
            )}
            {earning && <AnimatedPath animatedProps={outline} d={TILE_D} fill="none" stroke={c.ink} strokeWidth={1.6} strokeLinejoin="miter"
                                      strokeDasharray={[PERIMETER, PERIMETER]} />}
            <G transform="translate(36 40) scale(1.35) translate(-12 -12)">
              <Path d={icon} fill="none" strokeWidth={1.7} strokeLinecap="round" strokeLinejoin="round" stroke={c.ink2} />
            </G>
          </Svg>
        )}
        {/* earned: the ink tile (swept in), the paper glyph (popping) */}
        {earned && (
          <>
            <SweepMask p={sweep} w={size} h={h} side={earning ? 'behind' : null} set={FILL} style={{ position: 'absolute', width: size, height: h }}>
              <Svg width={size} height={h} viewBox="-1 -1 74 82">
                <Path d={TILE_D} fill={c.ink} stroke={c.ink} strokeWidth={1.3} />
              </Svg>
            </SweepMask>
            <Animated.View style={[{ position: 'absolute' }, earning && glyph]}>{glyphSvg(c.bg)}</Animated.View>
          </>
        )}
        {earning && <Burst t={u} at={700} x={43 * k} y={48 * k} n={10} dist={44 * k} step={8} base={8} pad={70} color={c.ink} />}
        {badge.new && (
          <Animated.View style={[{ position: 'absolute', right: -8, top: -8, paddingVertical: 3, paddingHorizontal: 6,
                                   backgroundColor: c.bg, borderWidth: 1, borderColor: c.ink }, earning && tag]}>
            <Mono size={9} style={{ letterSpacing: 1.08 }}>NEW</Mono>
          </Animated.View>
        )}
      </View>
      {labels && (
        <View style={{ gap: 4, alignItems: 'center' }}>
          <T font="semi" size={14} color={earned ? 'ink' : 'ink2'} style={{ textAlign: 'center' }}>{badge.title}</T>
          <T size={11.5} color="ink2" style={{ textAlign: 'center', lineHeight: 15.5 }}>{badge.desc}</T>
          {!!prog && <Mono size={10} style={{ letterSpacing: 1 }}>{prog}</Mono>}
        </View>
      )}
    </View>
  )
}
