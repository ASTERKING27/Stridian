import { Stack } from 'expo-router'
import { StatusBar } from 'expo-status-bar'
import * as SplashScreen from 'expo-splash-screen'
import { useFonts } from 'expo-font'
import { SafeAreaProvider } from 'react-native-safe-area-context'
import { KeyboardProvider } from 'react-native-keyboard-controller'
import { FONTS, ThemeProvider, useTheme } from '../lib/theme'
import { SessionProvider, useSession } from '../lib/session'
import ToastHost from '../ui/Toast'
import DialogHost from '../ui/Dialog'
import Launch, { useLaunchScale } from '../ui/Launch'
import Animated from 'react-native-reanimated'

SplashScreen.preventAutoHideAsync().catch(() => {})

export default function Root() {
  const [loaded, error] = useFonts(FONTS)
  return (
    <SafeAreaProvider>
      <KeyboardProvider>
        <ThemeProvider>
          <SessionProvider>
            {(loaded || error) && <Nav />}
          </SessionProvider>
        </ThemeProvider>
      </KeyboardProvider>
    </SafeAreaProvider>
  )
}

/* Signed out: welcome and sign-in. A student without a squad yet: enrol. Everyone else:
   their tabs. Stack.Protected sends each to the first screen they're allowed. */
function Nav() {
  const s = useSession()
  const { c, name } = useTheme()
  const settle = useLaunchScale()
  if (s.status === 'loading') return null       // the phone's splash stays up; Launch takes over from it

  const signedIn = s.status === 'in'
  const needsEnrol = signedIn && s.role === 'student' && !!s.me && !s.me.student
  return (
    <>
      <StatusBar style={name === 'dark' ? 'light' : 'dark'} />
      <Animated.View style={[{ flex: 1, backgroundColor: c.bg, transformOrigin: '50% 46%' }, settle]}>
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
      </Animated.View>
      <ToastHost />
      <DialogHost />
      <Launch />
    </>
  )
}
