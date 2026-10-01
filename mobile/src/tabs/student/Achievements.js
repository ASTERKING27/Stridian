import { useCallback, useState } from 'react'
import { Pressable, RefreshControl, View } from 'react-native'
import { router, useFocusEffect } from 'expo-router'
import { api } from '../../lib/api'
import { chooseCertificate } from '../../lib/media'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Btn, Eyebrow, H1, I, Icon, Mono, Note, OfflineBar, Screen, T, Top } from '../../ui'
import Badge from '../../ui/Badge'
import { levelWord } from '../../ui/DetailsForm'

export const CERT_STATUS = { draft: 'NOT SENT', pending: 'WITH YOUR COACH', verified: 'VERIFIED', rejected: 'NEEDS FIXING' }
const STREAKS = { streak_2: 2, streak_4: 4, streak_8: 8 }

// Badges (Badges board), the focus streak, and certificates for the coach to verify.
export default function Achievements() {
  const s = useSession()
  const { c } = useTheme()
  const [coach, setCoach] = useState(null)
  const [list, setList] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const [refreshing, setRefreshing] = useState(false)

  const load = useCallback(() => Promise.all([
    api.studentCoach().then(setCoach),
    api.myAchievements().then(setList),
  ]).then(() => setError(null), setError), [])
  useFocusEffect(useCallback(() => { load() }, [load]))

  async function add() {
    setBusy(true)
    try {
      const file = await chooseCertificate()
      if (file) {
        const item = await api.addMyAchievement(file.uri, file.type, file.name)
        haptic.success()
        router.push({ pathname: '/achievement', params: { item: JSON.stringify(item) } })
      }
    } catch (err) { haptic.error(); setError(err) }
    setBusy(false)
  }

  const badges = coach?.badges ?? []
  const earned = badges.filter(b => b.earned).length
  const streak = coach?.focus?.streak ?? 0
  return (
    <View style={{ flex: 1 }}>
      {error?.offline && <OfflineBar onRetry={load} />}
      <Screen bottom={110} gap={22}
              refreshControl={<RefreshControl refreshing={refreshing} tintColor={c.ink} colors={[c.ink]} progressBackgroundColor={c.bg}
                                              onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} />}>
        <Top context={contextLine(s)} />
        {error?.offline && <View style={{ height: 40 }} />}
        {error && !error.offline && <Note>{error.message}</Note>}

        <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end' }}>
          <View style={{ gap: 8 }}>
            <Eyebrow>ACHIEVEMENTS · BADGES</Eyebrow>
            <H1>{coach && earned === 0 ? 'Nothing here yet' : 'Badges'}</H1>
          </View>
          {coach && <Mono size={12} color="ink2">{earned} / {badges.length} EARNED</Mono>}
        </View>
        {coach && earned === 0 && (
          <T size={15} color="ink2" style={{ lineHeight: 22 }}>
            Badges unlock as you go. The first one, <T font="semi" size={15}>First rep</T>, arrives with your first test result.
          </T>
        )}

        <View style={{ flexDirection: 'row', flexWrap: 'wrap', rowGap: 26 }}>
          {badges.map(b => {
            const need = STREAKS[b.id]
            const going = need && !b.earned && streak > 0
            return (
              <View key={b.id} style={{ width: '33.33%', paddingHorizontal: 4 }}>
                <Badge badge={b} size={72} progress={going ? streak / need : 0} prog={going ? `${streak} / ${need} WEEKS` : ''} />
              </View>
            )
          })}
        </View>

        {coach?.focus && (
          <Pressable onPress={() => router.push('/streak')} accessibilityRole="button"
                     style={({ pressed }) => ({ borderWidth: 1, borderColor: c.ink, padding: 16, flexDirection: 'row',
                                                alignItems: 'center', gap: 16, backgroundColor: pressed ? c.soft : 'transparent' })}>
            <T font="display" size={56} style={{ lineHeight: 60 }}>{streak}</T>
            <View style={{ flex: 1, gap: 4 }}>
              <Eyebrow>FOCUS STREAK · {coach.focus.label.toUpperCase()}</Eyebrow>
              <T font="title" size={17}>{streak === 1 ? 'week in a row' : 'weeks in a row'}</T>
            </View>
            <Icon d={I.next} size={18} />
          </Pressable>
        )}

        <View>
          <Eyebrow style={{ paddingBottom: 8 }}>CERTIFICATES</Eyebrow>
          {list?.length === 0 && (
            <View style={{ borderWidth: 1, borderColor: c.ink, paddingVertical: 14, paddingHorizontal: 16, gap: 10 }}>
              <Eyebrow>A HEAD START</Eyebrow>
              <T size={15} style={{ lineHeight: 21 }}>
                Played at a zonal or state event? Add the certificate — once your coach verifies it, it counts.
              </T>
            </View>
          )}
          {(list ?? []).map(a => <CertRow key={a.id} item={a} />)}
        </View>
        <Btn label="Add a certificate" icon={I.add} busy={busy} busyLabel="Reading the certificate" onPress={add} />
      </Screen>
    </View>
  )
}

// `named`: a list across the squad, so each row says whose certificate it is
export function CertRow({ item, as = 'student', studentName, named }) {
  const { c } = useTheme()
  const st = item.status
  const sub = [named && studentName, levelWord(item.level), item.year, item.result].filter(Boolean).join(' · ') || 'No level or year yet'
  return (
    <Pressable accessibilityRole="button"
               onPress={() => router.push({ pathname: '/achievement', params: { item: JSON.stringify(item), as, studentName } })}
               style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12,
                                          borderTopWidth: 1, borderTopColor: c.line, backgroundColor: pressed ? c.soft : 'transparent' })}>
      <View style={{ flex: 1, gap: 3 }}>
        <T size={15}>{item.title || 'Certificate — details to fill in'}</T>
        <T size={12} color="ink2">{sub}</T>
      </View>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 5, paddingVertical: 5, paddingHorizontal: 7,
                     backgroundColor: st === 'verified' ? c.ink : 'transparent',
                     borderWidth: 1, borderColor: st === 'draft' ? c.ink2 : c.ink, borderStyle: st === 'rejected' ? 'dashed' : 'solid' }}>
        {st === 'verified' && <Icon d={I.check} size={11} sw={2.4} color={c.bg} />}
        <Mono size={9.5} color={st === 'verified' ? c.bg : st === 'draft' ? c.ink2 : c.ink} style={{ letterSpacing: 0.95 }}>
          {as === 'student' ? CERT_STATUS[st] : st === 'pending' ? 'TO CHECK' : CERT_STATUS[st]}
        </Mono>
      </View>
    </Pressable>
  )
}
