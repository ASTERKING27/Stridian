import { Platform } from 'react-native'
import * as Haptics from 'expo-haptics'

/* The design's haptic vocabulary, on the system haptics every phone tunes for its own
   motor (and which follow the phone's touch-feedback setting).
   ponytail: system patterns only — the rich AHAP / Composition patterns (launch, level
   reached, badges) come with the native module in the development build. */

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
