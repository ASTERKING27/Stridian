/* The hero's scene: a sprinter as the pose model sees one, in three dimensions.

   Tracked joints and the bones between them, the near knee measured on every frame,
   earlier poses left standing on the track like a chronophotograph, the hip's path
   drawn behind, and a floor of dots that lights where each foot lands. Everything is
   drawn from the page's own colour tokens, so it follows the look and the accent.

   The dotted floor is adapted from ThreeUI's Dot Matrix background (MIT,
   github.com/MengTo/threeui). */

import {
  Color, Fog, Mesh, PerspectiveCamera, PlaneGeometry, Points, BufferGeometry, BufferAttribute,
  Scene, ShaderMaterial, Vector3, WebGLRenderer,
} from 'three'
import { Line2 } from 'three/addons/lines/Line2.js'
import { LineGeometry } from 'three/addons/lines/LineGeometry.js'
import { LineMaterial } from 'three/addons/lines/LineMaterial.js'
import { LineSegments2 } from 'three/addons/lines/LineSegments2.js'
import { LineSegmentsGeometry } from 'three/addons/lines/LineSegmentsGeometry.js'
import { BONES, HEAD_R, JOINTS, STRIDE_M, hipHeight, pose, strikes } from './stride'

const T = 1.15                 // seconds a stride takes on screen: the clip plays slowed down
const GHOSTS = 6
const GHOST_EVERY = 0.105      // of a stride between the poses left behind
const TRAIL = 72
const HEAD_SEG = 28
const J = Object.fromEntries(JOINTS.map((name, i) => [name, i]))
const NEAR_DOTS = ['hipN', 'shN', 'elN', 'wrN', 'anN', 'toN', 'heN']
const FAR_DOTS = ['hipF', 'shF', 'elF', 'wrF', 'knF', 'anF', 'toF']

const GROUND_VERT = /* glsl */`
  varying vec3 vW;
  void main() {
    vec4 w = modelMatrix * vec4(position, 1.0);
    vW = w.xyz;
    gl_Position = projectionMatrix * viewMatrix * w;
  }`

const GROUND_FRAG = /* glsl */`
  uniform float uOff;
  uniform float uReveal;
  uniform vec3 uInk;
  uniform vec3 uAcc;
  uniform vec4 uStrike[4];     // where on the track, how long ago (s), how hard
  varying vec3 vW;

  void main() {
    vec2 p = vec2(vW.x + uOff, vW.z);
    float wx = fwidth(p.x), wz = fwidth(p.y);

    // lane lines every 1.22 m; the runner is in the middle of a lane
    float lz = abs(fract(p.y / 1.22) - 0.5) * 1.22;
    float lane = 1.0 - smoothstep(0.0, wz * 1.3, lz - 0.01);

    // a mark across each lane line every metre, a longer one every five
    float dx = 0.5 - abs(fract(p.x) - 0.5);
    float five = 1.0 - step(0.5, abs(mod(floor(p.x + 0.5), 5.0)));
    float tick = (1.0 - smoothstep(0.0, wx * 1.3, dx - 0.008)) * (1.0 - step(mix(0.09, 0.2, five), lz));

    // the line every 30 m, across the runner's own lane
    float d30 = abs(mod(p.x + 15.0, 30.0) - 15.0);
    float line30 = (1.0 - smoothstep(0.0, wx * 1.3, d30 - 0.012)) * (1.0 - step(0.61, abs(p.y)));

    // each foot strike: the contact, then a ring running out across the floor
    float ripple = 0.0;
    for (int i = 0; i < 4; i++) {
      vec4 s = uStrike[i];
      float d = length(p - s.xy);
      float ring = (d - s.z * 2.4) / 0.17;
      ripple += s.w * (exp(-ring * ring) * exp(-s.z * 2.1) + exp(-d * d / 0.035) * exp(-s.z * 5.0));
    }
    ripple = clamp(ripple, 0.0, 1.0);

    // the dot floor, lit in a pool around the runner and by the ripples
    vec2 g = (fract(p / 0.2) - 0.5) * 0.2;
    float r = 0.013 + 0.026 * ripple;
    float dots = 1.0 - smoothstep(r, r + max(wx, wz) * 1.3, length(g));
    float pool = smoothstep(4.6, 0.3, length(vW.xz * vec2(1.0, 1.5)));
    float dotA = dots * (0.2 * pool + 0.9 * ripple);

    float lineA = max(lane * 0.15, tick * 0.3);
    float accA = line30 * 0.7;
    float a = clamp(lineA + dotA + accA, 0.0, 1.0);
    vec3 c = (uInk * lineA + mix(uInk, uAcc, ripple) * dotA + uAcc * accA) / max(a, 0.0001);
    float fade = smoothstep(30.0, 7.0, length(vW.xz));
    gl_FragColor = vec4(c, a * fade * uReveal);
  }`

