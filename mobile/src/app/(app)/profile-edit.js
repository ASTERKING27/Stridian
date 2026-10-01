import { useEffect, useState } from 'react'
import { Pressable, View } from 'react-native'
import { router } from 'expo-router'
import { api, authedSource, getSports } from '../../lib/api'
import { pickPhoto } from '../../lib/media'
import { useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { haptic } from '../../lib/haptics'
import { Back, I, Icon, Lap, Mono, Note, Screen, T, TileImage, Title } from '../../ui'
import DetailsForm from '../../ui/DetailsForm'
import { toast } from '../../ui/Toast'

// Profile board, 02: their photo and details. RA number, date of birth and team are
// filled in once; after that an admin changes them.
export default function ProfileEdit() {
  const s = useSession()
  const { c } = useTheme()
  const st = s.me.student
  const [sports, setSports] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { getSports().then(setSports, err => setError(err.message)) }, [])

  async function photo() {
    setError('')
    try {
      const p = await pickPhoto({ maxSide: 800, quality: 0.88 })
      if (!p) return
      setBusy(true)
      const r = await api.setMyPhoto(p.uri)
      s.setMe({ ...s.me, student: { ...st, photo_version: r.photo_version } })
      haptic.success()
    } catch (err) { haptic.error(); setError(err.message) }
    setBusy(false)
  }

  const src = authedSource('/api/student/photo', st.photo_version)
  return (
    <Screen gap={18}>
      <Back label="Profile" onPress={() => router.back()} />
      <Title eyebrow="EDIT PROFILE">Your details</Title>
      <View style={{ flexDirection: 'row', alignItems: 'center', gap: 14 }}>
        {src ? <TileImage source={src} w={64} /> : (
          <View style={{ width: 64, height: 64, borderWidth: 1, borderColor: c.ink, alignItems: 'center', justifyContent: 'center' }}>
            <Icon d={I.camera} size={24} sw={1.5} />
          </View>
        )}
        <View style={{ gap: 3 }}>
          <Pressable onPress={photo} disabled={busy} accessibilityRole="button" style={{ flexDirection: 'row', gap: 8, alignItems: 'center' }}>
            {busy && <Lap size={14} />}
            <T font="semi" size={14} style={{ textDecorationLine: 'underline' }}>{busy ? 'Uploading' : 'Change photo'}</T>
          </Pressable>
          <Mono size={10} color="ink2" style={{ letterSpacing: 0.6 }}>SHRUNK ON YOUR PHONE BEFORE UPLOAD</Mono>
        </View>
      </View>
      <Note>{error}</Note>
      {sports && (
        <DetailsForm mode="self" student={st} sports={sports} submitLabel="Save changes"
                     onSubmit={async body => {
                       s.setMe(await api.updateMyProfile(body))
                       toast({ title: 'Details saved', sub: Object.keys(body).length + ' CHANGED' })
                       router.back()
                     }} />
      )}
    </Screen>
  )
}
