import { Fragment, useEffect, useMemo, useRef, useState } from 'react'
import Icon from '../Icon'
import Logo from '../Logo'
import { LookPicker } from '../Theme'
import Court from './Court'
import { SPORTKIT } from './sportkit'
import { BONES, JOINTS, pose } from './stride'
import { COMPACT, DESKTOP, MOTION, SCRAMBLE, ScrollTrigger, SplitText, calm, gsap, useGSAP } from './motion'

const SPORTS = Object.keys(SPORTKIT)

/* The public home page. Every figure on it is a labelled sample; the targets are the real
   men's football targets from backend/levels.json. */
export default function Home({ onSignIn, look, onLook }) {
  const root = useRef(null)
  // runs after every section has set up its own motion, so the pinned scenes above are
  // already in the page's height when these are measured
  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add(MOTION, () => {
      gsap.utils.toArray('.rise').forEach(el => {
        gsap.from(el, { opacity: 0, y: 28, duration: 0.85, scrollTrigger: { trigger: el, start: 'top 86%', once: true } })
      })
      ScrollTrigger.batch('.cell, .panel, .brow', {
        start: 'top 88%', once: true,
        onEnter: els => gsap.from(els, { opacity: 0, y: 30, duration: 0.8, stagger: 0.08, overwrite: true }),
      })
    })
    document.fonts?.ready.then(() => ScrollTrigger.refresh())
  }, { scope: root })

  return (
    <div className="site" ref={root}>
      <SiteNav onSignIn={onSignIn} look={look} onLook={onLook} />
      <main className="site-main">
        <Hero onSignIn={onSignIn} />
        <Marquee />
        <Sources />
        <Levels />
        <Coaches />
        <Athletes onSignIn={onSignIn} />
        <Basis />
        <Close onSignIn={onSignIn} />
      </main>
      <footer className="foot">
        <div className="wrap foot-in">
          <Logo size={26} />
          <nav aria-label="Legal">
            <a href="/privacy.html">Privacy policy</a>
            <a href="/terms.html">Terms of use</a>
          </nav>
          <small>© {new Date().getFullYear()} Stridian</small>
        </div>
      </footer>
    </div>
  )
}

/* A sign-in door: plain ink on the page; on hover the fill sweeps in and the colours swap. */
function Sign({ who, onSignIn, small, label }) {
  return (
    <button type="button" className={`sign${small ? ' sign-sm' : ''}`} onClick={() => onSignIn(who)}>
      {label ?? (who === 'coach' ? 'Coach sign in' : 'Athlete sign in')}
      {!small && <Icon name="next" size={20} />}
    </button>
  )
}

function SiteNav({ onSignIn, look, onLook }) {
  const bar = useRef(null)
  // the hairline under the bar fills as the page is read
  useGSAP(() => {
    gsap.to('.nav-prog', { scaleX: 1, ease: 'none', scrollTrigger: { start: 0, end: 'max', scrub: 0.3 } })
  }, { scope: bar })
  const go = (e, id) => {
    e.preventDefault()
    document.getElementById(id)?.scrollIntoView({ behavior: calm() ? 'auto' : 'smooth', block: 'start' })
  }
  return (
    <header className="nav" ref={bar}>
      <div className="wrap navin">
        <Logo onClick={() => window.scrollTo({ top: 0, behavior: calm() ? 'auto' : 'smooth' })} />
        <nav className="navlinks" aria-label="Sections">
          {[['how', 'How it works'], ['levels', 'Levels'], ['coaches', 'For coaches'], ['athletes', 'For athletes']].map(([id, text]) => (
            <a key={id} href={`#${id}`} onClick={e => go(e, id)}><span>{text}</span></a>
          ))}
        </nav>
        <div className="navcta">
          <LookPicker look={look} onLook={onLook} />
          <span className="hide-phone"><Sign who="athlete" onSignIn={onSignIn} small /></span>
          <span className="hide-phone"><Sign who="coach" onSignIn={onSignIn} small /></span>
          <span className="only-phone"><Sign who="athlete" onSignIn={onSignIn} small label="Sign in" /></span>
        </div>
      </div>
      <i className="nav-prog" aria-hidden="true" />
    </header>
  )
}

/* ------------------------------------------------------------------ hero */

