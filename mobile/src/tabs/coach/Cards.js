import { useState } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import * as Print from 'expo-print'
import { api } from '../../lib/api'
import { blankCardHtml, printedSquad } from '../../lib/blankCard'
import { mergeReading } from '../../lib/cards'
import { pickPhoto } from '../../lib/media'
import { primed } from '../../lib/notifications'
import { useBackInView, useData } from '../../lib/useData'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Btn, Choice, Eyebrow, H1, I, Lap, Mono, Note, OfflineBar, Screen, Switch, T, Tag, Top } from '../../ui'
import { LoadError } from '../../ui/States'

const HOME = 'SRMIST'
const shortDate = iso => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()
// the tournament is the heading; who played is the line under it
export const cardTitle = h => h.tournament || 'Match card'
export const cardVs = h => `${HOME} vs ${h.opponent || '—'}`

/* A photo on the card read by the AI and saved into it as a draft — the newest photo
   unless told which. Resolves to { card, read } or, when it couldn't be, { card, error }. */
export async function readInto(card, photo = card.photos.at(-1)) {
  try {
    const read = mergeReading(card, await api.readCardPhoto(card.id, photo.n, photo.v))
    return { card: await api.saveCard(card.id, read.body), read }
  } catch (err) {
    return { card, error: err.message }
  }
}
// what the card page says about the reading it lands from
export const readParams = ({ read, error }) => (error ? { problem: error }
  : read ? { players: String(read.players), unmatched: String(read.unmatched), unread: String(read.unread) } : {})

/* Match cards: the paper sheet the scorer fills in during a match. On the phone a coach
   prints it blank, then uploads a photo of it filled in — the AI reads it into the card,
   and the phone shows what went in. Correcting and finishing it happen on the website. */
export default function Cards({ active }) {
  const s = useSession()
  const { c } = useTheme()
  const cards = useData(api.cards, [s.coach?.sport])
  const [mode, setMode] = useState(null)              // 'upload' | 'print'
  useBackInView(cards.reload, active)
  const list = cards.data

  return (
    <View style={{ flex: 1 }}>
      {cards.error?.offline && <OfflineBar note={list ? 'SHOWING WHAT WAS LOADED' : 'NOTHING LOADED YET'} onRetry={cards.refresh} />}
      <Screen bottom={110} gap={16} refreshing={cards.refreshing} onRefresh={cards.refresh}>
        <Top context={contextLine(s)} />
        {cards.error?.offline && <View style={{ height: 40 }} />}
        <View style={{ gap: 8 }}>
          <Eyebrow>READ FROM A PHOTO</Eyebrow>
          <H1>Match cards</H1>
        </View>
        {mode === 'upload' ? <Upload onClose={() => setMode(null)} />
          : mode === 'print' ? <PrintCard onClose={() => setMode(null)} /> : (
            <>
              <T size={14} color="ink2" style={{ lineHeight: 20 }}>
                Print a blank card for the scorer. After the match, upload a photo of it filled in — the AI reads it and fills the
                card in. To correct anything or finish the card, use the website.
              </T>
              <Btn label="Upload a filled card" icon={I.camera} onPress={() => setMode('upload')} />
              <Btn kind="secondary" label="Print a blank card" icon={I.print} onPress={() => setMode('print')} />
            </>
          )}
        <LoadError error={cards.error} onRetry={cards.refresh} hasData={!!list} />
        {!list && !cards.error && <Lap size={28} />}
        {list?.length === 0 && !mode && <T font="semi" size={16}>No cards yet</T>}
        <View>
          {(list ?? []).map((x, i) => (
            <Pressable key={x.id} onPress={() => router.push({ pathname: '/card/[id]', params: { id: x.id } })} accessibilityRole="button"
                       style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12,
                                                  borderTopWidth: 1, borderTopColor: c.line, borderBottomWidth: i === list.length - 1 ? 1 : 0,
                                                  borderBottomColor: c.line, backgroundColor: pressed ? c.soft : 'transparent' })}>
              <View style={{ flex: 1, gap: 3 }}>
                <T font="semi" size={15} numberOfLines={1}>{cardTitle(x)}</T>
                <T size={13.5} numberOfLines={1}>{cardVs(x)}</T>
                <Mono size={10} color="ink2" style={{ letterSpacing: 0.5, paddingTop: 2 }} numberOfLines={2}>
                  {[x.date ? shortDate(x.date) : 'NO DATE', x.round?.toUpperCase(), x.match_no && `MATCH ${x.match_no}`, x.result?.toUpperCase(),
                    x.category === 'W' ? 'WOMEN' : 'MEN', `${x.players} PLAYER${x.players === 1 ? '' : 'S'}`].filter(Boolean).join(' · ')}
                </Mono>
              </View>
              <Tag label={x.status === 'final' ? 'FINISHED' : 'DRAFT'} on={x.status === 'final'} dashed={x.status !== 'final'} />
            </Pressable>
          ))}
        </View>
      </Screen>
    </View>
  )
}

// Men or Women, and the format where the sport has more than one — both forms ask it.
function Team({ cfg, f, set }) {
  const formats = cfg?.formats ?? []
  return (
    <>
      <Choice options={[['M', 'Men'], ['W', 'Women']]} value={f.category} onChange={set('category')} />
      {formats.length > 0 && (
        <View style={{ gap: 8 }}>
          <Eyebrow>FORMAT</Eyebrow>
          <Choice options={formats.map(x => [x.key, x.label])} value={f.format || cfg.format} onChange={set('format')} />
        </View>
      )}
    </>
  )
}

