import { useEffect } from 'react'

// Thin wrapper over fetch. Vite proxies /api to FastAPI in dev; when the built
// frontend is served by FastAPI the path is already right, so no base URL either way.

const TOKEN_KEY = 'stridian.token'
const ROLE_KEY = 'stridian.role'

// One signed-in person per browser: a coach or a student. A token saved before
// students had accounts has no role stored, and was a coach's.
export const token = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  role: () => { try { return localStorage.getItem(ROLE_KEY) || 'coach' } catch { return 'coach' } },
  set: (v, role = 'coach') => {
    try {
      if (v) {
        localStorage.setItem(TOKEN_KEY, v)
        localStorage.setItem(ROLE_KEY, role)
      } else {
        localStorage.removeItem(TOKEN_KEY)
        localStorage.removeItem(ROLE_KEY)
      }
    } catch { /* private mode */ }
  },
}

// Set by App so a stale session bounces straight back to the sign-in screen. It gets
// the role that was signed in, or null when nobody was (a wrong password, say).
let onUnauthorized = () => {}
export const setUnauthorizedHandler = fn => { onUnauthorized = fn }

async function unwrap(res) {
  if (res.status === 401) {
    const role = token.get() ? token.role() : null
    token.set(null)
    onUnauthorized(role)
  }
  if (res.status === 204) return null
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    const err = new Error(
      typeof detail === 'string' ? detail
        : Array.isArray(detail) ? detail.map(fieldError).join('; ')
          : `${res.status} ${res.statusText}`
    )
    err.status = res.status
    throw err
  }
  return body
}

// "father_phone" + "Value error, should be…" -> "Father's mobile should be…"
const FIELD_WORDS = {
  ra_number: 'RA number', dob: 'Date of birth', phone: 'Mobile', personal_email: 'Personal email',
  father_name: "Father's name", father_phone: "Father's mobile", mother_name: "Mother's name",
  mother_phone: "Mother's mobile", aadhaar: 'Aadhaar', passport: 'Passport', id_mark: 'Identification mark',
  blood_group: 'Blood group', highest_level: 'Highest level', employee_id: 'Employee ID',
  height_cm: 'Height', weight_kg: 'Weight', name: 'Name', year: 'Year',
}
function fieldError(d) {
  const msg = String(d.msg ?? '').replace(/^Value error, /, '')
  const field = d.loc?.at(-1)
  if (typeof field !== 'string' || field === 'body') return msg
  const word = FIELD_WORDS[field] ?? field.replaceAll('_', ' ')
  // a field left empty arrives as null ("Input should be a valid string")
  if (msg === 'Field required' || (d.input == null && msg.startsWith('Input should'))) return `${word} is needed`
  return /^(Input should|String should)/.test(msg) ? `${word}: ${msg.toLowerCase()}` : `${word} ${msg}`
}

function authHeaders(extra = {}) {
  const t = token.get()
  return t ? { ...extra, Authorization: `Bearer ${t}` } : extra
}

const send = (method, url, body) =>
  fetch(url, {
    method,
    headers: authHeaders(body === undefined ? {} : { 'Content-Type': 'application/json' }),
    body: body === undefined ? undefined : JSON.stringify(body),
  }).then(unwrap)

const get = url => fetch(url, { headers: authHeaders() }).then(unwrap)

// a photo or certificate goes up as the raw request body (the server checks what it is)
const sendFile = (method, url, blob, filename) =>
  fetch(url, {
    method,
    headers: authHeaders({ 'Content-Type': blob.type || 'application/octet-stream',
                           ...(filename ? { 'X-Filename': encodeURIComponent(filename) } : {}) }),
    body: blob,
  }).then(unwrap)

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms))

/* Videos go up in 4 MB pieces: the hosted API accepts at most 4.5 MB per request, and
   a dropped connection then costs one piece, not the whole file. The server always
   answers with how many bytes it really has, and the next piece starts from there. */
async function chunkedUpload(startUrl, extra, uploadUrl, file, onProgress = () => {}) {
  const { id, chunkSize } = await send('POST', startUrl, {
    filename: file.name, size: file.size, content_type: file.type || null, ...extra,
  })
  let offset = 0
  let failures = 0
  while (offset < file.size) {
    const end = Math.min(offset + chunkSize, file.size)
    try {
      const res = await fetch(uploadUrl(id), {
        method: 'PUT',
        headers: authHeaders({
          'Content-Type': 'application/octet-stream',
          'X-Chunk-Range': `bytes ${offset}-${end - 1}/${file.size}`,
        }),
        body: file.slice(offset, end),
      }).then(unwrap)
      if (res.done) {
        onProgress(1)
        return id
      }
      if (res.received === offset) throw new Error('The server did not accept that piece.')
      offset = res.received
      failures = 0
      onProgress(offset / file.size)
    } catch (err) {
      failures += 1
      if (failures > 4) throw err
      await sleep(1000 * 2 ** failures)   // 2, 4, 8, 16 s — rides out a patchy connection
    }
  }
  return id
}

