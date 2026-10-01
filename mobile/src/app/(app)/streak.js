import { useEffect, useState } from 'react'
import { View } from 'react-native'
import { router } from 'expo-router'
import * as SecureStore from 'expo-secure-store'
import Svg, { Polygon } from 'react-native-svg'
import { api } from '../../lib/api'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Back, Btn, Eyebrow, Lap, Mono, Note, Screen, T } from '../../ui'

const DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
const WORDS = ['No', 'One', 'Two', 'Three']
// today in India, where every user is (the server counts days the same way)
const todayIST = () => new Date(Date.now() + 5.5 * 3600e3)
const dayOf = iso => DAYS[new Date(`${iso}T00:00:00Z`).getUTCDay()]

/* Streaks board: the count, the last eight weeks, this week's sessions — and the three
   edge cases: about to break, broken, restored by the coach. */
export default function Streak() {
  const { c } = useTheme()
  const [f, setF] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => { api.studentCoach().then(r => setF(r.focus), setError) }, [])

  const now = todayIST()
  const dow = now.getUTCDay()                       // 0 Sunday
  const daysLeft = dow === 0 ? 1 : 8 - dow          // today included, to Sunday night
  const n = f?.sessions.length ?? 0
  const left = f ? Math.max(0, f.target - n) : 0
  const hist = f?.history ?? []
  const last = hist.at(-2)
  const before = hist.at(-3)
  const state = !f ? null
    : f.restored ? 'restored'
      : f.streak === 0 && last && last.sessions < f.target && before && before.sessions >= f.target ? 'broken'
        : f.streak > 0 && !f.complete && left > 0 && daysLeft <= left + 1 ? 'warn'
          : null

  // the warning buzzes once a day, the first time it is seen
  useEffect(() => {
    if (state !== 'warn') return
    const day = now.toISOString().slice(0, 10)
    SecureStore.getItemAsync('stridian.warned').then(v => {
      if (v !== day) { haptic.warning(); SecureStore.setItemAsync('stridian.warned', day).catch(() => {}) }
    }).catch(() => {})
  }, [state]) // eslint-disable-line react-hooks/exhaustive-deps

  async function tick() {
    setBusy(true)
    try { setF((await api.focusTick()).focus); haptic.success() } catch (err) { haptic.error(); setError(err) }
    setBusy(false)
  }

  const banner = state === 'warn' ? {
    title: 'Ends Sunday night',
    body: `${WORDS[left] ?? left} session${left > 1 ? 's' : ''} still to do this week. Miss ${left > 1 ? 'them' : 'it'} and the streak starts again from zero.`,
    ink: true,
  } : state === 'broken' ? {
    title: 'The streak reset',
    body: `Last week ended at ${last.sessions} of ${f.target}.${f.best ? ` Your best stays at ${f.best} week${f.best > 1 ? 's' : ''}` : ''} — and badges you earned are yours to keep.`,
  } : state === 'restored' ? {
    title: 'Streak restored',
    body: `${f.restored.by ?? 'Your coach'} logged ${f.restored.day ?? 'a'} session late, so that week counts. You’re at ${f.streak} week${f.streak === 1 ? '' : 's'}${f.best && f.streak >= f.best ? ' — a new best' : ''}.`,
    ink: true,
  } : null

  return (
    <Screen gap={20}>
      <Back label="Back" onPress={() => router.back()} />
      {error && <Note>{error.message}</Note>}
      {!f && !error && <Lap size={28} />}
      {f && (
        <>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline' }}>
            <Eyebrow>FOCUS STREAK · {f.label.toUpperCase()}</Eyebrow>
            <Mono size={10.5} color="ink2" style={{ letterSpacing: 1.05 }}>{['SUNDAY', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY'][dow]}</Mono>
          </View>
          <View style={{ flexDirection: 'row', alignItems: 'flex-end', gap: 14 }}>
            <T font="display" size={110} color={state === 'broken' ? 'ink2' : 'ink'} style={{ lineHeight: 112 }}>{f.streak}</T>
            <View style={{ gap: 6, paddingBottom: 14 }}>
              <T font="title" size={17}>{state === 'restored' ? 'weeks — back on' : f.streak === 1 ? 'week in a row' : 'weeks in a row'}</T>
              {f.best != null && <Mono size={10.5} color="ink2">{f.streak >= f.best && f.best > 0 ? 'NEW BEST' : 'BEST'} · {f.best} WEEK{f.best === 1 ? '' : 'S'}</Mono>}
            </View>
          </View>

          {banner && (
            <View accessibilityRole="alert"
                  style={{ paddingVertical: 14, paddingHorizontal: 16, flexDirection: 'row', gap: 12, alignItems: 'flex-start',
                           backgroundColor: banner.ink ? c.ink : 'transparent', borderWidth: 1, borderColor: c.ink,
                           borderStyle: banner.ink ? 'solid' : 'dashed' }}>
              <View style={{ width: 10, height: 10, marginTop: 5, backgroundColor: banner.ink ? c.bg : c.ink, transform: [{ rotate: '45deg' }] }} />
              <View style={{ flex: 1, gap: 4 }}>
                <T font="semi" size={16} color={banner.ink ? c.bg : c.ink}>{banner.title}</T>
                <T size={13.5} color={banner.ink ? c.bg : c.ink} style={{ lineHeight: 19, opacity: 0.85 }}>{banner.body}</T>
              </View>
            </View>
          )}

          {hist.length > 0 && (
            <View style={{ gap: 10 }}>
              <Eyebrow>LAST {hist.length} WEEKS</Eyebrow>
              <View style={{ flexDirection: 'row', gap: 8 }}>
                {hist.map((w, i) => <Week key={w.week} w={w} target={f.target} current={i === hist.length - 1} />)}
              </View>
            </View>
          )}

          <View style={{ gap: 10 }}>
            <Eyebrow>THIS WEEK · {n} OF {f.target}{left > 0 ? ` · ${daysLeft} DAY${daysLeft === 1 ? '' : 'S'} LEFT` : ''}</Eyebrow>
            <View style={{ flexDirection: 'row', gap: 10 }}>
              {Array.from({ length: Math.max(f.target, n) }, (_, i) => {
                const done = i < n
                return (
                  <View key={i} style={{ flex: 1, height: 50, alignItems: 'center', justifyContent: 'center', borderWidth: 1,
                                         borderColor: c.ink, borderStyle: done ? 'solid' : 'dashed', backgroundColor: done ? c.ink : 'transparent' }}>
                    <Mono size={11} color={done ? c.bg : c.ink2} style={{ letterSpacing: 1.32 }}>{done ? dayOf(f.sessions[i]) : '—'}</Mono>
                  </View>
                )
              })}
            </View>
          </View>

          <T size={13.5} color="ink2" style={{ lineHeight: 19 }}>{f.tip}</T>
          <Btn label={f.doneToday ? 'Done for today' : state === 'broken' ? 'Start a new streak' : 'Log today’s session'}
               busy={busy} busyLabel="Saving" haptics={!f.doneToday} onPress={f.doneToday ? undefined : tick} />
        </>
      )}
    </Screen>
  )
}

// one week as the design's slanted bar, filled by how many sessions it got
function Week({ w, target, current }) {
  const { c } = useTheme()
  const fill = Math.min(1, w.sessions / target)
  const H = 60
  return (
    <View style={{ flex: 1, gap: 8, alignItems: 'center' }}>
      <View style={{ width: '100%', height: H }}>
        <Svg width="100%" height={H} viewBox="0 0 100 100" preserveAspectRatio="none">
          <Polygon points="38,0 100,0 62,100 0,100" fill={c.line} />
          {fill > 0 && (
            <Polygon points={`${38 * fill},${100 - fill * 100} ${62 + 38 * fill},${100 - fill * 100} 62,100 0,100`} fill={c.ink} />
          )}
        </Svg>
      </View>
      <Mono size={9.5} color={current ? 'ink' : 'ink2'}>{w.week.slice(-3)}</Mono>
    </View>
  )
}
