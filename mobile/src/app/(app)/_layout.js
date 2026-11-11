import { router, Stack } from 'expo-router'
import { useTheme } from '../../lib/theme'
import { Screen } from '../../ui'
import { Crashed } from '../../ui/States'

// Everything behind sign-in: the tabs, and the pages pushed over them.
export default function AppLayout() {
  const { c } = useTheme()
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg } }} />
}

// A screen in here that crashes while drawing itself lands on this (States board, 08).
export function ErrorBoundary({ error, retry }) {
  return (
    <Screen fill>
      <Crashed error={error} retry={retry} home={() => router.replace('/')} />
    </Screen>
  )
}
