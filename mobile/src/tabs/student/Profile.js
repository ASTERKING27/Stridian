import { useCallback, useState } from 'react'
import { Pressable, View } from 'react-native'
import { router, useFocusEffect } from 'expo-router'
import { api, authedSource, initials } from '../../lib/api'
import { useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { Btn, Eyebrow, I, Icon, Logo, Mono, Rec, Screen, T, Tile, TileImage, Wordmark } from '../../ui'
import { levelWord } from '../../ui/DetailsForm'

export const fmtDate = iso => new Date(`${iso}T00:00:00`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
export const masked = a => (a ? `XXXX XXXX ${a.slice(-4)}` : '')

// What the sports directorate still needs from them (the website's checklist).
export function todos(s, achievements = []) {
  return [
    ['Add a profile photo', !!s.photo_version],
    ['Add your RA number and date of birth', !!(s.ra_number && s.dob)],
    ['Add a parent’s mobile number', !!(s.phone && (s.father_phone || s.mother_phone))],
    ['Add your Aadhaar number', !!s.aadhaar],
    ['Add your blood group', !!s.blood_group],
    ['Pick your team — men’s or women’s', !!s.category],
    ['Add your height and weight', !!(s.height_cm && s.weight_kg)],
    ...(s.highest_level ? [[`Send proof of your ${levelWord(s.highest_level).toLowerCase()}-level result`,
      achievements.some(a => a.status !== 'draft'), 'ach']] : []),
  ]
}

// Profile board, 01: who they are, how complete the record is, the university record.
export default function Profile({ go }) {
  const s = useSession()
  const { c } = useTheme()
  const st = s.me.student
  const [achievements, setAchievements] = useState([])
  useFocusEffect(useCallback(() => { api.myAchievements().then(setAchievements).catch(() => {}) }, []))

  const list = todos(st, achievements)
  const done = list.filter(t => t[1]).length
  const next = list.find(t => !t[1])
  const photo = authedSource('/api/student/photo', st.photo_version)
  const meta = [st.status === 'verified' ? st.verified_position : null,
                st.category ? (st.category === 'W' ? 'WOMEN’S TEAM' : 'MEN’S TEAM') : null,
                st.status === 'verified' ? 'VERIFIED' : 'WAITING FOR YOUR COACH'].filter(Boolean).join(' · ').toUpperCase()
  const rec = (label, value, locked) => <Rec key={label} label={label} value={value} locked={locked} />

  return (
    <Screen bottom={110} gap={18}>
      <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
        <View style={{ flexDirection: 'row', alignItems: 'center', gap: 9 }}><Logo size={22} /><Wordmark size={12} /></View>
        <Pressable accessibilityRole="button" accessibilityLabel="Settings" onPress={() => router.push('/settings')}
                   hitSlop={8} style={{ width: 44, height: 44, alignItems: 'flex-end', justifyContent: 'center' }}>
          <Icon d={I.settings} size={22} />
        </Pressable>
      </View>

      <View style={{ flexDirection: 'row', gap: 16, alignItems: 'center' }}>
        {photo ? <TileImage source={photo} w={72} /> : (
          <Tile w={72}><T font="wide" size={18} color={c.bg} style={{ letterSpacing: 1.44 }}>{initials(st.name)}</T></Tile>
        )}
        <View style={{ flex: 1, gap: 5 }}>
          <T font="title" size={24}>{st.name}</T>
          <Mono size={10.5} color="ink2" style={{ letterSpacing: 0.84 }}>{meta}</Mono>
        </View>
      </View>

      <View style={{ gap: 8 }}>
        <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}>
          <Eyebrow>PROFILE {Math.round((done / list.length) * 100)}% COMPLETE</Eyebrow>
          <Mono size={10.5} style={{ letterSpacing: 0.84 }}>{done} / {list.length}</Mono>
        </View>
        <View style={{ flexDirection: 'row', gap: 3 }}>
          {list.map((t, i) => (
            <View key={i} style={{ flex: 1, height: 6, borderWidth: 1, borderColor: c.ink, borderStyle: t[1] ? 'solid' : 'dashed',
                                   backgroundColor: t[1] ? c.ink : 'transparent' }} />
          ))}
        </View>
        {next && (
          <Pressable accessibilityRole="button" onPress={() => (next[2] === 'ach' ? go('ach') : router.push('/profile-edit'))}
                     style={({ pressed }) => ({ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
                                                paddingVertical: 10, paddingHorizontal: 12, borderWidth: 1, borderColor: c.ink,
                                                borderStyle: 'dashed', backgroundColor: pressed ? c.soft : 'transparent' })}>
            <T font="medium" size={14}>{next[0]}</T>
            <Icon d={I.next} size={18} />
          </Pressable>
        )}
      </View>

      <View>
        <Eyebrow style={{ paddingBottom: 4 }}>UNIVERSITY RECORD</Eyebrow>
        {rec('RA NUMBER', st.ra_number, !!st.ra_number)}
        {rec('DATE OF BIRTH', st.dob ? `${fmtDate(st.dob)}${st.age ? ` · ${st.age} years` : ''}` : '', !!st.dob)}
        {rec('AADHAAR', masked(st.aadhaar), true)}
        {rec('TEAM', st.category ? (st.category === 'W' ? 'Women’s' : 'Men’s') : '', !!st.category)}
        {rec('BLOOD GROUP', st.blood_group)}
        {rec('MOBILE', st.phone)}
        {rec('HIGHEST LEVEL PLAYED', levelWord(st.highest_level) || 'Not yet competed')}
        {rec('UNIVERSITY EMAIL', s.me.email)}
      </View>
      <Mono size={10} color="ink2" style={{ lineHeight: 16 }}>LOCKED FIELDS ARE CHANGED BY AN ADMIN.</Mono>
      <Btn kind="secondary" label="Edit details" icon={I.edit} onPress={() => router.push('/profile-edit')} />
    </Screen>
  )
}
