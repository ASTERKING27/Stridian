import { useCallback, useEffect, useState } from 'react'
import { RefreshControl, View } from 'react-native'
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router'
import { api } from '../../../lib/api'
import { useTheme } from '../../../lib/theme'
import { Back, Btn, Eyebrow, H1, I, Icon, Lap, Mono, Note, Screen, T, Tile } from '../../../ui'
import ClipRow from '../../../ui/ClipRow'

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
      {(list ?? []).map(v => <ClipRow key={v.id} v={v} studentId={id} />)}
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
