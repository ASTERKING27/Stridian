import { Pressable, View } from 'react-native'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { Icon, T } from './index'
import { SPORT_ICONS } from './icons'

// The sport chips (Icons board, "in use · sport picker").
export function SportPicker({ sports, value, onChange, disabled }) {
  const { c } = useTheme()
  return (
    <View accessibilityRole="radiogroup" style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
      {sports.map(s => {
        const on = s.name === value
        return (
          <Pressable key={s.slug} accessibilityRole="radio" accessibilityState={{ checked: on, disabled }}
                     onPress={() => { if (disabled) return; if (!on) { haptic.tick(); onChange(s.name) } }}
                     style={{ height: 40, paddingLeft: 11, paddingRight: 14, flexDirection: 'row', alignItems: 'center', gap: 8,
                              borderWidth: 1, borderColor: c.ink, backgroundColor: on ? c.ink : 'transparent' }}>
            <Icon d={SPORT_ICONS[s.name] ?? SPORT_ICONS.Football} size={18} color={on ? c.bg : c.ink} />
            <T font="medium" size={13} color={on ? c.bg : c.ink}>{s.name}</T>
          </Pressable>
        )
      })}
    </View>
  )
}

// Several at once (allergies): each chip toggles, ink when on.
export function Toggles({ options, value, onChange }) {
  const { c } = useTheme()
  return (
    <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 8 }}>
      {options.map(([k, label]) => {
        const on = value.includes(k)
        return (
          <Pressable key={k} accessibilityRole="checkbox" accessibilityState={{ checked: on }}
                     onPress={() => { haptic.tick(); onChange(on ? value.filter(x => x !== k) : [...value, k]) }}
                     style={{ height: 40, paddingHorizontal: 14, justifyContent: 'center', borderWidth: 1, borderColor: c.ink,
                              backgroundColor: on ? c.ink : 'transparent' }}>
            <T font="medium" size={13} color={on ? c.bg : c.ink}>{label}</T>
          </Pressable>
        )
      })}
    </View>
  )
}
