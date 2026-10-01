import { useEffect, useState } from 'react'
import { View } from 'react-native'
import { api, getSports } from '../lib/api'
import { useSession } from '../lib/session'
import { Btn, Field, I, Note, Screen, T, Title } from '../ui'
import DetailsForm from '../ui/DetailsForm'

/* A signed-in student who hasn't joined a squad yet: their record for the sports
   directorate, plus their sport's enrolment code from the coach. */
export default function Enrol() {
  const s = useSession()
  const [sports, setSports] = useState(null)
  const [error, setError] = useState('')
  const [code, setCode] = useState('')

  useEffect(() => { getSports().then(setSports, err => setError(err.message)) }, [])

  return (
    <Screen>
      <View style={{ flexDirection: 'row', justifyContent: 'flex-end' }}>
        <Btn kind="text" label="Sign out" icon={I.signout} onPress={s.signOut} />
      </View>
      <Title eyebrow="JOIN YOUR SQUAD">Enrol</Title>
      <T size={15} color="ink2" style={{ lineHeight: 22 }}>
        Signed in as <T font="semi" size={15}>{s.me?.email}</T>. This is your record with the sports directorate —
        your coach gives you your sport’s enrolment code.
      </T>
      <Note>{error}</Note>
      {sports && (
        <DetailsForm mode="enrol" sports={sports} submitLabel="Enrol" busyLabel="Enrolling"
                     onSubmit={async body => s.setMe(await api.enrol({ ...body, enrol_code: code }))}>
          <Field label="ENROLMENT CODE *" value={code} onChangeText={v => setCode(v.toUpperCase())}
                 autoCapitalize="characters" autoCorrect={false} placeholder="K7QM3X"
                 hint="Six characters, from your coach." />
        </DetailsForm>
      )}
    </Screen>
  )
}
