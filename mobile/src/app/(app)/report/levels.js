import { View } from 'react-native'
import { formatValue } from '../../../lib/api'
import { useTheme } from '../../../lib/theme'
import { Bar, Eyebrow, H1, Mono, Note, T } from '../../../ui'
import Page, { useReportPage } from '../../../report/Page'

const GROUPS = [
  ['test', 'TEST BATTERY & PHYSIQUE', r => r.source === 'test' || r.source === 'profile'],
  ['card', 'MATCH CARDS', r => r.source === 'card'],
  ['match', 'MATCH FOOTAGE · COUNTS HALF', r => r.source === 'match'],
]
const SHORT = ['U', 'Z', 'S', 'N', 'I']
const name = (lv, i) => (i == null ? '—' : i < 0 ? 'Below University' : lv.levels[i])

// met, or how far off ("+2 cm", "−0.08 s")
function gap(r, target) {
  if ((r.value - target) * (r.better === 'lower' ? -1 : 1) >= -1e-9) return '✓'
  if (r.unit === 'level') return 'not yet'
  const d = target - r.value
  const n = Number(Math.abs(d).toFixed(Math.abs(d) < 1 ? 2 : Math.abs(d) < 10 ? 1 : 0))
  const u = r.unit === 'sec' ? 's' : r.unit
  return `${d > 0 ? '+' : '−'}${n}${u === '%' ? '%' : u ? ` ${u}` : ''}`
}

// Every number against University → International, and the level they play at.
export default function Levels() {
  const { data, error, id } = useReportPage()
  const { c } = useTheme()
  const lv = data?.levels
  const they = id ? 'they' : 'you'
  return (
    <Page data={data} error={error}>
      {lv && (
        <>
          <View style={{ gap: 8 }}>
            <Eyebrow>{lv.overall.level != null && lv.overall.level >= 0 ? 'PLAYS AT' : 'LEVEL'}</Eyebrow>
            <H1>{lv.overall.level != null ? `${name(lv, lv.overall.level)} level` : 'Not enough measured yet'}</H1>
            <T size={13.5} color="ink2" style={{ lineHeight: 19 }}>
              Each level’s target is what players at that level typically post. Every score in the report is read off
              the same ladder: University 20, Zonal 40, State 60, National 80, International 100.
              {lv.overall.level == null && lv.overall.measures > 0 ? ` A level needs at least 3 comparable measures (${lv.overall.measures} so far).` : ''}
            </T>
          </View>
          {!lv.category && (
            <Note tone="info">
              {id ? 'Their team (men’s or women’s) isn’t set, so tests can’t be compared with a level.'
                : 'Your team (men’s or women’s) isn’t set yet, so your tests can’t be compared with a level — add it on your Profile.'}
            </Note>
          )}

          {lv.standing.length > 0 && (
            <View>
              <Eyebrow style={{ paddingBottom: 8 }}>WHERE {they.toUpperCase()} STAND AT EVERY LEVEL</Eyebrow>
              {lv.standing.map((x, i) => ({ ...x, i })).reverse().map(x => (
                <View key={x.i} style={{ gap: 8, paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line }}>
                  <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
                    <T font={x.i === lv.overall.level ? 'semi' : 'body'} size={15}>
                      {lv.levels[x.i]}{x.i === lv.overall.level ? '  ·  PLAYS HERE' : ''}
                    </T>
                    <Mono size={12}>{Math.round(x.share * 100)}% · {x.met}/{x.of}</Mono>
                  </View>
                  <Bar value={x.share} />
                </View>
              ))}
            </View>
          )}

          {GROUPS.map(([key, title, match]) => {
            const rows = lv.rows.filter(match)
            if (!rows.length) return null
            return (
              <View key={key}>
                <Eyebrow style={{ paddingBottom: 8 }}>{title}</Eyebrow>
                {rows.map(r => (
                  <View key={r.key} style={{ gap: 10, paddingVertical: 13, borderTopWidth: 1, borderTopColor: c.line }}>
                    <View style={{ flexDirection: 'row', justifyContent: 'space-between', gap: 10 }}>
                      <View style={{ flex: 1, gap: 3 }}>
                        <T size={15}>{r.label}{r.basis === 'estimated' ? ' *' : ''}</T>
                        <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84 }}>
                          {r.level != null ? `REACHES ${name(lv, r.level).toUpperCase()}` : r.ladder ? '—' : 'NOT COMPARED'}
                        </Mono>
                      </View>
                      <Mono size={15}>{formatValue(r.value, r)}</Mono>
                    </View>
                    {!!r.ladder && (
                      <View style={{ flexDirection: 'row', gap: 4 }}>
                        {r.ladder.map((t, i) => {
                          const hit = r.level != null && i <= r.level
                          const g = r.level != null ? gap(r, t) : ''
                          return (
                            <View key={i} style={{ flex: 1, paddingVertical: 6, alignItems: 'center', gap: 2,
                                                   borderWidth: 1, borderColor: hit ? c.ink : c.line, backgroundColor: hit ? c.ink : 'transparent' }}>
                              <Mono size={9} color={hit ? c.bg : c.ink2}>{SHORT[i]}</Mono>
                              <Mono size={11} color={hit ? c.bg : c.ink}>{formatValue(t, { key: r.key })}</Mono>
                              {!!g && <Mono size={9} color={hit ? c.bg : c.ink2}>{g}</Mono>}
                            </View>
                          )
                        })}
                      </View>
                    )}
                  </View>
                ))}
              </View>
            )
          })}
          <T size={12} color="ink2" style={{ lineHeight: 17 }}>
            * Estimated: no published norm for this level, so the number was spaced between ones that are.
          </T>
        </>
      )}
    </Page>
  )
}
