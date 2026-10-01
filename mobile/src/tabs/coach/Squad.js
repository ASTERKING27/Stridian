import { useMemo, useState } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { api, shortUnits } from '../../lib/api'
import { useBackInView, useData } from '../../lib/useData'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { Btn, Eyebrow, H1, I, IconBtn, Mono, Note, OfflineBar, PersonRow, Placeholder, Screen, SearchField, Seg, T, Tag, Top } from '../../ui'
import { CertRow } from '../student/Achievements'

// "RA…0214 · WINGER · NO RESULTS" — a squad row's second line
export function metaOf(s) {
  return [s.ra_number ? `RA…${s.ra_number.slice(-4)}` : 'NO RA NUMBER',
          s.verified_position || s.declared_position || 'NO POSITION',
          !s.has_results && 'NO RESULTS',
          s.achievements_pending > 0 && `${s.achievements_pending} TO CHECK`].filter(Boolean).join(' · ').toUpperCase()
}
export const openStudent = id => router.push({ pathname: '/student/[id]', params: { id } })

/* The coach's home (Coach board, 08): today's brief from the second coach, certificates
   waiting, then the squad — pending first to verify, search by name or RA number. */
export default function Squad({ go, active }) {
  const s = useSession()
  const sport = s.coach?.sport
  const squad = useData(api.students, [sport])
  const feed = useData(api.coachFeed, [sport])
  const certs = useData(() => api.achievements('pending'), [sport])
  const [q, setQ] = useState('')
  const [show, setShow] = useState('all')
  const [all, setAll] = useState(false)
  const reload = () => Promise.all([squad.reload(), feed.reload(), certs.reload()])
  useBackInView(reload, active)

  const list = squad.data
  const counts = useMemo(() => ({
    verified: (list ?? []).filter(x => x.status === 'verified').length,
    pending: (list ?? []).filter(x => x.status !== 'verified').length,
  }), [list])
  const visible = useMemo(() => {
    const term = q.trim().toLowerCase()
    return (list ?? [])
      .filter(x => show === 'all' || (show === 'verified') === (x.status === 'verified'))
      .filter(x => !term || x.name.toLowerCase().includes(term) || (x.ra_number ?? '').toLowerCase().includes(term))
  }, [list, q, show])
  // the certificates are listed in full below, so the brief needn't count them too
  const items = (feed.data?.feed ?? []).filter(f => f.kind !== 'certs' || !certs.data?.length)
  const missing = s.coach && (!s.coach.employee_id || !s.coach.phone)
  const offline = squad.error?.offline

  return (
    <View style={{ flex: 1 }}>
      {offline && <OfflineBar note={list ? 'SHOWING WHAT WAS LOADED' : 'NOTHING LOADED YET'} onRetry={reload} />}
      <Screen bottom={110} gap={18} refreshing={squad.refreshing} onRefresh={() => { squad.refresh(); feed.reload(); certs.reload() }}>
        <Top context={contextLine(s)} onContext={s.isAdmin ? () => router.push('/sport') : undefined} />
        {offline && <View style={{ height: 40 }} />}
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <View style={{ gap: 8 }}>
            <Eyebrow>{list ? `${list.length} PLAYER${list.length === 1 ? '' : 'S'}` : 'YOUR SQUAD'}</Eyebrow>
            <H1>Squad</H1>
          </View>
          <IconBtn icon={I.profile} label="Your details" onPress={() => router.push('/coach-details')} style={{ alignItems: 'flex-end' }} />
        </View>
        {squad.error && !offline && <Note>{squad.error.message}</Note>}

        {missing && (
          <Pressable onPress={() => router.push('/coach-details')} accessibilityRole="button">
            <Note tone="info">Add your employee ID and mobile — the sports directorate keeps them for every coach.</Note>
          </Pressable>
        )}

        {items.length > 0 && (
          <View>
            <Eyebrow style={{ paddingBottom: 6 }}>TODAY’S BRIEF</Eyebrow>
            {(all ? items : items.slice(0, 3)).map(f => <BriefItem key={f.kind} f={f} go={go} />)}
            {items.length > 3 && <Btn kind="text" label={all ? 'Show less' : `Show all ${items.length}`} onPress={() => setAll(a => !a)} />}
          </View>
        )}

        {(certs.data ?? []).length > 0 && (
          <View>
            <Eyebrow style={{ paddingBottom: 6 }}>CERTIFICATES TO CHECK · {certs.data.length}</Eyebrow>
            {certs.data.map(a => <CertRow key={a.id} item={a} as={s.isAdmin ? 'admin' : 'coach'} studentName={a.student_name} named />)}
          </View>
        )}

        <View style={{ gap: 14 }}>
          <SearchField value={q} onChangeText={setQ} />
          <Seg options={[['pending', `PENDING · ${counts.pending}`], ['verified', `VERIFIED · ${counts.verified}`], ['all', 'ALL']]}
               value={show} onChange={setShow} />
        </View>

        {!list && !squad.error && (
          <View style={{ gap: 12 }}>{[0, 1, 2, 3, 4].map(i => <Placeholder key={i} h={50} />)}</View>
        )}
        {list && visible.length === 0 && (
          <View style={{ gap: 10, paddingVertical: 8 }}>
            <T font="semi" size={16}>{list.length === 0 ? 'Nobody here yet' : 'Nobody matches'}</T>
            <T size={14} color="ink2" style={{ lineHeight: 20 }}>
              {list.length === 0
                ? `Students enrol themselves from the app or the website with their university email and your ${sport} enrolment code.`
                : 'Try a different name or filter.'}
            </T>
            {list.length === 0 && <Btn kind="secondary" small label="Show the enrolment code" onPress={() => router.push('/coach-details')} />}
          </View>
        )}
        {visible.length > 0 && (
          <View>
            {visible.map((x, i) => (
              <PersonRow key={x.id} name={x.name} meta={metaOf(x)} onPress={() => openStudent(x.id)} last={i === visible.length - 1}
                         right={<Tag label={x.status === 'verified' ? 'VERIFIED' : x.category ? 'PENDING' : 'NO TEAM'}
                                     on={x.status === 'verified'} dashed={x.status !== 'verified' && !x.category} />} />
            ))}
          </View>
        )}
      </Screen>
    </View>
  )
}

