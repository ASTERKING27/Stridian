import { useEffect, useState } from 'react'
import { Image, KeyboardAvoidingView, Platform, Pressable, RefreshControl, ScrollView, Text, TextInput, View } from 'react-native'
import { useSafeAreaInsets } from 'react-native-safe-area-context'
import Svg, { Defs, Line, Path, Pattern, Rect } from 'react-native-svg'
import Animated, { cubicBezier, Easing, useAnimatedProps, useSharedValue, withRepeat, withTiming } from 'react-native-reanimated'
import { F, useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { initials } from '../lib/api'
import { I, LOGO_D, LOGO_LEN } from './icons'

export { I }

/* ------------------------------------------------------------------ type */

export function T({ font = 'body', size = 15, color = 'ink', style, ...rest }) {
  const { c } = useTheme()
  return <Text {...rest} style={[{ fontFamily: F[font], fontSize: size, color: c[color] ?? color }, style]} />
}

// IBM Plex Mono caps, .14em tracking — the design's labels
export function Eyebrow({ children, color = 'ink2', size = 10.5, style }) {
  return <T font="mono" size={size} color={color} style={[{ letterSpacing: size * 0.14 }, style]}>{children}</T>
}

export function H1({ children, size = 30, style }) {
  return (
    <T font="title" size={size} accessibilityRole="header"
       style={[{ lineHeight: Math.round(size * 1.08), letterSpacing: -size * 0.015 }, style]}>{children}</T>
  )
}

export const Mono = ({ size = 13, ...rest }) => <T font="mono" size={size} {...rest} />

export function Wordmark({ size = 12, color = 'ink', style }) {
  return <T font="wide" size={size} color={color} style={[{ letterSpacing: size * 0.2 }, style]}>STRIDIAN</T>
}

/* --------------------------------------------------------- icons & marks */

export function Icon({ d, size = 20, sw = 1.6, color }) {
  const { c } = useTheme()
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d={d} stroke={color ?? c.ink} strokeWidth={sw} strokeLinecap="butt" strokeLinejoin="miter" />
    </Svg>
  )
}

export function Logo({ size = 22, color }) {
  const { c } = useTheme()
  return <Svg width={size} height={size} viewBox="0 0 100 100"><Path d={LOGO_D} fill={color ?? c.ink} /></Svg>
}

const APath = Animated.createAnimatedComponent(Path)

// The loading mark: a quarter of the logo's outline running laps around it.
export function Lap({ size = 18, color }) {
  const { c, reduced: still } = useTheme()
  const run = useSharedValue(0)
  useEffect(() => {
    if (!still) run.value = withRepeat(withTiming(1, { duration: 1000, easing: Easing.linear }), -1)
  }, [still, run])
  const props = useAnimatedProps(() => ({ strokeDashoffset: -run.value * LOGO_LEN }))
  return (
    <Svg width={size} height={size} viewBox="-4 -4 108 108">
      <APath d={LOGO_D} fill="none" stroke={color ?? c.ink} strokeWidth={8} strokeLinejoin="miter" strokeMiterlimit={12}
             strokeDasharray={[LOGO_LEN * 0.26, LOGO_LEN * 0.74]} animatedProps={props} />
    </Svg>
  )
}

// diagonal hatching: how the design says "disabled" without relying on a faded colour
function Hatch({ color }) {
  return (
    <Svg style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0 }} width="100%" height="100%">
      <Defs>
        <Pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
          <Line x1="0" y1="0" x2="0" y2="6" stroke={color} strokeWidth="1" />
        </Pattern>
      </Defs>
      <Rect width="100%" height="100%" fill="url(#hatch)" />
    </Svg>
  )
}

/* ---------------------------------------------------------------- buttons */

/* kind: primary (ink), secondary (outlined), text, icon. Pressed shrinks 3% with an inner
   paper ring; disabled is hatched with a dashed edge; busy swaps the icon for the lap
   loader and says what is happening, keeping its size. */
