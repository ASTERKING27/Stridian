import { useState } from 'react'
import { Alert, Linking, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api, authedSource, initials, utc } from '../../../lib/api'
import { forgetReport, useReport } from '../../../lib/report'
import { useBackInView, useData } from '../../../lib/useData'
import { chooseCertificate, openAuthedFile, XLSX } from '../../../lib/media'
import { useSession } from '../../../lib/session'
import { useTheme } from '../../../lib/theme'
import { haptic } from '../../../lib/haptics'
import { Back, Btn, Choice, Eyebrow, Field, I, LinkRow, Lap, Mono, Note, Rec, Screen, T, Tag, Tile, TileImage } from '../../../ui'
import { levelWord, TEAMS } from '../../../ui/DetailsForm'
import { toast } from '../../../ui/Toast'
import ReportHome from '../../../report/ReportHome'
import { CertRow } from '../../../tabs/student/Achievements'
import { fmtDate, masked } from '../../../tabs/student/Profile'

const DIETS = { nonveg: 'Non-veg', egg: 'Eggetarian', veg: 'Vegetarian', vegan: 'Vegan' }

/* One student, as their coach sees them: confirm their position, their report, the team
   and shirt number, a focus session they forgot to tick, their record and certificates.
   An admin can also edit the record and add certificates for them. */
export default function StudentPage() {
  const { id } = useLocalSearchParams()
  const s = useSession()
  const { c } = useTheme()
  const { data, error, reload } = useReport(id)
  const certs = useData(() => api.studentAchievements(id), [id])
  const [busy, setBusy] = useState('')
  const [problem, setProblem] = useState('')
  useBackInView(() => { reload(); certs.reload() })

  async function run(kind, action, done) {
    setBusy(kind)
    setProblem('')
    try {
      await action()
      haptic.success()
      if (done) toast(done)
    } catch (err) {
      haptic.error()
      setProblem(err.message)
    }
    setBusy('')
  }

  if (!data) {
    return (
      <Screen>
        <Back label="Squad" onPress={() => router.back()} />
        {error ? <Note>{error.message}</Note> : <Lap size={28} />}
      </Screen>
    )
  }

  const st = data.student
  const tested = data.positions.some(p => p.fit != null)
  const photo = authedSource(`/api/students/${id}/photo`, st.photo_version)
  const admin = s.isAdmin
  const call = n => (n ? () => Linking.openURL(`tel:${n}`) : undefined)
  const remove = () => Alert.alert(`Delete ${st.name}?`, 'Their results, videos, certificates and record all go. This can’t be undone.', [
    { text: 'Keep', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => run('delete', async () => {
      await api.deleteStudent(id)
      forgetReport(id)
      router.back()
    }, { title: `${st.name} deleted`, sub: st.sport.toUpperCase() }) },
  ])
  const addCert = () => run('cert', async () => {
    const file = await chooseCertificate()
    if (!file) return
    const item = await api.addStudentAchievement(id, file.uri, file.type, file.name)
    router.push({ pathname: '/achievement', params: { item: JSON.stringify(item), as: 'admin', studentName: st.name } })
  })

  return (
    <Screen gap={22}>
      <Back label="Squad" onPress={() => router.back()} />
      <View style={{ flexDirection: 'row', gap: 16, alignItems: 'center' }}>
        {photo ? <TileImage source={photo} w={72} /> : (
          <Tile w={72}><T font="wide" size={18} color={c.bg} style={{ letterSpacing: 1.44 }}>{initials(st.name)}</T></Tile>
        )}
        <View style={{ flex: 1, gap: 5 }}>
          <T font="title" size={24}>{st.name}</T>
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84 }}>
            {[st.verified_position || st.declared_position || 'NO POSITION', st.ra_number].filter(Boolean).join(' · ').toUpperCase()}
          </Mono>
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84 }}>
            {[st.age && `${st.age} YRS`, st.height_cm && `${st.height_cm} CM`, st.weight_kg && `${st.weight_kg} KG`].filter(Boolean).join(' · ') || ' '}
          </Mono>
        </View>
      </View>

      <Verify data={data} busy={busy} run={run} reload={reload} />
      <Note>{problem}</Note>

      {tested ? <ReportHome data={data} id={id} you={false} /> : (
        <View style={{ gap: 12 }}>
          <Eyebrow>THE REPORT</Eyebrow>
          <T size={14.5} color="ink2" style={{ lineHeight: 21 }}>
            No test results yet — their position, levels, training plan and diet appear once you record some.
          </T>
          <Btn label="Record their results" icon={I.entry}
               onPress={() => router.dismissTo({ pathname: '/', params: { tab: 'entry', student: String(id), at: String(Date.now()) } })} />
          <LinkRow label="Drill videos" sub="Film a drill for pose analysis" last
                   onPress={() => router.push({ pathname: '/videos', params: { id, name: st.name } })} />
        </View>
      )}

      <Team st={st} busy={busy} run={run} reload={reload} />
      {!!st.email && <FocusLog id={id} name={st.name} busy={busy} run={run} />}

      <View>
        <Eyebrow style={{ paddingBottom: 4 }}>UNIVERSITY RECORD</Eyebrow>
        <Rec label="RA NUMBER" value={st.ra_number} />
        <Rec label="DATE OF BIRTH" value={st.dob ? `${fmtDate(st.dob)}${st.age ? ` · ${st.age} years` : ''}` : ''} />
        <Rec label="UNIVERSITY EMAIL" value={st.email || 'Added by an admin — no login'} />
        <Rec label="MOBILE" value={st.phone} onPress={call(st.phone)} />
        <Rec label="FATHER" value={[st.father_name, st.father_phone].filter(Boolean).join(' · ')} onPress={call(st.father_phone)} />
        <Rec label="MOTHER" value={[st.mother_name, st.mother_phone].filter(Boolean).join(' · ')} onPress={call(st.mother_phone)} />
        <Rec label="BLOOD GROUP" value={st.blood_group} />
        <Rec label="AADHAAR" value={masked(st.aadhaar)} />
        <Rec label="HIGHEST LEVEL PLAYED" value={levelWord(st.highest_level) || 'Not yet competed'} />
        <Rec label="DIET" value={[DIETS[st.diet_preference], st.allergies && `allergic to ${st.allergies.replaceAll(',', ', ')}`].filter(Boolean).join(' · ')} last />
      </View>
      {admin
        ? <Btn kind="secondary" label="Edit details" icon={I.edit} onPress={() => router.push({ pathname: '/student-edit', params: { id } })} />
        : <Mono size={10} color="ink2" style={{ lineHeight: 16 }}>THE STUDENT CORRECTS THEIR OWN RECORD; AN ADMIN CAN CHANGE ANYTHING.</Mono>}

      <View>
        <Eyebrow style={{ paddingBottom: 6 }}>CERTIFICATES</Eyebrow>
        {!certs.data && !certs.error && <Lap />}
        {certs.data?.length === 0 && <T size={14} color="ink2" style={{ paddingVertical: 8 }}>Nothing sent yet.</T>}
        {(certs.data ?? []).map(a => <CertRow key={a.id} item={a} as={admin ? 'admin' : 'coach'} studentName={st.name} />)}
        {admin && <Btn kind="secondary" small label="Add a certificate" icon={I.add} busy={busy === 'cert'} busyLabel="Uploading"
                       onPress={addCert} style={{ marginTop: 10 }} />}
      </View>

      <View style={{ gap: 6 }}>
        <Btn kind="secondary" label="Download as Excel" icon={I.download} busy={busy === 'xlsx'} busyLabel="Preparing"
             onPress={() => run('xlsx', () => openAuthedFile(`/api/students/${id}/export`, `stridian-${st.name.replace(/\W+/g, '-')}.xlsx`, XLSX))} />
        <Btn kind="text" label="Delete student" icon={I.delete} busy={busy === 'delete'} busyLabel="Deleting" onPress={remove} />
      </View>
    </Screen>
  )
}

