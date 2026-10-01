import { Alert, Platform } from 'react-native'
import * as ImagePicker from 'expo-image-picker'
import * as DocumentPicker from 'expo-document-picker'
import * as Sharing from 'expo-sharing'
import { Directory, File, Paths } from 'expo-file-system'
import { ImageManipulator, SaveFormat } from 'expo-image-manipulator'
import { BASE, authHeaders } from './api'

/* Pick (or take) a photo and shrink it on the phone before it goes up: a phone photo is
   3–8 MB, the server takes 4 MB at most. Resolves to { uri, type, name } or null. */
export async function pickPhoto({ camera = false, maxSide = 1600, quality = 0.85 } = {}) {
  if (camera) {
    const p = await ImagePicker.requestCameraPermissionsAsync()
    if (!p.granted) throw new Error('Camera access is off for Stridian — turn it on in your phone’s Settings.')
  }
  const opts = { mediaTypes: ['images'], quality: 1 }
  const res = await (camera ? ImagePicker.launchCameraAsync(opts) : ImagePicker.launchImageLibraryAsync(opts))
  if (res.canceled) return null
  const a = res.assets[0]
  const scale = Math.min(1, maxSide / Math.max(a.width || maxSide, a.height || maxSide))
  let ctx = ImageManipulator.manipulate(a.uri)
  if (scale < 1) ctx = ctx.resize(a.width >= a.height ? { width: Math.round(a.width * scale) } : { height: Math.round(a.height * scale) })
  const out = await (await ctx.renderAsync()).saveAsync({ compress: quality, format: SaveFormat.JPEG })
  return { uri: out.uri, type: 'image/jpeg', name: (a.fileName ?? 'photo').replace(/\.\w+$/, '') + '.jpg' }
}

export async function pickPdf() {
  const res = await DocumentPicker.getDocumentAsync({ type: 'application/pdf', copyToCacheDirectory: true })
  if (res.canceled) return null
  const a = res.assets[0]
  if (a.size > 4 * 1024 * 1024) throw new Error('That PDF is over 4 MB — take a photo of the certificate instead.')
  return { uri: a.uri, type: 'application/pdf', name: a.name }
}

// Camera, photos or a PDF — the phone's own chooser.
export function chooseCertificate() {
  return new Promise((resolve, reject) => {
    const run = fn => () => fn().then(resolve, reject)
    Alert.alert('Add a certificate', 'A clear photo of the whole certificate works best.', [
      { text: 'Take a photo', onPress: run(() => pickPhoto({ camera: true, maxSide: 2000 })) },
      { text: 'Choose a photo', onPress: run(() => pickPhoto({ maxSide: 2000 })) },
      { text: 'Choose a PDF', onPress: run(pickPdf) },
      // Android dismisses on a tap outside; iOS needs the button
      ...(Platform.OS === 'ios' ? [{ text: 'Cancel', style: 'cancel', onPress: () => resolve(null) }] : []),
    ], { cancelable: true, onDismiss: () => resolve(null) })
  })
}

// A signed-in file (a certificate PDF, an Excel download): fetch it, then hand it to the phone.
export async function openAuthedFile(url, name = 'certificate.pdf', mimeType = 'application/pdf') {
  const dir = new Directory(Paths.cache, 'stridian')
  if (!dir.exists) dir.create()
  const file = await File.downloadFileAsync(BASE + url, new File(dir, name), { headers: authHeaders(), idempotent: true })
  await Sharing.shareAsync(file.uri, { mimeType })
}

// A drill clip: film it now, or pick one already on the phone.
export async function pickVideo({ camera = false, maxDuration = 120 } = {}) {
  if (camera) {
    const p = await ImagePicker.requestCameraPermissionsAsync()
    if (!p.granted) throw new Error('Camera access is off for Stridian — turn it on in your phone’s Settings.')
  }
  const opts = { mediaTypes: ['videos'], videoMaxDuration: maxDuration, quality: 1 }
  const res = await (camera ? ImagePicker.launchCameraAsync(opts) : ImagePicker.launchImageLibraryAsync(opts))
  if (res.canceled) return null
  return res.assets[0]
}

export const XLSX = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
