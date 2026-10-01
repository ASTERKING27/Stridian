import { useEffect, useState } from 'react'
import { router } from 'expo-router'
import { api, getSports } from '../../lib/api'
import { useSession } from '../../lib/session'
import { haptic } from '../../lib/haptics'
import { Back, Lap, Note, Screen, T, Title } from '../../ui'
import { SportPicker } from '../../ui/pickers'
import { toast } from '../../ui/Toast'

// An admin looks after every sport, one at a time: the squad, entry and weights follow this.
export default function Sport() {
  const s = useSession()
  const [sports, setSports] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { getSports().then(setSports, e => setError(e.message)) }, [])

  async function pick(name) {
    setBusy(true)
    setError('')
    try {
      s.setCoach(await api.switchSport(name))
      haptic.success()
      toast({ title: `Now looking after ${name}`, sub: 'ADMIN' })
      router.back()
    } catch (err) {
      haptic.error()
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <Screen>
      <Back label="Back" onPress={() => router.back()} />
      <Title eyebrow="ADMIN · WHICH SQUAD">Switch sport</Title>
      <T size={14.5} color="ink2" style={{ lineHeight: 21 }}>
        Every tab — the squad, coach entry, footage, cards, weights and the model — shows the sport you pick here.
      </T>
      {!sports ? !error && <Lap size={28} /> : <SportPicker sports={sports} value={s.coach.sport} onChange={pick} disabled={busy} />}
      {busy && <Lap size={22} />}
      <Note>{error}</Note>
    </Screen>
  )
}