export function Btn({ kind = 'primary', label, onPress, disabled, busy, busyLabel, icon, iconRight, small,
                      style, haptics = kind === 'primary' || kind === 'icon', accessibilityLabel }) {
  const { c } = useTheme()
  const h = kind === 'text' ? 44 : small ? 46 : 52
  const off = disabled && !busy
  return (
    <Pressable
      accessibilityRole="button" accessibilityLabel={accessibilityLabel ?? label}
      accessibilityState={{ disabled: !!off, busy: !!busy }}
      onPressIn={() => { if (!off && !busy && haptics) haptic.tap() }}
      onPress={() => { if (off) haptic.nope(); else if (!busy) onPress?.() }}
      style={({ pressed }) => {
        const on = pressed && !off && !busy
        const base = { height: h, flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 10,
                       overflow: 'hidden', transform: [{ scale: on && kind !== 'text' ? (kind === 'icon' ? 0.94 : 0.97) : 1 }] }
        if (kind === 'primary') return [base, { backgroundColor: off ? 'transparent' : c.ink },
          off && { borderWidth: 1, borderStyle: 'dashed', borderColor: c.ink2 }, style]
        if (kind === 'secondary' || kind === 'icon') return [base, kind === 'icon' && { width: h },
          { borderWidth: 1, borderColor: off ? c.ink2 : c.ink, borderStyle: off ? 'dashed' : 'solid',
            backgroundColor: on ? c.ink : 'transparent' }, style]
        return [base, { paddingHorizontal: 10, alignSelf: 'center', backgroundColor: on ? c.soft : 'transparent' }, style]
      }}>
      {({ pressed }) => {
        const on = pressed && !off && !busy
        const fg = off ? c.ink2 : kind === 'primary' ? c.bg : on && kind !== 'text' ? c.bg : kind === 'text' ? c.ink2 : c.ink
        return (
          <>
            {kind === 'primary' && off && <Hatch color={c.line} />}
            {kind === 'primary' && on && (
              <View pointerEvents="none" style={{ position: 'absolute', left: 2, top: 2, right: 2, bottom: 2, borderWidth: 2, borderColor: c.bg }} />
            )}
            {busy ? <Lap color={fg} /> : icon ? <Icon d={icon} size={kind === 'icon' ? 20 : 18} sw={1.8} color={fg} /> : null}
            {kind !== 'icon' && (
              <T font={kind === 'text' ? 'medium' : 'semi'} size={kind === 'text' ? 14 : small ? 14 : 15} color={fg}
                 style={on && kind === 'text' ? { textDecorationLine: 'underline' } : null}>
                {busy ? (busyLabel ?? label) : label}
              </T>
            )}
            {iconRight && !busy && <Icon d={iconRight} size={18} sw={1.8} color={fg} />}
          </>
        )
      }}
    </Pressable>
  )
}

export function Back({ label = 'Back', onPress, icon = I.back }) {
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} hitSlop={8}
               style={{ height: 44, flexDirection: 'row', alignItems: 'center', gap: 8, alignSelf: 'flex-start' }}>
      <Icon d={icon} size={20} />
      <T font="medium" size={14}>{label}</T>
    </Pressable>
  )
}

/* ----------------------------------------------------------------- fields */

// An underlined field: label above, 2 px line while focused, a dashed one with a problem.
export function Field({ label, error, hint, right, style, inputStyle, ...input }) {
  const { c } = useTheme()
  const [focus, setFocus] = useState(false)
  const msg = typeof error === 'string' ? error : ''
  return (
    <View style={[{ gap: 8 }, style]}>
      {(label || right) && (
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Eyebrow>{label}</Eyebrow>
          {right}
        </View>
      )}
      <TextInput
        placeholderTextColor={c.ink2} selectionColor={c.ink} cursorColor={c.ink}
        {...input}
        onFocus={e => { setFocus(true); input.onFocus?.(e) }}
        onBlur={e => { setFocus(false); input.onBlur?.(e) }}
        style={[{ fontFamily: F.regular, fontSize: 16, color: input.editable === false ? c.ink2 : c.ink,
                  paddingVertical: 6, paddingHorizontal: 0,
                  borderBottomWidth: error ? 0 : focus ? 2 : 1, borderBottomColor: c.ink,
                  marginBottom: error || focus ? 0 : 1 }, inputStyle]}
      />
      {!!error && (
        <Svg height={2} width="100%" style={{ marginTop: -8 }}>
          <Line x1="0" y1="1" x2="100%" y2="1" stroke={c.ink} strokeWidth={2} strokeDasharray={[5, 4]} />
        </Svg>
      )}
      {/* error={true} draws the dashed line only: the screen says what's wrong itself */}
      {!!(msg || hint) && (
        <View style={{ flexDirection: 'row', gap: 6 }}>
          {!!msg && <Icon d={I.warning} size={14} sw={1.8} />}
          <T size={12.5} color={msg ? 'ink' : 'ink2'} style={{ flex: 1, lineHeight: 17 }}>{msg || hint}</T>
        </View>
      )}
    </View>
  )
}

