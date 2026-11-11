import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { utc } from '../lib/api'
import { useTheme } from '../lib/theme'
import { I, Icon, Mono, T } from './index'

const KEEP_DAYS = 30
const STEP = { queued: 0, processing: 1, done: 2 }
const WORD = { queued: 'QUEUED', processing: 'PROCESSING', done: 'READY', failed: 'FAILED', unavailable: 'NOT ANALYSED', uploading: 'UPLOADING' }
const day = d => utc(d).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase()
const dur = s => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '')

/* One drill clip and where it is — queued, being analysed on the analysis computer, or
   ready to open (Upload board, 04). `who`: the student's name, in a list of the squad's clips. */
export default function ClipRow({ v, studentId, who }) {
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
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.63 }} numberOfLines={1}>
            {[who?.toUpperCase(), day(v.created_at), dur(v.duration_sec)].filter(Boolean).join(' · ')}
          </Mono>
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
