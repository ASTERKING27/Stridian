import { useEffect, useMemo, useState } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { api, formatValue, getSports, initials } from '../../lib/api'
import { check, parseValue } from '../../lib/entry'
import { forgetReport } from '../../lib/report'
import { useBackInView, useData } from '../../lib/useData'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Btn, Eyebrow, Field, H1, I, Icon, LinkRow, Mono, Note, PersonRow, Placeholder, Screen, SearchField, T, Top } from '../../ui'
import { toast } from '../../ui/Toast'
import { metaOf } from './Squad'

const UNIT_WORD = { sec: 'SECONDS', cm: 'CM', level: 'LEVEL', 'km/h': 'KM/H', m: 'METRES', kg: 'KG' }

/* Record a testing session (Coach board, 07): pick the player, type each test, fix what
   can't be right, save. Only what's typed is sent — each value becomes a new dated
   result, so last time's numbers stay in their history rather than being saved again. */
export default function Entry({ active, params }) {
  const s = useSession()
  const sport = s.coach?.sport
  const squad = useData(api.students, [sport])
  const [tests, setTests] = useState([])
  const [pick, setPick] = useState(null)
  const [q, setQ] = useState('')
  useBackInView(squad.reload, active)

  useEffect(() => {
    getSports().then(list => setTests((list.find(x => x.name === sport)?.metrics ?? []).filter(m => m.source === 'test'))).catch(() => {})
  }, [sport])
  useEffect(() => { setPick(null) }, [sport])
  // "Record their results" on a student's page lands here with them picked
  useEffect(() => { if (params?.student) setPick(Number(params.student)) }, [params?.student, params?.at])

  const list = squad.data ?? []
  const student = list.find(x => x.id === pick)
  const visible = useMemo(() => {
    const term = q.trim().toLowerCase()
    return (squad.data ?? []).filter(x => !term || x.name.toLowerCase().includes(term) || (x.ra_number ?? '').toLowerCase().includes(term))
  }, [squad.data, q])
  const today = new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }).toUpperCase()

  return (
    <Screen bottom={110} gap={16} refreshing={squad.refreshing} onRefresh={squad.refresh}>
      <Top context={contextLine(s)} />
      <View style={{ gap: 8 }}>
        <Eyebrow>RECORD RESULTS · {today}</Eyebrow>
        <H1>Coach Entry</H1>
      </View>
      {squad.error && <Note>{squad.error.message}</Note>}
      {student ? (
        <Sheet key={student.id} student={student} tests={tests} onChange={() => setPick(null)} reload={squad.reload} />
      ) : (
        <>
          <SearchField value={q} onChangeText={setQ} />
          {!squad.data && !squad.error && <View style={{ gap: 12 }}>{[0, 1, 2, 3].map(i => <Placeholder key={i} h={50} />)}</View>}
          {squad.data && visible.length === 0 && (
            <T size={14} color="ink2" style={{ lineHeight: 20 }}>
              {list.length === 0 ? `No students yet — anyone who enrols in ${sport} appears here.` : 'Nobody matches that search.'}
            </T>
          )}
          <View>
            {visible.map((x, i) => (
              <PersonRow key={x.id} name={x.name} meta={metaOf(x)} onPress={() => { haptic.tick(); setPick(x.id) }}
                         last={i === visible.length - 1} right={<Icon d={I.next} size={18} />} />
            ))}
          </View>
        </>
      )}
    </Screen>
  )
}

