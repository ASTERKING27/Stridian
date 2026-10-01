import { useCallback, useEffect, useRef, useState } from 'react'
import { AppState, Pressable, RefreshControl, View } from 'react-native'
import { router } from 'expo-router'
import Svg, { Circle } from 'react-native-svg'
import { api, formatValue, shortUnits } from '../../lib/api'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Btn, Eyebrow, I, Mono, Note, OfflineBar, Placeholder, Row, Screen, T, Top } from '../../ui'
import LevelReached from '../../ui/LevelReached'
import { toast } from '../../ui/Toast'

/* The student's home: what the second coach says today (backend/coach.py writes the
   words), the level they play at, this week's focus, and the next level for each result.
   Layout: the design's e-ink template (Themes board). */
export default function Dashboard({ go }) {
  const s = useSession()
  const { c: col } = useTheme()
  const st = s.me?.student
  const [c, setC] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [ticking, setTicking] = useState(false)
  const [all, setAll] = useState(false)
  const [record, setRecord] = useState(null)       // { party, snapshot, rings }: a level reached, on show
  const handled = useRef(null)

  const load = useCallback(() => api.studentCoach().then(v => { setC(v); setError(null) }, setError), [])
  useEffect(() => { load() }, [load, st?.status, st?.category, st?.photo_version])
  // back in the app after a while (overnight, say): today's tick and this week's focus move on
  useEffect(() => {
    const sub = AppState.addEventListener('change', a => { if (a === 'active') load() })
    return () => sub.remove()
  }, [load])

  // what is new since they last looked: a level first (it waits to be read), then badges
  useEffect(() => {
    if (!c || handled.current === c) return
    handled.current = c
    const party = c.celebrate
    if (party.level || party.levelUps.length) {
      setRecord({ party, snapshot: c.snapshot, rings: c.rings })
      haptic.success()
    } else if (party.badges.length) {
      announce(party.badges)
      api.studentCoachSeen(c.snapshot).catch(() => {})
    }
  }, [c])

  function closeRecord() {
    announce(record.party.badges)
    api.studentCoachSeen(record.snapshot).catch(() => {})
    setRecord(null)
  }

  async function refresh() {
    setRefreshing(true)
    await Promise.all([load(), s.refresh()])
    setRefreshing(false)
  }

  async function tick() {
    setTicking(true)
    try { setC(await api.focusTick()); setError(null) } catch (err) { setError(err) }
    setTicking(false)
  }

  const offline = error?.offline
  return (
    <View style={{ flex: 1 }}>
      {offline && <OfflineBar note={c ? 'SHOWING WHAT WAS LOADED' : 'NOTHING LOADED YET'} onRetry={refresh} />}
      <Screen bottom={110} gap={22}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={col.ink}
                                              colors={[col.ink]} progressBackgroundColor={col.bg} />}>
        <Top context={contextLine(s)} />
        {offline && <View style={{ height: 40 }} />}
        {error && !offline && <Note>{error.message}</Note>}
        {!c && !error && <Loading />}
        {c && (
          <>
            <View style={{ gap: 10 }}>
              <Eyebrow>{c.verified ? 'YOUR SECOND COACH' : 'GETTING YOU SET UP'}</Eyebrow>
              <T font="medium" size={27} style={{ lineHeight: 31, letterSpacing: -0.32 }}>{c.headline}</T>
            </View>

            {c.verified && c.standing.length > 0 && <Brief c={c} />}
            {!c.verified && (
              <View style={{ gap: 12, paddingTop: 18, borderTopWidth: 1, borderTopColor: col.line }}>
                <Row a="Your coach verifies your position" b={<Mono size={11} color="ink2">WAITING</Mono>} />
                <Btn kind="secondary" small label="Check again" busy={refreshing} busyLabel="Checking" onPress={refresh} />
              </View>
            )}

            {c.focus && <Focus f={c.focus} busy={ticking} offline={offline} onTick={tick} />}

            {c.cards.length > 0 && (
              <View>
                <Eyebrow style={{ paddingBottom: 8 }}>YOUR COACH SAYS</Eyebrow>
                {c.cards.map((card, i) => (
                  <Pressable key={`${card.kind}-${card.key ?? i}`} disabled={!card.tab} onPress={() => go(card.tab)}
                             accessibilityRole={card.tab ? 'button' : undefined}
                             style={{ paddingVertical: 12, borderTopWidth: 1, borderTopColor: col.line, gap: 4 }}>
                    <T font="semi" size={15}>{shortUnits(card.title)}</T>
                    <T size={13.5} color="ink2" style={{ lineHeight: 19 }}>{shortUnits(card.body)}</T>
                  </Pressable>
                ))}
              </View>
            )}

            {c.rings.length > 0 && (
              <View>
                <Eyebrow style={{ paddingBottom: 8 }}>NEXT LEVEL</Eyebrow>
                {(all ? c.rings : c.rings.slice(0, 4)).map(r => (
                  <Row key={r.key} a={r.label}
                       sub={r.next ? `${shortUnits(r.gap)} to ${r.next}` : 'Top level'}
                       b={formatValue(r.value, r)} />
                ))}
                {c.rings.length > 4 && (
                  <Btn kind="text" label={all ? 'Show fewer' : `Show all ${c.rings.length}`} onPress={() => setAll(a => !a)} />
                )}
              </View>
            )}
          </>
        )}
      </Screen>
      {record && <LevelReached party={record.party} rings={record.rings} onClose={closeRecord} />}
    </View>
  )
}

