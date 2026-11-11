import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { useTheme } from '../../../lib/theme'
import { Bar, I, Icon, Mono, T, Title } from '../../../ui'
import Page, { useReportPage } from '../../../report/Page'

// Every position ranked by fit; each opens its own "why".
export default function Positions() {
  const { data, error, id } = useReportPage()
  const { c } = useTheme()
  return (
    <Page data={data} error={error}>
      {data && (
        <>
          <Title eyebrow={`${data.sport.toUpperCase()} · RANKED`}>Every position</Title>
          <View>
            {data.positions.map((p, i) => (
              <Pressable key={p.position} accessibilityRole="button"
                         onPress={() => router.push({ pathname: '/report/why', params: { ...(id ? { id } : {}), position: p.position } })}
                         style={({ pressed }) => ({ gap: 8, paddingVertical: 13, borderTopWidth: 1, borderTopColor: c.line,
                                                    backgroundColor: pressed ? c.soft : 'transparent' })}>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12 }}>
                  <Mono size={11} color="ink2" style={{ width: 18 }}>{String(i + 1).padStart(2, '0')}</Mono>
                  <T font={i === 0 ? 'semi' : 'body'} size={15} style={{ flex: 1 }}>{p.position}</T>
                  <Mono size={15}>{p.fit == null ? '—' : Math.round(p.fit)}</Mono>
                  <Icon d={I.next} size={16} />
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingLeft: 30 }}>
                  <Bar value={(p.fit ?? 0) / 100} style={{ flex: 1 }} />
                  <Mono size={10} color="ink2" style={{ letterSpacing: 0.8 }}>{(p.confidence ?? '').toUpperCase()} CONFIDENCE</Mono>
                </View>
              </Pressable>
            ))}
          </View>
        </>
      )}
    </Page>
  )
}