// the same pose drawn flat, for a browser without WebGL: the scene is never an empty box
function PoseStill() {
  const lines = useMemo(() => {
    const j = pose(0.3).joints
    const at = i => [j[i * 3] - j[i * 3 + 2] * 0.35, 1.9 - j[i * 3 + 1]]
    const seg = (list, cls) => list.map(([a, b], i) => {
      const [x1, y1] = at(a), [x2, y2] = at(b)
      return <line key={cls + i} className={cls} x1={-x1} y1={y1} x2={-x2} y2={y2} />
    })
    const [hx, hy] = at(JOINTS.indexOf('head'))
    return [...seg(BONES.far, 'far'), ...seg(BONES.core, 'core'), ...seg(BONES.near, 'near'),
      <circle key="head" className="core" cx={-hx} cy={hy} r="0.09" />]
  }, [])
  return <svg className="pose-still" viewBox="-1.2 0 2.4 2" aria-hidden="true">{lines}<line className="floor" x1="-1.2" y1="1.9" x2="1.2" y2="1.9" /></svg>
}

function Hero({ onSignIn }) {
  const box = useRef(null)
  const canvas = useRef(null)
  const scene = useRef(null)
  const [flat, setFlat] = useState(false)       // no WebGL: the still pose stands in
  const [live, setLive] = useState(false)

  useEffect(() => {
    let dead = false
    const el = box.current
    const q = s => el.querySelector(s)
    const out = { knee: q('[data-ro="knee"]'), lean: q('[data-ro="lean"]'), foot: q('[data-ro="foot"]'), frame: q('[data-ro="frame"]'), tag: q('.knee-tag') }
    let shown = {}
    const say = (key, text) => { if (shown[key] !== text) { shown[key] = text; out[key].textContent = text } }
    const onFrame = d => {
      say('knee', `${Math.round(d.knee)}°`)
      say('lean', `${Math.round(d.lean)}°`)
      say('foot', d.grounded ? 'Ground' : 'Flight')
      say('frame', String(d.frame % 10000).padStart(4, '0'))
      say('tag', `${Math.round(d.knee)}°`)
      out.tag.style.transform = `translate3d(${Math.round(d.kneeX)}px, ${Math.round(d.kneeY)}px, 0)`
      out.tag.style.opacity = d.reveal
    }
    import('./Sprinter.js').then(({ createSprinter }) => {
      if (dead) return
      try { scene.current = createSprinter(canvas.current, { onFrame }) } catch { setFlat(true); return }
      setLive(true)
    }).catch(() => !dead && setFlat(true))
    return () => { dead = true; scene.current?.dispose(); scene.current = null }
  }, [])

  // the words arrive once, on load
  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add(MOTION, () => {
      const split = SplitText.create('.h1 .ln', { type: 'words', wordsClass: 'w' })
      gsap.timeline({ defaults: { ease: 'out' } })
        .from(split.words, { yPercent: 112, duration: 1.05, stagger: 0.085 }, 0.1)
        .from('.sitehero .eyebrow', { opacity: 0, x: -14, duration: 0.7 }, 0.15)
        .from('.hero-sub > *', { opacity: 0, y: 22, duration: 0.8, stagger: 0.09 }, 0.5)
        .from('.hud-edge', { scaleX: 0, duration: 1.1, ease: 'io' }, 0.5)
        .from('.hud .k, .hud .ro-v, .hud-tag', { opacity: 0, duration: 0.6, stagger: 0.05 }, 0.9)
      return () => split.revert()
    })
  }, { scope: box })

  // the scene arrives: flat and side-on like the video, then the camera turns and the depth opens
  useGSAP(() => {
    const s = scene.current
    if (!live || !s) return undefined
    const v = s.view
    if (s.still) {
      // for anyone who asked for less motion: one frame, already turned to show its depth
      const wide = window.matchMedia('(min-width: 1081px)').matches
      Object.assign(v, { shift: wide ? 0.17 : 0, dist: wide ? 5.9 : 6.6, aim: wide ? 0.8 : 0.94, yaw: wide ? 0.66 : 0.5, pitch: 0.11, reveal: 1 })
      s.draw()
      return undefined
    }
    const mm = gsap.matchMedia()
    mm.add({ wide: '(min-width: 1081px)', narrow: '(max-width: 1080px)' }, ctx => {
      const wide = ctx.conditions.wide
      gsap.set(v, { shift: wide ? 0.17 : 0, dist: wide ? 5.9 : 6.6, aim: wide ? 0.8 : 0.94 })
      gsap.timeline()
        .to(v, { reveal: 1, duration: 1.4, ease: 'power2.out' }, 0.25)
        .fromTo(v, { yaw: 0.04, pitch: 0.03 }, { yaw: wide ? 0.66 : 0.5, pitch: 0.11, duration: 2.8, ease: 'io' }, 0.55)
      // scrolling winds the clip on, and the camera climbs as the hero leaves
      gsap.timeline({ scrollTrigger: { trigger: box.current, start: 'top top', end: 'bottom top', scrub: 0.5 } })
        .to(v, { scrub: 2.6, ease: 'none' }, 0)
        .to(v, { dist: wide ? 7.2 : 7.6, ease: 'none' }, 0)
      if (wide) {
        const lx = gsap.quickTo(v, 'lookX', { duration: 1.1, ease: 'power3.out' })
        const ly = gsap.quickTo(v, 'lookY', { duration: 1.1, ease: 'power3.out' })
        const move = e => { lx((e.clientX / innerWidth - 0.5) * 2); ly((0.5 - e.clientY / innerHeight) * 2) }
        window.addEventListener('pointermove', move, { passive: true })
        return () => window.removeEventListener('pointermove', move)
      }
      return undefined
    })
  }, { scope: box, dependencies: [live] })

  return (
    <section className="sitehero" id="top" ref={box}>
      <figure className="stage">
        {flat ? <PoseStill /> : (
          <canvas ref={canvas} role="img"
                  aria-label="A sprinter's pose in three dimensions, joint by joint, with the near knee angle measured on every frame" />
        )}
        <div className="hud" aria-hidden="true">
          <i className="hud-edge" />
          <span className="k hud-l">Drill video · pose model</span>
          <span className="k hud-r">0.45x playback, frame <b data-ro="frame">0000</b></span>
          <span className="knee-tag mono" />
        </div>
      </figure>

      <div className="wrap hero-in">
        <div className="hero-copy">
          <p className="eyebrow">Sports talent intelligence</p>
          <h1 className="d h1">
            <span className="ln">Right role.</span>
            <span className="ln acc">Next level.</span>
          </h1>
          <div className="hero-sub">
            <p className="lede">Stridian scores every student athlete against every position in their sport, then shows the level each result reaches.</p>
            <div className="signs">
              <Sign who="athlete" onSignIn={onSignIn} />
              <Sign who="coach" onSignIn={onSignIn} />
            </div>
          </div>
        </div>

        <div className="readouts hud">
          <div><span className="k">Near knee</span><b className="d ro-v" data-ro="knee">156°</b></div>
          <div><span className="k">Trunk lean</span><b className="d ro-v" data-ro="lean">9°</b></div>
          <div><span className="k">Foot</span><b className="d ro-v" data-ro="foot">Flight</b></div>
          <span className="hud-tag mono">Sample clip</span>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ sports band */

function Marquee() {
  const band = useRef(null)
  // it drifts on its own, and leans into the scroll: faster and tilted while the page moves
  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add(MOTION, () => {
      const track = band.current.querySelector('.marq-track')
      const drift = gsap.to(track, { xPercent: -50, duration: 46, ease: 'none', repeat: -1 })
      const skew = gsap.quickTo(track, 'skewX', { duration: 0.5, ease: 'power3.out' })
      const st = ScrollTrigger.create({
        trigger: band.current, start: 'top bottom', end: 'bottom top',
        onUpdate: self => {
          const vel = gsap.utils.clamp(-3000, 3000, self.getVelocity())
          gsap.to(drift, { timeScale: 1 + Math.abs(vel) / 260, duration: 0.25, overwrite: true })
          gsap.to(drift, { timeScale: 1, duration: 1.2, delay: 0.25 })
          skew(vel / -260)
          gsap.delayedCall(0.3, () => skew(0))
        },
      })
      return () => { st.kill(); drift.kill() }
    })
  }, { scope: band })
  const set = hidden => (
    <div className="marq-set" aria-hidden={hidden || undefined}>
      {SPORTS.map((s, i) => (
        <span key={s} className="marq-item">
          <span className={`d mq${i % 2 ? ' o' : ''}`}>{s}</span><i className="sep" />
        </span>
      ))}
    </div>
  )
  return (
    <section className="marq" aria-label="Sports covered" ref={band}>
      <div className="marq-track">{set(false)}{set(true)}</div>
    </section>
  )
}