// new badges: a quiet note each, at most three
function announce(badges) {
  badges.slice(0, 3).forEach((b, i) => setTimeout(() => toast({ title: `Badge: ${b.title}`, sub: b.desc.toUpperCase(), ms: 4000 }), i * 400))
}

/* The level they play at as a ring (how far to the next one) beside the ladder: how many
   of their measures reach each level. */
function Brief({ c }) {
  const { c: col } = useTheme()
  const lv = c.level
  const next = lv == null || lv >= 4 ? null : lv + 1
  // they reach the next level once more than half their measures (by weight) do
  // (exactly half isn't "more than half": it stops at 99%, not a full ring)
  const progress = lv == null ? 0 : next == null ? 1 : Math.min(0.99, (c.standing[next]?.share ?? 0) / 0.5)
  const name = lv == null ? '—' : lv < 0 ? 'STARTER' : c.levels[lv].toUpperCase()
  const C = 2 * Math.PI * 50
  const said = lv == null ? 'Level: needs more tests'
    : `Playing at ${name.toLowerCase()} level${next != null ? `, ${Math.round(progress * 100)} percent of the way to ${c.levels[next]}` : ''}`
  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 24, paddingTop: 18, borderTopWidth: 1, borderTopColor: col.line }}>
      <View accessible accessibilityLabel={said} style={{ width: 112, height: 112 }}>
        <Svg width={112} height={112} viewBox="0 0 112 112">
          <Circle cx={56} cy={56} r={50} fill="none" strokeWidth={5} stroke={col.line} />
          <Circle cx={56} cy={56} r={50} fill="none" strokeWidth={5} stroke={col.ink}
                  strokeDasharray={[progress * C, C]} rotation={-90} origin="56, 56" />
        </Svg>
        <View style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, alignItems: 'center', justifyContent: 'center', gap: 4 }}>
          <T font="wide" size={13} style={{ letterSpacing: 1.56, paddingLeft: 1.56 }}>{name}</T>
          <Mono size={10} color="ink2">
            {lv == null ? 'MORE TESTS' : next != null ? `${Math.round(progress * 100)}% → ${c.levels[next].toUpperCase()}` : 'TOP LEVEL'}
          </Mono>
        </View>
      </View>
      <View style={{ flex: 1, gap: 6 }}>
        {[4, 3, 2, 1, 0].map(i => {
          const row = c.standing[i]
          const above = lv == null || i > lv
          return (
            <View key={i} style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
              <T font={i === lv ? 'semi' : 'body'} size={13} color={above ? 'ink2' : 'ink'}>{c.levels[i]}</T>
              <Mono size={13} color={above ? 'ink2' : 'ink'}>{row ? `${row.met}/${row.of}` : '—'}</Mono>
            </View>
          )
        })}
      </View>
    </View>
  )
}

function Focus({ f, busy, offline, onTick }) {
  const { c: col } = useTheme()
  const n = f.sessions.length
  const boxes = Array.from({ length: Math.max(f.target, n) }, (_, i) => i < n)
  const streak = f.streak ? `${f.streak}-week streak` : 'start a streak'
  return (
    <View style={{ borderWidth: 1, borderColor: col.ink, paddingVertical: 14, paddingHorizontal: 16, gap: 14 }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
        <Pressable onPress={() => router.push('/streak')} accessibilityRole="button" accessibilityHint="Opens your focus streak"
                   style={{ flex: 1, gap: 5 }}>
          <Eyebrow>THIS WEEK'S FOCUS</Eyebrow>
          <T font="semi" size={18}>{f.label}</T>
          <T size={12} color="ink2">{f.complete ? `Week done · ${streak}` : `${n} of ${f.target} sessions · ${streak}`}</T>
        </Pressable>
        <View accessible accessibilityLabel={`${n} of ${f.target} sessions done`} style={{ flexDirection: 'row', gap: 6, alignItems: 'center' }}>
          {boxes.map((on, i) => (
            <View key={i} style={on ? { width: 16, height: 16, backgroundColor: col.ink }
              : { width: 14, height: 14, borderWidth: 1, borderColor: col.ink, margin: 1 }} />
          ))}
        </View>
      </View>
      {!!f.ring?.next && <Mono size={11} color="ink2">{shortUnits(f.ring.gap)} TO {f.ring.next.toUpperCase()}</Mono>}
      <T size={13} color="ink2" style={{ lineHeight: 18 }}>{f.tip}</T>
      {/* once logged, the button becomes the confirmation (Feedback board) */}
      <Btn small icon={f.doneToday ? I.check : undefined} haptics={!f.doneToday}
           label={f.doneToday ? 'Done for today' : 'Log today’s session'} busy={busy} busyLabel="Saving"
           disabled={offline && !f.doneToday} onPress={f.doneToday ? undefined : onTick} />
      {offline && !f.doneToday && <T size={12.5} color="ink2">Logging a session needs a connection.</T>}
    </View>
  )
}

function Loading() {
  return (
    <View style={{ gap: 18 }}>
      <Eyebrow>LOADING</Eyebrow>
      <Placeholder h={27} w="90%" />
      <Placeholder h={27} w="60%" />
      <View style={{ flexDirection: 'row', gap: 24, alignItems: 'center' }}>
        <Placeholder h={112} w={112} />
        <View style={{ flex: 1, gap: 8 }}>{[0, 1, 2, 3, 4].map(i => <Placeholder key={i} h={13} />)}</View>
      </View>
      <Placeholder h={96} />
    </View>
  )
}
