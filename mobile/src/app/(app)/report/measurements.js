import { View } from 'react-native'
import { formatValue } from '../../../lib/api'
import { useTheme } from '../../../lib/theme'
import { Bar, Eyebrow, Mono, T, Title } from '../../../ui'
import Page, { useReportPage } from '../../../report/Page'

const GROUPS = [['TEST BATTERY & PHYSIQUE', m => m.source === 'test' || m.source === 'profile'],
                ['MATCH CARDS', m => m.source === 'card'], ['MATCH FOOTAGE', m => m.source === 'match']]

// Every result with its 0–100 score — 60 and up is a strength, under 40 a weak link.
export default function Measurements() {
  const { data, error } = useReportPage()
  const { c } = useTheme()
  return (
    <Page data={data} error={error}>
      {data && (
        <>
          <Title eyebrow="SCORED 0–100 ON THE LEVEL LADDER">Measurements</Title>
          {GROUPS.map(([title, match]) => {
            const rows = data.metrics.filter(m => match(m) && !m.role)
            if (!rows.length) return null
            return (
              <View key={title}>
                <Eyebrow style={{ paddingBottom: 8 }}>{title}</Eyebrow>
                {rows.map(m => (
                  <View key={m.key} style={{ gap: 8, paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.line }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 12 }}>
                      <T size={15} style={{ flex: 1 }}>{m.label}</T>
                      <Mono size={14}>{formatValue(m.value, m)}</Mono>
                    </View>
                    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                      <Bar value={(m.score ?? 0) / 100} style={{ flex: 1 }} />
                      <Mono size={11} color={m.score == null ? 'ink2' : 'ink'} style={{ width: 92, textAlign: 'right' }}>
                        {m.score == null ? 'NOT MEASURED' : `${Math.round(m.score)} · ${m.score >= 60 ? 'STRONG' : m.score < 40 ? 'WORK ON' : 'AVERAGE'}`}
                      </Mono>
                    </View>
                  </View>
                ))}
              </View>
            )
          })}
        </>
      )}
    </Page>
  )
}