export const api = {
  health: () => fetch('/api/health').then(unwrap),
  nutritionOptions: () => fetch('/api/nutrition/options').then(unwrap),

  // students: a code to their university inbox, then that code + the password they pick
  studentCode: email => send('POST', '/api/student/code', { email }),
  studentVerify: body => send('POST', '/api/student/verify', body),
  studentLogin: body => send('POST', '/api/student/login', body),
  studentMe: () => get('/api/student/me'),
  studentLogout: () => send('POST', '/api/student/logout'),
  enrol: body => send('POST', '/api/student/enrol', body),
  myReport: () => get('/api/student/report'),
  updateMyProfile: body => send('PATCH', '/api/student/profile', body),
  setMyPhoto: blob => sendFile('PUT', '/api/student/photo', blob),
  myAchievements: () => get('/api/student/achievements'),
  addMyAchievement: (blob, name) => sendFile('POST', '/api/student/achievements', blob, name),
  editMyAchievement: (id, body) => send('PATCH', `/api/student/achievements/${id}`, body),
  deleteMyAchievement: id => send('DELETE', `/api/student/achievements/${id}`),

  signup: body => send('POST', '/api/auth/signup', body),
  login: body => send('POST', '/api/auth/login', body),
  me: () => get('/api/auth/me'),
  updateMe: body => send('PATCH', '/api/auth/me', body),
  switchSport: sport => send('PATCH', '/api/auth/sport', { sport }),
  coaches: () => get('/api/coaches'),
  logout: () => send('POST', '/api/auth/logout'),

  sports: () => fetch('/api/sports').then(unwrap),
  weights: slug => get(`/api/sports/${slug}/weights`),
  saveWeights: (slug, weights) => send('PUT', `/api/sports/${slug}/weights`, { weights }),
  resetWeights: slug => send('POST', `/api/sports/${slug}/weights/reset`),

  enrolCode: () => get('/api/enrol-code'),
  newEnrolCode: () => send('POST', '/api/enrol-code/rotate'),

  students: () => get('/api/students'),
  student: id => get(`/api/students/${id}`),
  createStudent: body => send('POST', '/api/students', body),
  updateStudent: (id, body) => send('PATCH', `/api/students/${id}`, body),
  deleteStudent: id => send('DELETE', `/api/students/${id}`),
  setStudentPhoto: (id, blob) => sendFile('PUT', `/api/students/${id}/photo`, blob),

  achievements: (status = '') => get(`/api/achievements${status ? `?status=${status}` : ''}`),
  studentAchievements: id => get(`/api/students/${id}/achievements`),
  addStudentAchievement: (id, blob, name) => sendFile('POST', `/api/students/${id}/achievements`, blob, name),
  editAchievement: (id, body) => send('PATCH', `/api/achievements/${id}`, body),
  // `version` is what the coach was looking at, so a verdict never lands on details
  // the student changed after the page loaded
  reviewAchievement: (id, decision, note, version) =>
    send('POST', `/api/achievements/${id}/review`, { decision, note, version }),

  results: id => get(`/api/students/${id}/results`),
  saveResults: (id, body) => send('PUT', `/api/students/${id}/results`, body),
  history: id => get(`/api/students/${id}/history`),
  analysis: id => get(`/api/students/${id}/analysis`),

  verify: (id, position) => send('POST', `/api/students/${id}/verify`, { position }),
  unverify: id => send('DELETE', `/api/students/${id}/verify`),

  videos: id => get(`/api/students/${id}/videos`),
  uploadVideo: (id, file, onProgress) =>
    chunkedUpload(`/api/students/${id}/videos`, {}, v => `/api/videos/${v}/upload`, file, onProgress),
  deleteVideo: videoId => send('DELETE', `/api/videos/${videoId}`),

  // match lane (YOLO): clips belong to the sport, tracks get assigned to students
  matches: () => get('/api/matches'),
  match: id => get(`/api/matches/${id}`),
  uploadMatch: (file, { label = '', attackDirection = 'right' } = {}, onProgress) =>
    chunkedUpload('/api/matches', { label, attack_direction: attackDirection },
                  c => `/api/matches/${c}/upload`, file, onProgress),
  assignTrack: (clipId, trackId, studentId) =>
    send('POST', `/api/matches/${clipId}/assign`, { track_id: trackId, student_id: studentId }),
  unassignTrack: (clipId, trackId) => send('DELETE', `/api/matches/${clipId}/assign/${trackId}`),
  deleteMatch: id => send('DELETE', `/api/matches/${id}`),
  calibrate: (clipId, body) => send('POST', `/api/matches/${clipId}/calibrate`, body),
  clearCalibration: clipId => send('DELETE', `/api/matches/${clipId}/calibrate`),

  training: () => get('/api/training'),
  rollback: versionId => send('POST', `/api/training/versions/${versionId}/rollback`),
}

// Anything still waiting for (or being handled by) the analysis computer.
export const inFlight = status => status === 'queued' || status === 'processing'

export const statusPill = status =>
  status === 'done' ? 'good' : inFlight(status) || status === 'uploading' ? 'warn' : 'bad'