function Sheet({ student, tests, onChange, reload }) {
  const { c } = useTheme()
  const [last, setLast] = useState(null)
  const [values, setValues] = useState({})
  const [skip, setSkip] = useState({})
  const [kept, setKept] = useState({})
  const [touched, setTouched] = useState({})
  const [tried, setTried] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => { api.results(student.id).then(r => setLast(r.results)).catch(() => setLast({})) }, [student.id])

  const problems = Object.fromEntries(tests.map(m => [m.key, check(m, values[m.key], { skipped: skip[m.key], kept: kept[m.key] })]))
  const count = Object.values(problems).filter(Boolean).length
  const typed = tests.filter(m => !skip[m.key] && parseValue(values[m.key]) != null)
  const set = (k, v) => { setValues(x => ({ ...x, [k]: v })); setKept(x => ({ ...x, [k]: false })) }

  async function save() {
    setTried(true)
    setError('')
    if (count || !typed.length) { haptic.error(); return }
    setBusy(true)
    try {
      const res = await api.saveResults(student.id, { results: Object.fromEntries(typed.map(m => [m.key, parseValue(values[m.key])])) })
      haptic.success()
      toast({ title: `Saved ${res.saved} result${res.saved === 1 ? '' : 's'}`, sub: student.name.toUpperCase(), icon: I.check })
      forgetReport(student.id)
      setLast(res.results)
      setValues({}); setSkip({}); setKept({}); setTouched({}); setTried(false)
      reload()
    } catch (err) {
      haptic.error()
      setError(err.message)
    }
    setBusy(false)
  }

  return (
    <>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 12, paddingVertical: 10, paddingHorizontal: 12, borderWidth: 1, borderColor: c.line }}>
        <View style={{ width: 36, height: 36, backgroundColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
          <Mono size={12} color={c.bg}>{initials(student.name)}</Mono>
        </View>
        <View style={{ flex: 1, gap: 3 }}>
          <T font="semi" size={15}>{student.name}</T>
          <Mono size={10} color="ink2" style={{ letterSpacing: 0.6 }} numberOfLines={1}>{metaOf(student)}</Mono>
        </View>
        <Btn kind="secondary" small label="Change" onPress={onChange} style={{ height: 36, paddingHorizontal: 12 }} />
      </View>

      {tried && (count > 0 || !typed.length) && (
        <View accessibilityRole="alert" style={{ backgroundColor: c.ink, paddingVertical: 12, paddingHorizontal: 14, flexDirection: 'row', gap: 12 }}>
          <Icon d={I.warning} size={20} color={c.bg} />
          <T size={13.5} color={c.bg} style={{ flex: 1, lineHeight: 19 }}>
            {count > 0 ? <><T font="semi" size={13.5} color={c.bg}>{count} thing{count === 1 ? '' : 's'} to fix</T> before these results can be saved.</>
              : 'Type at least one result — or there’s nothing to save.'}
          </T>
        </View>
      )}

      {!tests.length && <Placeholder h={120} />}
      {tests.map(m => {
        const p = (tried || touched[m.key]) && problems[m.key]
        const prev = last?.[m.key]
        const time = m.key === 'timeTrial2km'
        if (skip[m.key]) {
          return (
            <View key={m.key} style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingVertical: 10,
                                       borderBottomWidth: 1, borderBottomColor: c.line, borderStyle: 'dashed' }}>
              <View style={{ gap: 4 }}>
                <Eyebrow>{m.label.toUpperCase()}</Eyebrow>
                <Mono size={11} color="ink2">NOT TESTED TODAY</Mono>
              </View>
              <Btn kind="text" label="Undo" onPress={() => setSkip(x => ({ ...x, [m.key]: false }))} />
            </View>
          )
        }
        return (
          <View key={m.key} style={{ gap: 7 }}>
            <Field label={`${m.label.toUpperCase()} · ${time ? 'MIN:SEC' : UNIT_WORD[m.unit] ?? m.unit.toUpperCase()}`}
                   value={values[m.key] ?? ''} onChangeText={v => set(m.key, v)}
                   onBlur={() => setTouched(x => ({ ...x, [m.key]: values[m.key] != null && values[m.key] !== '' }))}
                   keyboardType={time ? 'numbers-and-punctuation' : 'decimal-pad'} placeholder={prev != null ? formatValue(prev, m) : '—'}
                   error={!!p}
                   right={prev != null ? <Mono size={10} color="ink2">LAST {formatValue(prev, m)}</Mono> : null} />
            {p ? (
              <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 10, marginTop: -4 }}>
                <T size={12.5} style={{ flex: 1, lineHeight: 17 }}>{p.text}</T>
                {p.kind === 'range' && (p.fix != null
                  ? <Pill label={`USE ${p.fix}`} onPress={() => { haptic.tick(); set(m.key, p.fix) }} />
                  : <Pill label="KEEP IT" onPress={() => { haptic.tick(); setKept(x => ({ ...x, [m.key]: true })) }} />)}
                {p.kind === 'blank' && <Pill label="NOT TESTED" onPress={() => { haptic.tick(); setSkip(x => ({ ...x, [m.key]: true })) }} />}
              </View>
            ) : !values[m.key] && (
              <Pressable onPress={() => setSkip(x => ({ ...x, [m.key]: true }))} hitSlop={6} style={{ alignSelf: 'flex-start' }}>
                <Mono size={10} color="ink2" style={{ letterSpacing: 0.8, textDecorationLine: 'underline' }}>NOT TESTED TODAY</Mono>
              </Pressable>
            )}
          </View>
        )
      })}

      <Note>{error}</Note>
      <Btn label="Save results" busy={busy} busyLabel="Saving" disabled={tried && (count > 0 || !typed.length)} onPress={save} />
      <LinkRow label="Drill videos" sub={`Film ${student.name.split(' ')[0]} for pose analysis`} last
               onPress={() => router.push({ pathname: '/videos', params: { id: student.id, name: student.name } })} />
    </>
  )
}

// A small mono action beside a field's message: USE 3.8, KEEP IT, NOT TESTED.
function Pill({ label, onPress }) {
  const { c } = useTheme()
  return (
    <Pressable onPress={onPress} accessibilityRole="button" hitSlop={4}
               style={({ pressed }) => ({ paddingVertical: 6, paddingHorizontal: 9, borderWidth: 1, borderColor: c.ink,
                                          backgroundColor: pressed ? c.ink : 'transparent' })}>
      {({ pressed }) => <Mono size={10.5} color={pressed ? c.bg : c.ink} style={{ letterSpacing: 0.84 }}>{label}</Mono>}
    </Pressable>
  )
}
