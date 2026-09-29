import { useEffect, useState } from 'react'
import { api, formatValue, utc } from './api'
import { Photo, levelWord, teamWord } from './people'

/* The one-page report for the Directorate of Sports: who the player is, the level they
   play at, where they fit, their numbers, what to work on, and space for two signatures.
   Everything on it comes from the report already on screen; it prints on one A4 page. */

const day = d => d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
const FORMAT_WORDS = { t20: 'T20', odi: '50-over', mat: 'mat', traditional: 'traditional' }
// what fits on one page; the full report has the rest
const MAX = { tests: 7, cards: 8, strengths: 4, plan: 3, achievements: 3, positions: 3 }

export default function OfficialReport({ data, onBack }) {
  const s = data.student
  const lv = data.levels
  const [achievements, setAchievements] = useState(null)

  useEffect(() => {
    api.studentAchievements(s.id).then(setAchievements).catch(() => setAchievements([]))
  }, [s.id])

  const levelName = i => (i == null ? '—' : i < 0 ? 'Below University' : lv.levels[i])
  const rowOf = Object.fromEntries((lv?.rows ?? []).map(r => [r.key, r]))
  // how far from the top: ✓, or the International target they are working towards
  const toTop = r => (!r?.ladder || r.level == null ? '—'
    : r.level === r.ladder.length - 1 ? '✓' : formatValue(r.ladder[r.ladder.length - 1], r))
  const tests = data.metrics.filter(m => (m.source === 'test' || m.source === 'profile') && m.value != null)
  const cards = (lv?.rows ?? []).filter(r => r.source === 'card')
  const verified = (achievements ?? []).filter(a => a.status === 'verified')
    .sort((a, b) => (b.year ?? 0) - (a.year ?? 0))
  const confirmed = s.status === 'verified'
  const context = data.matchCards?.context
  const groups = [['test', 'Tests'], ['card', 'Match cards'], ['match', 'Footage']]
    .filter(([k]) => lv?.groups[k].measures > 0)
  const count = (n, one, many) => `${n} ${n === 1 ? one : many}`
  const evidence = [
    tests.length && count(tests.length, 'test', 'tests'),
    context?.matches && count(context.matches, 'match', 'matches'),
    data.matchClips?.length && count(data.matchClips.length, 'clip', 'clips'),
  ].filter(Boolean)

  // strengths and what to work on, read the same way as the page's headline: by level.
  // Tests and match cards only — one camera's footage is too shaky for an official page.
  const overall = lv?.overall.level
  const judged = (lv?.rows ?? []).filter(r => r.level != null && r.source !== 'match')
  const byLevel = judged.map((r, i) => ({ ...r, i }))
  const best = [...byLevel].sort((a, b) => b.level - a.level || a.i - b.i)
    .filter(r => r.level >= 0 && (overall == null || r.level >= overall)).slice(0, MAX.strengths)
  const behind = [...byLevel].sort((a, b) => a.level - b.level || a.i - b.i)   // height can't be trained
    .filter(r => r.next && r.source !== 'profile' && (overall == null || r.level < overall)).slice(0, MAX.plan)

  return (
    <>
      <div className="row noprint" style={{ marginBottom: 14 }}>
        <button className="linkbtn" onClick={onBack}>← Back to the report</button>
        <button className="btn sm" onClick={() => window.print()} disabled={achievements === null}>
          Print / save as PDF
        </button>
        <span className="muted">One A4 page, portrait. The full report has everything else.</span>
      </div>

      <div className="officialpreview">
        <article className="officialsheet cardprint">
          <header className="ct-mast">
            <div className="inst">SRM INSTITUTE OF SCIENCE AND TECHNOLOGY</div>
            <div className="dir">DIRECTORATE OF SPORTS</div>
            <div className="db">PLAYER PROFILE REPORT</div>
          </header>

          <div className="or-id">
            <table>
              <tbody>
                <tr><th>Name</th><td colSpan={3}><b>{s.name}</b></td></tr>
                <tr>
                  <th>RA number</th><td>{s.ra_number || '—'}</td>
                  <th>Date of birth</th>
                  <td>{s.dob ? `${day(new Date(`${s.dob}T00:00`))}${s.age ? ` (${s.age} yrs)` : ''}` : '—'}</td>
                </tr>
                <tr>
                  <th>Sport</th><td>{data.sport}{s.category ? ` — ${teamWord(s.category)}` : ''}</td>
                  <th>Jersey no.</th><td>{s.jersey_number ?? '—'}</td>
                </tr>
                <tr>
                  <th>Height / weight</th>
                  <td>{[s.height_cm && `${s.height_cm} cm`, s.weight_kg && `${s.weight_kg} kg`].filter(Boolean).join(' / ') || '—'}</td>
                  <th>Blood group</th><td>{s.blood_group || '—'}</td>
                </tr>
                <tr>
                  <th>Highest level</th>
                  <td colSpan={3}>
                    {s.top_verified_level ? `${levelWord(s.top_verified_level)} (certificate verified)`
                      : s.highest_level ? `${levelWord(s.highest_level)} (their word, not yet verified)` : 'Not yet competed'}
                  </td>
                </tr>
                <tr>
                  <th>Position</th>
                  <td colSpan={3}>
                    {confirmed
                      ? <><b>{s.verified_position}</b> — confirmed by {s.verified_by_name ?? 'the coach'}{s.verified_at ? ` on ${day(utc(s.verified_at))}` : ''}</>
                      : data.recommended ? <><b>{data.recommended.position}</b> — suggested by the data, not yet confirmed</> : 'Not enough data yet'}
                  </td>
                </tr>
              </tbody>
            </table>
            <div className="or-photo">
              <Photo url={`/api/students/${s.id}/photo`} version={s.photo_version} name={s.name} size={112} />
            </div>
          </div>

          <div className="or-head">
            <div>
              <span>{lv?.overall.level != null && lv.overall.level >= 0 ? 'Plays at' : 'Level'}</span>
              <b>{lv?.overall.level != null ? `${levelName(lv.overall.level)} level` : 'Not enough measured yet'}</b>
              {groups.length > 0 && (
                <small>{groups.map(([k, word]) => `${word}: ${levelName(lv.groups[k].level)}`).join(' · ')}</small>
              )}
            </div>
            <div>
              <span>Best-fit position</span>
              <b>{data.recommended ? data.recommended.position : '—'}</b>
              {data.recommended && <small>fit {data.recommended.fit}/100 · {data.recommended.confidence} confidence</small>}
            </div>
            <div>
              <span>Based on</span>
              <b>{evidence.length ? evidence.join(' · ') : 'No results yet'}</b>
              <small>the more of each, the firmer the picture</small>
            </div>
          </div>
          {lv?.standing.length > 0 && (
            <table className="or-standing">
              <tbody>
                <tr>
                  <th>Standing</th>
                  {lv.standing.map((x, i) => (
                    <td key={i} className={i === lv.overall.level ? 'here' : ''}>
                      {lv.levels[i]} <b>{Math.round(x.share * 100)}%</b> <small>({x.met}/{x.of})</small>
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          )}
          {data.reconciliation?.text && <p className="or-note">{data.reconciliation.text}</p>}

          <div className="or-cols">
            <section>
              <h3>Test results{lv?.category ? ` (${lv.category === 'M' ? "men's" : "women's"} targets)` : ''}</h3>
              {tests.length === 0 ? <p className="or-empty">No test results recorded yet.</p> : (
                <table>
                  <thead><tr><th>Measure</th><th>Result</th><th>Level</th><th>International</th></tr></thead>
                  <tbody>
                    {tests.slice(0, MAX.tests).map(m => (
                      <tr key={m.key}>
                        <td>{m.label}</td><td className="n">{formatValue(m.value, m)}</td>
                        <td>{levelName(rowOf[m.key]?.level)}</td><td>{toTop(rowOf[m.key])}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
            <section>
              <h3>
                Match cards
                {context ? ` (${context.matches} match${context.matches === 1 ? '' : 'es'}${context.format ? `, ${FORMAT_WORDS[context.format] ?? context.format}` : ''})` : ''}
              </h3>
              {cards.length === 0 ? <p className="or-empty">No finished match cards yet.</p> : (
                <table>
                  <thead><tr><th>Measure</th><th>Value</th><th>Level</th><th>International</th></tr></thead>
                  <tbody>
                    {cards.slice(0, MAX.cards).map(r => (
                      <tr key={r.key}>
                        <td>{r.label}</td><td className="n">{formatValue(r.value, r)}</td>
                        <td>{levelName(r.level)}</td><td>{toTop(r)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </section>
          </div>

          <div className="or-cols">
            <section>
              <h3>Position fit</h3>
              {data.positions.filter(p => p.fit != null).length === 0 ? <p className="or-empty">Not enough data yet.</p> : (
                <table>
                  <tbody>
                    {data.positions.filter(p => p.fit != null).slice(0, MAX.positions).map(p => (
                      <tr key={p.position}><td>{p.position}</td><td className="n">{p.fit}/100</td></tr>
                    ))}
                  </tbody>
                </table>
              )}
              <h3>Strengths</h3>
              {judged.length === 0 ? <p className="or-empty">Set their team and record tests to see these.</p>
                : best.length === 0 ? <p className="or-empty">Nothing at University level or above yet.</p> : (
                  <ul>
                    {best.map(r => (
                      <li key={r.key}><b>{r.label}</b> — {levelName(r.level)} level ({formatValue(r.value, r)})</li>
                    ))}
                  </ul>
                )}
            </section>
            <section>
              <h3>To work on</h3>
              {judged.length === 0 ? <p className="or-empty">Set their team and record tests to see these.</p>
                : behind.length === 0 ? <p className="or-empty">Nothing lags behind the level they play at.</p> : (
                  <ul>
                    {behind.map(r => (
                      <li key={r.key}>
                        <b>{r.label}</b> — {levelName(r.level)}; {lv.levels[r.next.level]} needs {formatValue(r.next.target, r)}.
                        {r.tip ? ` ${r.tip}` : ''}
                      </li>
                    ))}
                  </ul>
                )}
              <h3>Verified achievements</h3>
              {verified.length === 0 ? <p className="or-empty">None verified yet.</p> : (
                <ul>
                  {verified.slice(0, MAX.achievements).map(a => (
                    <li key={a.id}>
                      {[a.level && levelWord(a.level), a.title, a.year, a.result].filter(Boolean).join(' · ')}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          </div>

          <h3>Coach&apos;s remarks</h3>
          <div className="or-lines"><i /><i /><i /></div>

          <div className="or-sign">
            <div><i />Coach{confirmed && s.verified_by_name ? ` — ${s.verified_by_name}` : ''}<small>Signature and date</small></div>
            <div><i />Director of Sports<small>Signature, date and seal</small></div>
          </div>

          <footer className="ct-foot">
            Prepared with Stridian on {day(new Date())} from this player&apos;s tests, match cards and footage.
            Levels compare each result with what players typically post at each level; Standing is the share
            of what matters for the position that meets each level, and they play at the highest one more
            than half meets. Position fit uses the same ladder (University 20 … International 100). ID {s.id}.
          </footer>
        </article>
      </div>
    </>
  )
}
