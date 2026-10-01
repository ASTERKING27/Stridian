import { useEffect, useRef, useState } from 'react'
import { Pressable, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import Svg, { Defs, Line, Pattern, Rect } from 'react-native-svg'
import { getSports } from '../../../lib/api'
import { pickVideo } from '../../../lib/media'
import { clipName, uploadClip } from '../../../lib/upload'
import { useSession } from '../../../lib/session'
import { useTheme } from '../../../lib/theme'
import { haptic } from '../../../lib/haptics'
import { primed } from '../../../lib/notifications'
import { Back, Btn, Choice, Eyebrow, Field, I, Icon, Mono, Note, Screen, Seg, T, Title } from '../../../ui'

const TIPS = ['Film side-on, whole body in frame', 'One athlete only', 'Keep the phone still — prop it up',
              'Up to 200 MB · MP4, MOV, AVI, MKV, WEBM, M4V']
const MATCH_TIPS = ['A wide, steady shot — players a fair size in frame', 'Tracking reads the first 3 minutes',
                    'Keep the phone still — a tripod or a railing', 'Up to 600 MB · MP4, MOV, AVI, MKV, WEBM, M4V']
const mb = b => `${Math.round(b / 1048576)} MB`
const dur = ms => (ms ? `${Math.floor(ms / 60000)}:${String(Math.round((ms / 1000) % 60)).padStart(2, '0')}` : '')

/* Upload board, 01–03: choose the drill, film or pick the clip, watch it go up in pieces.
   `match`: a coach's match footage instead — a label and the way the team attacks. */
export default function AddVideo() {
  const { id, match } = useLocalSearchParams()
  const isMatch = !!match
  const s = useSession()
  const { c } = useTheme()
  const sport = s.role === 'student' ? s.me?.student?.sport : s.coach?.sport
  const [drills, setDrills] = useState([])
  const [drill, setDrill] = useState('')
  const [label, setLabel] = useState('')
  const [dir, setDir] = useState('right')
  const [clip, setClip] = useState(null)          // { uri, name, size, duration }
  const [stage, setStage] = useState('pick')      // pick | up | done | failed
  const [prog, setProg] = useState({ sent: 0, total: 1, piece: 1, pieces: 1 })
  const [error, setError] = useState(null)
  const abort = useRef(null)

  useEffect(() => {
    getSports().then(list => {
      const tests = (list.find(x => x.name === sport)?.metrics ?? []).filter(m => m.source === 'test').map(m => m.label.split(' (')[0])
      setDrills(tests)
      setDrill(d => d || tests[0] || '')
    }).catch(() => {})
  }, [sport])
  useEffect(() => () => abort.current?.abort(), [])

  async function choose(camera) {
    setError(null)
    // the first time, say why the camera is needed before the phone asks
    if (camera && !(await primed('camera'))) return router.push({ pathname: '/primer', params: { kind: 'camera' } })
    try {
      const a = await pickVideo({ camera, maxDuration: isMatch ? 180 : 120 })
      if (!a) return
      const picked = { uri: a.uri, name: clipName(a), size: a.fileSize, duration: a.duration }
      setClip(picked)
      send(picked)
    } catch (err) { haptic.error(); setError(err) }
  }

  async function send(file = clip) {
    abort.current = new AbortController()
    setStage('up')
    setError(null)
    try {
      await uploadClip(isMatch ? { uri: file.uri, name: file.name, label: label.trim() || null, match: dir }
        : { uri: file.uri, name: file.name, label: drill || null, studentId: id }, p => setProg(p), abort.current.signal)
      haptic.success()
      setStage('done')
    } catch (err) {
      if (err.kind === 'cancel') return setStage('pick')
      haptic.error()
      setError(err)
      setStage('failed')
    }
  }

  const pct = Math.round((prog.sent / prog.total) * 100)
  const pieces = (
    <View style={{ flexDirection: 'row', gap: 3 }}>
      {Array.from({ length: Math.min(prog.pieces, 50) }, (_, i) => {
        const sent = i < Math.floor((prog.sent / prog.total) * prog.pieces + 1e-6)
        return <View key={i} style={{ flex: 1, height: 14, borderWidth: 1, borderColor: c.ink, backgroundColor: sent ? c.ink : 'transparent',
                                     borderStyle: stage === 'failed' && !sent ? 'dashed' : 'solid' }} />
      })}
    </View>
  )

  if (stage === 'up' || stage === 'done') {
    const done = stage === 'done'
    return (
      <Screen fill>
        <Back label="Cancel" icon={I.close} onPress={() => (done ? router.back() : abort.current?.abort())} />
        <Title eyebrow={done ? 'UPLOADED · IN THE QUEUE' : 'UPLOADING'}>{isMatch ? label.trim() || 'Match clip' : drill || 'Drill clip'}</Title>
        <View style={{ height: 196, borderWidth: 1, borderColor: c.line, justifyContent: 'flex-end', padding: 12 }}>
          <Svg style={{ position: 'absolute', left: 0, top: 0 }} width="100%" height="100%">
            <Defs><Pattern id="uh" width="9" height="9" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
              <Line x1="0" y1="0" x2="0" y2="9" stroke={c.line} strokeWidth="1" /></Pattern></Defs>
            <Rect width="100%" height="100%" fill="url(#uh)" />
          </Svg>
          <View style={{ alignSelf: 'flex-start', backgroundColor: c.bg, paddingVertical: 4, paddingHorizontal: 7 }}>
            <Mono size={10.5} style={{ letterSpacing: 0.63 }}>
              {[clip?.name?.toUpperCase(), prog.total > 1 ? mb(prog.total) : null, dur(clip?.duration)].filter(Boolean).join(' · ')}
            </Mono>
          </View>
        </View>
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <Mono size={64} font="monoMedium" style={{ lineHeight: 60 }}>{done ? 100 : pct}<Mono size={26}>%</Mono></Mono>
          <Mono size={11} color="ink2" style={{ letterSpacing: 0.88, paddingBottom: 4 }}>
            {done ? `${prog.pieces} OF ${prog.pieces} PIECES` : `PIECE ${prog.piece} OF ${prog.pieces} · 4 MB`}
          </Mono>
        </View>
        {pieces}
        <T size={14} color="ink2" style={{ lineHeight: 20 }}>
          {!done ? 'Keep Stridian open until the upload finishes.'
            : isMatch ? 'The analysis computer follows every player in it. Once it’s done, tap your students on a frame to say who’s who.'
              : 'It will be analysed in the next session on the coach’s computer. You’ll get a notification when it’s ready.'}
        </T>
        <View style={{ flex: 1, justifyContent: 'flex-end' }}>
          {done ? <Btn label={isMatch ? 'Back to match footage' : 'See it in the queue'} onPress={() => router.back()} />
            : <Btn kind="secondary" label="Cancel upload" onPress={() => abort.current?.abort()} />}
        </View>
      </Screen>
    )
  }

  if (stage === 'failed') {
    const why = error?.kind === 'size' ? [`Over ${isMatch ? 600 : 200} MB`, error.message]
      : error?.kind === 'network' ? ['Connection lost', 'Check your Wi-Fi or mobile data, then try again. Your video is still on your phone.']
        : ['The upload was refused', error?.message]
    return (
      <Screen>
        <Back label={isMatch ? 'Match footage' : 'Drill videos'} onPress={() => router.back()} />
        <Title eyebrow="UPLOAD STOPPED">Couldn’t finish the upload</Title>
        <View style={{ gap: 10 }}>
          {pieces}
          <Mono size={11} color="ink2" style={{ letterSpacing: 0.88 }}>STOPPED AT {pct}% · PIECE {prog.piece} OF {prog.pieces}</Mono>
        </View>
        <View accessibilityRole="alert" style={{ backgroundColor: c.ink, padding: 16, flexDirection: 'row', gap: 14 }}>
          <Icon d={I.warning} size={22} color={c.bg} />
          <View style={{ flex: 1, gap: 5 }}>
            <T font="semi" size={16} color={c.bg}>{why[0]}</T>
            <T size={13.5} color={c.bg} style={{ lineHeight: 19, opacity: 0.8 }}>{why[1]}</T>
          </View>
        </View>
        <View style={{ gap: 10 }}>
          {error?.kind !== 'size' && <Btn label="Try again" icon={I.retry} onPress={() => send()} />}
          <Btn kind="secondary" label="Choose a different video" onPress={() => { setStage('pick'); setClip(null) }} />
        </View>
        <View>
          <Eyebrow style={{ paddingBottom: 6 }}>OTHER REASONS IT CAN STOP</Eyebrow>
          {[[`Over ${isMatch ? 600 : 200} MB`, 'Trim the clip, or record a shorter one.'], ['Not a video file', 'MP4, MOV, AVI, MKV, WEBM or M4V.']].map(([a, b]) => (
            <View key={a} style={{ gap: 3, paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line }}>
              <T size={14.5}>{a}</T><T size={12.5} color="ink2">{b}</T>
            </View>
          ))}
        </View>
      </Screen>
    )
  }

  const tile = (camera) => (
    <Pressable onPress={() => choose(camera)} onPressIn={() => haptic.tap()} accessibilityRole="button"
               style={({ pressed }) => ({ flex: 1, height: 150, padding: 18, justifyContent: 'space-between',
                                          backgroundColor: camera ? c.ink : 'transparent', borderWidth: 1, borderColor: c.ink,
                                          transform: [{ scale: pressed ? 0.97 : 1 }] })}>
      <Icon d={camera ? I.camera : I.gallery} size={30} sw={1.5} color={camera ? c.bg : c.ink} />
      <View style={{ gap: 5 }}>
        <T font="semi" size={17} color={camera ? c.bg : c.ink}>{camera ? 'Record' : 'From gallery'}</T>
        <Mono size={10} color={camera ? c.bg : c.ink2} style={{ letterSpacing: 0.8, opacity: camera ? 0.75 : 1 }}>
          {camera ? 'OPENS THE CAMERA' : 'PICK A SAVED CLIP'}
        </Mono>
      </View>
    </Pressable>
  )
  return (
    <Screen>
      <Back label={isMatch ? 'Match footage' : 'Drill videos'} onPress={() => router.back()} />
      <Title eyebrow={isMatch ? 'NEW MATCH CLIP' : 'NEW DRILL CLIP'}>{isMatch ? 'Upload a match' : 'Add a video'}</Title>
      {isMatch && (
        <>
          <Field label="LABEL (OPTIONAL)" value={label} onChangeText={setLabel} maxLength={160}
                 placeholder="e.g. Inter-dept semi-final, 2nd half" />
          <View style={{ gap: 10 }}>
            <Eyebrow>WHICH WAY IS YOUR TEAM ATTACKING?</Eyebrow>
            <Seg options={[['left', '← LEFT'], ['right', 'RIGHT →']]} value={dir} onChange={setDir} />
            <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>Positioning is read against where the other players are, so this is all the setting-up it needs.</T>
          </View>
        </>
      )}
      {!isMatch && drills.length > 0 && (
        <View style={{ gap: 10 }}>
          <Eyebrow>WHICH DRILL</Eyebrow>
          <Choice options={[...drills.map(d => [d, d]), ['', 'Something else']]} value={drill} onChange={setDrill} />
        </View>
      )}
      <View style={{ flexDirection: 'row', gap: 10 }}>{tile(true)}{tile(false)}</View>
      {error && <Note>{error.message}</Note>}
      <View>
        <Eyebrow style={{ paddingBottom: 6 }}>FOR A CLEAN READING</Eyebrow>
        {(isMatch ? MATCH_TIPS : TIPS).map((t, i) => (
          <View key={t} style={{ flexDirection: 'row', gap: 14, paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line }}>
            <Mono size={11} color="ink2" style={{ paddingTop: 2 }}>0{i + 1}</Mono>
            <T size={14.5}>{t}</T>
          </View>
        ))}
      </View>
      <Mono size={10.5} color="ink2" style={{ lineHeight: 17 }}>VIDEOS ARE DELETED AFTER 30 DAYS.{'\n'}YOUR MEASUREMENTS ARE KEPT.</Mono>
    </Screen>
  )
}