// A row of choices (segments, chips, pickers): ink fill when chosen, a tick on select.
export function Choice({ options, value, onChange, disabled, wrap = true }) {
  const { c } = useTheme()
  return (
    <View accessibilityRole="radiogroup" style={{ flexDirection: 'row', flexWrap: wrap ? 'wrap' : 'nowrap', gap: 8 }}>
      {options.map(([k, label]) => {
        const on = k === value
        return (
          <Pressable key={k} accessibilityRole="radio" accessibilityState={{ checked: on, disabled }}
                     onPress={() => { if (disabled) return haptic.nope(); if (!on) { haptic.tick(); onChange(k) } }}
                     style={{ height: 40, paddingHorizontal: 14, justifyContent: 'center', borderWidth: 1,
                              borderColor: disabled ? c.ink2 : c.ink, borderStyle: disabled ? 'dashed' : 'solid',
                              backgroundColor: on ? (disabled ? c.ink2 : c.ink) : 'transparent' }}>
            <T font="medium" size={13} color={on ? c.bg : disabled ? 'ink2' : 'ink'}>{label}</T>
          </Pressable>
        )
      })}
    </View>
  )
}

/* ---------------------------------------------------------------- layout */

// A plain page: safe area, the design's 22 px sides, scrolls, keeps clear of the keyboard.
// `onRefresh` adds pull to refresh in the theme's colours.
export function Screen({ children, bottom = 34, gap = 20, refreshControl, refreshing = false, onRefresh, scrollRef, fill }) {
  const { c } = useTheme()
  const inset = useSafeAreaInsets()
  const pull = refreshControl ?? (onRefresh && (
    <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={c.ink} colors={[c.ink]} progressBackgroundColor={c.bg} />
  ))
  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: c.bg }} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView ref={scrollRef} keyboardShouldPersistTaps="handled" refreshControl={pull || undefined}
                  contentContainerStyle={{ flexGrow: fill ? 1 : undefined, paddingTop: inset.top + 12,
                                           paddingBottom: inset.bottom + bottom, paddingHorizontal: 22, gap }}>
        {children}
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

// Label on the left, value on the right, a hairline above — the design's list row.
export function Row({ a, b, sub, onPress, bold, last }) {
  const { c } = useTheme()
  const Wrap = onPress ? Pressable : View
  return (
    <Wrap onPress={onPress} accessibilityRole={onPress ? 'button' : undefined}
          style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 12,
                   paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.line,
                   borderBottomWidth: last ? 1 : 0, borderBottomColor: c.line }}>
      <View style={{ flex: 1, gap: 3 }}>
        <T font={bold ? 'semi' : 'body'} size={15}>{a}</T>
        {!!sub && <Mono size={11} color="ink2">{sub}</Mono>}
      </View>
      {typeof b === 'string' || typeof b === 'number' ? <Mono size={15}>{b}</Mono> : b}
    </Wrap>
  )
}

// A message block: what went wrong (or right), in words, with an icon — never colour alone.
export function Note({ children, tone = 'bad', style }) {
  const { c } = useTheme()
  if (!children) return null
  return (
    <View accessibilityLiveRegion="polite"
          style={[{ flexDirection: 'row', gap: 10, padding: 12, borderWidth: 1, borderColor: c.ink,
                    borderStyle: tone === 'bad' ? 'dashed' : 'solid' }, style]}>
      <Icon d={tone === 'bad' ? I.warning : tone === 'ok' ? I.check : I.info} size={16} sw={1.8} />
      <T size={13.5} style={{ flex: 1, lineHeight: 19 }}>{children}</T>
    </View>
  )
}

// The top of every tab: the mark and wordmark, and whose space this is.
export function Top({ context, onContext }) {
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', minHeight: 24 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 9 }}>
        <Logo size={22} />
        <Wordmark size={12} />
      </View>
      <Pressable disabled={!onContext} onPress={onContext} hitSlop={10} accessibilityRole={onContext ? 'button' : undefined}
                 style={{ flexDirection: 'row', alignItems: 'center', gap: 4 }}>
        <Mono size={10.5} color="ink2" style={{ letterSpacing: 1.05 }}>{context}</Mono>
        {!!onContext && <Icon d="M7 10l5 5 5-5" size={14} />}
      </Pressable>
    </View>
  )
}

