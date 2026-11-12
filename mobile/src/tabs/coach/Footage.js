import { useEffect, useRef, useState } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { api, utc } from '../../lib/api'
import { useBackInView, useData } from '../../lib/useData'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { Btn, Eyebrow, H1, I, Icon, Lap, Mono, OfflineBar, Screen, Seg, Swap, T, Tag, Tile, Top } from '../../ui'
import ClipRow from '../../ui/ClipRow'
import { LoadError } from '../../ui/States'

export const CLIP_WORD = { queued: 'QUEUED', processing: 'PROCESSING', done: 'READY', failed: 'FAILED', unavailable: 'NOT ANALYSED', uploading: 'UPLOADING' }
export const inFlight = status => status === 'queued' || status === 'processing'
const day = d => utc(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase()
const dur = s => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '')
const first = name => (name ?? '').split(' ')[0]

/* All the squad's video, in two halves. Match footage: a clip with the whole squad in it;
   the analysis computer follows every player and the coach taps who's who (match/[id]).
   Drill footage: one player doing one drill, for pose analysis. Coach Entry sends a coach
   here, on the drills, for the student they just recorded. */
export default function Footage({ active, ask }) {
  const s = useSession()
  const sport = s.coach?.sport
  const [section, setSection] = useState('match')
  const [who, setWho] = useState(null)              // { id, name }: the drill list narrowed to one student
  const matches = useData(api.matches, [sport])
  const drills = useData(api.squadVideos, [sport])
  const cur = section === 'match' ? matches : drills
  useBackInView(() => { matches.reload(); drills.reload() }, active)

  // sent here from Coach Entry: the drills, for that student — no slide, the tab is sweeping in
  const [quiet, setQuiet] = useState(false)
  useEffect(() => {
    if (ask?.section !== 'drill') return
    setQuiet(true)
    setSection('drill')
    setWho(ask.student ? { id: Number(ask.student), name: ask.name } : null)
  }, [ask?.at])
  const pick = v => { setQuiet(false); setSection(v) }
  // an admin switching sport: that student isn't in this squad
  const shownSport = useRef(sport)
  useEffect(() => { if (shownSport.current !== sport) { shownSport.current = sport; setWho(null) } }, [sport])

  // while anything waits for the analysis computer, look again every few seconds
  const waiting = active && (cur.data ?? []).some(x => inFlight(x.status))
  useEffect(() => {
    if (!waiting) return undefined
    const t = setInterval(cur.reload, 8000)
    return () => clearInterval(t)
  }, [waiting, cur.reload])

  const addMatch = () => router.push({ pathname: '/videos/add', params: { match: '1' } })
  const addDrill = () => router.push({ pathname: '/videos/add', params: who ? { id: who.id, name: who.name } : {} })
  const list = cur.data
  const shown = section === 'drill' && who ? (list ?? []).filter(v => v.student_id === who.id) : list
  return (
    <View style={{ flex: 1 }}>
      {cur.error?.offline && <OfflineBar note={list ? 'SHOWING WHAT WAS LOADED' : 'NOTHING LOADED YET'} onRetry={cur.refresh} />}
      <Screen bottom={110} gap={16} refreshing={cur.refreshing} onRefresh={cur.refresh}>
        <Top context={contextLine(s)} />
        {cur.error?.offline && <View style={{ height: 40 }} />}
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <View style={{ gap: 8 }}>
            <Eyebrow>MATCH AND DRILL VIDEO</Eyebrow>
            <H1>Footage</H1>
          </View>
          {shown?.length > 0 && (
            <Btn kind="icon" icon={I.add} accessibilityLabel={section === 'match' ? 'Upload a match' : 'Add a drill clip'}
                 onPress={section === 'match' ? addMatch : addDrill} />
          )}
        </View>
        <Seg options={[['match', 'MATCH FOOTAGE'], ['drill', 'DRILL FOOTAGE']]} value={section} onChange={pick} />
        {/* the chosen half slides in from its side */}
        <Swap k={section} dir={quiet ? 0 : section === 'drill' ? 1 : -1} style={{ gap: 16 }}>
          <LoadError error={cur.error} onRetry={cur.refresh} hasData={!!list} />
          {!list && !cur.error && <Lap size={28} />}

          {section === 'drill' && who && (
            <View style={{ gap: 10 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10 }}>
                <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84, flex: 1 }}>SHOWING {who.name?.toUpperCase()}</Mono>
                <Btn kind="text" label="Show everyone" onPress={() => setWho(null)} style={{ height: 36, paddingHorizontal: 0 }} />
              </View>
              {shown?.length > 0 && <Btn label={`Film a drill for ${first(who.name)}`} icon={I.camera} onPress={addDrill} />}
            </View>
          )}

          {shown?.length === 0 && (section === 'match' ? (
            <Empty title="No match clips yet" label="Upload a match" onPress={addMatch}
                   text="Film a match or a snippet with several players in view. Every player is followed; you then tap your students once and their movement — distance, sprints, positioning — joins their report." />
          ) : (
            <Empty title={who ? `No drill clips of ${first(who.name)} yet` : 'No drill clips yet'}
                   label={who ? `Film a drill for ${first(who.name)}` : 'Film a drill'} onPress={addDrill}
                   text="Optional — the report works from the tests alone. Film one player doing one drill, side-on, and Stridian reads their technique: jump height, knee angles, left–right balance." />
          ))}

          {section === 'match' && <View>{(shown ?? []).map(x => <MatchRow key={x.id} x={x} />)}</View>}
          {section === 'drill' && (
            <View>{(shown ?? []).map(v => <ClipRow key={v.id} v={v} studentId={v.student_id} who={who ? null : v.student_name} />)}</View>
          )}
        </Swap>
      </Screen>
    </View>
  )
}

function Empty({ title, text, label, onPress }) {
  return (
    <>
      <Tile w={132} filled={false} dashed><Icon d={I.footage} size={55} sw={1.3} /></Tile>
      <View style={{ gap: 10 }}>
        <T font="title" size={22}>{title}</T>
        <T size={15} color="ink2" style={{ lineHeight: 22 }}>{text}</T>
      </View>
      <Btn label={label} icon={I.upload} onPress={onPress} />
    </>
  )
}

function MatchRow({ x }) {
  const { c } = useTheme()
  return (
    <Pressable onPress={() => router.push({ pathname: '/match/[id]', params: { id: x.id } })} accessibilityRole="button"
               style={({ pressed }) => ({ flexDirection: 'row', gap: 12, alignItems: 'center', paddingVertical: 12,
                                          borderTopWidth: 1, borderTopColor: c.line, backgroundColor: pressed ? c.soft : 'transparent' })}>
      <View style={{ width: 44, height: 44, borderWidth: 1, borderColor: c.line, alignItems: 'center', justifyContent: 'center' }}>
        <Icon d={I.footage} size={20} color={c.ink2} />
      </View>
      <View style={{ flex: 1, gap: 4 }}>
        <T font="semi" size={15} numberOfLines={1}>{x.label || x.original_name}</T>
        <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.63 }} numberOfLines={1}>
          {[day(x.created_at), dur(x.duration_sec), `ATTACKING ${x.attack_direction === 'left' ? '←' : '→'}`].filter(Boolean).join(' · ')}
        </Mono>
        {x.status === 'failed' && !!x.message && <T size={12} color="ink2" numberOfLines={2}>{x.message}</T>}
      </View>
      <Tag label={CLIP_WORD[x.status] ?? x.status.toUpperCase()} on={x.status === 'done'} dashed={x.status === 'failed'} />
    </Pressable>
  )
}