/* The coach's call on where they play. It moves them to the Verified tab of the squad
   sheet and is a lesson for the model — it counts even when it differs from the suggestion. */
function Verify({ data, busy, run, reload }) {
  const { c } = useTheme()
  const st = data.student
  const rec = data.recommended?.position
  const [pick, setPick] = useState(rec ?? data.positions[0]?.position ?? '')
  if (st.status === 'verified') {
    const undo = () => Alert.alert('Undo the verification?', `${st.name} goes back to pending.`, [
      { text: 'Keep it', style: 'cancel' },
      { text: 'Undo', onPress: () => run('verify', async () => { await api.unverify(st.id); await reload() }) },
    ])
    return (
      <View style={{ gap: 10, padding: 14, borderWidth: 1, borderColor: c.ink }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
          <Tag label="VERIFIED" on icon={I.check} />
          <T font="semi" size={16} style={{ flex: 1 }}>{st.verified_position}</T>
        </View>
        <T size={13.5} color="ink2" style={{ lineHeight: 19 }}>
          {`Confirmed${st.verified_by_name ? ` by ${st.verified_by_name}` : ''}${st.verified_at ? ` on ${utc(st.verified_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}` : ''}.`}
          {rec ? (rec === st.verified_position ? ' The numbers agree.' : ` By the numbers, ${rec} fits best.`) : ''}
        </T>
        <Btn kind="text" label="Undo verification" busy={busy === 'verify'} busyLabel="Undoing" onPress={undo} style={{ alignSelf: 'flex-start', paddingHorizontal: 0 }} />
      </View>
    )
  }
  return (
    <View style={{ gap: 12, padding: 14, borderWidth: 1, borderColor: c.ink, borderStyle: 'dashed' }}>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 10 }}>
        <Tag label="PENDING" />
        <T font="semi" size={15} style={{ flex: 1 }}>Confirm where they play</T>
      </View>
      <Choice options={data.positions.map(p => [p.position, p.position === rec ? `${p.position} · suggested` : p.position])}
              value={pick} onChange={setPick} />
      <T size={12.5} color="ink2" style={{ lineHeight: 18 }}>
        Verifying moves {st.name.split(' ')[0]} to the Verified tab of the squad sheet and teaches the model — your call counts even when it differs from the suggestion.
      </T>
      <Btn label={pick ? `Verify as ${pick}` : 'Pick a position'} disabled={!pick} busy={busy === 'verify'} busyLabel="Verifying"
           onPress={() => run('verify', async () => { await api.verify(st.id, pick); await reload() },
                              { title: `${st.name} verified`, sub: pick.toUpperCase(), icon: I.verified })} />
    </View>
  )
}

