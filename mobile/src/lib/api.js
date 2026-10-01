import Constants from 'expo-constants'

// The same FastAPI the website uses. The phone always talks to the hosted one.
export const BASE = Constants.expoConfig?.extra?.apiUrl ?? 'https://stridian.vercel.app'

let current = null                     // the bearer token, set by the session
export const setToken = t => { current = t }

// set by the session, so a stale token bounces straight back to sign-in
let onUnauthorized = () => {}
export const setUnauthorizedHandler = fn => { onUnauthorized = fn }

async function unwrap(res) {
  if (res.status === 401 && current) {
    current = null
    onUnauthorized()
  }
  if (res.status === 204) return null
  const body = await res.json().catch(() => null)
  if (!res.ok) {
    const detail = body?.detail
    const err = new Error(
      typeof detail === 'string' ? detail
        : Array.isArray(detail) ? detail.map(fieldError).join('; ')
          : `${res.status} — the server didn't answer as expected`
    )
    err.status = res.status
    err.path = res.url?.replace(BASE, '')
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
  height_cm: 'Height', weight_kg: 'Weight', name: 'Name', year: 'Year', category: 'Team',
  enrol_code: 'Enrolment code', password: 'Password', code: 'Code', email: 'Email',
}
function fieldError(d) {
  const msg = String(d.msg ?? '').replace(/^Value error, /, '')
  const field = d.loc?.at(-1)
  if (typeof field !== 'string' || field === 'body') return msg
  const word = FIELD_WORDS[field] ?? field.replaceAll('_', ' ')
  if (msg === 'Field required' || (d.input == null && msg.startsWith('Input should'))) return `${word} is needed`
  return /^(Input should|String should)/.test(msg) ? `${word}: ${msg.toLowerCase()}` : `${word} ${msg}`
}

const headers = (extra = {}) => (current ? { ...extra, Authorization: `Bearer ${current}` } : extra)
export const authHeaders = () => headers()

// No connection at all reads as its own error, so screens can show the offline state.
async function call(url, init) {
  let res
  try {
    res = await fetch(BASE + url, init)
  } catch {
    const err = new Error('No connection — check your Wi-Fi or mobile data.')
    err.offline = true
    throw err
  }
  return unwrap(res)
}

const send = (method, url, body) => call(url, {
  method,
  headers: headers(body === undefined ? {} : { 'Content-Type': 'application/json' }),
  body: body === undefined ? undefined : JSON.stringify(body),
})
const get = url => call(url, { headers: headers() })

// a photo or certificate goes up as the raw request body (the server checks what it is)
export async function sendFile(method, url, uri, type = 'image/jpeg', filename) {
  const blob = await (await fetch(uri)).blob()
  return call(url, {
    method,
    headers: headers({ 'Content-Type': type, ...(filename ? { 'X-Filename': encodeURIComponent(filename) } : {}) }),
    body: blob,
  })
}

// An image behind sign-in: the URL plus the header <Image source> needs.
export const authedSource = (url, version) =>
  (version ? { uri: `${BASE}${url}?v=${encodeURIComponent(version)}`, headers: headers() } : null)

export const api = {
  health: () => get('/api/health'),
  sports: () => get('/api/sports'),
  nutritionOptions: () => get('/api/nutrition/options'),

  // students: a code to their university inbox, then that code + the password they pick
  studentCode: email => send('POST', '/api/student/code', { email }),
  studentVerify: body => send('POST', '/api/student/verify', body),
  studentLogin: body => send('POST', '/api/student/login', body),
  studentMe: () => get('/api/student/me'),
  studentLogout: () => send('POST', '/api/student/logout'),
  enrol: body => send('POST', '/api/student/enrol', body),
  myReport: () => get('/api/student/report'),
  updateMyProfile: body => send('PATCH', '/api/student/profile', body),
  setMyPhoto: uri => sendFile('PUT', '/api/student/photo', uri),
  myAchievements: () => get('/api/student/achievements'),
  studentCoach: () => get('/api/student/coach'),
  studentCoachSeen: snapshot => send('POST', '/api/student/coach/seen', snapshot),
  focusTick: () => send('POST', '/api/student/focus/tick'),
  // drill clips the student films from the app (chunked upload: lib/upload.js)
  startMyVideo: body => send('POST', '/api/student/videos', body),
  myVideos: () => get('/api/student/videos'),
  myVideoPose: id => get(`/api/student/videos/${id}/pose`),
  deleteMyVideo: id => send('DELETE', `/api/student/videos/${id}`),
  // phone notifications
  pushRegister: (token, prefs) => send('POST', '/api/push/token', { token, prefs }),
  pushUnregister: token => send('DELETE', '/api/push/token', { token, prefs: {} }),

  // coaches and admins
  signup: body => send('POST', '/api/auth/signup', body),
  login: body => send('POST', '/api/auth/login', body),
  resetCode: email => send('POST', '/api/auth/reset-code', { email }),
  reset: body => send('POST', '/api/auth/reset', body),
  me: () => get('/api/auth/me'),
  logout: () => send('POST', '/api/auth/logout'),
  coachFeed: () => get('/api/coach/feed'),
  updateMe: body => send('PATCH', '/api/auth/me', body),
  // deleting an account needs the password again
  deleteMyStudentAccount: password => send('DELETE', '/api/student/me', { password }),
  deleteMyCoachAccount: password => send('DELETE', '/api/auth/me', { password }),
  switchSport: sport => send('PATCH', '/api/auth/sport', { sport }),
  coaches: () => get('/api/coaches'),

  // a student's own achievements (certificates)
  addMyAchievement: (uri, type, name) => sendFile('POST', '/api/student/achievements', uri, type, name),
  editMyAchievement: (id, body) => send('PATCH', `/api/student/achievements/${id}`, body),
  deleteMyAchievement: id => send('DELETE', `/api/student/achievements/${id}`),

  // the squad, for coaches
  weights: slug => get(`/api/sports/${slug}/weights`),
  saveWeights: (slug, weights) => send('PUT', `/api/sports/${slug}/weights`, { weights }),
  resetWeights: slug => send('POST', `/api/sports/${slug}/weights/reset`),
  levels: slug => get(`/api/sports/${slug}/levels`),
  enrolCode: () => get('/api/enrol-code'),
  newEnrolCode: () => send('POST', '/api/enrol-code/rotate'),
  students: () => get('/api/students'),
  student: id => get(`/api/students/${id}`),
  createStudent: body => send('POST', '/api/students', body),
  updateStudent: (id, body) => send('PATCH', `/api/students/${id}`, body),
  deleteStudent: id => send('DELETE', `/api/students/${id}`),
  setStudentPhoto: (id, uri) => sendFile('PUT', `/api/students/${id}/photo`, uri),
  achievements: (status = '') => get(`/api/achievements${status ? `?status=${status}` : ''}`),
  studentAchievements: id => get(`/api/students/${id}/achievements`),
  addStudentAchievement: (id, uri, type, name) => sendFile('POST', `/api/students/${id}/achievements`, uri, type, name),
  editAchievement: (id, body) => send('PATCH', `/api/achievements/${id}`, body),
  reviewAchievement: (id, decision, note, version) =>
    send('POST', `/api/achievements/${id}/review`, { decision, note, version }),
  results: id => get(`/api/students/${id}/results`),
  saveResults: (id, body) => send('PUT', `/api/students/${id}/results`, body),
  history: id => get(`/api/students/${id}/history`),
  analysis: id => get(`/api/students/${id}/analysis`),
  verify: (id, position) => send('POST', `/api/students/${id}/verify`, { position }),
  unverify: id => send('DELETE', `/api/students/${id}/verify`),
  videos: id => get(`/api/students/${id}/videos`),
  startVideo: (id, body) => send('POST', `/api/students/${id}/videos`, body),
  videoPose: videoId => get(`/api/videos/${videoId}/pose`),
  logFocus: (id, day) => send('POST', `/api/students/${id}/focus/log`, { day }),
  deleteVideo: videoId => send('DELETE', `/api/videos/${videoId}`),
  matches: () => get('/api/matches'),
  startMatch: body => send('POST', '/api/matches', body),
  match: id => get(`/api/matches/${id}`),
  assignTrack: (clipId, trackId, studentId) =>
    send('POST', `/api/matches/${clipId}/assign`, { track_id: trackId, student_id: studentId }),
  unassignTrack: (clipId, trackId) => send('DELETE', `/api/matches/${clipId}/assign/${trackId}`),
  deleteMatch: id => send('DELETE', `/api/matches/${id}`),
  cardsConfig: (category = 'M', format = '') =>
    get(`/api/cards/config?category=${encodeURIComponent(category)}${format ? `&format=${encodeURIComponent(format)}` : ''}`),
  cards: () => get('/api/cards'),
  card: id => get(`/api/cards/${id}`),
  createCard: body => send('POST', '/api/cards', body),
  saveCard: (id, body) => send('PUT', `/api/cards/${id}`, body),
  deleteCard: id => send('DELETE', `/api/cards/${id}`),
  addCardPhoto: (id, uri, type) => sendFile('POST', `/api/cards/${id}/photos`, uri, type),
  deleteCardPhoto: (id, n, v) => send('DELETE', `/api/cards/${id}/photos/${n}?v=${v}`),
  readCardPhoto: (id, n, v) => send('POST', `/api/cards/${id}/photos/${n}/read?v=${v}`),
  training: () => get('/api/training'),
  rollback: versionId => send('POST', `/api/training/versions/${versionId}/rollback`),
}

// The sports and their positions change only with a new server, so fetch them once.
let sportsOnce = null
export const getSports = () => (sportsOnce ??= api.sports().catch(err => { sportsOnce = null; throw err }))

// shared formatting lives in format.js (it imports nothing, so scripts/check.mjs can test it)
export { LEVEL_NAMES, utc, unitOf, formatValue, shortUnits, initials } from './format.js'
