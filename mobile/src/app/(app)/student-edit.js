import { useEffect, useState } from 'react'
import { Alert, View } from 'react-native'
import { router, useLocalSearchParams } from 'expo-router'
import { api, authedSource, getSports, initials } from '../../lib/api'
import { forgetReport } from '../../lib/report'
import { pickPhoto } from '../../lib/media'
import { useTheme } from '../../lib/theme'
import { Back, Btn, Lap, Note, Screen, T, Tile, TileImage, Title } from '../../ui'
import DetailsForm from '../../ui/DetailsForm'
import { toast } from '../../ui/Toast'

// An admin correcting anyone's record — the university's details, the sport, the photo.
export default function StudentEdit() {
  const { id } = useLocalSearchParams()
  const { c } = useTheme()
  const [st, setSt] = useState(null)
  const [sports, setSports] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.student(id).then(setSt, e => setError(e.message))
    getSports().then(setSports, e => setError(e.message))
  }, [id])

  async function photo() {
    setBusy(true)
    try {
      const p = await pickPhoto({ maxSide: 800 })
      if (p) {
        const r = await api.setStudentPhoto(id, p.uri)
        setSt(x => ({ ...x, ...r }))
        forgetReport(id)
      }
    } catch (err) { setError(err.message) }
    setBusy(false)
  }

  async function save(body) {
    const saved = await api.updateStudent(id, body)
    forgetReport(id)
    if (saved.sport !== st.sport) {
      // they've left this sport's squad, so their page here would be empty
      Alert.alert(`${saved.name} moved to ${saved.sport}`, 'Switch sport to see them there.')
      router.dismissTo('/')
      return null
    }
    setSt(saved)
    toast({ title: 'Saved', sub: saved.name.toUpperCase() })
    router.back()
    return null
  }

  const source = st && authedSource(`/api/students/${id}/photo`, st.photo_version)
  return (
    <Screen>
      <Back label={st?.name ?? 'Back'} onPress={() => router.back()} />
      <Title eyebrow="ADMIN · UNIVERSITY RECORD">Edit details</Title>
      <Note>{error}</Note>
      {!(st && sports) ? !error && <Lap size={28} /> : (
        <DetailsForm mode="admin" student={st} sports={sports} onSubmit={save} submitLabel="Save changes">
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
            {source ? <TileImage source={source} w={72} /> : (
              <Tile w={72}><T font="wide" size={18} color={c.bg} style={{ letterSpacing: 1.44 }}>{initials(st.name)}</T></Tile>
            )}
            <Btn kind="secondary" small label={st.photo_version ? 'Change photo' : 'Add a photo'} busy={busy} busyLabel="Uploading"
                 onPress={photo} style={{ flex: 1 }} />
          </View>
        </DetailsForm>
      )}
    </Screen>
  )
}
