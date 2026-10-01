import { router, useLocalSearchParams } from 'expo-router'
import { useReport } from '../lib/report'
import { Back, Lap, Note, Screen, Title } from '../ui'

// A page pushed from a report: Back, a title, and the report it belongs to.
export function useReportPage() {
  const { id } = useLocalSearchParams()
  return { id, ...useReport(id || undefined) }
}

export default function Page({ data, error, eyebrow, title, size, children }) {
  const { id } = useLocalSearchParams()
  const back = id ? (data?.student?.name ?? 'Back') : 'My report'
  return (
    <Screen gap={18}>
      <Back label={back} onPress={() => router.back()} />
      {!!title && <Title eyebrow={eyebrow} size={size}>{title}</Title>}
      {error && <Note>{error.message}</Note>}
      {!data && !error && <Lap size={28} />}
      {data && children}
    </Screen>
  )
}
