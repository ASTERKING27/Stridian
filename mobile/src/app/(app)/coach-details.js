import { useState } from 'react'
import { Alert, Share, View } from 'react-native'
import { router } from 'expo-router'
import { api, initials } from '../../lib/api'
import { useData } from '../../lib/useData'
import { openAuthedFile, XLSX } from '../../lib/media'
import { useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Back, Btn, Eyebrow, Field, I, IconBtn, Mono, Note, Rec, Screen, T, Tile } from '../../ui'
import { toast } from '../../ui/Toast'

/* Profile board, 04: who the coach is, the code their students enrol with, their
   details, the squad as Excel. An admin also sees every coach. */
export default function CoachDetails() {
  const s = useSession()
  const { c } = useTheme()
  const me = s.coach
  const code = useData(api.enrolCode, [me.sport])
  const coaches = useData(() => (s.isAdmin ? api.coaches() : Promise.resolve(null)), [s.isAdmin])
  const [editing, setEditing] = useState(!me.employee_id || !me.phone)
  const [f, setF] = useState({ name: me.name ?? '', employee_id: me.employee_id ?? '', phone: me.phone ?? '', designation: me.designation ?? '' })
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const set = k => v => setF(x => ({ ...x, [k]: v }))

  async function run(kind, action) {
    setBusy(kind)
    setError('')
    try { await action() } catch (err) { haptic.error(); setError(err.message) }
    setBusy('')
  }
  const save = () => run('save', async () => {
    s.setCoach(await api.updateMe(f))
    haptic.success()
    setEditing(false)
    toast({ title: 'Saved', sub: 'YOUR DETAILS' })
  })
  const renew = () => Alert.alert('Make a new enrolment code?',
    'The current one stops working for anyone who hasn’t enrolled yet. Students already enrolled aren’t affected.', [
      { text: 'Keep this one', style: 'cancel' },
      { text: 'Make a new code', onPress: () => run('code', async () => { code.setData(await api.newEnrolCode()); haptic.success() }) },
    ])
  const share = () => Share.share({
    message: `Join the ${me.sport} squad on Stridian: sign in with your university email and enter the code ${code.data.code}.`,
  })
  const excel = scope => run(scope, () => openAuthedFile(`/api/export/squad${scope === 'all' ? '?scope=all' : ''}`,
    scope === 'all' ? 'stridian-all-sports.xlsx' : `stridian-${me.sport.toLowerCase()}-squad.xlsx`, XLSX))

  return (
    <Screen gap={18}>
      <Back label="Squad" onPress={() => router.back()} />
      <View style={{ flexDirection: 'row', gap: 16, alignItems: 'center' }}>
        <Tile w={72} filled={false}><T font="wide" size={18} style={{ letterSpacing: 1.44 }}>{initials(me.name)}</T></Tile>
        <View style={{ flex: 1, gap: 5 }}>
          <T font="title" size={24}>{me.name}</T>
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84 }}>
            {[me.designation || (s.isAdmin ? 'Admin' : 'Coach'), me.sport].join(' · ').toUpperCase()}
          </Mono>
        </View>
      </View>

      <View style={{ backgroundColor: c.ink, padding: 16, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ gap: 6 }}>
          <Mono size={10} color={c.bg} style={{ letterSpacing: 1.2, opacity: 0.75 }}>ENROLMENT CODE · {me.sport.toUpperCase()}</Mono>
          <Mono size={30} font="monoMedium" color={c.bg} style={{ letterSpacing: 6 }} selectable
                accessibilityLabel={code.data ? `Enrolment code ${code.data.code.split('').join(' ')}` : 'Enrolment code loading'}>
            {code.data?.code ?? '······'}
          </Mono>
        </View>
        <View style={{ borderWidth: 1, borderColor: c.bg }}>
          <IconBtn icon={I.share} label="Share code" color={c.bg} size={20} onPress={code.data ? share : undefined} />
        </View>
      </View>
      {code.error && <Note>{code.error.message}</Note>}
      <Btn kind="text" label="Make a new code" busy={busy === 'code'} busyLabel="Making one" onPress={renew}
           style={{ alignSelf: 'flex-start', paddingHorizontal: 0 }} />
      <T size={13} color="ink2" style={{ lineHeight: 18, marginTop: -10 }}>
        Students sign in with their university email, pick {me.sport} and type this code to join your squad.
      </T>

      <View>
        <Eyebrow style={{ paddingBottom: 4 }}>YOUR DETAILS</Eyebrow>
        {editing ? (
          <View style={{ gap: 18, paddingTop: 8 }}>
            {(!me.employee_id || !me.phone) && <T size={13} color="ink2">The sports directorate keeps these for every coach.</T>}
            <Field label="NAME *" value={f.name} onChangeText={set('name')} maxLength={120} />
            <Field label="EMPLOYEE ID *" value={f.employee_id} onChangeText={set('employee_id')} maxLength={40} autoCapitalize="characters" />
            <Field label="MOBILE *" value={f.phone} onChangeText={set('phone')} keyboardType="phone-pad" maxLength={15} />
            <Field label="DESIGNATION" value={f.designation} onChangeText={set('designation')} maxLength={120}
                   placeholder="e.g. Assistant Professor, Physical Education" />
            <Btn label="Save details" busy={busy === 'save'} busyLabel="Saving"
                 disabled={!f.name.trim() || !f.employee_id.trim() || !f.phone.trim()} onPress={save} />
          </View>
        ) : (
          <>
            <Rec label="EMPLOYEE ID" value={me.employee_id} />
            <Rec label="EMAIL" value={me.email} />
            <Rec label="MOBILE" value={me.phone} />
            <Rec label="SPORT" value={me.sport} locked last />
            <Btn kind="text" label="Edit your details" icon={I.edit} onPress={() => setEditing(true)}
                 style={{ alignSelf: 'flex-start', paddingHorizontal: 0 }} />
          </>
        )}
      </View>
      <Note>{error}</Note>

      <View style={{ flexDirection: 'row', gap: 10 }}>
        <Btn kind="secondary" label="Squad as Excel" icon={I.download} busy={busy === 'sport'} busyLabel="Preparing"
             onPress={() => excel('sport')} style={{ flex: 1 }} />
        <Btn kind="icon" icon={I.settings} accessibilityLabel="Settings" onPress={() => router.push('/settings')} />
      </View>

      {s.isAdmin && (
        <View style={{ gap: 6 }}>
          <Btn kind="secondary" label="Every sport as Excel" icon={I.download} busy={busy === 'all'} busyLabel="Preparing"
               onPress={() => excel('all')} />
          <Eyebrow style={{ paddingTop: 12, paddingBottom: 4 }}>EVERY COACH · ADMINS ONLY</Eyebrow>
          {(coaches.data ?? []).map((x, i, all) => (
            <View key={x.id} style={{ gap: 3, paddingVertical: 11, borderTopWidth: 1, borderTopColor: c.line,
                                      borderBottomWidth: i === all.length - 1 ? 1 : 0, borderBottomColor: c.line }}>
              <T size={15}>{x.name}{x.is_admin ? ' · admin' : ''}</T>
              <Mono size={10} color="ink2" style={{ letterSpacing: 0.5 }}>
                {[x.sport.toUpperCase(), x.employee_id, x.phone, x.email].filter(Boolean).join(' · ')}
              </Mono>
            </View>
          ))}
        </View>
      )}
    </Screen>
  )
}