const DOT_VERT = /* glsl */`
  attribute float aSize;
  attribute float aKind;
  uniform float uDpr;
  varying float vKind;
  void main() {
    vKind = aKind;
    gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
    gl_PointSize = aSize * uDpr;
  }`

const DOT_FRAG = /* glsl */`
  uniform vec3 uInk;
  uniform vec3 uAcc;
  uniform vec3 uBg;
  uniform float uReveal;
  varying float vKind;
  void main() {
    float d = length(gl_PointCoord - 0.5) * 2.0;
    float w = fwidth(d);
    float disc = 1.0 - smoothstep(1.0 - w, 1.0, d);
    float core = 1.0 - smoothstep(0.52 - w, 0.52, d);
    // kind 0: the near side, an ink ring. 1: the far side, dimmer. 2: the measured joint.
    vec3 c = vKind > 1.5 ? uAcc : mix(uInk, uBg, core);
    float a = disc * (vKind > 0.5 && vKind < 1.5 ? 0.45 : 1.0);
    gl_FragColor = vec4(c, a * uReveal);
  }`

function tokens() {
  const cs = getComputedStyle(document.documentElement)
  const get = (name, fallback) => new Color((cs.getPropertyValue(name) || '').trim() || fallback)
  return { ink: get('--ink', '#ECEBE6'), bg: get('--plane', '#0B0C0D'), acc: get('--acc-line', '#CDF24A') }
}

