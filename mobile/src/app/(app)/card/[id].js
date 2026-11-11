import { useState } from 'react'
import { Image, Linking, Pressable, ScrollView, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api, authedSource, BASE } from '../../../lib/api'
import { openAuthedFile, pickPhoto } from '../../../lib/media'
import { useData } from '../../../lib/useData'
import { primed } from '../../../lib/notifications'
import { useTheme } from '../../../lib/theme'
import { haptic } from '../../../lib/haptics'
import { Back, Btn, Eyebrow, H1, I, Icon, Lap, Mono, Note, Row, Screen, T, Tag } from '../../../ui'
import { cardTitle, cardVs, readInto, readParams } from '../../../tabs/coach/Cards'
import { LoadError } from '../../../ui/States'
import { dialog } from '../../../ui/Dialog'

const MAX_PHOTOS = 4
const MARK_SHOW = { '+': '+', 0: '0', '-': '–' }
const MARK_AT = { '+': 0, 0: 1, '-': 2 }
const isNum = cell => /^[-+]?[\d.:%—]+$/.test(cell)
const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`

/* One match card on the phone: what the AI filled in from the photos — the match's
   details and every player's row, as on the paper — and Part C worked out from it.
   Photos go up and are read here; correcting the card and finishing it happen on the
   website. */
export default function Card() {
  const params = useLocalSearchParams()
  const { c } = useTheme()
  const card = useData(() => api.card(params.id), [params.id])
  const cfg = useData(() => api.cardsConfig(), [])
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [news, setNews] = useState(() => readParams({ read: params.players != null && params, error: params.problem }))

  const k = card.data
  async function run(kind, action) {
    setBusy(kind)
    setError('')
    try { await action() } catch (err) { haptic.error(); setError(err.message) }
    setBusy('')
  }
  if (!k) {
    return (
      <Screen>
        <Back label="Match cards" onPress={() => router.back()} />
        {card.error ? <LoadError error={card.error} onRetry={card.reload} /> : <Lap size={28} />}
      </Screen>
    )
  }

  const final = k.status === 'final'
  const aiOn = cfg.data?.aiOn
  // read a photo into the card, and say what went in
  const fill = async (now, photo) => {
    const done = await readInto(now, photo)
    card.setData(done.card)
    setNews(readParams(done))
    if (done.error) haptic.error(); else haptic.success()
  }
  const add = () => {
    const go = camera => () => run('add', async () => {
      // the first time, say why the camera is needed before the phone asks
      if (camera && !(await primed('camera'))) return router.push({ pathname: '/primer', params: { kind: 'camera' } })
      const p = await pickPhoto({ camera, maxSide: 2400, quality: 0.85 })
      if (!p) return
      const now = await api.addCardPhoto(k.id, p.uri, p.type)
      card.setData(now)
      if (aiOn) { setBusy('reading'); await fill(now) } else haptic.success()
    })
    dialog('Add a photo of the card', 'Part A flat, in good light, the whole sheet in frame.', [
      { text: 'Take a photo', onPress: go(true) },
      { text: 'Choose a photo', onPress: go(false) },
      { text: 'Cancel', style: 'cancel' },
    ])
  }
  const removePhoto = p => dialog('Delete this photo?', 'What was read from it stays on the card.', [
    { text: 'Keep', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => run('photo', async () => { card.setData(await api.deleteCardPhoto(k.id, p.n, p.v)) }) },
  ])
  const remove = () => dialog('Delete this card?', 'Its photos go too. This can’t be undone.', [
    { text: 'Keep', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => run('delete', async () => { await api.deleteCard(k.id); router.back() }) },
  ])
  const h = k.header
  const pc = k.partC

  return (
    <Screen gap={18}>
      <Back label="Match cards" onPress={() => router.back()} />
      <View style={{ gap: 8 }}>
        <Eyebrow>{[k.sport, k.category === 'W' ? 'WOMEN' : 'MEN', h.date && new Date(`${h.date}T00:00:00`)
                  .toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })].filter(Boolean).join(' · ').toUpperCase()}</Eyebrow>
        <H1 size={26}>{cardTitle(h)}</H1>
        <T font="semi" size={17}>{cardVs(h)}</T>
        <View style={{ flexDirection: 'row', paddingTop: 2 }}>
          <Tag label={final ? 'FINISHED · COUNTS IN REPORTS' : 'DRAFT · NOT COUNTED YET'} on={final} dashed={!final} />
        </View>
      </View>

      {(news.players || news.problem) && <News news={news} onClose={() => setNews({})} />}
      {busy === 'reading' && (
        <View style={{ flexDirection: 'row', gap: 10, alignItems: 'center' }}>
          <Lap size={18} /><T size={14}>The AI is reading the card…</T>
        </View>
      )}
      <Note>{error}</Note>

      {/* the preview: what's on the card now */}
      <View style={{ gap: 10 }}>
        <Eyebrow>WHAT’S ON THE CARD</Eyebrow>
        <Details h={h} cfg={cfg.data} />
        {k.lines.length > 0 && cfg.data ? (
          <>
            <PartA lines={k.lines} cfg={cfg.data} />
            {k.lines.some(l => !l.student_id) && (
              <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>* Not matched to a student yet — pick who it is on the website.</T>
            )}
          </>
        ) : k.lines.length > 0 ? <Lap size={22} /> : (
          <View style={{ flexDirection: 'row', gap: 10, alignItems: 'flex-start' }}>
            <Icon d={I.info} size={16} />
            <T size={13.5} color="ink2" style={{ flex: 1, lineHeight: 19 }}>
              No players on the card yet{aiOn === false ? ' — reading photos needs the AI switched on (GEMINI_API_KEY on the server).' : '.'}
            </T>
          </View>
        )}
        <View style={{ flexDirection: 'row', gap: 10, alignItems: 'flex-start', paddingTop: 6 }}>
          <Icon d={I.edit} size={16} />
          <T size={13.5} color="ink2" style={{ flex: 1, lineHeight: 19 }}>
            {final ? 'Finished on the website — that’s where to change it.'
              : 'Check it against the paper on the website, correct anything there, then finish the card so it counts in reports.'}
          </T>
        </View>
        <Btn kind="secondary" label="Open the website" iconRight={I.next} onPress={() => Linking.openURL(BASE)} />
      </View>

      <View style={{ gap: 10 }}>
        <Eyebrow>PHOTOS OF THE CARD · {k.photos.length} / {MAX_PHOTOS}</Eyebrow>
        {k.photos.map(p => (
          <View key={p.v} style={{ flexDirection: 'row', gap: 12, alignItems: 'center', paddingTop: 10, borderTopWidth: 1, borderTopColor: c.line }}>
            <Pressable onPress={() => run('open', () => openAuthedFile(`/api/cards/${k.id}/photos/${p.n}?v=${p.v}`,
                                                                     `card-${k.id}-${p.n + 1}${p.mime === 'application/pdf' ? '.pdf' : '.jpg'}`, p.mime ?? 'image/jpeg'))}
                       accessibilityRole="button" accessibilityLabel={`Open photo ${p.n + 1}`}>
              {p.mime === 'application/pdf'
                ? <View style={{ width: 64, height: 84, borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}><Mono size={11}>PDF</Mono></View>
                : <Image source={authedSource(`/api/cards/${k.id}/photos/${p.n}`, p.v)} style={{ width: 64, height: 84, backgroundColor: c.soft }} />}
            </Pressable>
            <View style={{ flex: 1, gap: 4 }}>
              <T size={15}>Photo {p.n + 1}</T>
              <Mono size={10} color="ink2">{p.read ? 'READ BY THE AI' : 'NOT READ YET'}</Mono>
              <View style={{ flexDirection: 'row', gap: 4, marginLeft: -10 }}>
                {aiOn && !p.read && !final && (
                  <Btn kind="text" label="Read with AI" busy={busy === `read${p.n}`} busyLabel="Reading" style={{ height: 36 }}
                       onPress={() => run(`read${p.n}`, () => fill(k, p))} />
                )}
                <Btn kind="text" label="Delete" onPress={() => removePhoto(p)} style={{ height: 36 }} />
              </View>
            </View>
          </View>
        ))}
        {k.photos.length < MAX_PHOTOS && !final && (
          <Btn kind="secondary" label={k.photos.length ? 'Add another photo' : 'Add a photo'} icon={I.camera} busy={busy === 'add' || busy === 'reading'}
               busyLabel={busy === 'reading' ? 'Reading' : 'Uploading'} onPress={add} />
        )}
      </View>

      {pc.rows.length > 0 && (
        <View style={{ gap: 10 }}>
          <Eyebrow>PART C · WORKED OUT FROM THE CARD</Eyebrow>
          <Table columns={pc.columns} rows={pc.rows} />
          <View>
            <Eyebrow style={{ paddingTop: 8, paddingBottom: 4 }}>{pc.teamTitle.toUpperCase()}</Eyebrow>
            {pc.team.map((t, i) => <Row key={t.key} a={t.label} b={t.value} last={i === pc.team.length - 1} />)}
            {!!pc.teamNote && <T size={12} color="ink2" style={{ paddingTop: 8, lineHeight: 17 }}>{pc.teamNote}</T>}
          </View>
        </View>
      )}

      <Btn kind="text" label="Delete this card" icon={I.delete} busy={busy === 'delete'} busyLabel="Deleting" onPress={remove} />
    </Screen>
  )
}

// What the last reading put on the card — or why it couldn't.
function News({ news, onClose }) {
  const { c } = useTheme()
  const [players, unmatched, unread] = [news.players, news.unmatched, news.unread].map(Number)
  return (
    <View accessibilityLiveRegion="polite" style={{ gap: 8, padding: 14, borderWidth: 1, borderColor: c.ink }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <Eyebrow color="ink">{news.problem ? 'THE PHOTO WASN’T READ' : 'FILLED IN FROM THE PHOTO'}</Eyebrow>
        <Pressable onPress={onClose} hitSlop={10} accessibilityRole="button" accessibilityLabel="Dismiss"><Icon d={I.close} size={16} /></Pressable>
      </View>
      <T size={14.5} style={{ lineHeight: 21 }}>
        {news.problem ? `${news.problem} It’s kept with the card — read it again below.`
          : `${plural(players, 'player')} read off the photo.${unmatched ? ` ${plural(unmatched, 'row')} need${unmatched === 1 ? 's' : ''} a student picked.` : ''}${
            unread ? ` ${plural(unread, 'number')} couldn’t be read — saved as 0.` : ''}`}
      </T>
    </View>
  )
}

// The match's details, as the top of the paper has them: only what's filled in.
function Details({ h, cfg }) {
  const score = (cfg?.score.parts ?? []).map((p, i) => h.score?.[i]?.some(v => v != null) && `${p} ${h.score[i][0] ?? '–'}–${h.score[i][1] ?? '–'}`)
    .filter(Boolean).join(' · ')
  const rows = [['Round / stage', h.round], ['Level', h.level], ['Venue', h.venue], ['Result', h.result],
    [cfg?.score.label ?? 'Score', score], ['Match no.', h.match_no], ['Recorded by', h.recorded_by], ['Coach', h.coach],
    ...(cfg?.headerExtra ?? []).map(x => [x.label, h[x.key]])].filter(([, v]) => v != null && v !== '')
  if (!rows.length) return null
  return <View>{rows.map(([a, b], i) => <Row key={a} a={a} b={String(b)} last={i === rows.length - 1} />)}</View>
}

// Part A, as on the paper: each skill's + / 0 / – counts and the other numbers, per player.
function PartA({ lines, cfg }) {
  const fields = cfg.fields.filter(f => f.sheet)
  const columns = ['Player', ...cfg.skills.map(s => `${s.sheet} (${[...s.marks].map(m => MARK_SHOW[m]).join(' ')})`), ...fields.map(f => f.short)]
  const rows = lines.map(l => [
    `${l.student_id ? '' : '* '}${l.jersey != null ? `#${l.jersey} ` : ''}${l.name ?? ''}`.trim(),
    ...cfg.skills.map(s => (l.tallies[s.key] ? [...s.marks].map(m => l.tallies[s.key][MARK_AT[m]] ?? 0).join(' · ') : '—')),
    ...fields.map(f => (l.fields[f.key] != null ? String(l.fields[f.key]) : '—')),
  ])
  return <Table columns={columns} rows={rows} />
}

// A table that scrolls sideways, numbers right-aligned under their headings.
function Table({ columns, rows }) {
  const { c } = useTheme()
  const numeric = columns.map((_, j) => rows.some(r => isNum(r[j])) && rows.every(r => !r[j] || isNum(r[j])))
  const cell = (text, j, head) => (
    <View key={j} style={{ width: j === 0 ? 140 : 84, paddingVertical: 8, paddingHorizontal: 6 }}>
      <Mono size={head ? 9.5 : 12} color={head ? 'ink2' : 'ink'} numberOfLines={head ? 3 : 1}
            style={{ textAlign: numeric[j] ? 'right' : 'left', letterSpacing: head ? 0.6 : 0 }}>
        {head ? String(text).toUpperCase() : text || '—'}
      </Mono>
    </View>
  )
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator style={{ borderTopWidth: 1, borderTopColor: c.ink }}>
      <View>
        <View style={{ flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: c.line }}>{columns.map((x, j) => cell(x, j, true))}</View>
        {rows.map((r, i) => (
          <View key={i} style={{ flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: c.line }}>{r.map((v, j) => cell(v, j))}</View>
        ))}
      </View>
    </ScrollView>
  )
}
