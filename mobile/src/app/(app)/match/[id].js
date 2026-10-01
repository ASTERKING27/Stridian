import { useEffect, useMemo, useState } from 'react'
import { Alert, Image, Pressable, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api, authedSource } from '../../../lib/api'
import { useData } from '../../../lib/useData'
import { useTheme } from '../../../lib/theme'
import { haptic } from '../../../lib/haptics'
import { Back, Btn, Eyebrow, H1, Lap, Mono, Note, Screen, SearchField, T } from '../../../ui'
import { toast } from '../../../ui/Toast'
import { inFlight } from '../../../tabs/coach/Footage'

const PANEL = '#151514'
const CHALK = '#EEEDE8'
const dur = s => (s ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : '')

/* Who's who (Coach board, 10): every tracked player boxed on one frame of the match. Tap
   a box, pick the student, assign — their movement from this clip joins their report. */
export default function Match() {
  const { id } = useLocalSearchParams()
  const { c } = useTheme()
  const clip = useData(() => api.match(id), [id])
  const squad = useData(api.students, [])
  const [track, setTrack] = useState(null)
  const [who, setWho] = useState(null)
  const [q, setQ] = useState('')
  const [size, setSize] = useState({ w: 0, aspect: 16 / 9 })
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  const m = clip.data
  const waiting = inFlight(m?.status)
  useEffect(() => {
    if (!waiting) return undefined
    const t = setInterval(clip.reload, 8000)
    return () => clearInterval(t)
  }, [waiting, clip.reload])

  const byTrack = useMemo(() => Object.fromEntries((m?.tracks ?? []).map(t => [t.trackId, t])), [m])
  const people = useMemo(() => {
    const term = q.trim().toLowerCase()
    return (squad.data ?? []).filter(x => !term || x.name.toLowerCase().includes(term))
  }, [squad.data, q])

  if (!m) {
    return (
      <Screen>
        <Back label="Match footage" onPress={() => router.back()} />
        {clip.error ? <Note>{clip.error.message}</Note> : <Lap size={28} />}
      </Screen>
    )
  }

  const boxes = m.keyframeBoxes ?? []
  const t = track != null ? byTrack[track] : null
  const named = t?.assignedTo
  const picked = (squad.data ?? []).find(x => x.id === who)
  const identified = m.tracks.filter(x => x.assignedTo).length
  const h = size.w / size.aspect

  async function run(kind, action, done) {
    setBusy(kind)
    setError('')
    try {
      clip.setData(await action())
      haptic.success()
      if (done) toast(done)
    } catch (err) { haptic.error(); setError(err.message) }
    setBusy('')
  }
  const assign = () => run('assign', () => api.assignTrack(m.id, track, who),
    { title: `Track #${track} is ${picked.name}`, sub: 'THEIR MOVEMENT JOINS THEIR REPORT' }).then(() => setWho(null))
  const clear = () => run('clear', () => api.unassignTrack(m.id, track), { title: `Track #${track} cleared`, sub: named.name.toUpperCase() })
  const remove = () => Alert.alert('Delete this clip?', 'Every identification made on it goes too — and the movement it added to those reports.', [
    { text: 'Keep', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: async () => {
      try { await api.deleteMatch(m.id); haptic.success(); router.back() } catch (err) { setError(err.message) }
    } },
  ])

  return (
    <Screen gap={14}>
      <Back label="Match footage" onPress={() => router.back()} />
      <View style={{ gap: 8 }}>
        <Eyebrow>{[(m.label || m.original_name).toUpperCase(), dur(m.duration_sec), `${identified} OF ${m.tracks.length} NAMED`].filter(Boolean).join(' · ')}</Eyebrow>
        <H1>Who’s who?</H1>
      </View>
      {waiting && <Note tone="info">{m.message || 'Waiting for the analysis computer.'} This page refreshes by itself.</Note>}
      {!waiting && m.status !== 'done' && <Note>{m.message || 'This clip couldn’t be analysed.'}</Note>}
      {m.status === 'done' && m.tracks.length === 0 && <Note>{m.message || 'No player was followed for long enough.'}</Note>}
      {!!m.video_deleted_at && <Note tone="info">The video was removed 30 days after upload. Every identification is kept.</Note>}

      {m.status === 'done' && boxes.length > 0 && (
        <>
          <View onLayout={e => { const w = e.nativeEvent.layout.width; setSize(x => ({ ...x, w })) }}
                style={{ height: h || 200, backgroundColor: PANEL, overflow: 'hidden' }}>
            {size.w > 0 && (
              <Image source={authedSource(`/api/matches/${m.id}/keyframe`, String(m.id))} resizeMode="cover"
                     onLoad={e => { const src = e.nativeEvent.source; if (src?.width && src?.height) setSize(x => ({ ...x, aspect: src.width / src.height })) }}
                     style={{ position: 'absolute', left: 0, top: 0, width: size.w, height: h }}
                     accessibilityLabel="A frame of the match with every tracked player boxed" />
            )}
            {size.w > 0 && boxes.map(b => {
              const on = b.trackId === track
              const tr = byTrack[b.trackId]
              const name = tr?.assignedTo?.name
              return (
                <Pressable key={b.trackId} onPress={() => { haptic.tick(); setTrack(b.trackId); setWho(null) }}
                           accessibilityRole="button" accessibilityLabel={name ? `${name}, track ${b.trackId}` : `Track ${b.trackId}, not named`}
                           accessibilityState={{ selected: on }} hitSlop={6}
                           style={{ position: 'absolute', left: b.x * size.w, top: b.y * h, width: b.w * size.w, height: b.h * h,
                                    opacity: track == null || on ? 1 : 0.55 }}>
                  <View style={{ position: 'absolute', left: 0, top: 0, right: 0, bottom: 0, borderWidth: 1,
                                 borderStyle: name ? 'solid' : 'dashed', borderColor: on ? 'rgba(238,237,232,0.9)' : 'rgba(238,237,232,0.45)' }} />
                  {on && <Brackets />}
                </Pressable>
              )
            })}
            {/* the tags sit above the boxes, outside them, so a narrow box doesn't clip its name */}
            {size.w > 0 && boxes.map(b => {
              const name = byTrack[b.trackId]?.assignedTo?.name
              return (
                <Mono key={b.trackId} size={9} color={CHALK} pointerEvents="none"
                      style={{ position: 'absolute', left: b.x * size.w, top: b.y * h - 15, letterSpacing: 0.5,
                               opacity: track == null || b.trackId === track ? 1 : 0.55 }}>
                  {name ? name.split(' ')[0].toUpperCase() : `#${b.trackId}`}
                </Mono>
              )
            })}
            <Mono size={9.5} color="#9D9C96" style={{ position: 'absolute', right: 10, bottom: 8, letterSpacing: 0.95 }}>TAP A PLAYER</Mono>
          </View>

          <View style={{ gap: 4 }}>
            <Eyebrow>{t ? `TRACK #${t.trackId} · ${Math.round(t.context?.trackedSeconds ?? 0)} S IN VIEW` : 'NO PLAYER PICKED'}</Eyebrow>
            <T font="semi" size={17}>{!t ? 'Tap a player in the frame' : named ? `This is ${named.name}` : 'Who is this?'}</T>
          </View>

          {t && (
            <>
              {(squad.data ?? []).length > 8 && <SearchField value={q} onChangeText={setQ} placeholder="Name" />}
              <View accessibilityRole="radiogroup">
                {people.map(x => {
                  const on = who === x.id || (who == null && named?.studentId === x.id)
                  return (
                    <Pressable key={x.id} onPress={() => { haptic.tick(); setWho(x.id) }} accessibilityRole="radio" accessibilityState={{ checked: on }}
                               style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, borderTopWidth: 1, borderTopColor: c.line }}>
                      <View style={{ width: 18, height: 18, borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center', transform: [{ rotate: '45deg' }] }}>
                        <View style={{ width: 8, height: 8, backgroundColor: on ? c.ink : 'transparent' }} />
                      </View>
                      <T size={15} style={{ flex: 1 }}>{x.name}</T>
                      <Mono size={10} color="ink2" style={{ letterSpacing: 0.6 }}>{(x.verified_position || x.declared_position || '').toUpperCase()}</Mono>
                    </Pressable>
                  )
                })}
              </View>
              <Note>{error}</Note>
              {(!named || (picked && picked.id !== named.studentId)) && (
                <Btn label={picked ? `Assign to ${picked.name.split(' ')[0]}` : 'Pick a name'} disabled={!picked}
                     busy={busy === 'assign'} busyLabel="Assigning" onPress={assign} />
              )}
              {named && <Btn kind="text" label={`Not ${named.name.split(' ')[0]} — clear this track`} busy={busy === 'clear'} busyLabel="Clearing" onPress={clear} />}
            </>
          )}
        </>
      )}

      <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>
        Marking out the pitch for distances in metres is done on the website, on a computer.
      </T>
      {!t && <Note>{error}</Note>}
      <Btn kind="text" label="Delete this clip" onPress={remove} />
    </Screen>
  )
}

// The selected box's corners, drawn just outside it (Coach board, 10).
function Brackets() {
  const arm = { position: 'absolute', width: 10, height: 10, borderColor: CHALK }
  return (
    <View pointerEvents="none" style={{ position: 'absolute', left: -6, top: -6, right: -6, bottom: -6 }}>
      <View style={[arm, { left: 0, top: 0, borderLeftWidth: 2, borderTopWidth: 2 }]} />
      <View style={[arm, { right: 0, top: 0, borderRightWidth: 2, borderTopWidth: 2 }]} />
      <View style={[arm, { left: 0, bottom: 0, borderLeftWidth: 2, borderBottomWidth: 2 }]} />
      <View style={[arm, { right: 0, bottom: 0, borderRightWidth: 2, borderBottomWidth: 2 }]} />
    </View>
  )
}