// One line of the brief: what, why, and the people it is about — each opens that player.
function BriefItem({ f, go }) {
  const { c } = useTheme()
  return (
    <View style={{ paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.line, gap: 6 }}>
      <T font="semi" size={15}>{shortUnits(f.title)}</T>
      <T size={13.5} color="ink2" style={{ lineHeight: 19 }}>{shortUnits(f.body)}</T>
      {f.people.length > 0 && (
        <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 6, paddingTop: 4 }}>
          {f.people.slice(0, 6).map(p => (
            <Pressable key={p.id} onPress={() => openStudent(p.id)} accessibilityRole="button"
                       style={({ pressed }) => ({ borderWidth: 1, borderColor: c.ink, paddingVertical: 6, paddingHorizontal: 9,
                                                  backgroundColor: pressed ? c.soft : 'transparent' })}>
              <T font="medium" size={12.5}>{p.name}{p.text ? <T size={12} color="ink2">{`  ${shortUnits(p.text)}`}</T> : null}</T>
            </Pressable>
          ))}
          {f.people.length > 6 && <Mono size={10.5} color="ink2" style={{ alignSelf: 'center' }}>+{f.people.length - 6} MORE</Mono>}
        </View>
      )}
      {f.tab === 'coach' && (
        <Btn kind="text" label="Open Coach Entry" iconRight={I.next} onPress={() => go('entry')}
             style={{ alignSelf: 'flex-start', paddingHorizontal: 0 }} />
      )}
    </View>
  )
}
