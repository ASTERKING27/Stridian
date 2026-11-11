import { useEffect, useMemo, useRef, useState } from 'react'
import { Pressable, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import Svg, { Circle, Defs, Line, Path, Pattern, Polyline, Rect } from 'react-native-svg'
import { api, utc } from '../../../lib/api'
import { useTheme } from '../../../lib/theme'
import { haptic } from '../../../lib/haptics'
import { measure, BONES } from '../../../lib/pose'
import { Back, Eyebrow, Lap, Mono, Note, Screen, T, Title } from '../../../ui'

const INK = '#EEEDE8', DIM = '#9D9C96', PANEL = '#151514'

/* Pose board, 05–06: the skeleton MediaPipe found, played back frame by frame over a
   timeline, with the knee angle, the hip's path and the phase of the movement — then the
   key moments and what the analysis measured. Only the skeleton is drawn: the video
   itself stays on the coach's computer and is deleted after 30 days. */
export default function PoseOverlay() {
  const { vid, id, label, at } = useLocalSearchParams()
  const { c, reduced } = useTheme()
  const [track, setTrack] = useState(null)
  const [video, setVideo] = useState(null)
  const [error, setError] = useState(null)
  const [frame, setFrame] = useState(0)
  const [playing, setPlaying] = useState(!reduced)
  const [layers, setLayers] = useState({ skel: true, ang: true, trail: true })
  const [box, setBox] = useState({ w: 0, h: 0 })
  const lastBin = useRef(-1)

  useEffect(() => {
    ;(id ? api.videoPose(vid) : api.myVideoPose(vid)).then(setTrack, setError)
    ;(id ? api.videos(id) : api.myVideos()).then(list => setVideo(list.find(v => String(v.id) === String(vid))), () => {})
  }, [vid, id])

  // everything worked out once per track: points per frame, the hips' path, phases, key moments
  const m = useMemo(() => track && measure(track), [track])
  const n = m?.frames.length ?? 0

  useEffect(() => {
    if (!playing || !n) return undefined
    const t = setInterval(() => setFrame(f => (f + 1) % n), 1000 / Math.max(4, Math.min(30, track.fps || 12)))
    return () => clearInterval(t)
  }, [playing, n, track])

  const seek = x => {
    const f = Math.max(0, Math.min(n - 1, Math.round((x / box.tw) * (n - 1))))
    const bin = Math.floor((f / n) * 16)
    if (bin !== lastBin.current) { lastBin.current = bin; haptic.tick() }
    setPlaying(false)
    setFrame(f)
  }

  const metrics = video?.metrics
  const drill = metrics?.drills?.[0]
  return (
    <Screen gap={16}>
      <Back label="Drill videos" onPress={() => router.back()} />
      <Title eyebrow={`${(label ?? '').toUpperCase()}${at ? ` · ${utc(at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase()}` : ''}`}>
        Pose overlay
      </Title>
      {error && <Note>{error.message}</Note>}
      {!track && !error && <Lap size={28} />}
      {m && (
        <>
          <View onLayout={e => setBox(b => ({ ...b, w: e.nativeEvent.layout.width, h: e.nativeEvent.layout.width * 392 / 346 }))}
                style={{ height: box.h || 300, backgroundColor: PANEL, overflow: 'hidden' }}
                accessible accessibilityLabel={`Skeleton, frame ${frame + 1} of ${n}${m.knee[frame] ? `, knee at ${m.knee[frame]} degrees` : ''}`}>
            {box.w > 0 && <Skeleton m={m} f={frame} w={box.w} h={box.h} layers={layers} />}
            <View style={{ position: 'absolute', left: 12, top: 12, paddingVertical: 4, paddingHorizontal: 7, borderWidth: 1, borderColor: 'rgba(238,237,232,0.5)' }}>
              <Mono size={9.5} color={INK} style={{ letterSpacing: 1.14 }}>MEDIAPIPE POSE · 33 POINTS</Mono>
            </View>
            <Mono size={9.5} color={DIM} style={{ position: 'absolute', right: 12, top: 12, letterSpacing: 0.95 }}>FRAME {frame + 1} / {n}</Mono>
            {!!m.phase[frame] && <Mono size={10} color={DIM} style={{ position: 'absolute', left: 12, bottom: 12, letterSpacing: 1.2 }}>{m.phase[frame]}</Mono>}
          </View>

          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
            <Pressable onPress={() => { haptic.tap(); setPlaying(p => !p) }} accessibilityRole="button" accessibilityLabel={playing ? 'Pause' : 'Play'}
                       style={{ width: 44, height: 44, backgroundColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
              <Svg width={20} height={20} viewBox="0 0 24 24">
                <Path d={playing ? 'M8 5v14M16 5v14' : 'M8 5v14l11-7L8 5Z'} fill={c.bg} stroke={c.bg} strokeWidth={2} />
              </Svg>
            </Pressable>
            <View onLayout={e => { const w = e.nativeEvent.layout.width; setBox(b => ({ ...b, tw: w })) }}
                  onStartShouldSetResponder={() => true} onMoveShouldSetResponder={() => true}
                  onResponderGrant={e => seek(e.nativeEvent.locationX)} onResponderMove={e => seek(e.nativeEvent.locationX)}
                  accessibilityRole="adjustable" accessibilityLabel="Timeline"
                  style={{ flex: 1, height: 44, flexDirection: 'row', gap: 2, alignItems: 'flex-end' }}>
              {m.ticks.map((h, i) => <View key={i} pointerEvents="none" style={{ flex: 1, height: h, backgroundColor: c.line }} />)}
              <View pointerEvents="none" style={{ position: 'absolute', top: 0, bottom: 0, width: 2, backgroundColor: c.ink, left: `${(frame / Math.max(1, n - 1)) * 100}%` }} />
            </View>
          </View>

          <View style={{ flexDirection: 'row', gap: 6 }}>
            {[['skel', 'SKELETON'], ['ang', 'ANGLES'], ['trail', 'HIP PATH']].map(([k, l]) => (
              <Pressable key={k} accessibilityRole="switch" accessibilityState={{ checked: layers[k] }}
                         onPress={() => { haptic.tick(); setLayers(x => ({ ...x, [k]: !x[k] })) }}
                         style={{ flex: 1, height: 40, alignItems: 'center', justifyContent: 'center', borderWidth: 1, borderColor: c.ink,
                                  backgroundColor: layers[k] ? c.ink : 'transparent' }}>
                <Mono size={11} color={layers[k] ? c.bg : c.ink} style={{ letterSpacing: 1.1 }}>{l}</Mono>
              </Pressable>
            ))}
          </View>

          <View style={{ gap: 8, paddingTop: 8 }}>
            <Eyebrow>KEY MOMENTS · {n} FRAMES</Eyebrow>
            <View style={{ flexDirection: 'row', gap: 8 }}>
              {m.stills.map(s => (
                <Pressable key={s.label} style={{ flex: 1, gap: 6 }} onPress={() => { haptic.tick(); setPlaying(false); setFrame(s.f) }}>
                  <View onLayout={e => setBox(b => ({ ...b, sw: e.nativeEvent.layout.width }))} style={{ height: 132, backgroundColor: PANEL }}>
                    {box.sw > 0 && <Skeleton m={m} f={s.f} w={box.sw} h={132} layers={{ skel: true }} />}
                  </View>
                  <Mono size={9.5} color="ink2" style={{ letterSpacing: 0.95 }}>{s.label}</Mono>
                </Pressable>
              ))}
            </View>
          </View>
        </>
      )}

      {metrics?.values && (
        <View>
          <Eyebrow style={{ paddingBottom: 4 }}>WHAT THE OVERLAY MEASURED</Eyebrow>
          {Object.entries(metrics.values).filter(([, v]) => v != null).slice(0, 10).map(([k, v]) => (
            <View key={k} style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', gap: 12,
                                   paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line }}>
              <T size={14.5} style={{ flex: 1 }}>{metrics.labels?.[k] ?? k}</T>
              <Mono size={16} font="monoMedium">{typeof v === 'number' ? Number(v.toFixed(2)) : v}{metrics.units?.[k] ? ` ${metrics.units[k]}` : ''}</Mono>
            </View>
          ))}
        </View>
      )}
      {!!drill && (
        <View style={{ borderWidth: 1, borderColor: c.ink, paddingVertical: 13, paddingHorizontal: 15, gap: 5 }}>
          <Eyebrow>DRILL FOR IT</Eyebrow>
          <T size={14.5} style={{ lineHeight: 20 }}>{drill.finding}. {drill.drill}</T>
        </View>
      )}
    </Screen>
  )
}

function Skeleton({ m, f, w, h, layers }) {
  const { x0, y0, x1, y1 } = m.bounds
  const s = Math.min(w / (x1 - x0), h / (y1 - y0))
  const ox = (w - (x1 - x0) * s) / 2, oy = (h - (y1 - y0) * s) / 2
  const P = q => (q ? [(q[0] - x0) * s + ox, (q[1] - y0) * s + oy] : null)
  const p = m.frames[f]
  if (!p) return <Mono size={10} color={DIM} style={{ position: 'absolute', left: 12, top: h / 2 - 6 }}>NOBODY FOUND IN THIS FRAME</Mono>
  const bone = (side, a, b, opacity, k) => {
    const A = P(p[side[a]]), B = P(p[side[b]])
    return A && B ? <Line key={k} x1={A[0]} y1={A[1]} x2={B[0]} y2={B[1]} stroke={INK} strokeWidth={1.6} strokeOpacity={opacity} /> : null
  }
  const head = P(p[0]), neck = P(p[m.near.sh])
  const kn = P(p[m.near.kn]), hp = P(p[m.near.hip]), an = P(p[m.near.an])
  let arc = null
  if (layers.ang && kn && hp && an) {
    const R = 16, a1 = Math.atan2(hp[1] - kn[1], hp[0] - kn[0]), a2 = Math.atan2(an[1] - kn[1], an[0] - kn[0])
    let d = a2 - a1
    while (d < 0) d += 2 * Math.PI
    arc = `M${kn[0] + Math.cos(a1) * R} ${kn[1] + Math.sin(a1) * R} A${R} ${R} 0 0 ${d > Math.PI ? 0 : 1} ${kn[0] + Math.cos(a2) * R} ${kn[1] + Math.sin(a2) * R}`
  }
  const trail = layers.trail ? m.hip.slice(Math.max(0, f - 24), f + 1).map(P).filter(Boolean).map(q => q.join(',')).join(' ') : ''
  const ground = Math.max(...[p[m.near.to], p[m.near.he], p[m.near.an]].map(P).filter(Boolean).map(q => q[1]), 0)
  return (
    <>
      <Svg width={w} height={h} style={{ position: 'absolute' }}>
        <Defs>
          <Pattern id="ph" width="10" height="10" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <Line x1="0" y1="0" x2="0" y2="10" stroke="rgba(238,237,232,0.05)" strokeWidth="1" />
          </Pattern>
        </Defs>
        <Rect width={w} height={h} fill="url(#ph)" />
        {ground > 0 && <Line x1={0} y1={ground + 2} x2={w} y2={ground + 2} stroke="#6E6D68" strokeWidth={0.8} strokeDasharray={[3, 3]} />}
        {!!trail && <Polyline points={trail} fill="none" stroke={INK} strokeWidth={1} strokeDasharray={[3, 2]} />}
        {layers.skel !== false && BONES.map(([a, b], i) => bone(m.far, a, b, 0.35, `f${i}`))}
        {layers.skel !== false && BONES.map(([a, b], i) => bone(m.near, a, b, 1, `n${i}`))}
        {layers.skel !== false && head && neck && <Line x1={head[0]} y1={head[1]} x2={neck[0]} y2={neck[1]} stroke={INK} strokeWidth={1.6} />}
        {layers.skel !== false && Object.values(m.near).map(j => P(p[j])).filter(Boolean).map((q, i) => (
          <Rect key={`j${i}`} x={q[0] - 2.2} y={q[1] - 2.2} width={4.4} height={4.4} fill={INK} rotation={45} origin={`${q[0]}, ${q[1]}`} />
        ))}
        {head && <Circle cx={head[0]} cy={head[1]} r={Math.max(6, s * 0.035)} fill="none" stroke={INK} strokeWidth={1.4} />}
        {!!arc && <Path d={arc} fill="none" stroke={INK} strokeWidth={1} />}
      </Svg>
      {layers.ang && kn && m.knee[f] != null && (
        <View style={{ position: 'absolute', left: Math.min(w - 52, kn[0] + 18), top: kn[1] - 10, backgroundColor: INK, paddingVertical: 3, paddingHorizontal: 6 }}>
          <Mono size={12} font="monoMedium" color="#0F0F0E">{m.knee[f]}°</Mono>
        </View>
      )}
    </>
  )
}
