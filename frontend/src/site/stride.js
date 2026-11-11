/* One sprint stride, as a pose model reads it off a drill video.

   Each leg follows the same nine keyframes half a stride apart: thigh angle from the
   vertical, knee flexion and ankle plantarflexion, in degrees. The foot that is on the
   ground holds the hip up; between contacts the body is in flight. From that the whole
   pose follows, in metres: x forward, y up, z across (the near side, facing the camera,
   is z < 0). Everything is a pure function of the stride phase, so the scene can be
   scrubbed forwards and backwards. */

const KF = [
  [0.00, 26, 118, 0], [0.12, 52, 112, -6], [0.25, 70, 86, -8], [0.38, 42, 34, 2],
  [0.47, 24, 22, 10], [0.60, 12, 40, -22], [0.72, -16, 16, 30], [0.82, -8, 70, 26], [0.91, 6, 112, 12],
]
const N = KF.length
const RAD = Math.PI / 180
const BODY = 1.8
const S = {
  thigh: 0.245 * BODY, shank: 0.245 * BODY, foot: 0.105 * BODY, trunk: 0.3 * BODY,
  upper: 0.17 * BODY, fore: 0.155 * BODY, head: 0.05 * BODY, neck: 0.04 * BODY, hip: 0.125, sh: 0.19,
}
export const HEAD_R = S.head
export const STANCE = [0.47, 0.72]          // the part of a leg's stride its foot is down

export const wrap = t => ((t % 1) + 1) % 1

// Catmull-Rom through the keyframes, round the loop
function interp(t, c) {
  t = wrap(t)
  let i = 0
  for (let j = 0; j < N; j++) if (KF[j][0] <= t) i = j
  const i0 = (i - 1 + N) % N, i2 = (i + 1) % N, i3 = (i + 2) % N
  const t1 = KF[i][0], t2 = KF[i2][0] + (i2 <= i ? 1 : 0)
  const u = (t - t1) / (t2 - t1), u2 = u * u, u3 = u2 * u
  const p0 = KF[i0][c], p1 = KF[i][c], p2 = KF[i2][c], p3 = KF[i3][c]
  return 0.5 * (2 * p1 + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)
}

// one leg in its own plane, measured from the hip
function leg(t) {
  const th = interp(t, 1) * RAD, flex = interp(t, 2), pf = interp(t, 3) * RAD, sh = th - flex * RAD
  const kx = Math.sin(th) * S.thigh, ky = -Math.cos(th) * S.thigh
  const ax = kx + Math.sin(sh) * S.shank, ay = ky - Math.cos(sh) * S.shank
  const fa = sh + Math.PI / 2 - pf
  return {
    kx, ky, ax, ay, flex,
    tx: ax + Math.sin(fa) * S.foot, ty: ay - Math.cos(fa) * S.foot,
    hx: ax - Math.sin(fa) * S.foot * 0.25, hy: ay + Math.cos(fa) * S.foot * 0.25,
  }
}

const low = t => { const p = leg(t); return -Math.min(p.ay, p.ty, p.hy) }
export const inStance = t => { t = wrap(t); return t >= STANCE[0] && t <= STANCE[1] }

// the planted foot holds the hip up; in flight it travels from toe-off to the next contact
export function hipHeight(t) {
  t = wrap(t)
  if (inStance(t)) return low(t)
  if (inStance(t + 0.5)) return low(t + 0.5)
  const a = t > STANCE[1] ? STANCE[1] : STANCE[1] - 0.5
  const s = (t - a) / 0.25, eA = low(STANCE[1]), eB = low(STANCE[0])
  return eA + (eB - eA) * s + BODY * 0.028 * Math.sin(Math.PI * s)
}

// the ground passes under the planted foot, so one stride covers this many metres
export const STRIDE_M = (leg(STANCE[0]).ax - leg(STANCE[1]).ax) / (STANCE[1] - STANCE[0])
// where a foot meets the ground, ahead of the hip, and how far off the centre line
export const CONTACT_X = leg(STANCE[0]).ax
export const STEP_Z = S.hip * 0.55

export const JOINTS = ['head', 'neck', 'shN', 'shF', 'elN', 'elF', 'wrN', 'wrF', 'hipN', 'hipF',
  'knN', 'knF', 'anN', 'anF', 'heN', 'heF', 'toN', 'toF']
const ix = Object.fromEntries(JOINTS.map((j, i) => [j, i]))
const pairs = list => list.map(([a, b]) => [ix[a], ix[b]])
export const BONES = {
  near: pairs([['shN', 'elN'], ['elN', 'wrN'], ['hipN', 'knN'], ['knN', 'anN'], ['anN', 'toN'], ['heN', 'anN']]),
  far: pairs([['shF', 'elF'], ['elF', 'wrF'], ['hipF', 'knF'], ['knF', 'anF'], ['anF', 'toF'], ['heF', 'anF']]),
  core: pairs([['shN', 'shF'], ['hipN', 'hipF'], ['shN', 'hipN'], ['shF', 'hipF']]),
}

