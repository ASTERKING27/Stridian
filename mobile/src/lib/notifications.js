import { Platform } from 'react-native'
import * as Notifications from 'expo-notifications'
import * as Device from 'expo-device'
import Constants from 'expo-constants'
import * as SecureStore from 'expo-secure-store'
import { api } from './api'

// Settings › Notifications — what this phone wants to hear about (the server filters on it)
export const NOTIFY_KEY = 'stridian.notify'
export const NOTIFY_DEFAULT = { video: true, coach: true, focus: false }
const TOKEN_KEY = 'stridian.pushToken'

Notifications.setNotificationHandler({
  handleNotification: async () => ({ shouldShowBanner: true, shouldShowList: true, shouldPlaySound: false, shouldSetBadge: false }),
})

export const notifyPrefs = async () => {
  try { return { ...NOTIFY_DEFAULT, ...JSON.parse((await SecureStore.getItemAsync(NOTIFY_KEY)) ?? '{}') } } catch { return NOTIFY_DEFAULT }
}

/* Tell the server this phone's push token and what it wants. `ask`: show the system
   permission prompt (after the app's own "why we ask" screen). Best-effort and silent:
   Expo Go on Android and emulators can't receive push — the development build can. */
export async function registerPush(ask = false) {
  try {
    if (!Device.isDevice) return null
    let { status } = await Notifications.getPermissionsAsync()
    if (status !== 'granted' && ask) status = (await Notifications.requestPermissionsAsync()).status
    if (status !== 'granted') return null
    if (Platform.OS === 'android') {
      await Notifications.setNotificationChannelAsync('default', { name: 'Stridian', importance: Notifications.AndroidImportance.DEFAULT })
    }
    const projectId = Constants.expoConfig?.extra?.eas?.projectId ?? Constants.easConfig?.projectId
    if (!projectId) return null
    const token = (await Notifications.getExpoPushTokenAsync({ projectId })).data
    await api.pushRegister(token, await notifyPrefs())
    await SecureStore.setItemAsync(TOKEN_KEY, token)
    return token
  } catch {
    return null
  }
}

// Signing out: this phone stops getting that account's notifications.
export async function unregisterPush() {
  try {
    const token = await SecureStore.getItemAsync(TOKEN_KEY)
    if (token) await api.pushUnregister(token)
  } catch { /* nothing to undo */ }
}

// whether the app's own "why we ask" screen (app/(app)/primer) has been shown for this
export const primed = kind => SecureStore.getItemAsync(`stridian.primed.${kind}`).then(v => !!v).catch(() => true)
