import { useMemo, useState } from 'react'
import { Alert, Image, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api, authedSource, utc } from '../../lib/api'
import { openAuthedFile } from '../../lib/media'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Back, Btn, Choice, Eyebrow, Field, Mono, Note, Row, Screen, T, Title } from '../../ui'
import { LEVELS, levelWord } from '../../ui/DetailsForm'
import { toast } from '../../ui/Toast'
import { CERT_STATUS } from '../../tabs/student/Achievements'

/* One certificate. A student fills in (or checks the AI's reading of) the event, level,
   year and result, then sends it; a coach opens it and verifies or rejects it with a
   reason; an admin can also correct the details. */
export default function Achievement() {
  const p = useLocalSearchParams()
  const as = p.as ?? 'student'
  const [item, setItem] = useState(() => JSON.parse(p.item))
  const { c } = useTheme()
  const student = as === 'student'
  const reviewer = !student
  const editable = (student && item.status !== 'verified') || as === 'admin'
  const [f, setF] = useState({ title: item.title ?? '', level: item.level ?? '', year: item.year ? String(item.year) : '',
                               result: item.result ?? '', details: item.details ?? '' })
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const [why, setWhy] = useState('')
  const set = k => v => setF(x => ({ ...x, [k]: v }))
  const certUrl = student ? `/api/student/achievements/${item.id}/certificate` : `/api/achievements/${item.id}/certificate`
  const pdf = item.cert_mime === 'application/pdf'
  const image = useMemo(() => (pdf ? null : authedSource(certUrl, String(item.id))), [certUrl, pdf, item.id])
  const ai = item.ai_read
  const nameOnIt = ai?.name_on_certificate
  const nameDiffers = nameOnIt && p.studentName &&
    !nameOnIt.toLowerCase().split(/\s+/).some(w => w.length > 2 && p.studentName.toLowerCase().includes(w))

  async function run(kind, action) {
    setBusy(kind)
    setError('')
    try { await action() } catch (err) { haptic.error(); setError(err.message) }
    setBusy('')
  }
  const body = submit => ({ ...f, year: f.year ? Number(f.year) : null, ...(submit ? { submit: true } : {}) })
  const save = submit => run(submit ? 'send' : 'save', async () => {
    const saved = await (student ? api.editMyAchievement(item.id, body(submit)) : api.editAchievement(item.id, body(false)))
    setItem(saved)
    haptic.success()
    toast({ title: submit ? 'Sent to your coach' : 'Saved', sub: (saved.title || '').toUpperCase() })
    if (submit) router.back()
  })
  const review = (decision, note) => run(decision, async () => {
    setItem(await api.reviewAchievement(item.id, decision, note || null, item.version))
    haptic.success()
    toast({ title: decision === 'verified' ? 'Certificate verified' : 'Sent back to the student', sub: (item.title || '').toUpperCase() })
    router.back()
  })
  const remove = () => Alert.alert('Delete this certificate?', 'It can’t be brought back.', [
    { text: 'Keep it', style: 'cancel' },
    { text: 'Delete', style: 'destructive', onPress: () => run('delete', async () => { await api.deleteMyAchievement(item.id); router.back() }) },
  ])

  const status = student ? CERT_STATUS[item.status] : item.status === 'pending' ? 'TO CHECK' : CERT_STATUS[item.status]
  return (
    <Screen gap={18}>
      <Back label={student ? 'Achievements' : 'Back'} onPress={() => router.back()} />
      <Title eyebrow={`CERTIFICATE · ${status}`}>{item.title || 'Fill in the details'}</Title>

      {image
        ? <Image source={image} resizeMode="contain" accessibilityLabel="The certificate"
                 style={{ width: '100%', aspectRatio: 1.414, backgroundColor: c.soft, borderWidth: 1, borderColor: c.line }} />
        : <Btn kind="secondary" label="Open the PDF" busy={busy === 'pdf'} busyLabel="Opening"
               onPress={() => run('pdf', () => openAuthedFile(certUrl, `certificate-${item.id}.pdf`))} />}

      {ai?.is_certificate === false && <Note>The AI reader doesn’t think this is a sports certificate — check it’s the right file.</Note>}
      {reviewer && !!nameOnIt && (
        <Note tone={nameDiffers ? 'bad' : 'info'}>
          Name on the certificate, as the AI read it: {nameOnIt}{nameDiffers ? ' — it doesn’t match the student.' : '.'}
        </Note>
      )}
      {(item.status === 'rejected' || item.status === 'draft') && !!item.review_note && (
        <Note>{item.reviewed_by_name ?? 'Your coach'}: {item.review_note}</Note>
      )}
      {item.status === 'verified' && (
        <T size={13.5} color="ink2">
          Verified{item.reviewed_by_name ? ` by ${item.reviewed_by_name}` : ''}{item.reviewed_at ? ` on ${utc(item.reviewed_at).toLocaleDateString()}` : ''}.
        </T>
      )}

      {editable ? (
        <>
          {student && !!ai && item.status === 'draft' && (
            <T size={13} color="ink2">The AI filled these in from the certificate — check them before you send it.</T>
          )}
          <Field label="EVENT / TOURNAMENT *" value={f.title} onChangeText={set('title')} maxLength={200} />
          <View style={{ gap: 10 }}>
            <Eyebrow>LEVEL *</Eyebrow>
            <Choice options={LEVELS} value={f.level} onChange={set('level')} />
          </View>
          <View style={{ flexDirection: 'row', gap: 16 }}>
            <Field style={{ flex: 1 }} label="YEAR" value={f.year} onChangeText={v => set('year')(v.replace(/\D/g, '').slice(0, 4))}
                   keyboardType="number-pad" />
            <Field style={{ flex: 2 }} label="RESULT" value={f.result} onChangeText={set('result')} maxLength={80}
                   placeholder="Gold, Runners-up…" />
          </View>
          <Field label="DETAILS" value={f.details} onChangeText={set('details')} multiline maxLength={2000} />
          <Note>{error}</Note>
          {student ? (
            <View style={{ gap: 8 }}>
              <Btn label="Send to coach" busy={busy === 'send'} busyLabel="Sending" disabled={!f.title.trim() || !f.level}
                   onPress={() => save(true)} />
              <Btn kind="secondary" label="Save, send later" busy={busy === 'save'} busyLabel="Saving" onPress={() => save(false)} />
              <Btn kind="text" label="Delete certificate" onPress={remove} />
            </View>
          ) : (
            <Btn kind="secondary" label="Save details" busy={busy === 'save'} busyLabel="Saving" onPress={() => save(false)} />
          )}
        </>
      ) : (
        <View>
          <Row a="Level" b={levelWord(item.level) || '—'} />
          <Row a="Year" b={item.year ? String(item.year) : '—'} />
          <Row a="Result" b={item.result || '—'} last={!item.details} />
          {!!item.details && <T size={14} style={{ paddingTop: 10, lineHeight: 20 }}>{item.details}</T>}
        </View>
      )}

      {reviewer && (
        <View style={{ gap: 10, paddingTop: 8 }}>
          {!editable && <Note>{error}</Note>}
          {item.status !== 'verified' && (
            <Btn label="Verify" busy={busy === 'verified'} busyLabel="Verifying" disabled={!item.title || !item.level}
                 onPress={() => review('verified')} />
          )}
          {!item.title || !item.level ? <Mono size={10.5} color="ink2">IT NEEDS AN EVENT AND A LEVEL BEFORE IT CAN BE VERIFIED</Mono> : null}
          {item.status !== 'rejected' && (
            <>
              <Field label="WHY IT’S REJECTED" value={why} onChangeText={setWhy} maxLength={500}
                     placeholder="The student sees this — e.g. the photo is blurry" />
              <Btn kind="secondary" label="Reject" busy={busy === 'rejected'} busyLabel="Sending back" disabled={!why.trim()}
                   onPress={() => review('rejected', why.trim())} />
            </>
          )}
        </View>
      )}
    </Screen>
  )
}
