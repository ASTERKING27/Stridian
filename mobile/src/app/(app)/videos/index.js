import { useCallback, useEffect, useState } from 'react'
import { Pressable, RefreshControl, View } from 'react-native'
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router'
import { api, utc } from '../../../lib/api'
import { useTheme } from '../../../lib/theme'
import { Back, Btn, Eyebrow, H1, I, Icon, Lap, Mono, Note, Screen, T, Tile } from '../../../ui'

const KEEP_DAYS = 30
const STEP = { queued: 0, processing: 1, done: 2 }
const WORD = { queued: 'QUEUED', processing: 'PROCESSING', done: 'READY', failed: 'FAILED', unavailable: 'NOT ANALYSED', uploading: 'UPLOADING' }
const day = d => utc(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase()
const dur = s => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '')

/* Upload board, 04 (and States, 01 when empty): every drill clip and where it is —
   queued, being analysed on the coach's computer, or ready. `id`: a coach looking at
   one student's clips. */
export default function Videos() {
  const { id, name } = useLocalSearchParams()
  const { c } = useTheme()
  const [list, setList] = useState(null)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const load = useCallback(() => (id ? api.videos(id) : api.myVideos()).then(v => { setList(v); setError(null) }, setError), [id])
  useFocusEffect(useCallback(() => { load() }, [load]))
  // while anything waits for the analysis computer, look again every few seconds
  const waiting = list?.some(v => v.status === 'queued' || v.status === 'processing')
  useEffect(() => {
    if (!waiting) return undefined
    const t = setInterval(load, 8000)
    return () => clearInterval(t)
  }, [waiting, load])

  const add = () => router.push({ pathname: '/videos/add', params: id ? { id } : {} })
  return (
    <Screen gap={16} refreshControl={<RefreshControl refreshing={refreshing} tintColor={c.ink} colors={[c.ink]} progressBackgroundColor={c.bg}
                                                     onRefresh={async () => { setRefreshing(true); await load(); setRefreshing(false) }} />}>
      <Back label={id ? (name || 'Back') : 'My report'} onPress={() => router.back()} />
      <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' }}>
        <View style={{ gap: 8 }}>
          <Eyebrow>DRILL VIDEOS</Eyebrow>
          <H1>{id ? 'Their clips' : 'Your clips'}</H1>
        </View>
        {list?.length > 0 && <Btn kind="icon" icon={I.add} accessibilityLabel="Add a video" onPress={add} />}
      </View>
      {error && <Note>{error.message}</Note>}
      {!list && !error && <Lap size={28} />}

      {list?.length === 0 && (
        <>
          <Tile w={132} filled={false} dashed><Icon d={I.footage} size={55} sw={1.3} /></Tile>
          <View style={{ gap: 10 }}>
            <T font="title" size={22}>No clips yet</T>
            <T size={15} color="ink2" style={{ lineHeight: 22 }}>
              Film one drill side-on and Stridian reads {id ? 'their' : 'your'} technique — jump height, knee angles, left–right balance.
            </T>
          </View>
          <View>
            <Fact a="Takes about" b="10 SECONDS OF VIDEO" />
            <Fact a="Results in" b="THE NEXT SESSION" />
          </View>
          <Btn label="Add the first video" icon={I.add} onPress={add} />
        </>
      )}

      {list?.length > 0 && (
        <View style={{ flexDirection: 'row', gap: 12, alignItems: 'flex-start', paddingVertical: 12, paddingHorizontal: 14,
                       borderWidth: 1, borderColor: c.ink, borderStyle: 'dashed' }}>
          <View style={{ width: 8, height: 8, backgroundColor: c.ink, marginTop: 5 }} />
          <T size={13} style={{ flex: 1, lineHeight: 19 }}>
            Clips are analysed on the coach’s computer. They wait in line and run in its next session — no need to keep the app open.
          </T>
        </View>
      )}
      {(list ?? []).map(v => <Clip key={v.id} v={v} studentId={id} />)}
    </Screen>
  )
}

function Fact({ a, b }) {
  const { c } = useTheme()
  return (
    <View style={{ flexDirection: 'row', justifyContent: 'space-between', paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line }}>
      <T size={14}>{a}</T><Mono size={13}>{b}</Mono>
    </View>
  )
}

function Clip({ v, studentId }) {
  const { c } = useTheme()
  const at = STEP[v.status]
  const ready = v.status === 'done'
  const left = KEEP_DAYS - Math.floor((Date.now() - utc(v.created_at)) / 864e5)
  const expiry = v.video_deleted_at ? 'VIDEO DELETED · RESULTS KEPT' : `DELETES IN ${Math.max(0, left)} DAY${left === 1 ? '' : 'S'}`
  const detail = ready ? 'VIEW ANALYSIS →' : v.status === 'queued' ? 'WAITING FOR THE ANALYSIS COMPUTER'
    : v.status === 'processing' ? 'BEING ANALYSED' : (v.message ?? '').toUpperCase().slice(0, 60)
  const open = () => router.push({ pathname: '/videos/[vid]', params: { vid: v.id, ...(studentId ? { id: studentId } : {}), label: v.label ?? v.original_name, at: v.created_at } })
  return (
    <Pressable disabled={!ready} onPress={open} accessibilityRole={ready ? 'button' : undefined}
               style={({ pressed }) => ({ gap: 10, paddingTop: 13, borderTopWidth: 1, borderTopColor: c.line, backgroundColor: pressed ? c.soft : 'transparent' })}>
      <View style={{ flexDirection: 'row', gap: 12, alignItems: 'center' }}>
        <View style={{ width: 44, height: 44, borderWidth: 1, borderColor: c.line, alignItems: 'center', justifyContent: 'center' }}>
          <Icon d={I.footage} size={20} color={c.ink2} />
        </View>
        <View style={{ flex: 1, gap: 4 }}>
          <T font="semi" size={15} numberOfLines={1}>{v.label || v.original_name}</T>
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.63 }}>{[day(v.created_at), dur(v.duration_sec)].filter(Boolean).join(' · ')}</Mono>
        </View>
        <View style={{ paddingVertical: 5, paddingHorizontal: 8, borderWidth: 1, borderColor: c.ink, backgroundColor: ready ? c.ink : 'transparent',
                       borderStyle: v.status === 'failed' ? 'dashed' : 'solid' }}>
          <Mono size={10} color={ready ? c.bg : c.ink} style={{ letterSpacing: 1 }}>{WORD[v.status] ?? v.status.toUpperCase()}</Mono>
        </View>
      </View>
      {at != null && (
        <View style={{ flexDirection: 'row', gap: 4 }}>
          {['QUEUED', 'PROCESSING', 'READY'].map((label, i) => (
            <View key={label} style={{ flex: 1, gap: 5 }}>
              <View style={{ height: 4, backgroundColor: i < at || (i === at && at !== 1) ? c.ink : i === at ? 'transparent' : c.line,
                             borderWidth: i === at && at === 1 ? 1 : 0, borderColor: c.ink, borderStyle: 'dashed' }} />
              <Mono size={9} color={i <= at ? 'ink' : 'ink2'} style={{ letterSpacing: 0.9 }}>{label}</Mono>
            </View>
          ))}
        </View>
      )}
      <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 12, paddingBottom: 2 }}>
        <Mono size={10} color={ready ? 'ink' : 'ink2'} style={{ letterSpacing: 0.6, flex: 1 }} numberOfLines={2}>{detail}</Mono>
        <Mono size={10} color={v.video_deleted_at ? 'ink' : 'ink2'} style={{ letterSpacing: 0.6 }}>{expiry}</Mono>
      </View>
    </Pressable>
  )
}
