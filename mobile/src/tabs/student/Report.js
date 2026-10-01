import { useState } from 'react'
import { RefreshControl, View } from 'react-native'
import { router } from 'expo-router'
import { useReport } from '../../lib/report'
import { contextLine, useSession } from '../../lib/session'
import { useTheme } from '../../lib/theme'
import { Btn, Eyebrow, Note, OfflineBar, Placeholder, Screen, Top } from '../../ui'
import ReportHome, { ReportWaiting } from '../../report/ReportHome'

// My report: read-only, and only once the coach has verified them.
export default function Report({ go }) {
  const s = useSession()
  const verified = s.me?.student?.status === 'verified'
  return verified ? <Verified /> : (
    <Screen bottom={110}>
      <Top context={contextLine(s)} />
      <ReportWaiting status={s.me?.student?.status} />
      <Btn kind="secondary" label="Finish your profile meanwhile" onPress={() => go('profile')} />
      <Btn kind="text" label="Send a drill video" onPress={() => router.push('/videos')} />
    </Screen>
  )
}

function Verified() {
  const s = useSession()
  const { c } = useTheme()
  const { data, error, reload } = useReport()
  const [refreshing, setRefreshing] = useState(false)
  const refresh = async () => { setRefreshing(true); await reload(); setRefreshing(false) }
  return (
    <View style={{ flex: 1 }}>
      {error?.offline && <OfflineBar note={data ? 'SHOWING WHAT WAS LOADED' : 'NOTHING LOADED YET'} onRetry={refresh} />}
      <Screen bottom={110}
              refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={c.ink}
                                              colors={[c.ink]} progressBackgroundColor={c.bg} />}>
        <Top context={contextLine(s)} />
        {error?.offline && <View style={{ height: 40 }} />}
        {error && !error.offline && <Note>{error.message}</Note>}
        {!data && !error && <Loading />}
        {data && <ReportHome data={data} />}
      </Screen>
    </View>
  )
}

function Loading() {
  return (
    <View style={{ gap: 12 }}>
      <Eyebrow>LOADING</Eyebrow>
      <View style={{ flexDirection: 'row', justifyContent: 'space-between' }}><Placeholder h={34} w={180} /><Placeholder h={30} w={48} /></View>
      <Placeholder h={12} /><Placeholder h={12} w="80%" />
      <Placeholder h={222} style={{ marginTop: 8 }} />
    </View>
  )
}
