import { useState } from 'react'
import { Alert, Image, Platform, Pressable, ScrollView, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api, authedSource } from '../../../lib/api'
import { mergeReading } from '../../../lib/cards'
import { openAuthedFile, pickPhoto } from '../../../lib/media'
import { useData } from '../../../lib/useData'
import { primed } from '../../../lib/notifications'
import { useTheme } from '../../../lib/theme'
import { haptic } from '../../../lib/haptics'
import { Back, Btn, Eyebrow, H1, I, Icon, Lap, Mono, Note, Row, Screen, T, Tag } from '../../../ui'
import { toast } from '../../../ui/Toast'
import { cardTitle } from '../../../tabs/coach/Cards'

const MAX_PHOTOS = 4
const isNum = cell => /^[-+]?[\d.:%—]+$/.test(cell)

/* One match card on the phone: the photos of the paper (add, read with the AI, delete),
   and Part C — the review worked out from the last save. Typing in or correcting the
   grid, and finishing the card, happen on the website. */
export default function Card() {
  const { id } = useLocalSearchParams()
  const { c } = useTheme()
  const card = useData(() => api.card(id), [id])
  const cfg = useData(() => api.cardsConfig(), [])
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [read, setRead] = useState(null)            // a reading waiting to be saved: { n, merged }

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
        {card.error ? <Note>{card.error.message}</Note> : <Lap size={28} />}
      </Screen>
    )
  }

  const final = k.status === 'final'
  const add = () => {
    const go = camera => () => run('add', async () => {
      // the first time, say why the camera is needed before the phone asks
      if (camera && !(await primed('camera'))) return router.push({ pathname: '/primer', params: { kind: 'camera' } })
      const p = await pickPhoto({ camera, maxSide: 2400, quality: 0.85 })
      if (!p) return
      card.setData(await api.addCardPhoto(k.id, p.uri, p.type))
      haptic.success()
    })
    Alert.alert('Add a photo of the card', 'Part A flat, in good light, the whole sheet in frame.', [
      { text: 'Take a photo', onPress: go(true) },
      { text: 'Choose a photo', onPress: go(false) },
      ...(Platform.OS === 'ios' ? [{ text: 'Cancel', style: 'cancel' }] : []),
    ], { cancelable: true })
  }
  const readPhoto = p => run(`read${p.n}`, async () => {
    const reading = await api.readCardPhoto(k.id, p.n, p.v)
    setRead({ n: p.n, ...mergeReading(k, reading) })
    haptic.success()
  })
  const keep = () => run('save', async () => {
    card.setData(await api.saveCard(k.id, read.body))
    setRead(null)
    haptic.success()
    toast({ title: 'Saved to the card', sub: 'AS A DRAFT · CHECK IT ON THE WEBSITE' })
  })
  const removePhoto = p => Alert.alert('Delete this photo?', '', [
    { text: 'Keep', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => run('photo', async () => { card.setData(await api.deleteCardPhoto(k.id, p.n, p.v)) }) },
  ])
  const remove = () => Alert.alert('Delete this card?', 'Its photos go too. This can’t be undone.', [
    { text: 'Keep', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => run('delete', async () => { await api.deleteCard(k.id); router.back() }) },
  ])
  const pc = k.partC

  return (
    <Screen gap={18}>
      <Back label="Match cards" onPress={() => router.back()} />
      <View style={{ gap: 8 }}>
        <Eyebrow>{[k.sport, k.category === 'W' ? 'WOMEN' : 'MEN', k.header.date && new Date(`${k.header.date}T00:00:00`)
                  .toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })].filter(Boolean).join(' · ').toUpperCase()}</Eyebrow>
        <H1 size={26}>{cardTitle(k.header)}</H1>
        <View style={{ flexDirection: 'row' }}>
          <Tag label={final ? 'FINISHED · COUNTS IN REPORTS' : 'DRAFT · NOT COUNTED YET'} on={final} dashed={!final} />
        </View>
      </View>

      <View style={{ gap: 10 }}>
        <Eyebrow>PHOTOS OF THE CARD · {k.photos.length} / {MAX_PHOTOS}</Eyebrow>
        {cfg.data && !cfg.data.aiOn && (
          <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>Kept with the card for reference — reading photos needs the AI switched on (GEMINI_API_KEY on the server).</T>
        )}
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
                {cfg.data?.aiOn && <Btn kind="text" label={p.read ? 'Read again' : 'Read with AI'} busy={busy === `read${p.n}`} busyLabel="Reading"
                                        onPress={() => readPhoto(p)} style={{ height: 36 }} />}
                <Btn kind="text" label="Delete" onPress={() => removePhoto(p)} style={{ height: 36 }} />
              </View>
            </View>
          </View>
        ))}
        {k.photos.length < MAX_PHOTOS && (
          <Btn kind="secondary" label="Add a photo" icon={I.camera} busy={busy === 'add'} busyLabel="Uploading" onPress={add} />
        )}
      </View>

      {read && (
        <View accessibilityLiveRegion="polite" style={{ gap: 10, padding: 14, borderWidth: 1, borderColor: c.ink }}>
          <Eyebrow color="ink">PHOTO {read.n + 1} · WHAT THE AI READ</Eyebrow>
          <T size={14.5} style={{ lineHeight: 21 }}>
            {read.players} player{read.players === 1 ? '' : 's'} read off the photo.
            {read.unmatched ? ` ${read.unmatched} row${read.unmatched === 1 ? '' : 's'} need${read.unmatched === 1 ? 's' : ''} a student picked.` : ''}
            {read.unread ? ` ${read.unread} cell${read.unread === 1 ? '' : 's'} couldn’t be read and will be saved as 0.` : ''}
          </T>
          <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>
            It goes on the card as a draft{final ? ' (this takes the finished card out of the reports until you finish it again)' : ''}. Check every number against the paper on the website, then finish it there.
          </T>
          <Btn label="Save to the card" busy={busy === 'save'} busyLabel="Saving" onPress={keep} />
          <Btn kind="text" label="Don’t save" onPress={() => setRead(null)} />
        </View>
      )}
      <Note>{error}</Note>

      {pc.rows.length > 0 ? (
        <View style={{ gap: 10 }}>
          <Eyebrow>PART C · WORKED OUT FROM THE LAST SAVE</Eyebrow>
          <PartC part={pc} />
          <View>
            <Eyebrow style={{ paddingTop: 8, paddingBottom: 4 }}>{pc.teamTitle.toUpperCase()}</Eyebrow>
            {pc.team.map((t, i) => <Row key={t.key} a={t.label} b={t.value} last={i === pc.team.length - 1} />)}
            {!!pc.teamNote && <T size={12} color="ink2" style={{ paddingTop: 8, lineHeight: 17 }}>{pc.teamNote}</T>}
          </View>
        </View>
      ) : (
        <View style={{ flexDirection: 'row', gap: 10, alignItems: 'flex-start' }}>
          <Icon d={I.info} size={16} />
          <T size={13.5} color="ink2" style={{ flex: 1, lineHeight: 19 }}>No players on the card yet — read a photo, or type the card in on the website.</T>
        </View>
      )}

      <Btn kind="text" label="Delete this card" icon={I.delete} busy={busy === 'delete'} busyLabel="Deleting" onPress={remove} />
    </Screen>
  )
}

