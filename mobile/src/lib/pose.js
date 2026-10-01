/* The pose overlay's arithmetic (videos/[vid].js): the worker's skeleton track turned into
   points per frame, the knee angle, the hips' path, phases and the key moments. */

// the joints the worker saves (video.POSE_JOINTS), and each side's chain
const JOINTS = [0, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32]
const SIDE = {
  left: { sh: 11, el: 13, wr: 15, hip: 23, kn: 25, an: 27, he: 29, to: 31 },
  right: { sh: 12, el: 14, wr: 16, hip: 24, kn: 26, an: 28, he: 30, to: 32 },
}
export const BONES = [['sh', 'el'], ['el', 'wr'], ['sh', 'hip'], ['hip', 'kn'], ['kn', 'an'], ['an', 'he'], ['he', 'to'], ['an', 'to']]

const angleAt = (a, b, c) => {
  if (!a || !b || !c) return null
  const v1 = [a[0] - b[0], a[1] - b[1]], v2 = [c[0] - b[0], c[1] - b[1]]
  const cos = (v1[0] * v2[0] + v1[1] * v2[1]) / (Math.hypot(...v1) * Math.hypot(...v2) || 1)
  return Math.round((Math.acos(Math.max(-1, Math.min(1, cos))) * 180) / Math.PI)
}

export function measure(track) {
  const near = SIDE[track.near] ?? SIDE.left
  const far = SIDE[track.near === 'left' ? 'right' : 'left']
  const at = (fr, j) => {
    const i = JOINTS.indexOf(j)
    if (!fr || fr[2 * i] == null || fr[2 * i + 1] == null) return null
    return [fr[2 * i] * track.aspect, fr[2 * i + 1]]
  }
  const frames = track.frames.map(fr => (fr ? JOINTS.reduce((o, j) => ({ ...o, [j]: at(fr, j) }), {}) : null))
  // the area the athlete moves through, padded, so the skeleton fills the panel
  const xs = [], ys = []
  frames.forEach(p => p && Object.values(p).forEach(q => { if (q) { xs.push(q[0]); ys.push(q[1]) } }))
  const pad = 0.12 * Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys), 0.1)
  const bounds = { x0: Math.min(...xs) - pad, y0: Math.min(...ys) - pad, x1: Math.max(...xs) + pad, y1: Math.max(...ys) + pad }
  const hip = frames.map(p => (p?.[near.hip] && p?.[far.hip] ? [(p[near.hip][0] + p[far.hip][0]) / 2, (p[near.hip][1] + p[far.hip][1]) / 2] : p?.[near.hip] ?? null))
  const knee = frames.map(p => (p ? angleAt(p[near.hip], p[near.kn], p[near.an]) : null))
  // phases from the hips against standing height (a jump-shaped clip only)
  const hy = hip.map(h => h?.[1] ?? null)
  const valid = hy.filter(v => v != null)
  const start = valid.slice(0, Math.max(3, Math.round(valid.length * 0.15))).sort((a, b) => a - b)
  const base = start[Math.floor(start.length / 2)] ?? 0          // standing height: the opening frames' median
  const span = bounds.y1 - bounds.y0
  const jumpy = valid.length > 0 && Math.min(...valid) < base - 0.08 * span
  const phase = hy.map((y, i) => {
    if (!jumpy || y == null) return ''
    const d = (y - base) / span, prev = hy[i - 1] ?? y
    if (d < -0.04) return 'IN THE AIR'
    if (d > 0.04) return y >= prev ? 'LOADING' : 'DRIVE'
    return 'STANDING'
  })
  // 16 timeline ticks: how much the hips moved in each sixteenth
  const n = frames.length
  const moves = Array.from({ length: 16 }, (_, b) => {
    let s = 0
    for (let i = Math.floor((b * n) / 16) + 1; i < Math.floor(((b + 1) * n) / 16); i++) {
      if (hip[i] && hip[i - 1]) s += Math.hypot(hip[i][0] - hip[i - 1][0], hip[i][1] - hip[i - 1][1])
    }
    return s
  })
  const top = Math.max(...moves, 1e-6)
  const ticks = moves.map(v => Math.round(12 + (v / top) * 32))
  const pick = (score) => frames.reduce((best, p, i) => (score(i) != null && (best < 0 || score(i) < score(best)) ? i : best), -1)
  const deep = pick(i => knee[i])
  const peak = pick(i => hy[i])
  const stills = [
    { f: deep, label: `LOADING${knee[deep] ? ` · ${knee[deep]}°` : ''}` },
    { f: deep >= 0 && peak >= 0 ? Math.round((deep + peak) / 2) : Math.floor(n / 2), label: 'DRIVE' },
    { f: peak, label: 'PEAK' },
  ].filter(s => s.f >= 0)
  return { frames, near, far, bounds, hip, knee, phase, ticks, stills }
}