export function Title({ eyebrow, children, size }) {
  return (
    <View style={{ gap: 8 }}>
      {!!eyebrow && <Eyebrow>{eyebrow}</Eyebrow>}
      <H1 size={size}>{children}</H1>
    </View>
  )
}

// The ink bar across the top when there is no connection (States · errors, 06).
export function OfflineBar({ note = 'SHOWING WHAT WAS LOADED', onRetry }) {
  const { c } = useTheme()
  const inset = useSafeAreaInsets()
  return (
    <View accessibilityRole="alert"
          style={{ position: 'absolute', left: 0, right: 0, top: 0, zIndex: 2, paddingTop: inset.top + 8, paddingBottom: 12,
                   paddingHorizontal: 22, backgroundColor: c.ink, flexDirection: 'row', alignItems: 'center', gap: 12 }}>
      <Icon d={I.offline} size={20} color={c.bg} />
      <View style={{ flex: 1, gap: 3 }}>
        <T font="semi" size={14} color={c.bg}>You’re offline</T>
        <Mono size={10} color={c.bg} style={{ letterSpacing: 0.6, opacity: 0.75 }}>{note}</Mono>
      </View>
      {!!onRetry && (
        <Pressable onPress={onRetry} accessibilityRole="button" style={{ paddingVertical: 8, paddingHorizontal: 10, borderWidth: 1, borderColor: c.bg }}>
          <Mono size={10.5} color={c.bg} style={{ letterSpacing: 1.05 }}>RETRY</Mono>
        </Pressable>
      )}
    </View>
  )
}

// A still placeholder block for loading screens (the shimmer comes with the motion build).
export function Placeholder({ h = 16, w = '100%', style }) {
  const { c } = useTheme()
  return <View style={[{ height: h, width: w, backgroundColor: c.soft }, style]} />
}

// "OR" / "NEW HERE" divider
export function Divider({ label }) {
  const { c } = useTheme()
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
      <View style={{ flex: 1, height: 1, backgroundColor: c.line }} />
      {!!label && <Eyebrow size={10}>{label}</Eyebrow>}
      <View style={{ flex: 1, height: 1, backgroundColor: c.line }} />
    </View>
  )
}

/* ------------------------------------------------------- more pieces (M2) */

// The design's square switch: ink when on, the knob slides.
export function Switch({ value, onChange, label }) {
  const { c } = useTheme()
  return (
    <Pressable accessibilityRole="switch" accessibilityLabel={label} accessibilityState={{ checked: value }}
               onPress={() => { haptic.toggle(!value); onChange(!value) }} hitSlop={8}
               style={{ width: 48, height: 28, borderWidth: 1.5, borderColor: c.ink, backgroundColor: value ? c.ink : 'transparent' }}>
      <Animated.View style={{ position: 'absolute', top: 3, left: value ? 23 : 3, width: 18, height: 18,
                              backgroundColor: value ? c.bg : c.ink, transitionProperty: 'left', transitionDuration: 220,
                              transitionTimingFunction: cubicBezier(0.5, 0, 0.2, 1) }} />
    </Pressable>
  )
}

// A full-width segmented control in mono caps (Settings › Appearance, Results › radar/bars).
export function Seg({ options, value, onChange }) {
  const { c } = useTheme()
  return (
    <View accessibilityRole="radiogroup" style={{ flexDirection: 'row', borderWidth: 1, borderColor: c.ink }}>
      {options.map(([k, label]) => {
        const on = k === value
        return (
          <Pressable key={k} accessibilityRole="radio" accessibilityState={{ checked: on }}
                     onPress={() => { if (!on) { haptic.tick(); onChange(k) } }}
                     style={{ flex: 1, height: 38, alignItems: 'center', justifyContent: 'center', backgroundColor: on ? c.ink : 'transparent' }}>
            <Mono size={11} color={on ? c.bg : c.ink} style={{ letterSpacing: 0.88 }}>{label}</Mono>
          </Pressable>
        )
      })}
    </View>
  )
}

