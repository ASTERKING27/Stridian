import { useEffect, useRef, useState } from 'react'
import { Platform, View } from 'react-native'
import { BlurTargetView } from 'expo-blur'
import { router, useLocalSearchParams } from 'expo-router'
import { useLastNotificationResponse } from 'expo-notifications'
import { primed, registerPush } from '../../lib/notifications'
import { useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { I } from '../../ui'
import TabBar from '../../ui/TabBar'
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
import AdminAdd from '../../tabs/admin/Add'

const STUDENT = [
  { key: 'dash', label: 'Dashboard', short: 'Dashboard', icon: I.dashboard, C: StudentDashboard },
  { key: 'report', label: 'My report', short: 'Report', icon: I.report, eyebrow: 'MY REPORT', C: StudentReport },
  { key: 'ach', label: 'Achievements', short: 'Achievements', icon: I.achievements, eyebrow: 'CERTIFICATES & MILESTONES', C: StudentAchievements },
  { key: 'profile', label: 'Profile', short: 'Profile', icon: I.profile, eyebrow: 'UNIVERSITY RECORD', C: StudentProfile },
]
const COACH = [
  { key: 'entry', label: 'Coach Entry', short: 'Entry', icon: I.entry, eyebrow: 'RECORD RESULTS', C: CoachEntry },
  { key: 'footage', label: 'Match Footage', short: 'Footage', icon: I.footage, eyebrow: 'MATCH VIDEO', C: CoachFootage },
  { key: 'cards', label: 'Match Cards', short: 'Cards', icon: I.report, eyebrow: 'READ FROM A PHOTO', C: CoachCards },
  { key: 'squad', label: 'Dashboard', short: 'Squad', icon: I.squad, eyebrow: 'TODAY’S BRIEF', C: CoachSquad },
  { key: 'weights', label: 'Weights', short: 'Weights', icon: I.weights, eyebrow: 'POSITION WEIGHTS', C: CoachWeights },
  { key: 'ai', label: 'AI Training', short: 'AI', icon: I.ai, eyebrow: 'THE MODEL', C: CoachTraining },
]
const ADMIN = [{ key: 'add', label: 'Add Student', short: 'Add', icon: I.add, eyebrow: 'BY HAND · NO LOGIN', C: AdminAdd }, ...COACH]

// phones only: the web build (used for previews) has no notifications to have been tapped
const useTapped = Platform.OS === 'web' ? () => null : useLastNotificationResponse

/* The signed-in app: one screen per tab under the glass tab bar. A tab stays mounted once
   visited, so going back to it keeps its scroll and whatever was typed. */
export default function Home() {
  const s = useSession()
  const { c, reduced } = useTheme()
  const tabs = s.role === 'student' ? STUDENT : s.isAdmin ? ADMIN : COACH
  const [active, setActive] = useState(() => (s.role === 'student' ? 0 : tabs.findIndex(t => t.key === 'squad')))
  const [seen, setSeen] = useState(() => new Set([active]))
  const behind = useRef(null)
  // a page further in can send the app to a tab: "Record their results" → Entry, with them picked
  const params = useLocalSearchParams()
  useEffect(() => { if (params.tab) go(params.tab) }, [params.tab, params.at])

  // notifications: this phone's token to the server (once the person has said yes), and
  // the "why we ask" screen the first time round
  useEffect(() => {
    registerPush(false)
    const t = setTimeout(() => primed('notifications').then(done => { if (!done) router.push({ pathname: '/primer', params: { kind: 'notifications' } }) }), 1500)
    return () => clearTimeout(t)
  }, [])

  // a tapped notification opens what it is about
  const tapped = useTapped()
  useEffect(() => {
    const d = tapped?.notification?.request?.content?.data
    if (!d) return
    if (d.tab) go(d.tab)
    if (d.video && s.role === 'student') router.push({ pathname: '/videos/[vid]', params: { vid: d.video } })
    if (d.student && s.role === 'coach') router.push({ pathname: '/student/[id]', params: { id: d.student } })
  }, [tapped])

  const go = key => {
    const i = typeof key === 'number' ? key : tabs.findIndex(t => t.key === key || t.label === key)
    if (i < 0) return
    setSeen(v => (v.has(i) ? v : new Set(v).add(i)))
    setActive(i)
  }

  return (
    <View style={{ flex: 1, backgroundColor: c.bg }}>
      <BlurTargetView ref={behind} style={{ flex: 1 }}>
        {tabs.map((tab, i) => seen.has(i) && (
          <View key={tab.key} style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, display: i === active ? 'flex' : 'none' }}>
            <tab.C tab={tab} go={go} active={i === active} params={params} />
          </View>
        ))}
      </BlurTargetView>
      <TabBar tabs={tabs} active={active} onChange={go} blurTarget={behind} reduced={reduced} />
    </View>
  )
}
