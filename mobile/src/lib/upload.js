import { fetch as expoFetch } from 'expo/fetch'
import { File } from 'expo-file-system'
import { BASE, api, authHeaders } from './api'

const ALLOWED = ['.mp4', '.mov', '.avi', '.mkv', '.webm', '.m4v']
export const MAX_BYTES = 200 * 1024 * 1024          // a drill clip
export const MAX_MATCH_BYTES = 600 * 1024 * 1024    // match footage is longer
const sleep = ms => new Promise(r => setTimeout(r, ms))

// The server takes a clip by its name's extension; a camera file may not have a usable one.
export function clipName(asset) {
  const raw = asset.fileName || asset.uri.split('/').pop() || 'clip.mp4'
  const ext = (raw.match(/\.[a-z0-9]+$/i)?.[0] ?? '').toLowerCase()
  return ALLOWED.includes(ext) ? raw : `${raw.replace(/\.[^.]*$/, '')}.mp4`
}

/* A drill clip goes up in the pieces the server asks for (4 MB): the hosted API takes at
   most 4.5 MB a request, and a dropped connection then costs one piece, not the clip.
   The server answers every piece with how many bytes it really has; the next piece
   starts from there. `studentId` set: a coach uploading for that student; `match` set
   ('left' or 'right', the way the team attacks): match footage for the whole squad. */
export async function uploadClip({ uri, name, label, studentId, match }, onProgress, signal) {
  const file = new File(uri)
  const total = file.size
  const max = match ? MAX_MATCH_BYTES : MAX_BYTES
  if (!total) throw new Error('Couldn’t read that video on the phone — try choosing it again.')
  if (total > max) throw Object.assign(new Error(`That clip is over ${max / 1048576} MB — trim it or record a shorter one.`), { kind: 'size' })
  const body = { filename: name, size: total, content_type: 'application/octet-stream', label }
  const { id, chunkSize } = await (match ? api.startMatch({ ...body, attack_direction: match })
    : studentId ? api.startVideo(studentId, body) : api.startMyVideo(body))
  const url = match ? `${BASE}/api/matches/${id}/upload`
    : studentId ? `${BASE}/api/videos/${id}/upload` : `${BASE}/api/student/videos/${id}/upload`
  const pieces = Math.ceil(total / chunkSize)
  const handle = file.open()
  let offset = 0
  let failures = 0
  onProgress?.({ sent: 0, total, piece: 1, pieces })
  try {
    while (offset < total) {
      if (signal?.aborted) throw Object.assign(new Error('Upload cancelled'), { kind: 'cancel' })
      const end = Math.min(offset + chunkSize, total)
      handle.offset = offset
      const bytes = handle.readBytes(end - offset)
      try {
        const res = await expoFetch(url, {
          method: 'PUT', signal, body: bytes,
          headers: { ...authHeaders(), 'Content-Type': 'application/octet-stream', 'X-Chunk-Range': `bytes ${offset}-${end - 1}/${total}` },
        })
        const r = await res.json().catch(() => null)
        if (!res.ok) throw Object.assign(new Error(r?.detail ?? `The server said ${res.status}`), { status: res.status })
        if (r.done) {
          onProgress?.({ sent: total, total, piece: pieces, pieces, done: true })
          return { id, pieces }
        }
        if (r.received === offset) throw new Error('The server didn’t take that piece.')
        offset = r.received
        failures = 0
        onProgress?.({ sent: offset, total, piece: Math.min(pieces, Math.floor(offset / chunkSize) + 1), pieces })
      } catch (err) {
        if (signal?.aborted) throw Object.assign(new Error('Upload cancelled'), { kind: 'cancel' })
        if (err.status && err.status < 500) throw err           // the server refused it: retrying won't help
        failures += 1
        if (failures > 4) throw Object.assign(err, { kind: 'network', sent: offset, piece: Math.floor(offset / chunkSize) + 1, pieces })
        await sleep(1000 * 2 ** failures)                        // 2, 4, 8, 16 s — rides out a patchy signal
      }
    }
  } finally {
    handle.close()
  }
  return { id, pieces }
}
