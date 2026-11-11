import { memo, useCallback, useEffect, useRef, useState } from 'react'
import { Easing, useSharedValue, withTiming } from 'react-native-reanimated'
import { View } from 'react-native'
import { BlurTargetView } from 'expo-blur'
import { router, useLocalSearchParams } from 'expo-router'
import { primed, pushAvailable, registerPush, useTappedNotification } from '../../lib/notifications'
import { useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { I } from '../../ui'
import TabBar from '../../ui/TabBar'
import { SWEEP_MS, SweepLines, TabLayer } from '../../ui/Sweep'
import { haptic } from '../../lib/haptics'
import StudentDashboard from '../../tabs/student/Dashboard'
import StudentReport from '../../tabs/student/Report'
import StudentAchievements from '../../tabs/student/Achievements'
import StudentProfile from '../../tabs/student/Profile'
import CoachEntry from '../../tabs/coach/Entry'
import CoachFootage from '../../tabs/coach/Footage'
import CoachCards from '../../tabs/coach/Cards'
import CoachSquad from '../../tabs/coach/Squad'
import CoachWeights from '../../tabs/coach/Weights'
import CoachTraining from '../../tabs/coach/Training'
import CoachProfile from '../../tabs/coach/Profile'
import AdminAdd from '../../tabs/admin/Add'

const STUDENT = [
  { key: 'dash', label: 'Dashboard', short: 'Dashboard', icon: I.dashboard, C: StudentDashboard },
  { key: 'report', label: 'My report', short: 'Report', icon: I.report, eyebrow: 'MY REPORT', C: StudentReport },
  { key: 'ach', label: 'Achievements', short: 'Achievements', icon: I.achievements, eyebrow: 'CERTIFICATES & MILESTONES', C: StudentAchievements },
  { key: 'profile', label: 'Profile', short: 'Profile', icon: I.profile, eyebrow: 'UNIVERSITY RECORD', C: StudentProfile },
]
const COACH = [
  { key: 'entry', label: 'Coach Entry', short: 'Entry', icon: I.entry, eyebrow: 'RECORD RESULTS', C: CoachEntry },
  { key: 'footage', label: 'Footage', short: 'Footage', icon: I.footage, eyebrow: 'MATCH AND DRILL VIDEO', C: CoachFootage },
  { key: 'cards', label: 'Match Cards', short: 'Cards', icon: I.cards, eyebrow: 'READ FROM A PHOTO', C: CoachCards },
  { key: 'squad', label: 'Dashboard', short: 'Squad', icon: I.squad, eyebrow: 'TODAY’S BRIEF', C: CoachSquad },
  { key: 'weights', label: 'Weights', short: 'Weights', icon: I.weights, eyebrow: 'POSITION WEIGHTS', C: CoachWeights },
  { key: 'ai', label: 'AI Training', short: 'AI', icon: I.ai, eyebrow: 'THE MODEL', C: CoachTraining },
  { key: 'profile', label: 'Profile', short: 'Profile', icon: I.profile, eyebrow: 'YOUR DETAILS', C: CoachProfile },
]
const ADMIN = [{ key: 'add', label: 'Add Student', short: 'Add', icon: I.addPerson, eyebrow: 'BY HAND · NO LOGIN', C: AdminAdd }, ...COACH]

/* The signed-in app: one screen per tab under the glass tab bar. A tab stays mounted once
   visited (the rest are mounted quietly a few seconds after launch), so switching never
   waits for a page to be built, and going back keeps its scroll and whatever was typed.
   The sweep between tabs runs on the UI thread from three shared values (Sweep.js), set
   the moment a tab is chosen. */
export default function Home() {
  const s = useSession()
  const { c, name, reduced } = useTheme()
  const tabs = s.role === 'student' ? STUDENT : s.isAdmin ? ADMIN : COACH
  const startAt = s.role === 'student' ? 0 : tabs.findIndex(t => t.key === 'squad')
  const [active, setActive] = useState(startAt)
  const [seen, setSeen] = useState(() => new Set([startAt]))
  const built = useRef(seen)                         // the same set, readable without waiting for a render
  const [ask, setAsk] = useState(null)              // what a jump asked a tab to show: { key, …, at }
  const [size, setSize] = useState({ w: 0, h: 0 })
  const cur = useSharedValue(startAt), from = useSharedValue(-1), p = useSharedValue(1)
  const now = useRef(startAt)
  const waiting = useRef(null)                      // a tab chosen before it was ever drawn
  const latest = useRef({ tabs, reduced })
  latest.current = { tabs, reduced }
  const behind = useRef(null)

  const sweep = useCallback(i => {
    // p first, so there's never a moment with the new tab chosen and the sweep finished
    p.value = 0
    from.value = cur.value
    cur.value = i
    p.value = withTiming(1, { duration: latest.current.reduced ? 150 : SWEEP_MS, easing: Easing.linear })
    if (!latest.current.reduced) setTimeout(haptic.sweep, 300)          // as the lines cross
  }, [cur, from, p])

  // go('footage') — or go('footage', { section: 'drill', … }) to have the tab show something
  const go = useCallback((key, payload) => {
    const list = latest.current.tabs
    const i = typeof key === 'number' ? key : list.findIndex(t => t.key === key || t.label === key)
    if (i < 0) return
    if (payload) setAsk({ ...payload, key: list[i].key, at: payload.at ?? String(Date.now()) })
    if (i === now.current) return
    now.current = i
    setActive(i)
    if (built.current.has(i)) return sweep(i)
    waiting.current = i                              // sweep once it's been drawn (below)
    built.current = new Set(built.current).add(i)
    setSeen(built.current)
  }, [sweep])
  useEffect(() => {
    if (waiting.current == null || !seen.has(waiting.current)) return
    const i = waiting.current
    waiting.current = null
    if (i === now.current) sweep(i)
  }, [seen, sweep])

  // the other tabs, built one at a time once the launch is over
  useEffect(() => {
    let t = setTimeout(function next() {
      const i = tabs.findIndex((_, k) => !built.current.has(k))
      if (i < 0) return
      built.current = new Set(built.current).add(i)
      setSeen(built.current)
      t = setTimeout(next, 350)
    }, 3200)
    return () => clearTimeout(t)
  }, [tabs])

  // a page further in can send the app to a tab: "Record their results" → Entry, with them picked
  const params = useLocalSearchParams()
  useEffect(() => { if (params.tab) go(params.tab, { ...params }) }, [params.tab, params.at])

  // notifications: this phone's token to the server (once the person has said yes), and
  // the "why we ask" screen the first time round
  useEffect(() => {
    if (!pushAvailable) return undefined        // Expo Go on Android: no point asking
    registerPush(false)
    const t = setTimeout(() => primed('notifications').then(done => { if (!done) router.push({ pathname: '/primer', params: { kind: 'notifications' } }) }), 1500)
    return () => clearTimeout(t)
  }, [])

  // a tapped notification opens what it is about
  const tapped = useTappedNotification()
  useEffect(() => {
    const d = tapped?.notification?.request?.content?.data
    if (!d) return
    if (d.tab) go(d.tab)
    if (d.video && s.role === 'student') router.push({ pathname: '/videos/[vid]', params: { vid: d.video } })
    if (d.student && s.role === 'coach') router.push({ pathname: '/student/[id]', params: { id: d.student } })
  }, [tapped])

  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      <BlurTargetView ref={behind} style={{ flex: 1 }}
                      onLayout={e => setSize({ w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.height })}>
        {tabs.map((tab, i) => seen.has(i) && (
          <TabLayer key={tab.key} i={i} cur={cur} from={from} p={p} w={size.w} h={size.h} reduced={reduced}
                    dim={name === 'dark' ? 0.32 : 0.1} live={i === active}>
            <Page C={tab.C} tab={tab} go={go} active={i === active} ask={ask?.key === tab.key ? ask : null} />
          </TabLayer>
        ))}
        {!reduced && size.w > 0 && (
          <SweepLines p={p} w={size.w} h={size.h} color={c.ink} shadow={name === 'dark' ? null : 'rgba(18,18,17,0.13)'} />
        )}
      </BlurTargetView>
      <TabBar tabs={tabs} active={active} onChange={go} blurTarget={behind} reduced={reduced} />
    </View>
  )
}

// A tab's screen, drawn again only when its own props change — not on every switch.
const Page = memo(function Page({ C, ...props }) {
  return <C {...props} />
})