/* The photo goes up as a new card, the AI reads it into the card, and the card opens
   showing what was filled in. Tournament, opponent, date and every row come off the photo. */
function Upload({ onClose }) {
  const { c } = useTheme()
  const cfg = useData(() => api.cardsConfig(), [])
  const [f, setF] = useState({ category: 'M', format: '' })
  const [step, setStep] = useState('')
  const [error, setError] = useState('')
  const set = k => v => setF(x => ({ ...x, [k]: v }))

  async function go(camera) {
    setError('')
    // the first time, say why the camera is needed before the phone asks
    if (camera && !(await primed('camera'))) return router.push({ pathname: '/primer', params: { kind: 'camera' } })
    let card = null
    try {
      const p = await pickPhoto({ camera, maxSide: 2400, quality: 0.85 })
      if (!p) return
      setStep('Uploading')
      card = await api.createCard({ category: f.category, format: f.format || cfg.data.format || null, header: {} })
      card = await api.addCardPhoto(card.id, p.uri, p.type)
    } catch (err) {
      if (card) api.deleteCard(card.id).catch(() => {})       // no half-made card left behind
      haptic.error()
      setError(err.message)
      setStep('')
      return
    }
    let done = { card }
    if (cfg.data.aiOn) {
      setStep('Reading the card')
      done = await readInto(card)
    }
    if (done.error) haptic.error(); else haptic.success()
    setStep('')
    onClose()
    router.push({ pathname: '/card/[id]', params: { id: card.id, ...readParams(done) } })
  }

  return (
    <View style={{ gap: 16, padding: 14, borderWidth: 1, borderColor: c.ink }}>
      <Eyebrow color="ink">UPLOAD A FILLED CARD</Eyebrow>
      <Team cfg={cfg.data} f={f} set={set} />
      <T size={13} color="ink2" style={{ lineHeight: 18 }}>
        {cfg.data && !cfg.data.aiOn ? 'The photo is kept with the card — reading it needs the AI switched on (GEMINI_API_KEY on the server), so fill the card in on the website.'
          : 'Part A flat, in good light, the whole sheet in frame. The AI fills in the tournament, the opponent and every player’s row.'}
      </T>
      <Note>{error || cfg.error?.message}</Note>
      {step ? <Btn label={step} busy busyLabel={step} onPress={() => {}} /> : (
        <>
          <Btn label="Take a photo" icon={I.camera} disabled={!cfg.data} onPress={() => go(true)} />
          <Btn kind="secondary" label="Choose a photo" icon={I.gallery} disabled={!cfg.data} onPress={() => go(false)} />
          <Btn kind="text" label="Cancel" onPress={onClose} />
        </>
      )}
    </View>
  )
}

/* Part A blank, to the phone's printer (or saved as a PDF from the print screen) — with
   the team's names and shirt numbers already written in, or blank rows. */
function PrintCard({ onClose }) {
  const { c } = useTheme()
  const cfg = useData(() => api.cardsConfig(), [])
  const students = useData(api.students, [])
  const [f, setF] = useState({ category: 'M', format: '' })
  const [names, setNames] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = k => v => setF(x => ({ ...x, [k]: v }))
  const squad = printedSquad(students.data ?? [], f.category)
  const racket = cfg.data?.layout === 'player'
  const sheets = racket && names ? Math.max(squad.length, 1) : 1

  async function print() {
    setBusy(true)
    setError('')
    try {
      const html = blankCardHtml({ ...cfg.data, category: f.category, format: f.format || cfg.data.format }, names ? squad : [])
      await Print.printAsync({ html, width: 842, height: 595 })       // A4 landscape, in points
    } catch (err) {
      haptic.error()
      setError(err.message)
    }
    setBusy(false)
  }

  return (
    <View style={{ gap: 16, padding: 14, borderWidth: 1, borderColor: c.ink }}>
      <Eyebrow color="ink">PRINT A BLANK CARD</Eyebrow>
      <Team cfg={cfg.data} f={f} set={set} />
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14, paddingTop: 12, borderTopWidth: 1, borderTopColor: c.line }}>
        <View style={{ flex: 1, gap: 3 }}>
          <T size={15}>Print the squad’s names</T>
          <T size={12} color="ink2" style={{ lineHeight: 17 }}>
            {!names ? 'Blank rows — the scorer writes the names in.'
              : !students.data ? 'Loading the squad…'
                : squad.length === 0 ? `No ${f.category === 'W' ? 'women' : 'men'} in the squad yet — it prints blank.`
                  : `${squad.length} player${squad.length === 1 ? '' : 's'}${squad.some(p => p.jersey != null) ? ' with shirt numbers' : ''}${
                    racket ? ` · one sheet each` : ''}`}
          </T>
        </View>
        <Switch value={names} onChange={setNames} label="Print the squad’s names" />
      </View>
      <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>
        Prints Part A — the sheet the scorer fills in and you photograph{sheets > 1 ? ` (${sheets} sheets)` : ''}. A4, landscape. The full set,
        with Parts B to D, prints from the website.
      </T>
      <Note>{error || cfg.error?.message || students.error?.message}</Note>
      <Btn label="Print" icon={I.print} busy={busy} busyLabel="Opening the printer" disabled={!cfg.data || (names && !students.data)} onPress={print} />
      <Btn kind="text" label="Cancel" onPress={onClose} />
    </View>
  )
}
