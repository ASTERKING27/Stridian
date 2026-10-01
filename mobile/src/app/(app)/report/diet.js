import { View } from 'react-native'
import { useTheme } from '../../../lib/theme'
import { Eyebrow, Mono, Note, T, Title } from '../../../ui'
import Page, { useReportPage } from '../../../report/Page'

// Daily fuelling targets and a day of eating, already filtered for preferences and allergies.
export default function Diet() {
  const { data, error } = useReportPage()
  const { c } = useTheme()
  const d = data?.diet
  const t = d?.targets
  const tile = (k, v, s) => (
    <View key={k} style={{ flexBasis: '47%', flexGrow: 1, borderWidth: 1, borderColor: c.ink, padding: 12, gap: 4 }}>
      <Eyebrow>{k}</Eyebrow>
      <Mono size={22} font="monoMedium">{v}</Mono>
      <T size={11.5} color="ink2">{s}</T>
    </View>
  )
  return (
    <Page data={data} error={error}>
      {d && !d.available && (
        <>
          <Title eyebrow="DIET">Not enough to work from</Title>
          <T size={14} color="ink2">{d.reason}</T>
        </>
      )}
      {d?.available && (
        <>
          <Title eyebrow={`${d.dietPreference} · ${d.style}-WEIGHTED SPORT`.toUpperCase()}>Daily fuelling</Title>
          {d.allergies.length > 0 && <T size={13} color="ink2">Avoiding {d.allergies.join(', ')}.</T>}
          <View style={{ flexDirection: 'row', flexWrap: 'wrap', gap: 10 }}>
            {tile('ENERGY', t.kcal.toLocaleString(), `kcal a day · ${t.per_kg.kcal} per kg`)}
            {tile('CARBOHYDRATE', `${t.carbs_g} g`, 'the main fuel')}
            {tile('PROTEIN', `${t.protein_g} g`, `~${Math.round(t.protein_g / 4.5)} g per meal`)}
            {tile('WATER', `${(t.hydration_ml / 1000).toFixed(1)} L`, 'plus 500–750 ml per extra hour')}
          </View>
          <View style={{ gap: 8 }}>
            <Eyebrow>WHERE THE ENERGY COMES FROM</Eyebrow>
            <View style={{ flexDirection: 'row', height: 14, borderWidth: 1, borderColor: c.ink }}>
              <View style={{ flex: t.carbs_kcal, backgroundColor: c.ink }} />
              <View style={{ flex: t.protein_kcal, backgroundColor: c.ink2 }} />
              <View style={{ flex: t.fat_kcal, backgroundColor: c.line }} />
            </View>
            <View style={{ flexDirection: 'row', gap: 14, flexWrap: 'wrap' }}>
              {[['CARBS', c.ink, t.carbs_g], ['PROTEIN', c.ink2, t.protein_g], ['FAT', c.line, t.fat_g]].map(([k, col, g]) => (
                <View key={k} style={{ flexDirection: 'row', alignItems: 'center', gap: 6 }}>
                  <View style={{ width: 10, height: 10, backgroundColor: col, borderWidth: 1, borderColor: c.ink }} />
                  <Mono size={10.5}>{k} {g} G</Mono>
                </View>
              ))}
            </View>
          </View>
          <View>
            <Eyebrow style={{ paddingBottom: 8 }}>A DAY OF EATING · PICK ONE PER MEAL</Eyebrow>
            {d.meals.map(m => (
              <View key={m.slot} style={{ gap: 6, paddingVertical: 12, borderTopWidth: 1, borderTopColor: c.line }}>
                <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                  <T font="semi" size={15}>{m.label}</T><Mono size={12}>{m.kcal} KCAL</Mono>
                </View>
                {m.options.length === 0
                  ? <T size={13.5} color="ink2">No option fits the current restrictions — plan this one with your coach.</T>
                  : m.options.map(o => <T key={o.name} size={14} style={{ lineHeight: 20 }}>{o.name} <T size={12} color="ink2">· {o.tag}</T></T>)}
              </View>
            ))}
          </View>
          <View>
            <Eyebrow style={{ paddingBottom: 8 }}>HOW TO USE IT</Eyebrow>
            {d.notes.map((n, i) => <T key={i} size={14} style={{ lineHeight: 20, paddingVertical: 6 }}>{n}</T>)}
          </View>
          <Note tone="info">{d.disclaimer}</Note>
        </>
      )}
    </Page>
  )
}
