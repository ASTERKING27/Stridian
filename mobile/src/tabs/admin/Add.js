import { useEffect, useState } from 'react'
import { Image, View } from 'react-native'
import { router } from 'expo-router'
import { api, getSports } from '../../lib/api'
import { pickPhoto } from '../../lib/media'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { Btn, Eyebrow, H1, Icon, I, Lap, Note, Screen, T, Tile, Top } from '../../ui'
import DetailsForm from '../../ui/DetailsForm'
import { toast } from '../../ui/Toast'

/* An admin adding a student by hand — someone with no login of their own, in any sport.
   Students with a university email enrol themselves instead. */
export default function Add() {
  const s = useSession()
  const { c } = useTheme()
  const [sports, setSports] = useState(null)
  const [error, setError] = useState('')
  const [photo, setPhoto] = useState(null)
  const [round, setRound] = useState(0)           // a fresh, empty form after each one added
  useEffect(() => { getSports().then(setSports, e => setError(e.message)) }, [])

  async function choose() {
    try { setPhoto(await pickPhoto({ maxSide: 800 }) ?? photo) } catch (err) { setError(err.message) }
  }

  async function add(body) {
    const st = await api.createStudent(body)
    const here = st.sport === s.coach.sport
    // the photo goes to the sport the admin is looking after; another sport's needs a switch first
    if (photo && here) await api.setStudentPhoto(st.id, photo.uri).catch(() => {})
    toast({ title: `${st.name} added`, sub: here || !photo ? st.sport.toUpperCase() : `${st.sport.toUpperCase()} · ADD THE PHOTO FROM THEIR PAGE` })
    setPhoto(null)
    setRound(r => r + 1)
    if (here) router.push({ pathname: '/student/[id]', params: { id: st.id } })
    return null
  }

  return (
    <Screen bottom={110}>
      <Top context={contextLine(s)} onContext={() => router.push('/sport')} />
      <View style={{ gap: 8 }}>
        <Eyebrow>BY HAND · NO LOGIN</Eyebrow>
        <H1>Add a student</H1>
      </View>
      <T size={14} color="ink2" style={{ lineHeight: 20 }}>
        For someone without a university login. Anyone with one enrols themselves with the coach’s code. Only the name is needed now.
      </T>
      <Note>{error}</Note>
      {!sports ? !error && <Lap size={28} /> : (
        <DetailsForm key={round} mode="create" sports={sports} sport={s.coach.sport} onSubmit={add}
                     submitLabel="Add student" busyLabel="Adding">
          <View style={{ flexDirection: 'row', alignItems: 'center', gap: 16 }}>
            {photo ? <Image source={{ uri: photo.uri }} style={{ width: 72, height: 80 }} accessibilityLabel="Their photo" /> : (
              <Tile w={72} filled={false} dashed><Icon d={I.camera} size={24} color={c.ink2} /></Tile>
            )}
            <Btn kind="secondary" small label={photo ? 'Change photo' : 'Add a photo'} onPress={choose} style={{ flex: 1 }} />
          </View>
        </DetailsForm>
      )}
    </Screen>
  )
}