/* ------------------------------------------------------------------ three sources */

const SOURCES = [
  { icon: 'clipboard', title: 'Test battery', text: 'Sprint, jump, agility and endurance, entered by the coach.', k: '30 m sprint', v: '4.38 s' },
  { icon: 'film', title: 'Match footage', text: 'Every player tracked through a match clip.', k: 'Top speed', v: '28.9 km/h' },
  { icon: 'card', title: 'Match cards', text: 'The paper match sheet, photographed and read.', k: 'Passes completed', v: '78%' },
]
const WIRES = ['M0 66 C 80 66 80 214 160 214', 'M0 214 L 160 214', 'M0 362 C 80 362 80 214 160 214']

function Sources() {
  const sec = useRef(null)
  useGSAP(() => {
    const mm = gsap.matchMedia()
    // on a desk the section holds still while the three sources report in, one scroll at a time
    mm.add(`${MOTION} and ${DESKTOP}`, () => {
      const srcs = gsap.utils.toArray('.src'), lit = gsap.utils.toArray('.wires .lit'), pulses = gsap.utils.toArray('.pulse')
      const tl = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: { trigger: sec.current, start: 'top top+=68', end: '+=170%', pin: true, scrub: 0.5, anticipatePin: 1 },
      })
      tl.from('.how-head > *', { opacity: 0.25, duration: 0.3 }, 0)
      srcs.forEach((el, i) => {
        const at = 0.25 + i * 1
        tl.fromTo(el, { '--on': 0 }, { '--on': 1, duration: 0.5 }, at)
          .from(el.querySelector('.src-v'), { scrambleText: { text: '0.00', chars: SCRAMBLE, speed: 0.6 }, duration: 0.45 }, at)
          .fromTo(lit[i], { drawSVG: '0%' }, { drawSVG: '100%', duration: 0.55 }, at + 0.35)
          .fromTo(pulses[i], { '--d': 0, opacity: 1 }, { '--d': 1, duration: 0.55 }, at + 0.35)
          .to(pulses[i], { opacity: 0, duration: 0.05 }, at + 0.9)
      })
      tl.fromTo('.vcard', { '--on': 0 }, { '--on': 1, duration: 0.5 }, 3.2)
        .from('.v-pos', { scrambleText: { text: '······', chars: 'ABCDEFGHIKLMNOPRSTW', speed: 0.5 }, duration: 0.6 }, 3.2)
        .from('.v-fit b', { textContent: 0, snap: { textContent: 1 }, duration: 0.7 }, 3.25)
        .from('.v-agree, .v-rest li', { opacity: 0, x: -12, stagger: 0.08, duration: 0.3 }, 3.85)
        .to({}, { duration: 0.5 })
    })
    // anywhere else each part simply arrives as it is reached
    mm.add(COMPACT.split(', ').map(q => `${MOTION} and ${q}`).join(', '), () => {
      gsap.from('.src, .vcard', {
        opacity: 0, y: 26, duration: 0.7, stagger: 0.1,
        scrollTrigger: { trigger: '.how', start: 'top 82%', once: true },
      })
    })
  }, { scope: sec })

  return (
    <section className="sec how-sec" id="how" ref={sec}>
      <div className="wrap">
        <div className="how-head">
          <h2 className="d h2">Three sources. One verdict.</h2>
          <p className="lede">Tests, match footage and match cards are scored on their own, then compared. When all three agree, you can pick with confidence.</p>
        </div>
        <div className="how">
          <div className="srcs">
            {SOURCES.map(s => (
              <article className="src" key={s.title}>
                <span className="src-ico"><Icon name={s.icon} size={22} /></span>
                <div><h3>{s.title}</h3><p>{s.text}</p></div>
                <div className="src-datum"><span className="k">{s.k}</span><b className="d src-v">{s.v}</b></div>
              </article>
            ))}
          </div>

          <div className="wires" aria-hidden="true">
            <svg viewBox="0 0 160 428">
              {WIRES.map(d => <path key={d} d={d} />)}
              {WIRES.map(d => <path key={`l${d}`} className="lit" d={d} />)}
            </svg>
            {WIRES.map(d => <i key={`p${d}`} className="pulse" style={{ offsetPath: `path('${d}')` }} />)}
          </div>

          <div className="vcard">
            <div className="v-head"><span className="k">Sample player</span><span className="k">Football, men&apos;s</span></div>
            <p className="v-name">Karthik Selvaraj</p>
            <div className="v-main">
              <div><span className="k">Best-fit position</span><b className="d v-pos">Winger</b></div>
              <div className="v-fit"><span className="k">Fit out of 100</span><b className="d acc">81</b></div>
            </div>
            <p className="v-agree"><Icon name="check" size={22} />All three sources agree.</p>
            <ol className="v-rest">
              <li>Full-back<b className="mono">74</b></li>
              <li>Striker<b className="mono">70</b></li>
              <li>Central Midfielder<b className="mono">61</b></li>
            </ol>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ five levels */

const LEVELS = ['University', 'Zonal', 'State', 'National', 'International']
// men's football targets from backend/levels.json; the results are a sample player's
const MEASURES = {
  sprint: { label: '30 m sprint', name: '30 m sprint', unit: 's', better: -1, poor: 4.8, elite: 4.0, t: [4.55, 4.44, 4.33, 4.22, 4.1], v: 4.38, dp: 2, basis: 'a published norm' },
  cmj: { label: 'CMJ', name: 'Countermovement jump', unit: 'cm', better: 1, poor: 30, elite: 44, t: [33, 35, 37, 39, 41], v: 38, dp: 0, basis: 'a published norm' },
  yoyo: { label: 'Yo-Yo IR1', name: 'Yo-Yo IR1', unit: 'level', better: 1, poor: 16.6, elite: 20, t: [17.2, 17.6, 18.2, 18.8, 19.5], v: 17.4, dp: 1, basis: 'a published norm' },
  ttest: { label: 'T-test', name: 'Agility T-test', unit: 's', better: -1, poor: 10.9, elite: 9.4, t: [10.5, 10.25, 10.0, 9.8, 9.6], v: 10.12, dp: 2, basis: 'an estimate' },
}
const KEYS = Object.keys(MEASURES)

function Levels() {
  const sec = useRef(null)
  const [key, setKey] = useState('sprint')
  const [swap, setSwap] = useState(false)     // a tab was picked: the lanes ease to the new measure
  const m = MEASURES[key]
  const x = v => Math.max(0, Math.min(100, 4 + 92 * (v - m.poor) / (m.elite - m.poor)))
  const fmt = v => (m.unit === 'level' ? `Level ${v.toFixed(1)}` : `${v.toFixed(m.dp)} ${m.unit}`)
  const ax = x(m.v)
  let best = -1
  const lanes = m.t.map((t, i) => {
    const ok = (m.v - t) * m.better >= -1e-9
    if (ok) best = i
    const tx = x(t)
    return {
      // the target's label sits left of its line, unless that would land on the result's dot
      name: LEVELS[i], ok, tx, target: fmt(t), lo: tx < 34 || (tx > ax && tx - ax < 14),
      gap: ok ? 'Reached' : m.unit === 'level' ? 'Not yet' : `${Math.abs(t - m.v).toFixed(m.dp)} ${m.unit} to go`,
    }
  })

  const pick = k => { setSwap(true); setKey(k) }
  const onKey = (e, i) => {
    const step = { ArrowRight: 1, ArrowLeft: -1, Home: -i, End: KEYS.length - 1 - i }[e.key]
    if (step === undefined) return
    e.preventDefault()
    const j = (i + step + KEYS.length) % KEYS.length
    pick(KEYS[j])
    e.currentTarget.parentNode.querySelectorAll('[role="tab"]')[j]?.focus()
  }

  useGSAP(() => {
    const mm = gsap.matchMedia()
    // the board holds still and the result runs each lane in turn: reached, reached, not yet
    mm.add(`${MOTION} and ${DESKTOP}`, () => {
      const rows = gsap.utils.toArray('.lane')
      const tl = gsap.timeline({
        defaults: { ease: 'none' },
        scrollTrigger: { trigger: sec.current, start: 'top top+=68', end: '+=150%', pin: true, scrub: 0.5, anticipatePin: 1 },
      })
      rows.forEach((row, i) => {
        tl.fromTo(row, { '--p': 0 }, { '--p': 1, duration: 0.8, ease: 'power1.inOut' }, 0.15 + i * 0.55)
          .fromTo(row, { '--lit': 0 }, { '--lit': 1, duration: 0.25 }, 0.75 + i * 0.55)
      })
      tl.from('.board-foot b', { opacity: 0.15, duration: 0.4, stagger: 0.15 }, 3.0)
        .to({}, { duration: 0.4 })
    })
    mm.add(COMPACT.split(', ').map(q => `${MOTION} and ${q}`).join(', '), () => {
      gsap.fromTo('.lane', { '--p': 0, '--lit': 0 }, {
        '--p': 1, '--lit': 1, duration: 1.1, stagger: 0.12, ease: 'power2.out',
        scrollTrigger: { trigger: '.board', start: 'top 75%', once: true },
      })
    })
  }, { scope: sec })

  return (
    <section className="sec levels-sec" id="levels" ref={sec}>
      <div className="wrap">
        <h2 className="d h2">Five levels. Every&nbsp;result placed.</h2>
        <p className="lede">Each test is checked against what players post at University, Zonal, State, National and International level, with separate targets for men&apos;s and women&apos;s teams.</p>

        <div className={`board${swap ? ' swap' : ''}`}>
          <div className="board-top">
            <div className="tabs" role="tablist" aria-label="Measure">
              <i className="tab-ind" style={{ transform: `translateX(${KEYS.indexOf(key) * 100}%)` }} />
              {KEYS.map((k, i) => (
                <button key={k} type="button" role="tab" id={`m-${k}`} className={`tab${k === key ? ' on' : ''}`}
                        aria-selected={k === key} aria-controls="levels-panel" tabIndex={k === key ? 0 : -1}
                        onClick={() => pick(k)} onKeyDown={e => onKey(e, i)}>{MEASURES[k].label}</button>
              ))}
            </div>
            <p className="board-who mono">Karthik Selvaraj, sample results</p>
          </div>
          <div role="tabpanel" id="levels-panel" aria-labelledby={`m-${key}`}>
            <div className="lanes">
              {lanes.map((lane, i) => (
                <div key={lane.name} className={`lane${lane.ok ? ' ok' : ''}`} style={{ '--ax': ax.toFixed(2), '--tx': lane.tx.toFixed(2) }}>
                  <span className="d lane-n">{i + 1}</span>
                  <span className="lane-name">{lane.name}</span>
                  <span className="lane-track">
                    <i className="lane-gap" />
                    <i className="lane-run" />
                    <i className={`lane-fin${lane.lo ? ' lo' : ''}`}><b className="mono">{lane.target}</b></i>
                    <i className="lane-dot" />
                  </span>
                  <span className="mono lane-gaptext">{lane.gap}</span>
                </div>
              ))}
            </div>
            <div className="board-foot">
              <div><span className="k">{m.name}</span><b className="d">{fmt(m.v)}</b></div>
              <div><span className="k">Level reached</span><b className="d acc">{best < 0 ? 'Below University' : LEVELS[best]}</b></div>
              <p>Targets shown are for men&apos;s football and are {m.basis}. Stridian marks every number as an official standard, a published norm or an estimate.</p>
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ for coaches */

// a light that follows the pointer across a cell
const spot = e => {
  const r = e.currentTarget.getBoundingClientRect()
  e.currentTarget.style.setProperty('--mx', `${e.clientX - r.left}px`)
  e.currentTarget.style.setProperty('--my', `${e.clientY - r.top}px`)
}

const BRIEF = [
  { icon: 'target', title: 'Close to a level-up', text: 'A focused block could tip these over.', people: [['Karthik Selvaraj', '0.05 s off State in 30 m sprint'], ['Nivetha Raman', '1 cm off National in CMJ']] },
  { icon: 'trend', title: 'Improving', text: 'Worth a word of praise.', people: [['Arjun Prakash', 'CMJ up 3 cm since 12 Aug']] },
  { icon: 'flame', title: 'On a roll', text: 'Doing their weekly focus week after week.', people: [['Harini Subramanian', '6-week streak'], ['Rohit Balaji', '4-week streak']] },
]
const WEIGHTS = [['30 m sprint', 40, 1], ['Agility', 30, 0.78], ['Yo-Yo', 15, 0.5], ['CMJ', 10, 0.3], ['Height', 5, 0.16]]

function Coaches() {
  const sec = useRef(null)
  const [sport, setSport] = useState('Football')
  const kit = SPORTKIT[sport]
  const positions = [...new Set(kit.spots.map(s => s.pos))]

  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add(MOTION, () => {
      gsap.from('.c-code .code', {
        scrambleText: { text: '······', chars: 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789', speed: 0.5 }, duration: 1.1,
        scrollTrigger: { trigger: '.c-code', start: 'top 80%', once: true },
      })
      gsap.from('.wbar i', {
        scaleX: 0, transformOrigin: 'left center', duration: 0.9, stagger: 0.08, ease: 'io',
        scrollTrigger: { trigger: '.c-weights', start: 'top 80%', once: true },
      })
    })
  }, { scope: sec })

  return (
    <section className="sec" id="coaches" ref={sec}>
      <div className="wrap">
        <h2 className="d h2 rise">Your squad, read for you.</h2>
        <p className="lede rise">What needs you today, who is close to a level-up and who has gone quiet, worked out from your squad&apos;s own numbers.</p>

        <div className="bento">
          <article className="cell c-brief" onMouseMove={spot}>
            <div className="cell-head"><span className="k">Today&apos;s brief</span><span className="k">Football squad, sample</span></div>
            <ul className="brief-list">
              {BRIEF.map(b => (
                <li key={b.title}>
                  <span className="b-ico"><Icon name={b.icon} size={22} /></span>
                  <div>
                    <h3>{b.title}</h3>
                    <p>{b.text}</p>
                    <div className="people">
                      {b.people.map(([name, text]) => <span className="person" key={name}><b>{name}</b><small>{text}</small></span>)}
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </article>

          <article className="cell c-code">
            <span className="k">Football enrolment code</span>
            <b className="mono code">HV4KTX</b>
            <p>Students join your squad with their university email and this code. Make a new one whenever it travels too far.</p>
          </article>

          <article className="cell c-weights" onMouseMove={spot}>
            <span className="k">Scoring weights, Winger</span>
            <div className="wbar" aria-hidden="true">
              {WEIGHTS.map(([name, w, o], i) => <i key={name} style={{ flex: w, background: i ? 'var(--ink)' : 'var(--acc-line)', opacity: o }} />)}
            </div>
            <ul className="wlegend">
              {WEIGHTS.map(([name, w, o], i) => <li key={name}><i style={{ background: i ? 'var(--ink)' : 'var(--acc-line)', opacity: o }} />{name} {w}%</li>)}
            </ul>
            <h3>Weights you control</h3>
            <p>Every position starts from the sport&apos;s defaults. Retune them for your own squad.</p>
          </article>

          <article className="cell c-court">
            <div className="court-copy">
              <span className="k">Seven sports, one system</span>
              <h3>Every squad, on its own court.</h3>
              <p>Each sport keeps its real positions, tests and targets. Pick one to see where its positions play.</p>
              <div className="sportlist" role="group" aria-label="Sport">
                {SPORTS.map((s, i) => (
                  <button key={s} type="button" aria-pressed={s === sport} onClick={() => setSport(s)}>
                    <span className="mono">{String(i + 1).padStart(2, '0')}</span>{s}
                  </button>
                ))}
              </div>
            </div>
            <div className="court-stage">
              <Court sport={sport} spots view="full" />
              <p className="court-pos mono" key={sport}>
                {positions.length} positions: {positions.map((p, i) => <Fragment key={p}><span>{p}</span>{i < positions.length - 1 ? ', ' : ''}</Fragment>)}
              </p>
            </div>
          </article>

          <article className="cell c-cards" onMouseMove={spot}>
            <h3>Match cards, read from a photo</h3>
            <p>Photograph the paper card. Stridian reads it and works out each player&apos;s numbers.</p>
            <table className="worked">
              <thead><tr><th>Karthik, last match</th><th>Made</th><th>Rate</th></tr></thead>
              <tbody>
                <tr><td>Passes</td><td className="mono">31 of 40</td><td className="mono">78%</td></tr>
                <tr><td>Dribbles</td><td className="mono">7 of 14</td><td className="mono">50%</td></tr>
                <tr><td>Crosses</td><td className="mono">3 of 17</td><td className="mono">18%</td></tr>
              </tbody>
            </table>
          </article>

          <article className="cell c-sheets" onMouseMove={spot}>
            <span className="sheets-ico"><Icon name="download" size={24} /></span>
            <h3>Excel for coaches. Live Sheets for admins.</h3>
            <p>One click downloads your squad. Admins see every sport as a live Google Sheet.</p>
          </article>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ for athletes */

const MILES = [
  ['shield', 'Squad official', 'Your coach confirmed your position.', true],
  ['l1', 'State-ready', 'A result at State level or better.', true],
  ['bolt', 'Machine', 'Four weeks of focus in a row.', true],
  ['whistle', 'Match day', 'Played on a finished match card.', true],
  ['l2', 'National contender', 'A result at National level or better.', false],
  ['medal', 'Unstoppable', 'Eight weeks of focus in a row.', false],
]

function Athletes({ onSignIn }) {
  const sec = useRef(null)
  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add(MOTION, () => {
      gsap.fromTo('.ring .pr', { strokeDashoffset: 452.4 }, {
        strokeDashoffset: 226.2, duration: 1.6, ease: 'io',
        scrollTrigger: { trigger: '.p-level', start: 'top 78%', once: true },
      })
      gsap.from('.ladder i', {
        scaleX: 0, transformOrigin: 'left center', duration: 0.7, stagger: 0.09, ease: 'io',
        scrollTrigger: { trigger: '.p-level', start: 'top 78%', once: true },
      })
      const st = { trigger: '.p-focus', start: 'top 78%', once: true }
      gsap.from('.sessions i.on', { scale: 0.4, opacity: 0, duration: 0.45, stagger: 0.14, ease: 'back.out(2.2)', scrollTrigger: st })
      gsap.from('.streak b', { textContent: 0, snap: { textContent: 1 }, duration: 1, ease: 'power2.out', scrollTrigger: st })
    })
  }, { scope: sec })

  return (
    <section className="sec" id="athletes" ref={sec}>
      <div className="wrap ath">
        <div className="ath-copy">
          <p className="eyebrow">For athletes</p>
          <h2 className="d h2">Your second coach.</h2>
          <p className="lede">Where you stand at every level, what to work on this week, and how close the next level is.</p>
          <Sign who="athlete" onSignIn={onSignIn} />
        </div>

        <div className="ath-stack">
          <article className="panel p-level">
            <div className="ring" role="img" aria-label="Playing at Zonal level, halfway to State">
              <svg viewBox="0 0 168 168" aria-hidden="true">
                <circle className="tr" cx="84" cy="84" r="72" />
                <circle className="pr" cx="84" cy="84" r="72" />
              </svg>
              <div className="ring-in"><small>Playing at</small><b className="d">Zonal</b><small>50% to State</small></div>
            </div>
            <div>
              <h3>You meet Zonal targets in 3 of your 4 tests. Two more at State and you move up.</h3>
              <ol className="ladder" aria-label="How many of your tests reach each level">
                <li className="got"><i /><b>University</b><small>4/4</small></li>
                <li className="got here"><i /><b>Zonal</b><small>3/4</small></li>
                <li className="next"><i /><b>State</b><small>1/4</small></li>
                <li><i /><b>National</b><small>0/4</small></li>
                <li><i /><b>Intl.</b><small>0/4</small></li>
              </ol>
            </div>
          </article>

          <article className="panel p-focus">
            <div className="focus-top">
              <div>
                <span className="k">This week&apos;s focus, sample</span>
                <h3 className="d focus-h">30 m sprint</h3>
                <p className="focus-gap">0.05 s to State level</p>
                <p className="focus-tip">Acceleration work: 6 x 20 m from a three-point start, full recovery between reps.</p>
              </div>
              <div className="streak">
                <Icon name="flame" size={24} />
                <b className="d">5</b>
                <small>week streak</small>
              </div>
            </div>
            <div className="sessions">
              {[1, 2, 3].map(n => <i key={n} className="on"><Icon name="check" size={18} /></i>)}
              <i>4</i>
              <span>3 of 4 sessions, 1 more this week</span>
            </div>
          </article>

          <article className="panel">
            <div className="panel-head"><span className="k">Milestones</span><span>4 of 6 shown earned</span></div>
            <ul className="miles">
              {MILES.map(([icon, title, text, got]) => (
                <li key={title} className={got ? '' : 'off'}>
                  <span className="ms-ico"><Icon name={icon} size={18} /></span>
                  <span><b>{title}</b><small>{text}</small></span>
                </li>
              ))}
            </ul>
          </article>
        </div>
      </div>
    </section>
  )
}

/* ------------------------------------------------------------------ where numbers come from */

function Basis() {
  return (
    <section className="sec" id="data">
      <div className="wrap">
        <h2 className="d h2 rise">Every number says where it came from.</h2>
        <div className="origins">
          <div className="brow"><b className="d">Standard</b><p>An official threshold from a governing body, such as <strong>BCCI&apos;s Yo-Yo level 17.1</strong> for cricket.</p></div>
          <div className="brow"><b className="d">Published</b><p>Widely reported norms for the level, such as <strong>NBA Draft Combine</strong> lane-agility times for basketball.</p></div>
          <div className="brow"><b className="d">Estimated</b><p>A sensible starting range. The test is the real protocol, and you retune the range for your own squad.</p></div>
        </div>
      </div>
    </section>
  )
}

function Close({ onSignIn }) {
  const sec = useRef(null)
  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add(MOTION, () => {
      const split = SplitText.create('.close-h', { type: 'chars', charsClass: 'ch' })
      gsap.from(split.chars, {
        yPercent: 105, duration: 0.9, stagger: 0.028, ease: 'out',
        scrollTrigger: { trigger: sec.current, start: 'top 70%', once: true },
      })
      return () => split.revert()
    })
  }, { scope: sec })
  return (
    <section className="close" ref={sec}>
      <div className="wrap">
        <h2 className="d close-h">Bring your <span className="acc">squad.</span></h2>
        <p className="lede">Coaches sign up once and pick their sport. Students join with their university email and the squad&apos;s code.</p>
        <div className="signs">
          <Sign who="athlete" onSignIn={onSignIn} />
          <Sign who="coach" onSignIn={onSignIn} />
        </div>
      </div>
    </section>
  )
}
