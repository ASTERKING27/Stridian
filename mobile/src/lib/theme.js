import { createContext, useContext, useEffect, useMemo, useState } from 'react'
import { useColorScheme } from 'react-native'
import * as SecureStore from 'expo-secure-store'
import { useReducedMotion } from 'react-native-reanimated'

// The e-ink palettes, straight from the design's build.py.
export const PALETTES = {
  white: {
    bg: '#F3F2EE', ink: '#121211', ink2: '#55544F',
    line: 'rgba(18,18,17,0.14)', soft: 'rgba(18,18,17,0.07)',
    glass: 'rgba(246,245,241,0.56)', glassEdge: 'rgba(18,18,17,0.10)', hi: 'rgba(255,255,255,0.8)',
    shadow: 'rgba(18,18,17,0.16)', shadowOpacity: 1,
  },
  dark: {
    bg: '#0F0F0E', ink: '#EEEDE8', ink2: '#9D9C96',
    line: 'rgba(238,237,232,0.16)', soft: 'rgba(238,237,232,0.08)',
    glass: 'rgba(34,34,32,0.5)', glassEdge: 'rgba(238,237,232,0.12)', hi: 'rgba(255,255,255,0.09)',
    shadow: 'rgba(0,0,0,0.55)', shadowOpacity: 1,
  },
}

// Static cuts of Archivo (the design's weights and widths) and IBM Plex Mono.
export const FONTS = {
  'Archivo-400': require('../../assets/fonts/Archivo-400.ttf'),
  'Archivo-450': require('../../assets/fonts/Archivo-450.ttf'),
  'Archivo-500': require('../../assets/fonts/Archivo-500.ttf'),
  'Archivo-600': require('../../assets/fonts/Archivo-600.ttf'),
  'Archivo-Title': require('../../assets/fonts/Archivo-Title.ttf'),       // 600 at 112% width
  'Archivo-Wide': require('../../assets/fonts/Archivo-Wide.ttf'),         // 620 at 125%: the wordmark
  'Archivo-Display': require('../../assets/fonts/Archivo-Display.ttf'),   // 700 at 125%: big numbers
  'PlexMono-400': require('../../assets/fonts/PlexMono-400.ttf'),
  'PlexMono-500': require('../../assets/fonts/PlexMono-500.ttf'),
}

export const F = {
  body: 'Archivo-450', regular: 'Archivo-400', medium: 'Archivo-500', semi: 'Archivo-600',
  title: 'Archivo-Title', wide: 'Archivo-Wide', display: 'Archivo-Display',
  mono: 'PlexMono-400', monoMedium: 'PlexMono-500',
}

const KEY = 'stridian.theme'
const MOTION = 'stridian.motion'
const ThemeContext = createContext(null)

/* Settings › Appearance. Theme: 'auto' follows the phone, or 'white' / 'dark'.
   Motion: 'system' follows the phone's Reduce Motion / Remove animations, or 'full' /
   'reduced'. `reduced` is what every animation asks. */
export function ThemeProvider({ children }) {
  const system = useColorScheme()
  const systemReduced = useReducedMotion()
  const [choice, setChoice] = useState('auto')
  const [motion, setMotion] = useState('system')
  useEffect(() => {
    SecureStore.getItemAsync(KEY).then(v => v && setChoice(v)).catch(() => {})
    SecureStore.getItemAsync(MOTION).then(v => v && setMotion(v)).catch(() => {})
  }, [])
  const value = useMemo(() => {
    const name = choice === 'auto' ? (system === 'dark' ? 'dark' : 'white') : choice
    return {
      name, choice, c: PALETTES[name], motion,
      reduced: motion === 'reduced' || (motion === 'system' && systemReduced),
      setChoice: v => { setChoice(v); SecureStore.setItemAsync(KEY, v).catch(() => {}) },
      setMotion: v => { setMotion(v); SecureStore.setItemAsync(MOTION, v).catch(() => {}) },
    }
  }, [choice, system, motion, systemReduced])
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export const useTheme = () => useContext(ThemeContext)
