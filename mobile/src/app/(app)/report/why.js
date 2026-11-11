import { View } from 'react-native'
import { useLocalSearchParams } from 'expo-router'
import { formatValue } from '../../../lib/api'
import { breakdown, focusPosition } from '../../../lib/report'
import { useTheme } from '../../../lib/theme'
import { Bar, Eyebrow, Mono, T } from '../../../ui'
import Page, { useReportPage } from '../../../report/Page'

const a = w => (/^[aeiou]/i.test(w) ? 'an' : 'a')

// Results board, 02: every measure behind the fit — its weight and the points it adds.
export default function Why() {
  const { data, error, id } = useReportPage()
  const { position } = useLocalSearchParams()
  const { c } = useTheme()
  const pos = data && (data.positions.find(p => p.position === position) ?? focusPosition(data))
  const rows = data ? breakdown(pos, data.metrics) : []
  const full = !!pos?.contributions
  const fit = pos?.fit == null ? '—' : Math.round(pos.fit)
  const lever = rows.map(r => ({ ...r, room: (100 - r.score) * r.share })).sort((x, y) => y.room - x.room)[0]
  const up = lever ? Math.min(100, lever.score + 10) - lever.score : 0
  const untested = (pos?.missing ?? []).filter(m => !/^(match|card_)/.test(m.key))

  return (
    <Page data={data} error={error}>
      {pos && (
        <>
          <View style={{ gap: 8 }}>
            <Eyebrow>WHY {pos.position.toUpperCase()}</Eyebrow>
            <T font="medium" size={26} style={{ lineHeight: 30 }}>
              {id ? 'Their' : 'Your'} {full ? `${rows.length} ` : ''}scores, weighted the way {a(pos.position)} {pos.position} is judged.
            </T>
          </View>
          <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
            <Mono size={10} color="ink2" style={{ letterSpacing: 1 }}>MEASURE · SCORE</Mono>
            <Mono size={10} color="ink2" style={{ letterSpacing: 1 }}>WEIGHT · ADDS</Mono>
          </View>
          <View style={{ marginTop: -8 }}>
            {rows.map(r => (
              <View key={r.key} style={{ gap: 9, paddingVertical: 13, borderTopWidth: 1, borderTopColor: c.line }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', gap: 10 }}>
                  <T size={15} style={{ flex: 1 }}>{r.label}</T>
                  <Mono size={12} color="ink2">×{Math.round(r.share * 100)}%</Mono>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                  <Mono size={11} color="ink2" style={{ width: 64 }} numberOfLines={1}>{formatValue(r.metric?.value, r.metric)}</Mono>
                  <Bar value={r.score / 100} h={6} style={{ flex: 1 }} />
                  <Mono size={12} style={{ width: 24, textAlign: 'right' }}>{Math.round(r.score)}</Mono>
                  <Mono size={13} font="monoMedium" style={{ width: 40, textAlign: 'right' }}>+{r.adds.toFixed(1)}</Mono>
                </View>
              </View>
            ))}
            {full && (
              <View style={{ flexDirection: 'row', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: 14,
                             borderTopWidth: 1, borderTopColor: c.ink }}>
                <Mono size={11} style={{ letterSpacing: 1.32 }}>FIT FOR {pos.position.toUpperCase()}</Mono>
                <Mono size={24} font="monoMedium">{fit}</Mono>
              </View>
            )}
          </View>
          {!full && (
            <T size={12.5} color="ink2">These are the measures that moved the fit most; the full breakdown arrives with the next server update.</T>
          )}
          {!!lever && full && (
            <View style={{ borderWidth: 1, borderColor: c.ink, paddingVertical: 14, paddingHorizontal: 16, gap: 5 }}>
              <Eyebrow>BIGGEST LEVER</Eyebrow>
              <T size={15} style={{ lineHeight: 20 }}>
                {lever.label} carries {Math.round(lever.share * 100)}% of the score and sits at {Math.round(lever.score)}.
                {up > 0 ? ` Moving it to ${Math.round(lever.score + up)} adds ${(up * lever.share).toFixed(1)} to ${id ? 'their' : 'your'} fit.` : ''}
              </T>
            </View>
          )}
          {/* tests not done yet; footage and match cards fill in on their own */}
          {!!untested.length && (
            <View>
              <Eyebrow style={{ paddingBottom: 6 }}>NOT TESTED YET</Eyebrow>
              <T size={13.5} color="ink2" style={{ lineHeight: 19 }}>{untested.map(m => m.label).join(' · ')}</T>
            </View>
          )}
        </>
      )}
    </Page>
  )
}
