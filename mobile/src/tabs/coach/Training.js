import { useEffect, useState } from 'react'
import { Alert, Linking, View } from 'react-native'
import { api, utc } from '../../lib/api'
import { useData } from '../../lib/useData'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Bar, Btn, Eyebrow, H1, Lap, Mono, Note, OfflineBar, Row, Screen, T, Tag, Top } from '../../ui'
import { toast } from '../../ui/Toast'

const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`)
const ago = s => (s < 90 ? 'just now' : s < 3600 ? `${Math.round(s / 60)} min ago` : s < 86400 ? `${Math.round(s / 3600)} h ago` : `${Math.round(s / 86400)} days ago`)
const when = iso => utc(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })

/* What the model has learned from the coaches' verifications, how often it agrees with
   them, and whether the analysis computer and the video queue are keeping up. */
export default function Training({ active }) {
  const s = useSession()
  const { c } = useTheme()
  const t = useData(api.training, [s.coach?.sport])
  const [busy, setBusy] = useState(null)
  // while it's on screen, it keeps itself current (the worker reports every few seconds)
  useEffect(() => {
    if (!active) return undefined
    const timer = setInterval(t.reload, 30000)
    return () => clearInterval(timer)
  }, [active, t.reload])

  const d = t.data
  const rollback = v => Alert.alert(`Put model #${v.id} back live?`, 'The current one stays in the history, so you can switch back.', [
    { text: 'Cancel', style: 'cancel' },
    { text: 'Use this one', onPress: async () => {
      setBusy(v.id)
      try {
        t.setData(await api.rollback(v.id))
        haptic.success()
        toast({ title: `Model #${v.id} is live`, sub: 'EVERY REPORT NOW USES IT' })
      } catch (err) { haptic.error(); Alert.alert('Couldn’t switch models', err.message) }
      setBusy(null)
    } },
  ])

  return (
    <View style={{ flex: 1 }}>
      {t.error?.offline && <OfflineBar note={d ? 'SHOWING THE LAST UPDATE' : 'NOTHING LOADED YET'} onRetry={t.refresh} />}
      <Screen bottom={110} gap={20} refreshing={t.refreshing} onRefresh={t.refresh}>
        <Top context={contextLine(s)} />
        {t.error?.offline && <View style={{ height: 40 }} />}
        <View style={{ gap: 8 }}>
          <Eyebrow>THE MODEL · {(s.coach?.sport ?? '').toUpperCase()}</Eyebrow>
          <H1>AI training</H1>
        </View>
        <T size={14} color="ink2" style={{ lineHeight: 20 }}>
          Every student you verify is a lesson: the model looks at what sets the players in each position apart and adjusts
          that position’s weights. A new model only goes live if it predicts your verified students better than the current one.
        </T>
        {t.error && !t.error.offline && <Note>{t.error.message}</Note>}
        {!d && !t.error && <Lap size={28} />}
        {d && (
          <>
            <View>
              <Row a="Verified students" b={String(d.labels.verified)}
                   sub={d.labels.verified >= d.minLabels ? `${d.labels.pending} STILL PENDING` : `${d.minLabels - d.labels.verified} MORE BEFORE TRAINING STARTS`} />
              <Row a="Agrees with you" b={d.agreement.judged ? pct(d.agreement.agree / d.agreement.judged) : '—'}
                   sub={d.agreement.judged ? `${d.agreement.agree} OF ${d.agreement.judged} VERIFIED` : 'NOTHING VERIFIED YET'} />
              <Row a="Live model" b={d.live ? `#${d.live.id}` : 'Default'}
                   sub={d.live?.kind === 'trained' ? `TRAINED ON ${d.live.labels} STUDENTS` : d.live ? 'WEIGHTS SET BY A COACH' : 'BUILT-IN STARTING WEIGHTS'} />
              <Row a="Analysis computer" b={<Tag label={d.worker.online ? 'ON' : 'OFF'} on={d.worker.online} dashed={!d.worker.online} />}
                   sub={d.worker.seen ? `${d.worker.host} · ${d.worker.online && d.worker.doing !== 'idle' ? d.worker.doing : `seen ${ago(d.worker.secondsAgo)}`}`.toUpperCase()
                     : 'HAS NEVER CONNECTED'} last />
            </View>

            <View>
              <Eyebrow style={{ paddingBottom: 4 }}>WHERE VERIFIED STUDENTS PLAY</Eyebrow>
              <T size={12.5} color="ink2" style={{ paddingBottom: 8 }}>The model can only learn a position it has examples of.</T>
              {d.labels.positions.map(p => {
                const n = d.labels.byPosition[p] ?? 0
                const most = Math.max(1, ...d.labels.positions.map(x => d.labels.byPosition[x] ?? 0))
                return (
                  <View key={p} style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, borderTopWidth: 1, borderTopColor: c.line }}>
                    <T size={14} style={{ flex: 1 }}>{p}</T>
                    <Bar value={n / most} w={90} />
                    <Mono size={13} style={{ width: 24, textAlign: 'right' }}>{n}</Mono>
                  </View>
                )
              })}
            </View>

            <View>
              <Eyebrow style={{ paddingBottom: 6 }}>WHAT IT HAS LEARNED</Eyebrow>
              {d.learned.length === 0 ? (
                <T size={14} color="ink2" style={{ lineHeight: 20 }}>
                  {d.live?.kind === 'trained' ? 'The live model barely differs from its starting weights.'
                    : 'Nothing yet — the starting weights are in use until a trained model beats them.'}
                </T>
              ) : d.learned.map(item => (
                <View key={item.position} style={{ gap: 4, paddingVertical: 10, borderTopWidth: 1, borderTopColor: c.line }}>
                  <T font="semi" size={14.5}>{item.position}</T>
                  {item.changes.map(ch => (
                    <Mono key={ch.label} size={11} color="ink2">{ch.label.toUpperCase()} {ch.to > ch.from ? '↑' : '↓'} {pct(ch.from)} → {pct(ch.to)}</Mono>
                  ))}
                </View>
              ))}
            </View>

            <View>
              <Eyebrow style={{ paddingBottom: 6 }}>MODEL HISTORY</Eyebrow>
              {d.versions.length === 0 ? (
                <T size={14} color="ink2" style={{ lineHeight: 20 }}>
                  No training runs yet. They happen on the analysis computer once {d.minLabels} students are verified across at least two positions.
                </T>
              ) : d.versions.map(v => {
                const live = v.id === d.live?.id
                return (
                  <View key={v.id} style={{ gap: 6, paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line }}>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
                      <Mono size={13} font="monoMedium">#{v.id}</Mono>
                      <Tag label={live ? 'LIVE' : v.kind === 'trained' && !v.deployed ? 'KEPT OUT' : v.kind === 'trained' ? 'TRAINED' : 'SET BY A COACH'}
                           on={live} dashed={v.kind === 'trained' && !v.deployed && !live} />
                      <View style={{ flex: 1 }} />
                      <Mono size={11} color="ink2">{when(v.createdAt).toUpperCase()}</Mono>
                    </View>
                    {!!v.note && <T size={13} color="ink2" style={{ lineHeight: 18 }}>{v.note}</T>}
                    <Mono size={10.5} color="ink2">
                      {v.labels ? `${v.labels} STUDENTS · ` : ''}ACCURACY {pct(v.accuracy)} · OLD MODEL {pct(v.liveAccuracy)}
                    </Mono>
                    {!live && <Btn kind="text" label="Use this one" busy={busy === v.id} busyLabel="Switching" onPress={() => rollback(v)}
                                   style={{ alignSelf: 'flex-start', paddingHorizontal: 0, height: 36 }} />}
                  </View>
                )
              })}
            </View>

            <View>
              <Eyebrow style={{ paddingBottom: 4 }}>PIPELINE</Eyebrow>
              <Row a="Waiting for analysis" b={`${d.queue.videos} + ${d.queue.matches}`} sub="DRILL + MATCH CLIPS" />
              <Row a="Video storage" b={d.storage === 'drive' ? 'Drive' : 'Server'} sub={d.storage === 'drive' ? 'KEPT 30 DAYS' : 'THIS COMPUTER'} />
              {!d.sheetsConfigured ? <Row a="Google Sheets" b="Off" last />
                : !d.sheets ? <Row a="Google Sheets" sub="KEPT BY THE ADMINS — USE SQUAD AS EXCEL" b="On" last />
                  : d.sheets.map((p, i) => (
                    <Row key={p.title} a={`${p.title} sheet`} last={i === d.sheets.length - 1}
                         sub={p.at ? (p.ok ? `SYNCED ${when(p.at).toUpperCase()}` : `LAST SYNC FAILED: ${p.error}`) : 'MADE ON THE NEXT CHANGE'}
                         b={p.url ? <Btn kind="text" label="Open" onPress={() => Linking.openURL(p.url)} style={{ height: 36 }} /> : '—'} />
                  ))}
            </View>
          </>
        )}
      </Screen>
    </View>
  )
}