export function createSprinter(canvas, { onFrame } = {}) {
  const renderer = new WebGLRenderer({ canvas, antialias: true, alpha: false, powerPreference: 'high-performance' })
  const scene = new Scene()
  const camera = new PerspectiveCamera(27, 1, 0.1, 120)
  let col = tokens()
  scene.fog = new Fog(col.bg, 9, 30)
  renderer.setClearColor(col.bg, 1)

  /* what the page drives: the camera's place, how much of the scene has arrived, and the
     stride time. `yaw` 0 is the flat side-on view a drill video gives; turning it brings
     the depth out. */
  const view = { yaw: 0, pitch: 0.1, dist: 5.9, shift: 0, reveal: 0, lookX: 0, lookY: 0, rate: 1, scrub: 0 }

  // ------------------------------------------------------------------ the floor
  const ground = new Mesh(
    new PlaneGeometry(90, 44, 1, 1).rotateX(-Math.PI / 2),
    new ShaderMaterial({
      vertexShader: GROUND_VERT, fragmentShader: GROUND_FRAG, transparent: true, depthWrite: false,
      uniforms: {
        uOff: { value: 0 }, uReveal: { value: 0 }, uInk: { value: col.ink }, uAcc: { value: col.acc },
        uStrike: { value: new Float32Array(16) },      // four strikes, flat: x, z, age (s), strength
      },
    }),
  )
  ground.position.x = -8
  ground.renderOrder = 0
  scene.add(ground)

  // ------------------------------------------------------------------ the lines
  const lines = []
  const segments = (count, width, opacity, colour = 'ink') => {
    const geo = new LineSegmentsGeometry()
    geo.setPositions(new Float32Array(count * 6))
    const mat = new LineMaterial({ color: col[colour], linewidth: width, transparent: true, opacity, depthWrite: false, fog: true })
    const obj = new LineSegments2(geo, mat)
    obj.frustumCulled = false
    obj.userData = { base: opacity, colour, buf: geo.attributes.instanceStart.data }
    scene.add(obj)
    lines.push(obj)
    return obj
  }
  const write = (obj, joints, bones, dx = 0) => {
    const a = obj.userData.buf.array
    bones.forEach(([p, q], i) => {
      a[i * 6] = joints[p * 3] + dx; a[i * 6 + 1] = joints[p * 3 + 1]; a[i * 6 + 2] = joints[p * 3 + 2]
      a[i * 6 + 3] = joints[q * 3] + dx; a[i * 6 + 4] = joints[q * 3 + 1]; a[i * 6 + 5] = joints[q * 3 + 2]
    })
    obj.userData.buf.needsUpdate = true
  }

  const ALL = [...BONES.far, ...BONES.core, ...BONES.near]
  const ghosts = Array.from({ length: GHOSTS }, () => segments(ALL.length + HEAD_SEG + 1, 1.25, 0.2))
  const far = segments(BONES.far.length, 2.1, 0.36)
  const core = segments(BONES.core.length + HEAD_SEG + 1, 2.1, 0.72)
  const near = segments(BONES.near.length, 2.6, 1)

  const polyline = (count, width, colour) => {
    const geo = new LineGeometry()
    geo.setPositions(new Float32Array(count * 3))
    geo.setColors(new Float32Array(count * 3))
    const mat = new LineMaterial({ linewidth: width, vertexColors: true, transparent: true, opacity: 1, depthWrite: false })
    const obj = new Line2(geo, mat)
    obj.frustumCulled = false
    obj.userData = { base: 1, colour, buf: geo.attributes.instanceStart.data, cbuf: geo.attributes.instanceColorStart.data }
    scene.add(obj)
    lines.push(obj)
    return obj
  }
  const trail = polyline(TRAIL, 1.6, 'acc')
  const arc = segments(20, 2.2, 1, 'acc')

  // ------------------------------------------------------------------ the joints
  const dotCount = NEAR_DOTS.length + FAR_DOTS.length + 1
  const dotGeo = new BufferGeometry()
  const dotPos = new Float32Array(dotCount * 3)
  dotGeo.setAttribute('position', new BufferAttribute(dotPos, 3))
  dotGeo.setAttribute('aSize', new BufferAttribute(new Float32Array([
    ...NEAR_DOTS.map(() => 9), ...FAR_DOTS.map(() => 7), 11]), 1))
  dotGeo.setAttribute('aKind', new BufferAttribute(new Float32Array([
    ...NEAR_DOTS.map(() => 0), ...FAR_DOTS.map(() => 1), 2]), 1))
  const dots = new Points(dotGeo, new ShaderMaterial({
    vertexShader: DOT_VERT, fragmentShader: DOT_FRAG, transparent: true, depthTest: false, depthWrite: false,
    uniforms: { uDpr: { value: 1 }, uReveal: { value: 0 }, uInk: { value: col.ink }, uAcc: { value: col.acc }, uBg: { value: col.bg } },
  }))
  dots.frustumCulled = false
  dots.renderOrder = 5
  scene.add(dots)

  // ------------------------------------------------------------------ drawing a frame
  const cur = new Float32Array(JOINTS.length * 3)
  const tmp = new Float32Array(JOINTS.length * 3)
  const right = new Vector3(), up = new Vector3(), v = new Vector3()
  let W = 1, H = 1, dpr = 1, clock = 0.3 * T

  // the head, a ring facing the camera, and the neck up to it
  const head = (obj, joints, from, dx = 0) => {
    const a = obj.userData.buf.array
    const hx = joints[J.head * 3] + dx, hy = joints[J.head * 3 + 1], hz = joints[J.head * 3 + 2]
    for (let i = 0; i < HEAD_SEG; i++) {
      for (let e = 0; e < 2; e++) {
        const ang = ((i + e) / HEAD_SEG) * Math.PI * 2, c = Math.cos(ang) * HEAD_R, s = Math.sin(ang) * HEAD_R
        const o = (from + i) * 6 + e * 3
        a[o] = hx + right.x * c + up.x * s; a[o + 1] = hy + right.y * c + up.y * s; a[o + 2] = hz + right.z * c + up.z * s
      }
    }
    const nx = joints[J.neck * 3] + dx, ny = joints[J.neck * 3 + 1], nz = joints[J.neck * 3 + 2]
    const len = Math.hypot(hx - nx, hy - ny, hz - nz) || 1, k = (len - HEAD_R) / len
    const o = (from + HEAD_SEG) * 6
    a[o] = nx; a[o + 1] = ny; a[o + 2] = nz
    a[o + 3] = nx + (hx - nx) * k; a[o + 4] = ny + (hy - ny) * k; a[o + 5] = nz + (hz - nz) * k
    obj.userData.buf.needsUpdate = true
  }

  function draw() {
    const tau = clock / T                       // strides run so far
    const reveal = view.reveal

    // the camera: on the near side, turned towards the front of the runner
    const yaw = view.yaw + view.lookX * 0.1, pitch = view.pitch + view.lookY * 0.04
    const tx = -0.3, ty = 0.94
    camera.position.set(tx + Math.sin(yaw) * Math.cos(pitch) * view.dist, ty + Math.sin(pitch) * view.dist,
      -Math.cos(yaw) * Math.cos(pitch) * view.dist)
    camera.lookAt(tx, ty, 0)
    camera.setViewOffset(W, H, -view.shift * W, 0, W, H)
    camera.updateMatrixWorld()
    right.setFromMatrixColumn(camera.matrixWorld, 0)
    up.setFromMatrixColumn(camera.matrixWorld, 1)

    // the floor passes under the planted foot
    const gu = ground.material.uniforms
    gu.uOff.value = tau * STRIDE_M
    gu.uReveal.value = reveal
    strikes(tau).forEach((s, i) => {
      const u = gu.uStrike.value
      u[i * 4] = s.x; u[i * 4 + 1] = s.z; u[i * 4 + 2] = s.age * T; u[i * 4 + 3] = reveal
    })

    const now = pose(tau, cur)
    write(far, cur, BONES.far)
    write(core, cur, BONES.core)
    head(core, cur, BONES.core.length)
    write(near, cur, BONES.near)

    // earlier poses, left where they happened: stamped at fixed moments, so they stand
    // still on the track while the runner moves on
    const last = Math.floor(tau / GHOST_EVERY) * GHOST_EVERY
    ghosts.forEach((g, i) => {
      const at = last - i * GHOST_EVERY, age = tau - at
      pose(at, tmp)
      write(g, tmp, ALL, -age * STRIDE_M)
      head(g, tmp, ALL.length, -age * STRIDE_M)
      // the newest one appears as the runner pulls away from it; the oldest fades out
      const born = Math.min(1, age / GHOST_EVERY), old = 1 - (age - GHOST_EVERY) / (GHOSTS * GHOST_EVERY)
      g.userData.base = 0.3 * born * Math.max(0, old) ** 1.4
    })

    // the hip's path over the last stride and a half: the bounce of the run
    const tb = trail.userData.buf.array, tc = trail.userData.cbuf.array
    for (let i = 0; i < TRAIL; i++) {
      const back = (i / (TRAIL - 1)) * 1.5, x = -back * STRIDE_M
      // eased across each change between ground and flight, so the path reads as one curve
      const y = (hipHeight(tau - back - 0.014) + 2 * hipHeight(tau - back) + hipHeight(tau - back + 0.014)) / 4
      const k = (1 - i / (TRAIL - 1)) ** 1.6
      // LineGeometry keeps each segment as start + end: point i ends segment i-1 and starts segment i
      if (i < TRAIL - 1) { tb[i * 6] = x; tb[i * 6 + 1] = y; tb[i * 6 + 2] = 0; tc[i * 6] = col.acc.r * k + col.bg.r * (1 - k); tc[i * 6 + 1] = col.acc.g * k + col.bg.g * (1 - k); tc[i * 6 + 2] = col.acc.b * k + col.bg.b * (1 - k) }
      if (i > 0) { const o = (i - 1) * 6 + 3; tb[o] = x; tb[o + 1] = y; tb[o + 2] = 0; tc[o] = col.acc.r * k + col.bg.r * (1 - k); tc[o + 1] = col.acc.g * k + col.bg.g * (1 - k); tc[o + 2] = col.acc.b * k + col.bg.b * (1 - k) }
    }
    trail.userData.buf.needsUpdate = true
    trail.userData.cbuf.needsUpdate = true

    // the angle being measured, drawn at the near knee between thigh and shin
    const K = J.knN * 3, Hh = J.hipN * 3, A = J.anN * 3
    const ux = cur[Hh] - cur[K], uy = cur[Hh + 1] - cur[K + 1], uz = cur[Hh + 2] - cur[K + 2]
    const wx = cur[A] - cur[K], wy = cur[A + 1] - cur[K + 1], wz = cur[A + 2] - cur[K + 2]
    const ul = Math.hypot(ux, uy, uz), wl = Math.hypot(wx, wy, wz)
    const cosA = (ux * wx + uy * wy + uz * wz) / (ul * wl), ang = Math.acos(Math.max(-1, Math.min(1, cosA)))
    // a unit vector in the leg's plane, square to the thigh, on the shin's side
    let px = wx / wl - cosA * ux / ul, py = wy / wl - cosA * uy / ul, pz = wz / wl - cosA * uz / ul
    const pl = Math.hypot(px, py, pz) || 1
    px /= pl; py /= pl; pz /= pl
    const ab = arc.userData.buf.array, rad = 0.15
    for (let i = 0; i < 20; i++) {
      for (let e = 0; e < 2; e++) {
        const t = ((i + e) / 20) * ang, c = Math.cos(t) * rad, s = Math.sin(t) * rad, o = i * 6 + e * 3
        ab[o] = cur[K] + (ux / ul) * c + px * s; ab[o + 1] = cur[K + 1] + (uy / ul) * c + py * s; ab[o + 2] = cur[K + 2] + (uz / ul) * c + pz * s
      }
    }
    arc.userData.buf.needsUpdate = true

    const put = (name, i) => { dotPos[i * 3] = cur[J[name] * 3]; dotPos[i * 3 + 1] = cur[J[name] * 3 + 1]; dotPos[i * 3 + 2] = cur[J[name] * 3 + 2] }
    NEAR_DOTS.forEach((n, i) => put(n, i))
    FAR_DOTS.forEach((n, i) => put(n, NEAR_DOTS.length + i))
    put('knN', dotCount - 1)
    dotGeo.attributes.position.needsUpdate = true
    dots.material.uniforms.uReveal.value = reveal

    lines.forEach(l => { l.material.opacity = l.userData.base * reveal })
    renderer.render(scene, camera)

    if (onFrame) {
      v.set(cur[K], cur[K + 1], cur[K + 2]).project(camera)
      onFrame({
        knee: now.knee, lean: now.lean, grounded: now.grounded, frame: Math.floor(clock * 60),
        kneeX: (v.x * 0.5 + 0.5) * W, kneeY: (-v.y * 0.5 + 0.5) * H, reveal,
      })
    }
  }

  // ------------------------------------------------------------------ running it
  function fit() {
    const w = Math.max(1, canvas.clientWidth), h = Math.max(1, canvas.clientHeight)
    const d = Math.min(w < 700 ? 1.75 : 2, window.devicePixelRatio || 1)
    if (w === W && h === H && d === dpr) return
    W = w; H = h; dpr = d
    renderer.setPixelRatio(dpr)
    renderer.setSize(W, H, false)
    camera.aspect = W / H
    // a tall phone screen needs a wider view to keep the whole runner and the trail in
    camera.fov = W / H < 0.9 ? 34 : 27
    camera.updateProjectionMatrix()
    dots.material.uniforms.uDpr.value = dpr
    lines.forEach(l => l.material.resolution.set(W, H))
    draw()
  }

  function recolour() {
    col = tokens()
    scene.fog.color.copy(col.bg)
    renderer.setClearColor(col.bg, 1)
    ground.material.uniforms.uInk.value = col.ink
    ground.material.uniforms.uAcc.value = col.acc
    Object.assign(dots.material.uniforms, { uInk: { value: col.ink }, uAcc: { value: col.acc }, uBg: { value: col.bg } })
    lines.forEach(l => { if (!l.material.vertexColors) l.material.color.copy(col[l.userData.colour]) })
    draw()
  }

  const still = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
  let raf = 0, last = 0, visible = true, dead = false, scrubbed = 0
  const frame = now => {
    if (dead) return
    raf = requestAnimationFrame(frame)
    if (!visible || document.hidden) { last = now; return }
    const dt = last ? Math.min(0.05, (now - last) / 1000) : 0
    last = now
    // scrolling the page winds the clip on (or back); left alone it plays at its own pace
    clock += dt * view.rate + (view.scrub - scrubbed)
    scrubbed = view.scrub
    draw()
  }

  const ro = new ResizeObserver(fit)
  ro.observe(canvas)
  const io = new IntersectionObserver(es => { visible = es[0].isIntersecting })
  io.observe(canvas)
  const mo = new MutationObserver(recolour)
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme', 'data-accent'] })
  fit()
  if (still) { view.reveal = 1; view.yaw = 0.62; draw() } else raf = requestAnimationFrame(frame)

  return {
    view,
    still,
    draw,
    dispose() {
      dead = true
      cancelAnimationFrame(raf)
      ro.disconnect(); io.disconnect(); mo.disconnect()
      scene.traverse(o => { o.geometry?.dispose(); o.material?.dispose() })
      renderer.dispose()
    },
  }
}
