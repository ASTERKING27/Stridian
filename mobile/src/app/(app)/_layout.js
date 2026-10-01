import { Stack } from 'expo-router'
import { useTheme } from '../../lib/theme'

// Everything behind sign-in: the tabs, and the pages pushed over them.
export default function AppLayout() {
  const { c } = useTheme()
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: c.bg } }} />
}