export const statusWord = status => ({
  queued: 'waiting', processing: 'analysing', uploading: 'uploading', done: 'done',
  failed: 'failed', unavailable: 'not analysed',
}[status] ?? status)

// The API stores UTC without a zone marker, which JS would read as local time.
export const utc = s => new Date(/(Z|[+-]\d\d:?\d\d)$/.test(s) ? s : `${s}Z`)

// "3 min ago" for the worker's last check-in.
export function ago(seconds) {
  if (seconds == null) return 'never'
  if (seconds < 90) return 'just now'
  if (seconds < 5400) return `${Math.round(seconds / 60)} min ago`
  if (seconds < 172800) return `${Math.round(seconds / 3600)} h ago`
  return `${Math.round(seconds / 86400)} days ago`
}

// Re-run `load` every `ms` while `active` is true — for queued videos finishing.
export function usePoll(active, load, ms = 8000) {
  useEffect(() => {
    if (!active) return undefined
    const timer = setInterval(load, ms)
    return () => clearInterval(timer)
  }, [active]) // eslint-disable-line react-hooks/exhaustive-deps
}

// Images can't carry an Authorization header, so fetch them and hand back a blob URL.
export async function authedImage(url) {
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) throw new Error('not available')
  return URL.createObjectURL(await res.blob())
}

// A signed-in file (a certificate): open it in a new tab. The tab is opened before the
// download starts, or pop-up blockers would stop it.
export async function openAuthed(url) {
  const tab = window.open('', '_blank')
  try {
    const blobUrl = await authedImage(url)
    if (tab) tab.location = blobUrl
    else window.location.assign(blobUrl)
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60000)   // the tab has loaded it by then
  } catch (err) {
    tab?.close()
    throw err
  }
}

// A signed-in download (the Excel files), saved under the name the server gives it.
export async function download(url) {
  const res = await fetch(url, { headers: authHeaders() })
  if (!res.ok) await unwrap(res)
  // the real name (filename*, percent-encoded UTF-8) when given, else the plain one
  const header = res.headers.get('Content-Disposition') ?? ''
  const encoded = /filename\*=UTF-8''([^;]+)/i.exec(header)?.[1]
  const name = encoded ? decodeURIComponent(encoded) : (/filename="([^"]+)"/.exec(header)?.[1] ?? 'stridian.xlsx')
  const link = document.createElement('a')
  link.href = URL.createObjectURL(await res.blob())
  link.download = name
  link.click()
  setTimeout(() => URL.revokeObjectURL(link.href), 10000)
}

// ---- shared formatting -----------------------------------------------------

// Coaches can type "8:30" or "510" for a time trial; both land as seconds.
export function parseValue(text) {
  const s = String(text ?? '').trim()
  if (!s) return null
  if (s.includes(':')) {
    const [m, sec] = s.split(':').map(Number)
    return Number.isNaN(m) || Number.isNaN(sec) ? null : m * 60 + sec
  }
  const n = Number(s)
  return Number.isNaN(n) ? null : n
}

export function formatValue(value, metric) {
  if (value === null || value === undefined) return '—'
  if (metric?.key === 'timeTrial2km') {
    return `${Math.floor(value / 60)}:${String(Math.round(value % 60)).padStart(2, '0')}`
  }
  return `${value}${metric?.unit ? ' ' + metric.unit : ''}`
}

export const band = score =>
  score === null || score === undefined ? '' : score >= 65 ? 'good' : score <= 40 ? 'bad' : 'warn'

export const bandWord = score =>
  score === null || score === undefined ? 'not measured'
    : score >= 85 ? 'elite' : score >= 65 ? 'strong' : score > 40 ? 'average' : 'needs work'

// Radar axis labels. A bracketed ACRONYM is the better short form
// ("Countermovement Jump (CMJ)" -> "CMJ"); a bracketed aside is not
// ("Max Vertical Leap (run-up)" -> "Max Vertical Leap").
export function shortLabel(label) {
  const bracket = label.match(/\(([^)]+)\)/)?.[1]
  // must contain a letter, so "(5-10-5)" stays an aside rather than becoming the label
  if (bracket && /^(?=.*[A-Z])[A-Z0-9][A-Z0-9-]{1,7}$/.test(bracket)) return bracket
  return label.replace(/\s*\([^)]*\)/, '').trim()
}

// Break a label onto at most two lines so radar axes stay readable without truncating.
export function wrapLabel(text, max = 14) {
  if (text.length <= max) return [text]
  const words = text.split(' ')
  let first = ''
  let i = 0
  while (i < words.length && (first + ' ' + words[i]).trim().length <= max) {
    first = (first + ' ' + words[i]).trim()
    i += 1
  }
  if (!first) return [text.slice(0, max - 1) + '…']
  const second = words.slice(i).join(' ')
  if (!second) return [first]
  return [first, second.length > max + 4 ? second.slice(0, max + 3) + '…' : second]
}

export const initials = name =>
  (name || '?').trim().split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase()
