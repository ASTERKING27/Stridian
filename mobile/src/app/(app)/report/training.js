import { View } from 'react-native'
import { focusPosition } from '../../../lib/report'
import { useTheme } from '../../../lib/theme'
import { Eyebrow, Mono, T, Title } from '../../../ui'
import Page, { useReportPage } from '../../../report/Page'

// What to work on: weakest-and-most-relevant first from the tests, then what the video found.
export default function Training() {
  const { data, error } = useReportPage()
  const { c } = useTheme()
  const plan = data?.developmentPlan ?? []
  const drills = (data?.videos ?? []).flatMap(v => v.metrics?.drills ?? [])
  const role = data && (data.levels?.position ?? focusPosition(data)?.position)
  const item = { gap: 6, paddingVertical: 13, borderTopWidth: 1, borderTopColor: c.line }
  return (
    <Page data={data} error={error}>
      {data && (
        <>
          <Title eyebrow={`FOR ${String(role ?? 'THE TOP ROLE').toUpperCase()}`}>Training plan</Title>
          <View>
            <Eyebrow style={{ paddingBottom: 8 }}>FROM THE TESTS</Eyebrow>
            {plan.length === 0
              ? <T size={14} color="ink2">Nothing scored below 40 — no priority weak point from the tests.</T>
              : plan.map(p => (
                <View key={p.key} style={item}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                    <T font="semi" size={15} style={{ flex: 1 }}>{p.label}</T>
                    <Mono size={12}>{Math.round(p.score)}/100</Mono>
                  </View>
                  <T size={14} color="ink2" style={{ lineHeight: 20 }}>{p.tip}</T>
                </View>
              ))}
          </View>
          <View>
            <Eyebrow style={{ paddingBottom: 8 }}>FROM THE VIDEO</Eyebrow>
            {(data.videos ?? []).length === 0
              ? <T size={14} color="ink2">Movement work appears here once a drill clip has been analysed.</T>
              : drills.length === 0
                ? <T size={14} color="ink2">Nothing in the clips crossed a coaching threshold.</T>
                : drills.map((d, i) => (
                  <View key={i} style={item}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10 }}>
                      <T font="semi" size={15} style={{ flex: 1 }}>{d.finding}</T>
                      {d.value != null && <Mono size={12}>{d.value}</Mono>}
                    </View>
                    <T size={13.5} color="ink2" style={{ lineHeight: 19 }}>{d.why}</T>
                    <T size={14} style={{ lineHeight: 20 }}>{d.drill}</T>
                  </View>
                ))}
          </View>
        </>
      )}
    </Page>
  )
}
