import { useEffect, useMemo, useState } from 'react'
import { Alert, View } from 'react-native'
import { api, getSports } from '../../lib/api'
import { useData } from '../../lib/useData'
import { changes, SOURCES, sum, toDraft, unfinished } from '../../lib/weights'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Btn, Choice, Eyebrow, H1, Lap, Mono, Note, Screen, Seg, Slider, T, Top } from '../../ui'
import { toast } from '../../ui/Toast'

/* How much each measure counts towards each position (Coach board, 09). Every report is
   worked out again from these as soon as they're saved. */
export default function Weights() {
  const s = useSession()
  const { c } = useTheme()
  const sport = s.coach?.sport
  const [slug, setSlug] = useState(null)
  useEffect(() => { getSports().then(list => setSlug(list.find(x => x.name === sport)?.slug ?? null)).catch(() => {}) }, [sport])
  const data = useData(() => (slug ? api.weights(slug) : Promise.resolve(null)), [slug])
  const [base, setBase] = useState(null)
  const [draft, setDraft] = useState(null)
  const [pos, setPos] = useState(null)
  const [src, setSrc] = useState('test')
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')

  const start = d => {
    const shaped = toDraft(d.weights, d.metrics)
    setBase(shaped)
    setDraft(shaped)
    setPos(p => (p && shaped[p] ? p : Object.keys(shaped)[0]))
  }
  useEffect(() => { if (data.data) start(data.data) }, [data.data])

  const labels = useMemo(() => Object.fromEntries((data.data?.metrics ?? []).map(m => [m.key, m.label])), [data.data])
  if (!draft || !pos) {
    return (
      <Screen bottom={110}>
        <Top context={contextLine(s)} />
        {data.error ? <Note>{data.error.message}</Note> : <Lap size={28} />}
      </Screen>
    )
  }

  const groups = draft[pos]
  const sources = SOURCES.filter(([k]) => groups[k])
  const here = groups[src] ? src : sources[0][0]
  const group = groups[here]
  const total = sum(group)
  const max = Math.max(60, Math.ceil(Math.max(...Object.values(group)) / 5) * 5)
  const edits = changes(draft, base)
  const dirty = Object.keys(edits).length > 0
  const todo = unfinished(draft, base)
  const word = k => SOURCES.find(x => x[0] === k)[1].toLowerCase()

  const setOne = (key, v) => {
    const next = { ...group, [key]: v }
    if (sum(next) === 100 && total !== 100) haptic.snap()
    setDraft(d => ({ ...d, [pos]: { ...d[pos], [here]: next } }))
  }
  async function save() {
    setBusy('save')
    setError('')
    try {
      const res = await api.saveWeights(slug, edits)
      start({ ...data.data, weights: res.weights })
      haptic.success()
      toast({ title: 'Weights saved', sub: 'EVERY REPORT NOW USES THEM' })
    } catch (err) { haptic.error(); setError(err.message) }
    setBusy('')
  }
  const reset = () => Alert.alert('Back to the built-in weights?', `Every ${sport} position goes back to Stridian’s starting weights. The model’s history keeps the ones you had.`, [
    { text: 'Keep mine', style: 'cancel' },
    { text: 'Reset', style: 'destructive', onPress: async () => {
      setBusy('reset')
      try {
        const res = await api.resetWeights(slug)
        start({ ...data.data, weights: res.weights })
        haptic.success()
        toast({ title: 'Back to the built-in weights', sub: sport.toUpperCase() })
      } catch (err) { haptic.error(); setError(err.message) }
      setBusy('')
    } },
  ])

  return (
    <Screen bottom={110} gap={16}>
      <Top context={contextLine(s)} />
      <View style={{ gap: 8 }}>
        <Eyebrow>SCORING WEIGHTS · {sport.toUpperCase()}</Eyebrow>
        <H1>Weights</H1>
      </View>
      <Choice options={Object.keys(draft).map(p => [p, p])} value={pos} onChange={setPos} />
      {sources.length > 1 && <Seg options={sources.map(([k, label]) => [k, label])} value={here} onChange={setSrc} />}
      <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>{SOURCES.find(x => x[0] === here)[2]}</T>

      <View style={{ gap: 14 }}>
        {Object.entries(group).map(([key, v]) => (
          <View key={key} style={{ gap: 4 }}>
            <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10 }}>
              <T size={14.5} style={{ flex: 1 }}>{labels[key] ?? key}</T>
              <Mono size={14} font="monoMedium">{v}%</Mono>
            </View>
            <Slider value={v} max={max} label={labels[key] ?? key} onChange={x => setOne(key, x)} />
          </View>
        ))}
      </View>

      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.ink }}>
        <Mono size={11} style={{ letterSpacing: 1.32 }}>TOTAL</Mono>
        <View style={{ paddingVertical: 5, paddingHorizontal: 8, borderWidth: 1, borderColor: c.ink, backgroundColor: total === 100 ? 'transparent' : c.ink }}
              accessibilityLiveRegion="polite">
          <Mono size={12} color={total === 100 ? c.ink : c.bg} style={{ letterSpacing: 0.72 }}>
            {total === 100 ? '100% · READY TO SAVE' : `${total}% · ${total < 100 ? `${100 - total}% LEFT TO GIVE` : `${total - 100}% TOO MUCH`}`}
          </Mono>
        </View>
      </View>
      {todo.filter(([p, k]) => p !== pos || k !== here).map(([p, k, t]) => (
        <T key={p + k} size={12.5} color="ink2">{p} · {word(k)} adds up to {t}% — it needs 100% before saving.</T>
      ))}
      <Note>{error}</Note>
      <View style={{ gap: 6 }}>
        <Btn label={dirty ? 'Save weights' : 'No changes yet'} disabled={!dirty || todo.length > 0} busy={busy === 'save'} busyLabel="Saving" onPress={save} />
        {dirty && <Btn kind="text" label="Undo my changes" onPress={() => { haptic.tick(); setDraft(base) }} />}
        <Btn kind="text" label="Reset to the built-in weights" busy={busy === 'reset'} busyLabel="Resetting" onPress={reset} />
      </View>
    </Screen>
  )
}