// A row that opens something: label (and a line under it), a chevron.
export function LinkRow({ label, sub, icon, right, onPress, last }) {
  const { c } = useTheme()
  return (
    <Pressable onPress={onPress} accessibilityRole="button"
               style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 13,
                                          borderTopWidth: 1, borderTopColor: c.line, borderBottomWidth: last ? 1 : 0,
                                          borderBottomColor: c.line, backgroundColor: pressed ? c.soft : 'transparent' })}>
      {!!icon && <Icon d={icon} size={20} />}
      <View style={{ flex: 1, gap: 3 }}>
        <T size={15}>{label}</T>
        {!!sub && <T size={12} color="ink2">{sub}</T>}
      </View>
      {right}
      <Icon d={I.next} size={18} />
    </Pressable>
  )
}

// A thin progress track: ink fill over a hairline.
export function Bar({ value, h = 5, w, style }) {
  const { c } = useTheme()
  return (
    <View style={[{ height: h, width: w, backgroundColor: c.line }, style]}>
      <View style={{ height: h, width: `${Math.max(0, Math.min(100, value * 100))}%`, backgroundColor: c.ink }} />
    </View>
  )
}

// The tile every badge and avatar sits in: a square with two corners cut (72 × 80).
export const TILE_D = 'M19 0H72V64L53 80H0V16Z'
export function Tile({ w = 72, filled = true, dashed, stroke, children, style }) {
  const { c } = useTheme()
  const h = Math.round(w * 80 / 72)
  return (
    <View style={[{ width: w, height: h, alignItems: 'center', justifyContent: 'center' }, style]}>
      <Svg width={w} height={h} viewBox="-1 -1 74 82" style={{ position: 'absolute' }}>
        <Path d={TILE_D} fill={filled ? c.ink : 'none'} stroke={stroke ?? (filled ? 'none' : c.ink)}
              strokeWidth={1.3} strokeDasharray={dashed ? [4, 3] : undefined} />
      </Svg>
      {children}
    </View>
  )
}

// An image inside the tile: the picture, with the two corners cut back out in paper colour.
export function TileImage({ source, w = 72 }) {
  const { c } = useTheme()
  const h = Math.round(w * 80 / 72)
  return (
    <View style={{ width: w, height: h }}>
      <Image source={source} style={{ width: w, height: h }} resizeMode="cover" accessibilityIgnoresInvertColors />
      <Svg width={w} height={h} viewBox="0 0 72 80" preserveAspectRatio="none" style={{ position: 'absolute' }}>
        <Path d="M0 0H19L0 16Z" fill={c.bg} />
        <Path d="M72 64V80H53Z" fill={c.bg} />
      </Svg>
    </View>
  )
}

/* ------------------------------------------------------ coach pieces (M3) */

// A bare 44 px icon button (settings, share, your details).
export function IconBtn({ icon, label, onPress, size = 22, color, style }) {
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} onPress={onPress} hitSlop={8}
               style={[{ width: 44, height: 44, alignItems: 'center', justifyContent: 'center' }, style]}>
      <Icon d={icon} size={size} color={color} />
    </Pressable>
  )
}

// A status tag in mono caps: ink when `on`, dashed when `dashed`.
export function Tag({ label, on, dashed, icon }) {
  const { c } = useTheme()
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, paddingVertical: 5, paddingHorizontal: 7,
                   backgroundColor: on ? c.ink : 'transparent', borderWidth: 1, borderColor: c.ink,
                   borderStyle: dashed ? 'dashed' : 'solid' }}>
      {!!icon && <Icon d={icon} size={11} sw={2.4} color={on ? c.bg : c.ink} />}
      <Mono size={9.5} color={on ? c.bg : c.ink} style={{ letterSpacing: 0.95 }}>{label}</Mono>
    </View>
  )
}

// A squad member: initials in a square, name, a mono line, something on the right.
export function PersonRow({ name, meta, right, onPress, filled, last }) {
  const { c } = useTheme()
  return (
    <Pressable onPress={onPress} disabled={!onPress} accessibilityRole={onPress ? 'button' : undefined}
               style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 11,
                                          borderTopWidth: 1, borderTopColor: c.line, borderBottomWidth: last ? 1 : 0,
                                          borderBottomColor: c.line, backgroundColor: pressed ? c.soft : 'transparent' })}>
      <View style={{ width: 38, height: 38, borderWidth: 1, borderColor: c.ink, backgroundColor: filled ? c.ink : 'transparent',
                     alignItems: 'center', justifyContent: 'center' }}>
        <Mono size={11.5} color={filled ? c.bg : c.ink}>{initials(name)}</Mono>
      </View>
      <View style={{ flex: 1, minWidth: 0, gap: 3 }}>
        <T size={15} numberOfLines={1}>{name}</T>
        {!!meta && <Mono size={10} color="ink2" numberOfLines={1} style={{ letterSpacing: 0.5 }}>{meta}</Mono>}
      </View>
      {right}
    </Pressable>
  )
}

