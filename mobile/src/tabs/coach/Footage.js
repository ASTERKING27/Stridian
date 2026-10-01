import { useEffect } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { api, utc } from '../../lib/api'
import { useBackInView, useData } from '../../lib/useData'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { Btn, Eyebrow, H1, I, Icon, Lap, Mono, Note, OfflineBar, Screen, T, Tag, Tile, Top } from '../../ui'

export const CLIP_WORD = { queued: 'QUEUED', processing: 'PROCESSING', done: 'READY', failed: 'FAILED', unavailable: 'NOT ANALYSED', uploading: 'UPLOADING' }
export const inFlight = status => status === 'queued' || status === 'processing'
const day = d => utc(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase()
const dur = s => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '')

/* Match footage: a clip with the whole squad in it. The analysis computer follows every
   player; the coach then taps their students on a frame (match/[id]). */
export default function Footage({ active }) {
  const s = useSession()
  const { c } = useTheme()
  const clips = useData(api.matches, [s.coach?.sport])
  useBackInView(clips.reload, active)
  const waiting = active && (clips.data ?? []).some(x => inFlight(x.status))
  useEffect(() => {
    if (!waiting) return undefined
    const t = setInterval(clips.reload, 8000)
    return () => clearInterval(t)
  }, [waiting, clips.reload])

  const add = () => router.push({ pathname: '/videos/add', params: { match: '1' } })
  const list = clips.data
  return (
    <View style={{ flex: 1 }}>
      {clips.error?.offline && <OfflineBar note={list ? 'SHOWING WHAT WAS LOADED' : 'NOTHING LOADED YET'} onRetry={clips.refresh} />}
      <Screen bottom={110} gap={16} refreshing={clips.refreshing} onRefresh={clips.refresh}>
        <Top context={contextLine(s)} />
        {clips.error?.offline && <View style={{ height: 40 }} />}
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <View style={{ gap: 8 }}>
            <Eyebrow>MATCH VIDEO</Eyebrow>
            <H1>Match footage</H1>
          </View>
          {list?.length > 0 && <Btn kind="icon" icon={I.add} accessibilityLabel="Upload a match" onPress={add} />}
        </View>
        {clips.error && !clips.error.offline && <Note>{clips.error.message}</Note>}
        {!list && !clips.error && <Lap size={28} />}

        {list?.length === 0 && (
          <>
            <Tile w={132} filled={false} dashed><Icon d={I.footage} size={55} sw={1.3} /></Tile>
            <View style={{ gap: 10 }}>
              <T font="title" size={22}>No match clips yet</T>
              <T size={15} color="ink2" style={{ lineHeight: 22 }}>
                Film a match or a snippet with several players in view. Every player is followed; you then tap your students once and
                their movement — distance, sprints, positioning — joins their report.
              </T>
            </View>
            <Btn label="Upload a match" icon={I.upload} onPress={add} />
          </>
        )}

        <View>
        {(list ?? []).map(x => (
          <Pressable key={x.id} onPress={() => router.push({ pathname: '/match/[id]', params: { id: x.id } })} accessibilityRole="button"
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
        ))}
        </View>
      </Screen>
    </View>
  )
}
