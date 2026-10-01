import { useState } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { api } from '../../lib/api'
import { useBackInView, useData } from '../../lib/useData'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Btn, Choice, Eyebrow, Field, H1, I, Lap, Mono, Note, OfflineBar, Screen, T, Tag, Top } from '../../ui'
import { dmyMask, toDMY, toISO } from '../../ui/DetailsForm'

const pad = n => String(n).padStart(2, '0')
const todayISO = () => { const d = new Date(); return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` }
const shortDate = iso => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()
export const cardTitle = h => `${h.tournament || 'Untitled match'}${h.opponent ? ` vs ${h.opponent}` : ''}`

/* Match cards: the paper sheet the scorer fills in during a match. On the phone a coach
   starts a card, photographs the paper and has it read; the grid itself is checked,
   corrected and finished on the website. */
export default function Cards({ active }) {
  const s = useSession()
  const { c } = useTheme()
  const cards = useData(api.cards, [s.coach?.sport])
  const [adding, setAdding] = useState(false)
  useBackInView(cards.reload, active)
  const list = cards.data

  return (
    <View style={{ flex: 1 }}>
      {cards.error?.offline && <OfflineBar note={list ? 'SHOWING WHAT WAS LOADED' : 'NOTHING LOADED YET'} onRetry={cards.refresh} />}
      <Screen bottom={110} gap={16} refreshing={cards.refreshing} onRefresh={cards.refresh}>
        <Top context={contextLine(s)} />
        {cards.error?.offline && <View style={{ height: 40 }} />}
        <View style={{ flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between' }}>
          <View style={{ gap: 8 }}>
            <Eyebrow>READ FROM A PHOTO</Eyebrow>
            <H1>Match cards</H1>
          </View>
          {!adding && <Btn kind="icon" icon={I.add} accessibilityLabel="New card" onPress={() => setAdding(true)} />}
        </View>
        {adding ? <NewCard onCancel={() => setAdding(false)} /> : (
          <T size={14} color="ink2" style={{ lineHeight: 20 }}>
            After a match, start its card and photograph the paper — the AI reads every row. Check the numbers and finish the card on the
            website; a finished card feeds each player’s report.
          </T>
        )}
        {cards.error && !cards.error.offline && <Note>{cards.error.message}</Note>}
        {!list && !cards.error && <Lap size={28} />}
        {list?.length === 0 && !adding && <T font="semi" size={16}>No cards yet</T>}
        <View>
          {(list ?? []).map((x, i) => (
            <Pressable key={x.id} onPress={() => router.push({ pathname: '/card/[id]', params: { id: x.id } })} accessibilityRole="button"
                       style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 12,
                                                  borderTopWidth: 1, borderTopColor: c.line, borderBottomWidth: i === list.length - 1 ? 1 : 0,
                                                  borderBottomColor: c.line, backgroundColor: pressed ? c.soft : 'transparent' })}>
              <View style={{ flex: 1, gap: 4 }}>
                <T font="semi" size={15} numberOfLines={1}>{cardTitle(x)}</T>
                <Mono size={10} color="ink2" style={{ letterSpacing: 0.5 }} numberOfLines={2}>
                  {[x.date ? shortDate(x.date) : 'NO DATE', x.match_no && `MATCH ${x.match_no}`, x.result?.toUpperCase(),
                    x.category === 'W' ? 'WOMEN' : 'MEN', `${x.players} PLAYER${x.players === 1 ? '' : 'S'}`,
                    x.photos && `${x.photos} PHOTO${x.photos === 1 ? '' : 'S'}`].filter(Boolean).join(' · ')}
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

function NewCard({ onCancel }) {
  const { c } = useTheme()
  const cfg = useData(() => api.cardsConfig(), [])
  const [f, setF] = useState({ category: 'M', format: '', date: toDMY(todayISO()), tournament: '', opponent: '' })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const set = k => v => setF(x => ({ ...x, [k]: v }))
  const formats = cfg.data?.formats ?? []

  async function start() {
    setBusy(true)
    setError('')
    try {
      const card = await api.createCard({
        category: f.category, format: f.format || cfg.data?.format || null,
        header: { tournament: f.tournament.trim(), opponent: f.opponent.trim(), date: toISO(f.date) || null },
      })
      haptic.success()
      onCancel()
      router.push({ pathname: '/card/[id]', params: { id: card.id } })
    } catch (err) {
      haptic.error()
      setError(err.message)
    }
    setBusy(false)
  }

  return (
    <View style={{ gap: 16, padding: 14, borderWidth: 1, borderColor: c.ink }}>
      <Eyebrow color="ink">NEW CARD</Eyebrow>
      <Choice options={[['M', 'Men'], ['W', 'Women']]} value={f.category} onChange={set('category')} />
      {formats.length > 0 && (
        <View style={{ gap: 8 }}>
          <Eyebrow>FORMAT</Eyebrow>
          <Choice options={formats.map(x => [x.key, x.label])} value={f.format || cfg.data.format} onChange={set('format')} />
        </View>
      )}
      <Field label="DATE" value={f.date} onChangeText={v => set('date')(dmyMask(v))} keyboardType="number-pad" placeholder="DD/MM/YYYY" />
      <Field label="TOURNAMENT" value={f.tournament} onChangeText={set('tournament')} maxLength={120} />
      <Field label="OPPONENT" value={f.opponent} onChangeText={set('opponent')} maxLength={120} />
      <Note>{error || cfg.error?.message}</Note>
      <Btn label="Start the card" busy={busy} busyLabel="Starting" disabled={!cfg.data} onPress={start} />
      <Btn kind="text" label="Cancel" onPress={onCancel} />
    </View>
  )
}