// Search: a magnifier and an underlined input (Coach board, 08).
export function SearchField({ value, onChangeText, placeholder = 'Name or RA number' }) {
  const { c } = useTheme()
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10, borderBottomWidth: 1, borderBottomColor: c.ink, paddingBottom: 6 }}>
      <Icon d={I.search} size={18} />
      <TextInput value={value} onChangeText={onChangeText} placeholder={placeholder} accessibilityLabel="Search players"
                 placeholderTextColor={c.ink2} selectionColor={c.ink} cursorColor={c.ink} autoCorrect={false}
                 style={{ flex: 1, fontFamily: F.regular, fontSize: 15, color: c.ink, paddingVertical: 2 }} />
      {!!value && <IconBtn icon={I.close} label="Clear search" size={16} onPress={() => onChangeText('')} style={{ width: 28, height: 28 }} />}
    </View>
  )
}

/* The weight slider (Coach board, 09): a 4 px track filled in ink, a diamond thumb. Drags
   in whole steps, ticks every `tick`, and answers the screen reader's swipe up / down. */
export function Slider({ value, onChange, min = 0, max = 100, step = 1, tick = 5, label }) {
  const { c } = useTheme()
  const [w, setW] = useState(0)
  const set = v => {
    const next = Math.min(max, Math.max(min, Math.round(v / step) * step))
    if (next === value) return
    if (Math.floor(next / tick) !== Math.floor(value / tick) || next % tick === 0) haptic.tick()
    onChange(next)
  }
  const at = x => (w ? set(min + (x / w) * (max - min)) : null)
  const p = ((value - min) / (max - min)) * 100
  return (
    <View onLayout={e => setW(e.nativeEvent.layout.width)}
          onStartShouldSetResponder={() => true} onMoveShouldSetResponder={() => true}
          onResponderTerminationRequest={() => false}
          onResponderGrant={e => at(e.nativeEvent.locationX)} onResponderMove={e => at(e.nativeEvent.locationX)}
          accessible accessibilityRole="adjustable" accessibilityLabel={label}
          accessibilityValue={{ min, max, now: value, text: `${value}%` }}
          accessibilityActions={[{ name: 'increment' }, { name: 'decrement' }]}
          onAccessibilityAction={e => set(value + (e.nativeEvent.actionName === 'increment' ? tick : -tick))}
          style={{ height: 28, justifyContent: 'center' }}>
      <View pointerEvents="none" style={{ height: 4, backgroundColor: c.line }}>
        <View style={{ height: 4, width: `${p}%`, backgroundColor: c.ink }} />
      </View>
      <View pointerEvents="none"
            style={{ position: 'absolute', left: `${p}%`, marginLeft: -9, width: 18, height: 18, backgroundColor: c.ink,
                     borderWidth: 3, borderColor: c.bg, outlineWidth: 1, outlineColor: c.ink, transform: [{ rotate: '45deg' }] }} />
    </View>
  )
}

// A record row (Profile board): a mono label over the value, a lock if it is the admin's to change.
export function Rec({ label, value, locked, onPress, last }) {
  const { c } = useTheme()
  return (
    <Pressable onPress={onPress} disabled={!onPress} accessibilityRole={onPress ? 'button' : undefined}
               style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 13,
                                          borderTopWidth: 1, borderTopColor: c.line, borderBottomWidth: last ? 1 : 0, borderBottomColor: c.line,
                                          backgroundColor: pressed ? c.soft : 'transparent' })}>
      <View style={{ flex: 1, gap: 3 }}>
        <Mono size={10} color="ink2" style={{ letterSpacing: 1 }}>{label}</Mono>
        <T size={15} style={onPress ? { textDecorationLine: 'underline' } : null}>{value || '—'}</T>
      </View>
      {locked && <Icon d={I.lock} size={16} color={c.ink2} />}
    </Pressable>
  )
}
