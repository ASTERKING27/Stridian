import { View } from 'react-native'
import Svg, { G, Path } from 'react-native-svg'
import { useTheme } from '../lib/theme'
import { Mono, T, TILE_D } from './index'
import { BADGE_ICONS } from './icons'

const PERIMETER = 283.68           // the tile outline's length, for drawing part of it

/* A badge (Badges board): earned is the ink tile with a paper glyph; locked is a hairline
   tile with a grey glyph, part-drawn in ink when there is progress (0–1) towards it.
   ponytail: static looks — the earning animation comes with the motion build. */
export default function Badge({ badge, progress = 0, prog, size = 86, labels = true }) {
  const { c } = useTheme()
  const h = Math.round(size * 80 / 72)
  const earned = badge.earned
  return (
    <View style={{ alignItems: 'center', gap: 10 }} accessible
          accessibilityLabel={`${badge.title}: ${badge.desc} ${earned ? 'Earned' : 'Locked'}${badge.new ? ', new' : ''}`}>
      <View style={{ width: size, height: h }}>
        <Svg width={size} height={h} viewBox="-1 -1 74 82">
          <Path d={TILE_D} fill={earned ? c.ink : 'none'} stroke={earned ? c.ink : c.line} strokeWidth={1.3} />
          {!earned && progress > 0 && (
            <Path d={TILE_D} fill="none" stroke={c.ink} strokeWidth={1.6} strokeLinejoin="miter"
                  strokeDasharray={[progress * PERIMETER, PERIMETER]} />
          )}
          <G transform="translate(36 40) scale(1.35) translate(-12 -12)">
            <Path d={BADGE_ICONS[badge.icon] ?? BADGE_ICONS.target} fill="none" strokeWidth={1.7} strokeLinecap="round"
                  strokeLinejoin="round" stroke={earned ? c.bg : c.ink2} />
          </G>
        </Svg>
        {badge.new && (
          <View style={{ position: 'absolute', right: -8, top: -8, paddingVertical: 3, paddingHorizontal: 6,
                         backgroundColor: c.bg, borderWidth: 1, borderColor: c.ink }}>
            <Mono size={9} style={{ letterSpacing: 1.08 }}>NEW</Mono>
          </View>
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
