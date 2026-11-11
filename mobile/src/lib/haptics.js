import { Platform, Vibration } from 'react-native'
import * as Haptics from 'expo-haptics'
import { requireOptionalNativeModule } from 'expo'
import { PATTERNS, PRIM, levels, onOff, waveform } from './patterns'

/* The design's haptic vocabulary, on the system haptics every phone tunes for its own
   motor (and which follow the phone's touch-feedback setting). The big moments — launch,
   the tab sweep — are patterns (code/haptics_data.py) played by the app's own module
   (modules/stridian-haptics) in the installed app on Android: a Composition where the
   motor has the primitives, the budget waveform where it doesn't. Without the module
   (Expo Go, iPhone for now) they fall back to a few system haptics at their moments —
   except launch, drawn a ms at a time (`buzz`), which Expo Go's plain vibrator plays too.
   ponytail: iPhone gets the fallback until its Core Haptics twin comes with the iPhone build. */

const A = Haptics.AndroidHaptics
const android = Platform.OS === 'android'
const api = Number(Platform.Version) || 0
const run = p => { p?.catch?.(() => {}) }
const tickA = api >= 34 ? A.Segment_Tick : A.Clock_Tick

export const haptic = {
  tick: () => run(android ? Haptics.performAndroidHapticsAsync(tickA) : Haptics.selectionAsync()),
  tap: () => run(android ? Haptics.performAndroidHapticsAsync(A.Virtual_Key)
    : Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Rigid)),
  snap: () => run(android ? Haptics.performAndroidHapticsAsync(A.Virtual_Key)
    : Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Heavy)),
  success: () => run(android ? Haptics.performAndroidHapticsAsync(api >= 30 ? A.Confirm : A.Virtual_Key)
    : Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success)),
  error: () => run(android ? Haptics.performAndroidHapticsAsync(api >= 30 ? A.Reject : A.Long_Press)
    : Haptics.notificationAsync(Haptics.NotificationFeedbackType.Error)),
  warning: () => {
    if (!android) return run(Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning))
    run(Haptics.performAndroidHapticsAsync(A.Clock_Tick))
    setTimeout(() => run(Haptics.performAndroidHapticsAsync(A.Clock_Tick)), 80)
  },
  toggle: on => run(android ? Haptics.performAndroidHapticsAsync(on ? A.Toggle_On : A.Toggle_Off)
    : Haptics.impactAsync(on ? Haptics.ImpactFeedbackStyle.Light : Haptics.ImpactFeedbackStyle.Soft)),
  nope: () => {
    if (!android) return run(Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Soft))
    run(Haptics.performAndroidHapticsAsync(A.Clock_Tick))
    setTimeout(() => run(Haptics.performAndroidHapticsAsync(A.Clock_Tick)), 80)
  },
}

// installed app on Android only; null in Expo Go, on iPhone and on the web
const Rich = android ? requireOptionalNativeModule('StridianHaptics') : null
export function play(name) {
  const p = PATTERNS[name]
  if (!p) return
  if (Rich) return run(Rich.play(p.rich.flatMap(([k, at, s]) => [PRIM[k], at, s]), waveform(p.budget ?? []), []))
  for (const [at, kind] of p.fallback ?? []) setTimeout(haptic[kind], at)
}
// A moment as one strength per ms: the module plays it as is; on a plain vibrator (Expo Go,
// or a motor that can't set its strength) strength becomes how long each pulse lasts.
export function buzz(a, fallback = []) {
  if (Rich) return run(Rich.play([], levels(a), onOff(a)))
  if (android) return Vibration.vibrate(onOff(a))
  for (const [at, kind] of fallback) setTimeout(haptic[kind], at)
}
haptic.sweep = () => play('sweep')