// Part C as a table that scrolls sideways, numbers right-aligned under their headings.
function PartC({ part }) {
  const { c } = useTheme()
  const numeric = part.columns.map((_, j) => part.rows.some(r => isNum(r[j])) && part.rows.every(r => !r[j] || isNum(r[j])))
  const cell = (text, j, head) => (
    <View key={j} style={{ width: j === 0 ? 132 : 76, paddingVertical: 8, paddingHorizontal: 6 }}>
      <Mono size={head ? 9.5 : 12} color={head ? 'ink2' : 'ink'} numberOfLines={head ? 3 : 1}
            style={{ textAlign: numeric[j] ? 'right' : 'left', letterSpacing: head ? 0.6 : 0 }}>
        {head ? String(text).toUpperCase() : text || '—'}
      </Mono>
    </View>
  )
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator style={{ borderTopWidth: 1, borderTopColor: c.ink }}>
      <View>
        <View style={{ flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: c.line }}>{part.columns.map((h, j) => cell(h, j, true))}</View>
        {part.rows.map((r, i) => (
          <View key={i} style={{ flexDirection: 'row', borderBottomWidth: 1, borderBottomColor: c.line }}>{r.map((v, j) => cell(v, j))}</View>
        ))}
      </View>
    </ScrollView>
  )
}