// What the coach sets: the team (whose level targets they're read against) and the shirt number (how a match card names them).
function Team({ st, busy, run, reload }) {
  const [team, setTeam] = useState(st.category ?? '')
  const [jersey, setJersey] = useState(st.jersey_number == null ? '' : String(st.jersey_number))
  const changes = {
    ...(team !== (st.category ?? '') && { category: team || null }),
    ...(jersey !== (st.jersey_number == null ? '' : String(st.jersey_number)) && { jersey_number: jersey === '' ? null : Number(jersey) }),
  }
  const dirty = Object.keys(changes).length > 0
  return (
    <View style={{ gap: 12 }}>
      <Eyebrow>TEAM AND SHIRT</Eyebrow>
      <Choice options={TEAMS} value={team} onChange={setTeam} />
      <Field label="JERSEY NUMBER" value={jersey} onChangeText={v => setJersey(v.replace(/\D/g, '').slice(0, 3))}
             keyboardType="number-pad" hint="Match cards name players by their number; the team picks their level targets." />
      {dirty && <Btn kind="secondary" small label="Save team and number" busy={busy === 'team'} busyLabel="Saving"
                     onPress={() => run('team', async () => { await api.updateStudent(st.id, changes); await reload() }, { title: 'Saved', sub: st.name.toUpperCase() })} />}
    </View>
  )
}

const pad = n => String(n).padStart(2, '0')
const isoDay = d => `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`

// Today back to last week's Monday: the days a forgotten focus session can still be logged.
function recentDays() {
  const today = new Date()
  const back = ((today.getDay() + 6) % 7) + 7
  return Array.from({ length: back + 1 }, (_, i) => {
    const d = new Date(today.getFullYear(), today.getMonth(), today.getDate() - i)
    return [isoDay(d), i === 0 ? 'Today' : i === 1 ? 'Yesterday' : d.toLocaleDateString('en-GB', { weekday: 'short', day: 'numeric' })]
  })
}

// A session they trained but forgot to tick — it can complete a week and save their streak.
function FocusLog({ id, name, busy, run }) {
  const [open, setOpen] = useState(false)
  const [day, setDay] = useState('')
  const days = recentDays()
  if (!open) return <Btn kind="secondary" label="Log a missed focus session" icon={I.streak} onPress={() => setOpen(true)} />
  const label = days.find(d => d[0] === day)?.[1]
  return (
    <View style={{ gap: 12 }}>
      <Eyebrow>WEEKLY FOCUS · A SESSION {name.split(' ')[0].toUpperCase()} FORGOT TO TICK</Eyebrow>
      <Choice options={days} value={day} onChange={setDay} />
      <Btn label={!day ? 'Pick the day' : label === 'Today' || label === 'Yesterday' ? `Log ${label.toLowerCase()}’s session` : `Log the session on ${label}`}
           disabled={!day} busy={busy === 'focus'} busyLabel="Logging"
           onPress={() => run('focus', async () => {
             const r = await api.logFocus(id, day)
             setOpen(false)
             setDay('')
             toast({ title: 'Session logged', sub: `${r.sessions.length} SESSION${r.sessions.length === 1 ? '' : 'S'} THAT WEEK FOR ${name.split(' ')[0].toUpperCase()}` })
           })} />
      <Btn kind="text" label="Cancel" onPress={() => setOpen(false)} />
    </View>
  )
}
