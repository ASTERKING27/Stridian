import { useRef } from 'react'
import { Seg } from '../fx'
import Login from '../Login'
import Logo from '../Logo'
import StudentAuth from '../StudentAuth'
import { LookPicker } from '../Theme'
import Court from './Court'
import { MOTION, gsap, useGSAP } from './motion'

const LEVELS = ['University', 'Zonal', 'State', 'National', 'International']
const SIDE = {
  athlete: {
    eyebrow: 'Stridian for athletes', title: 'Your second coach.',
    lede: 'Where you stand at every level, what to work on this week, and how close the next level is.',
  },
  coach: {
    eyebrow: 'Stridian for coaches', title: 'Your squad, read for you.',
    lede: 'Who is close to a level-up, who needs a check-in, and what needs you today.',
  },
}

/* Sign in, for athletes and coaches: what Stridian does for you on the left, the form on
   the right. The forms themselves (StudentAuth, Login) keep every step they had. */
export default function SignIn({ role, sports, onRole, onHome, onAthlete, onCoach, look, onLook }) {
  const page = useRef(null)
  const side = SIDE[role]

  useGSAP(() => {
    const mm = gsap.matchMedia()
    mm.add(MOTION, () => {
      gsap.from('.si-copy > *', { opacity: 0, y: 24, duration: 0.8, stagger: 0.08 })
      gsap.from('.si-ladder li', { opacity: 0, x: -18, duration: 0.6, stagger: 0.07, delay: 0.25 })
      gsap.fromTo('.si-ladder .bar i', { scaleX: 0 }, { scaleX: 1, duration: 1.1, stagger: 0.16, delay: 0.5, ease: 'io' })
    })
  }, { scope: page, dependencies: [role], revertOnUpdate: true })

  return (
    <div className="site signin" ref={page}>
      <aside className="si-side">
        <div className="si-top">
          <Logo onClick={onHome} />
        </div>
        <div className="si-copy" key={role}>
          <p className="eyebrow">{side.eyebrow}</p>
          <h2 className="d si-title">{side.title}</h2>
          <p className="lede">{side.lede}</p>
        </div>
        {role === 'athlete' ? (
          <ol className="si-ladder" aria-hidden="true">
            {LEVELS.map((name, i) => (
              <li key={name} className={i < 1 ? 'full' : i === 1 ? 'here' : ''}>
                <b className="d">{i + 1}</b><span>{name}</span>
                <span className="bar"><i /></span>
              </li>
            ))}
          </ol>
        ) : (
          <div className="si-court" aria-hidden="true"><Court sport="Football" /></div>
        )}
      </aside>

      <main className="si-main">
        <div className="si-bar">
          <Seg options={[['athlete', 'Athlete'], ['coach', 'Coach']]} value={role} onChange={onRole}
               label="Who is signing in" className="si-role" />
          <LookPicker look={look} onLook={onLook} />
        </div>
        <div className="si-form" key={role}>
          {role === 'coach'
            ? <Login sports={sports} onAuthed={onCoach} />
            : <StudentAuth onAuthed={onAthlete} />}
        </div>
        <footer className="si-foot">
          <a href="/privacy.html">Privacy policy</a>
          <a href="/terms.html">Terms of use</a>
        </footer>
      </main>
    </div>
  )
}
