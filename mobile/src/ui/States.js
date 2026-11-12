import { useEffect, useRef, useState } from 'react'
import { View } from 'react-native'
import { useTheme } from '../lib/theme'
import { haptic } from '../lib/haptics'
import { Btn, Eyebrow, I, Icon, Mono, Note, T } from './index'

const AGAIN = 30                 // seconds between tries on its own
const clock = d => d.toLocaleTimeString('en-GB', { hour: '2-digit', minute: '2-digit' })

/* What a screen shows when its data didn't load (States board): nothing when offline (the
   offline bar says so), the server-down state when the server answered with a 5xx and
   there's nothing loaded to show, otherwise the message. */
export function LoadError({ error, onRetry, hasData }) {
  if (!error || error.offline) return null
  if (error.status >= 500 && !hasData) return <ServerDown error={error} onRetry={onRetry} />
  return <Note>{error.message}</Note>
}

/* 07 · Server down: on our side, not the phone's. It tries again by itself every 30 s,
   counting down; "Try now" doesn't wait. A retry the person asked for that fails buzzes
   a warning. */
export function ServerDown({ error, onRetry }) {
  const { c } = useTheme()
  const [left, setLeft] = useState(AGAIN)
  const [checked, setChecked] = useState(() => new Date())
  const [busy, setBusy] = useState(false)
  const latest = useRef(onRetry)
  latest.current = onRetry
  const asked = useRef(false)

  async function retry(byHand) {
    asked.current = byHand
    setBusy(true)
    await latest.current?.()
    setChecked(new Date())
    setLeft(AGAIN)
    setBusy(false)
  }
  // a new error after a try they asked for: it failed (a success takes this screen away)
  useEffect(() => { if (asked.current) { asked.current = false; haptic.warning() } }, [error])
  useEffect(() => {
    const t = setInterval(() => setLeft(s => (s > 0 ? s - 1 : 0)), 1000)
    return () => clearInterval(t)
  }, [])
  useEffect(() => { if (left === 0 && !busy) retry(false) }, [left])

  return (
    <View accessibilityRole="alert" style={{ gap: 18, paddingTop: 8 }}>
      <View style={{ width: 56, height: 56, borderWidth: 1, borderColor: c.ink, borderStyle: 'dashed', alignItems: 'center', justifyContent: 'center' }}>
        <Icon d={I.offline} size={26} />
      </View>
      <View style={{ gap: 8 }}>
        <Eyebrow>SERVER NOT ANSWERING</Eyebrow>
        <T font="title" size={24}>Can’t reach Stridian right now</T>
        <T size={15} color="ink2" style={{ lineHeight: 22 }}>
          This one’s on our side, not your phone. Your data is safe — nothing you saved is lost.
        </T>
      </View>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', paddingVertical: 12,
                     borderTopWidth: 1, borderBottomWidth: 1, borderColor: c.line }}>
        <Mono size={10.5} color="ink2" style={{ letterSpacing: 1.05 }}>{busy ? 'TRYING NOW' : 'TRYING AGAIN BY ITSELF'}</Mono>
        <Mono size={13} font="monoMedium">0:{String(left).padStart(2, '0')}</Mono>
      </View>
      <Btn label="Try now" icon={I.retry} busy={busy} busyLabel="Trying" onPress={() => retry(true)} />
      <Mono size={10} color="ink2" style={{ letterSpacing: 1, textAlign: 'center' }}>LAST CHECKED {clock(checked)}</Mono>
    </View>
  )
}

/* 08 · Something went wrong: a screen that crashed while drawing itself (the router's
   error boundary). The details are for the coach — or whoever looks into it. */
export function Crashed({ error, retry, home }) {
  const { c } = useTheme()
  const [ref] = useState(() => Math.random().toString(16).slice(2, 6).toUpperCase())
  const now = new Date()
  return (
    <View accessibilityRole="alert" style={{ flex: 1, gap: 18, justifyContent: 'center' }}>
      <View style={{ width: 56, height: 56, borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
        <Icon d={I.warning} size={26} />
      </View>
      <View style={{ gap: 8 }}>
        <Eyebrow>UNEXPECTED ERROR</Eyebrow>
        <T font="title" size={24}>Something went wrong</T>
        <T size={15} color="ink2" style={{ lineHeight: 22 }}>
          This screen hit a problem we didn’t expect. Going back and trying again usually fixes it.
        </T>
      </View>
      <View style={{ gap: 6, padding: 14, borderWidth: 1, borderColor: c.line }}>
        <Eyebrow>DETAILS FOR YOUR COACH</Eyebrow>
        <Mono size={11} numberOfLines={3}>{String(error?.message ?? error).slice(0, 200)}</Mono>
        <Mono size={10} color="ink2">
          {now.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()} · {clock(now)} · REF {ref}
        </Mono>
      </View>
      <Btn label="Try again" icon={I.retry} onPress={retry} />
      <Btn kind="secondary" label="Go to the start" onPress={home} />
    </View>
  )
}
