import { useCallback } from 'react'
import { findNodeHandle, Platform } from 'react-native'
import Animated, { scrollTo, useAnimatedReaction, useAnimatedRef, useAnimatedStyle, useScrollOffset, useSharedValue } from 'react-native-reanimated'
import { useKeyboardHandler, useReanimatedFocusedInput, useWindowDimensions } from 'react-native-keyboard-controller'

const GAP = 24            // the least room kept between the field being typed in and the keyboard

/* A page's scroll view that rides up with the keyboard. As the keyboard rises, the page
   rises with it, frame by frame — as far as the keyboard does, but never so far that the
   field being typed in passes `top` — so what was under the field (the next fields, the
   Save button) comes up into view instead of disappearing behind the keyboard. As the
   keyboard falls, the page comes back down. Choosing another field while the keyboard is
   up scrolls that one clear of it. Only this page's own fields move it (every tab keeps
   its page mounted, so each checks the field is inside it). */
export default function KeyboardScroll({ top, contentContainerStyle, children, ...rest }) {
  const ref = useAnimatedRef()
  const offset = useScrollOffset(ref)
  const { height: winH } = useWindowDimensions()       // the same frame the field and keyboard are measured in
  const { input } = useReanimatedFocusedInput()
  const tag = useSharedValue(0)            // this scroll view: fields name the scroll view they sit in
  const mine = useSharedValue(false)       // the keyboard is up for one of this page's fields
  const pad = useSharedValue(0)            // room after the page's end, so it can rise above the keyboard
  const size = useSharedValue(0)           // the page's height, room included
  const view = useSharedValue(0)           // the scroll view's own height
  const now = useSharedValue(0)            // the keyboard's height this frame
  const up = useSharedValue(0)             // ...once it has settled
  const start = useSharedValue(0)          // ...when this movement started
  const goal = useSharedValue(0)           // ...when this movement ends
  const from = useSharedValue(0)           // the scroll when this movement started
  const to = useSharedValue(0)             // ...and where it ends
  const base = useSharedValue(0)           // how far the page had risen before this movement
  const risen = useSharedValue(0)          // how far the page has risen for the keyboard
  const moving = useSharedValue(false)
  const seenT = useSharedValue(-1)         // the field last measured,
  const seenAt = useSharedValue(0)         // ...and the scroll it was measured at

  const onLayout = useCallback(e => {
    view.value = e.nativeEvent.layout.height
    // the scroll view itself: with pull to refresh, Android wraps it in the refresh view,
    // which is what findNodeHandle(ref.current) alone would find
    if (Platform.OS !== 'web') tag.value = ref.current?.getScrollableNode?.() ?? findNodeHandle(ref.current) ?? 0
  }, [ref, tag, view])
  const onContentSizeChange = useCallback((w, h) => { size.value = h }, [size])

  const ours = f => {
    'worklet'
    return !!f && f.target > 0 && tag.value > 0 && f.parentScrollViewTarget === tag.value
  }
  // aim this movement at a field: as the keyboard grows, rise as much as it does, short of the
  // field passing `top`; and always at least enough that the keyboard doesn't cover the field
  const aim = f => {
    'worklet'
    const y = f.layout.absoluteY - (f.target === seenT.value ? offset.value - seenAt.value : 0)   // where it is now
    const need = y + f.layout.height + GAP - (winH - goal.value)
    const lift = Math.max(0, need, Math.min(goal.value - start.value, y - top))
    mine.value = true
    pad.value = Math.max(pad.value, goal.value)
    to.value = from.value + lift
  }

  useKeyboardHandler({
    onStart: e => {
      'worklet'
      moving.value = true
      start.value = now.value
      goal.value = e.height
      from.value = offset.value
      to.value = offset.value
      base.value = risen.value
      if (e.height === 0) {
        // falling: back down by as much as it rose, but not past the page's end without the room
        if (mine.value) to.value = Math.max(0, Math.min(from.value - risen.value, size.value - pad.value - view.value))
      } else if (ours(input.value)) {
        aim(input.value)
      }
    },
    onMove: e => {
      'worklet'
      now.value = e.height
      if (to.value === from.value || goal.value === start.value) return
      const t = Math.min(1, Math.max(0, (e.height - start.value) / (goal.value - start.value)))
      const y = from.value + (to.value - from.value) * t
      scrollTo(ref, 0, y, false)
      risen.value = base.value + y - from.value
    },
    // also where it lands when the keyboard changed without moving (another field, same keyboard)
    onEnd: e => {
      'worklet'
      moving.value = false
      now.value = e.height
      up.value = e.height
      if (to.value !== from.value) scrollTo(ref, 0, to.value, false)
      risen.value = base.value + to.value - from.value
      if (e.height === 0) { mine.value = false; risen.value = 0; pad.value = 0 }
    },
  }, [winH, top])

  // a field was focused or measured again (typing measures it too)
  useAnimatedReaction(() => input.value, f => {
    if (!f || f.target < 1) return
    seenT.value = f.target
    seenAt.value = moving.value ? from.value : offset.value
    if (!ours(f)) return
    if (moving.value) { if (goal.value > 0) aim(f); return }      // it arrived after the keyboard set off
    if (up.value === 0) return                                     // the keyboard is about to open: onStart aims
    // the keyboard is already up: bring this field clear of it, or down from under the top
    const y = f.layout.absoluteY
    const below = y + f.layout.height + GAP - (winH - up.value)
    const delta = below > 0 ? below : Math.min(0, y - top)
    if (delta === 0) return
    mine.value = true
    risen.value = Math.max(0, risen.value + delta)
    scrollTo(ref, 0, Math.max(0, offset.value + delta), true)
  }, [winH, top])

  // the room, after the page's own end: the negative margin cancels the page's gap before it
  const gap = contentContainerStyle?.gap ?? 0
  const room = useAnimatedStyle(() => ({ height: pad.value, marginTop: -gap }), [gap])

  return (
    <Animated.ScrollView ref={ref} onLayout={onLayout} onContentSizeChange={onContentSizeChange}
                         contentContainerStyle={contentContainerStyle} {...rest}>
      {children}
      <Animated.View style={room} pointerEvents="none" />
    </Animated.ScrollView>
  )
}
