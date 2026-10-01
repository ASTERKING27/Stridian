import { useEffect } from 'react'
import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import * as SplashScreen from 'expo-splash-screen'
import { useFonts } from 'expo-font'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { FONTS, ThemeProvider, useTheme } from '../lib/theme'
import { SessionProvider, useSession } from '../lib/session'
import ToastHost from '../ui/Toast'

SplashScreen.preventAutoHideAsync().catch(() => {})

export default function Root() {
  const [loaded, error] = useFonts(FONTS)
  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <SessionProvider>
          {(loaded || error) && <Nav />}
        </SessionProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  )
}

/* Signed out: welcome and sign-in. A student without a squad yet: enrol. Everyone else:
   their tabs. Stack.Protected sends each to the first screen they're allowed. */
function Nav() {
  const s = useSession()
  const { c, name } = useTheme()
  useEffect(() => { if (s.status !== 'loading') SplashScreen.hideAsync().catch(() => {}) }, [s.status])
  if (s.status === 'loading') return null

  const signedIn = s.status === 'in'
  const needsEnrol = signedIn && s.role === 'student' && !!s.me && !s.me.student
  return (
    <>
      <StatusBar style={name === 'dark' ? 'light' : 'dark'} />
      <Stack screenOptions={{ headerShown: false, animation: 'fade', contentStyle: { backgroundColor: c.bg } }}>
        <Stack.Protected guard={!signedIn}>
          <Stack.Screen name="welcome" />
          <Stack.Screen name="sign-in" />
          <Stack.Screen name="code" />
          <Stack.Screen name="coach-signup" />
        </Stack.Protected>
        <Stack.Protected guard={needsEnrol}>
          <Stack.Screen name="enrol" />
        </Stack.Protected>
        <Stack.Protected guard={signedIn && !needsEnrol}>
          <Stack.Screen name="(app)" />
        </Stack.Protected>
      </Stack>
      <ToastHost />
    </>
  )
}