/* The pose at stride phase t, written into `out` (a Float32Array of JOINTS.length * 3) and
   returned with what the analysis reads off it. */
export function pose(t, out = new Float32Array(JOINTS.length * 3)) {
  const set = (name, x, y, z) => { const i = ix[name] * 3; out[i] = x; out[i + 1] = y; out[i + 2] = z }
  const hy = hipHeight(t)
  const swing = Math.sin(2 * Math.PI * t)
  const yawP = 9 * RAD * swing            // the hip of the leg swinging forward leads
  const yawS = -12 * RAD * swing          // the shoulders turn the other way
  const lean = (9 + 2 * Math.sin(4 * Math.PI * t)) * RAD

  const nx = Math.sin(lean) * S.trunk, ny = hy + Math.cos(lean) * S.trunk
  set('neck', nx, ny, 0)
  set('head', nx + Math.sin(lean + 4 * RAD) * (S.neck + S.head), ny + Math.cos(lean + 4 * RAD) * (S.neck + S.head), 0)

  for (const [side, sign, phase] of [['N', -1, t], ['F', 1, t + 0.5]]) {
    const hx = -sign * Math.sin(yawP) * S.hip, hz = sign * Math.cos(yawP) * S.hip
    set(`hip${side}`, hx, hy, hz)
    const L = leg(phase)
    set(`kn${side}`, hx + L.kx, hy + L.ky, hz * 0.82)
    set(`an${side}`, hx + L.ax, hy + L.ay, hz * 0.55)
    set(`to${side}`, hx + L.tx, hy + L.ty, hz * 0.55)
    set(`he${side}`, hx + L.hx, hy + L.hy, hz * 0.55)

    const sx = nx - sign * Math.sin(yawS) * S.sh, sz = sign * Math.cos(yawS) * S.sh
    set(`sh${side}`, sx, ny, sz)
    const s = Math.sin(2 * Math.PI * phase)
    const a = (10 - 50 * s) * RAD, e = (78 + 8 * s) * RAD
    const ex = sx + Math.sin(a) * S.upper, ey = ny - Math.cos(a) * S.upper
    set(`el${side}`, ex, ey, sz * 1.1)
    set(`wr${side}`, ex + Math.sin(a + e) * S.fore, ey - Math.cos(a + e) * S.fore, sz * 0.72)
  }

  return {
    joints: out,
    knee: 180 - interp(t, 2),                       // the near knee's angle
    lean: lean / RAD,
    grounded: inStance(t) || inStance(t + 0.5),
  }
}

/* The last four foot strikes before stride time `tau` (in strides): where on the track
   each landed and how long ago, in strides. Near foot at STANCE[0], far foot half a
   stride later. */
export function strikes(tau) {
  const out = []
  for (const [at, z] of [[STANCE[0], -STEP_Z], [STANCE[0] + 0.5, STEP_Z]]) {
    const n = Math.floor(tau - at)
    for (const k of [n, n - 1]) out.push({ x: CONTACT_X + (k + at) * STRIDE_M, z, age: tau - (k + at) })
  }
  return out
}

if (import.meta.url === `file://${globalThis.process?.argv?.[1]}`) {
  // node src/site/stride.js
  const assert = (ok, msg) => { if (!ok) throw new Error(msg) }
  assert(STRIDE_M > 1.5 && STRIDE_M < 6, `a stride covers ${STRIDE_M} m`)
  let minFoot = Infinity, maxHead = 0
  for (let i = 0; i < 200; i++) {
    const t = i / 200, p = pose(t), j = p.joints
    assert(p.knee > 50 && p.knee <= 180, `knee ${p.knee} at ${t}`)
    for (const name of ['anN', 'toN', 'heN', 'anF', 'toF', 'heF']) minFoot = Math.min(minFoot, j[ix[name] * 3 + 1])
    maxHead = Math.max(maxHead, j[ix.head * 3 + 1])
    // the planted foot is on the ground, nothing goes through it
    if (p.grounded) assert(Math.min(...['anN', 'toN', 'heN', 'anF', 'toF', 'heF'].map(n => j[ix[n] * 3 + 1])) < 0.012, `stance foot off the ground at ${t}`)
    // the pose has no jump in it from one frame to the next
    const q = pose(t + 1 / 200).joints
    for (let k = 0; k < j.length; k++) assert(Math.abs(j[k] - q[k]) < 0.12, `jump at ${t}, coordinate ${k}`)
  }
  assert(minFoot > -0.012, `a foot goes ${minFoot} m under the ground`)
  assert(maxHead > 1.5 && maxHead < 2.0, `head reaches ${maxHead} m`)
  const s = strikes(3.6)
  assert(s.length === 4 && s.every(x => x.age >= 0 && x.age < 2), JSON.stringify(s))
  console.log(`stride: ok (stride ${STRIDE_M.toFixed(2)} m, head ${maxHead.toFixed(2)} m)`)
}
