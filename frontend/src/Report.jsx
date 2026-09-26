import { useEffect, useMemo, useState } from 'react'
import { api, band, bandWord, download, formatValue, shortLabel, utc, wrapLabel } from './api'
import { Radar, Sparkline } from './charts'
import Diet from './Diet'
import Icon from './Icon'
import VideoCard from './VideoCard'
import {
  Achievement, CertificateUpload, DetailsForm, DetailsView, Photo, PhotoButton,
} from './people'

const TABS = ['Overview', 'Profile', 'Measurements', 'Positions', 'Match', 'Training', 'Diet', 'Video']

/* A coach's view of one student, or — with `readOnly` — a verified student's view of
   their own report: no verifying, no deleting, no profile or video tab (their portal
   has their profile). */
export default function Report({ id, readOnly = false, initialTab = 'Overview', isAdmin = false, sports,
                                 onBack, onDeleted, onChanged }) {
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])
  const [error, setError] = useState('')
  const [tab, setTab] = useState(initialTab)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    setData(null)
    if (readOnly) {
      api.myReport().then(r => { setHistory(r.history); setData(r) }).catch(e => setError(e.message))
      return
    }
    api.analysis(id).then(setData).catch(e => setError(e.message))
    api.history(id).then(setHistory).catch(() => {})
  }, [id, readOnly])

  const byMetric = useMemo(() => {
    const out = {}
    for (const row of history) {
      (out[row.metric_key] ??= []).push({ t: row.recorded_at, v: row.value })
    }
    return out
  }, [history])

  if (error) return <div className="banner bad">{error}</div>
  if (!data) return <div className="skeleton">Building report…</div>

  const { student, recommended, metrics, positions, developmentPlan, videos, diet } = data
  const videoDrills = (videos ?? []).flatMap(v => v.metrics?.drills ?? [])
  const tabs = TABS.filter(t =>
    (t !== 'Profile' || !readOnly) &&
    (t !== 'Video' || (!readOnly && videos && videos.length > 0)) &&
    (t !== 'Match' || (data.matchClips && data.matchClips.length > 0))
  )

  async function remove() {
    if (!confirm(`Delete ${student.name} and all their data? This can't be undone.`)) return
    await api.deleteStudent(id)
    onDeleted()
  }

  async function saveExcel() {
    setSaving(true)
    try {
      await download(`/api/students/${id}/export`)
    } catch (err) {
      alert(err.message)
    } finally {
      setSaving(false)
    }
  }

  const setStudent = s => { setData(d => ({ ...d, student: s })); onChanged?.() }

  return (
    <>
      {onBack && (
        <button className="linkbtn noprint" onClick={onBack} style={{ marginBottom: 12 }}>
          <Icon name="back" size={13} /> All students
        </button>
      )}

      {/* the Profile tab carries its own header, photo included, when printed */}
      <div className={`pagehead${tab === 'Profile' ? ' noprint' : ''}`}>
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div className="row" style={{ gap: 14, flexWrap: 'nowrap', minWidth: 0 }}>
          {!readOnly && <Photo url={`/api/students/${id}/photo`} version={student.photo_version} name={student.name} size={56} />}
          <div style={{ minWidth: 0 }}>
            <h1>{student.name}</h1>
            <p className="muted">
              {data.sport}
              {student.ra_number ? ` · ${student.ra_number}` : ''}
              {student.email ? ` · ${student.email}` : ''}
              {student.age ? ` · ${student.age} yrs` : ''}
              {student.height_cm ? ` · ${student.height_cm} cm` : ''}
              {student.weight_kg ? ` · ${student.weight_kg} kg` : ''}
              {student.blood_group ? ` · ${student.blood_group}` : ''}
            </p>
          </div>
          </div>
          {!readOnly && (
            <div className="row noprint">
              <button className="btn sec sm" disabled={saving} onClick={saveExcel}>
                {saving ? 'Preparing…' : 'Download Excel'}
              </button>
              <button className="linkbtn danger" onClick={remove}>Delete student</button>
            </div>
          )}
        </div>
      </div>

      <VerifyCard student={student} positions={positions} recommended={recommended} readOnly={readOnly}
                  onChange={s => { setData(d => ({ ...d, student: s })); onChanged?.() }} />

      <div className="seg noprint" role="tablist" style={{ maxWidth: 700 }}>
        {tabs.map(t => (
          <button key={t} role="tab" aria-pressed={tab === t} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>

      {tab === 'Overview' && <Overview data={data} />}

      {tab === 'Profile' && (
        <ProfileTab student={student} isAdmin={isAdmin} sports={sports} onStudent={setStudent}
                    onMoved={onDeleted} />
      )}

      {tab === 'Measurements' && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Measurements</h2>
              <p className="muted">
                Test battery and physique, each scored 0–100 against the poor → elite range
                for {data.sport}. Match-derived metrics live on the Match tab.
              </p>
            </div>
          </div>
          {metrics.filter(m => m.source !== 'match').map(m => (
            <MetricRow key={m.key} metric={m} series={byMetric[m.key]} />
          ))}
        </div>
      )}

      {tab === 'Positions' && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Every position, ranked</h2>
              <p className="muted">Open one to see exactly which results drove its score.</p>
            </div>
          </div>
          {positions.map(p => <PositionRow key={p.position} pos={p} />)}
        </div>
      )}

      {tab === 'Match' && <MatchTab data={data} />}

      {tab === 'Training' && (
        <Training plan={developmentPlan} drills={videoDrills}
                  role={recommended?.position} hasVideo={(videos ?? []).length > 0} />
      )}

      {tab === 'Diet' && <Diet diet={diet} name={student.name} />}

      {tab === 'Video' && (
        <div className="card">
          <div className="card-head"><div><h2>Video analysis</h2></div></div>
          {videos.map(v => <VideoCard key={v.id} video={v} />)}
        </div>
      )}
    </>
  )
}

/* Who the student is — their details, photo and achievements. Coaches verify or reject
   achievements here; admins can also edit the details, change the photo and add
   certificates for students who have no portal of their own. */
function ProfileTab({ student, isAdmin, sports, onStudent, onMoved }) {
  const [list, setList] = useState(null)
  const [editing, setEditing] = useState(false)
  const [aiOn, setAiOn] = useState(false)

  useEffect(() => {
    api.studentAchievements(student.id).then(setList).catch(() => setList([]))
    if (isAdmin) api.health().then(h => setAiOn(!!h.documentAI)).catch(() => {})
  }, [student.id, isAdmin])

  // a verdict can change their highest verified level, so the details are fetched again
  const changed = async item => {
    setList(l => l.map(a => (a.id === item.id ? item : a)))
    onStudent(await api.student(student.id))
  }

  if (editing) {
    return (
      <DetailsForm mode="admin" student={student} sports={sports} submitLabel="Save changes"
                   onCancel={() => setEditing(false)}
                   onSubmit={async body => {
                     const saved = await api.updateStudent(student.id, body)
                     setEditing(false)
                     if (saved.sport !== student.sport) {
                       alert(`${saved.name} moved to ${saved.sport}. Switch sport to see them there.`)
                       onMoved()
                       return null
                     }
                     onStudent(saved)
                     return null
                   }} />
    )
  }

  return (
    <>
      <div className="card printable">
        <div className="card-head">
          <div className="row" style={{ gap: 16, flexWrap: 'nowrap' }}>
            <Photo url={`/api/students/${student.id}/photo`} version={student.photo_version}
                   name={student.name} size={96} />
            <div>
              <h2>{student.name}</h2>
              <p className="muted">{student.sport}{student.ra_number ? ` · ${student.ra_number}` : ''}</p>
            </div>
          </div>
          <div className="row noprint">
            {isAdmin && (
              <PhotoButton label={student.photo_version ? 'Change photo' : 'Add photo'}
                           onPhoto={async blob => onStudent({ ...student, ...(await api.setStudentPhoto(student.id, blob)) })} />
            )}
            {isAdmin && <button className="btn sec sm" onClick={() => setEditing(true)}>Edit details</button>}
            <button className="btn sec sm" onClick={() => window.print()}>Print / save as PDF</button>
          </div>
        </div>
        <DetailsView student={student} />
        {!isAdmin && (
          <p className="muted noprint" style={{ marginTop: 12 }}>
            Personal details are the university&apos;s record — the student corrects their own from
            their portal, and admins can change anything.
          </p>
        )}
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Achievements</h2>
            <p className="muted">
              Open each certificate before verifying it. Rejecting asks for a reason, which the
              student sees so they can fix it.
            </p>
          </div>
          {isAdmin && (
            <div className="noprint">
              <CertificateUpload aiOn={aiOn} label="Add a certificate"
                                 upload={(blob, name) => api.addStudentAchievement(student.id, blob, name)}
                                 onUploaded={a => setList(l => [a, ...(l ?? [])])} />
            </div>
          )}
        </div>
        {!list ? <div className="skeleton">Loading…</div>
          : list.length === 0 ? <p className="muted">Nothing sent yet.</p>
            : list.map(a => (
              <Achievement key={a.id} item={a} as={isAdmin ? 'admin' : 'coach'} studentName={student.name}
                           certUrl={`/api/achievements/${a.id}/certificate`} onChange={changed}
                           onDelete={() => setList(l => l.filter(x => x.id !== a.id))} />
            ))}
      </div>
    </>
  )
}

/* The coach's confirmation of where this student plays. It moves them to the Verified
   tab of the squad sheet and becomes a training example for the model. */
function VerifyCard({ student, positions, recommended, readOnly, onChange }) {
  const [choice, setChoice] = useState(recommended?.position ?? positions[0]?.position ?? '')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  async function run(action) {
    setBusy(true)
    setError('')
    try {
      onChange(await action())
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (student.status === 'verified') {
    const agrees = recommended?.position === student.verified_position
    return (
      <div className="card noprint">
        <div className="verify">
          <span className="pill good"><i className="dot" />Verified</span>
          <span>
            Plays <b>{student.verified_position}</b>
            {student.verified_by_name ? ` — confirmed by ${student.verified_by_name}` : ''}
            {student.verified_at ? ` on ${utc(student.verified_at).toLocaleDateString()}` : ''}.
          </span>
          <span className="muted">
            {recommended
              ? agrees ? 'The system agrees.' : `The system currently suggests ${recommended.position}.`
              : ''}
          </span>
          {!readOnly && (
            <button className="linkbtn" disabled={busy}
                    onClick={() => run(() => api.unverify(student.id))}>Undo</button>
          )}
        </div>
        {error && <div className="note err">{error}</div>}
      </div>
    )
  }

  return (
    <div className="card noprint">
      <div className="verify">
        <span className="pill warn"><i className="dot" />Pending</span>
        <label htmlFor="vpos">Confirm the position they play:</label>
        <select id="vpos" value={choice} onChange={e => setChoice(e.target.value)}>
          {positions.map(p => (
            <option key={p.position} value={p.position}>
              {p.position}{p.position === recommended?.position ? ' (suggested)' : ''}
            </option>
          ))}
        </select>
        <button className="btn sm" disabled={busy || !choice}
                onClick={() => run(() => api.verify(student.id, choice))}>
          {busy ? 'Saving…' : 'Verify'}
        </button>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        Verifying moves {student.name} to the Verified tab of the squad sheet, and teaches the
        model — your call counts even when it differs from the suggestion.
      </p>
      {error && <div className="note err">{error}</div>}
    </div>
  )
}

function Overview({ data }) {
  const { recommended, metrics, student, positions } = data
  // the overview radar is the testing profile; match metrics get their own on the Match tab
  const testMetrics = metrics.filter(m => m.source !== 'match')
  const radar = testMetrics.map(m => ({
    label: m.label, score: m.score, lines: wrapLabel(shortLabel(m.label)),
  }))
  const unmeasured = testMetrics.filter(m => m.score === null)
  const strengths = data.strengths.filter(s => s.source !== 'match')
  const weaknesses = data.weaknesses.filter(s => s.source !== 'match')

  if (!recommended) {
    return (
      <div className="card">
        <p className="empty">
          <b>No test results yet</b>
          The full report appears here once test results are recorded.
        </p>
      </div>
    )
  }

  return (
    <>
      <div className="split">
        <div className="card">
          <div className="hero">
            <div>
              <div className="label">Best-fit position</div>
              <div className="big">{recommended.position}</div>
            </div>
            <div>
              <div className="label">Fit</div>
              <div className="score">{recommended.fit}</div>
            </div>
          </div>

          <div className="chips">
            <span className={`pill ${recommended.confidence === 'high' ? 'good' : 'warn'}`}>
              <i className="dot" />{recommended.confidence} confidence
            </span>
            <span className="pill">{Math.round(recommended.coverage * 100)}% of the profile measured</span>
            {data.margin > 0 && <span className="pill accent">+{data.margin} ahead of next</span>}
            <span className="pill">Overall {data.overallScore}/100</span>
          </div>

          <p className="why">{recommended.why}</p>

          {data.declaredPositionFit && data.declaredPositionFit.position !== recommended.position && (
            <div className="banner" style={{ marginTop: 14, marginBottom: 0 }}>
              Currently listed as <b>{data.declaredPositionFit.position}</b> (fit{' '}
              {data.declaredPositionFit.fit}/100) — the data points to {recommended.position} instead.
            </div>
          )}

          {unmeasured.length > 0 && (
            <p className="muted" style={{ marginTop: 12 }}>
              Not yet measured: {unmeasured.map(m => m.label).join(', ')}.
            </p>
          )}

          {/* testing profile only — match standouts live on the Match tab, where the
              body-height units and the clip they came from are in view */}
          <div style={{ marginTop: 'auto', paddingTop: 16 }}>
            <h3>Standout results</h3>
            {strengths.length === 0
              ? <p className="muted">Nothing above 65/100 yet.</p>
              : <div className="chips">
                  {strengths.map(s => (
                    <span className="pill good" key={s.key}><i className="dot" />{s.label} {s.score}</span>
                  ))}
                </div>}

            <h3 style={{ marginTop: 14 }}>Weak links</h3>
            {weaknesses.length === 0
              ? <p className="muted">Nothing below 40/100 — no obvious hole.</p>
              : <div className="chips">
                  {weaknesses.map(s => (
                    <span className="pill bad" key={s.key}><i className="dot" />{s.label} {s.score}</span>
                  ))}
                </div>}
          </div>
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <h2>Athlete profile</h2>
              <p className="muted">Every metric on one 0–100 scale. Hover a point for the value.</p>
            </div>
          </div>
          <Radar points={radar} />
          <p className="muted" style={{ marginTop: 6 }}>
            The Measurements tab lists the same numbers as a table.
          </p>
        </div>
      </div>

      <Reconciliation data={data} />

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Top three roles</h2>
            <p className="muted">Full ranking and reasoning on the Positions tab.</p>
          </div>
        </div>
        {positions.slice(0, 3).map(p => (
          <div className="metric" key={p.position}>
            <div className="mtop">
              <span className="mname">{p.position}</span>
              <span className="mval"><b>{p.fit}</b>/100</span>
            </div>
            <div className="track"><i style={{ width: `${p.fit ?? 0}%` }} /></div>
          </div>
        ))}
        {student.declared_position && <p className="muted">Listed role: {student.declared_position}</p>}
      </div>
    </>
  )
}

const AGREEMENT_TONE = {
  agree: 'good', near: 'warn', disagree: 'bad',
  'tests-only': '', 'match-only': '', none: '',
}

function VerdictPanel({ title, hint, summary }) {
  if (!summary?.available) {
    return (
      <div className="verdict none">
        <div className="k">{title}</div>
        <div className="v">No data yet</div>
        <p className="muted" style={{ margin: 0 }}>{hint}</p>
      </div>
    )
  }
  const r = summary.recommended
  return (
    <div className="verdict">
      <div className="k">{title}</div>
      <div className="v">{r.position}</div>
      <div className="chips" style={{ marginTop: 6 }}>
        <span className="pill accent">Fit {r.fit}</span>
        <span className={`pill ${r.confidence === 'high' ? 'good' : 'warn'}`}>
          <i className="dot" />{r.confidence}
        </span>
      </div>
      <p className="muted" style={{ marginTop: 8 }}>
        Then {summary.positions.filter(p => p.position !== r.position).slice(0, 2)
          .map(p => `${p.position} ${p.fit}`).join(', ')}
      </p>
    </div>
  )
}

function Reconciliation({ data }) {
  const rec = data.reconciliation
  const sources = data.bySource ?? {}
  if (!rec) return null

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>Two sources, one verdict</h2>
          <p className="muted">
            The test battery and the match footage are scored independently, then compared.
          </p>
        </div>
      </div>

      <div className="verdicts">
        <VerdictPanel title="From the tests" summary={sources.test}
                      hint="Record the test battery in Coach Entry." />
        <VerdictPanel title="From match footage" summary={sources.match}
                      hint="Upload a clip and identify this student in it." />
      </div>

      <div className={`banner ${AGREEMENT_TONE[rec.agreement] ?? ''}`} style={{ marginTop: 14, marginBottom: 0 }}>
        {rec.text}
      </div>

      {data.recommended && (
        <p className="muted" style={{ marginTop: 10 }}>
          Headline above uses everything together: <b>{data.recommended.position}</b> at{' '}
          {data.recommended.fit}/100.
        </p>
      )}
    </div>
  )
}

function MatchTab({ data }) {
  const matchMetrics = data.metrics.filter(m => m.source === 'match')
  const ranking = data.bySource?.match
  const clips = data.matchClips ?? []

  return (
    <>
      <div className="card">
        <div className="card-head">
          <div>
            <h2>What the footage says on its own</h2>
            <p className="muted">
              Scored using only match metrics — no test results, no height. This is the
              in-game verdict to weigh against the testing one.
            </p>
          </div>
        </div>
        {!ranking?.available
          ? <p className="muted">Not enough tracked time yet to rank positions from footage.</p>
          : ranking.positions.slice(0, 5).map(p => (
              <div className="metric" key={p.position}>
                <div className="mtop">
                  <span className="mname">{p.position}</span>
                  <span className="mval"><b>{p.fit}</b>/100 · {p.confidence}</span>
                </div>
                <div className="track"><i style={{ width: `${p.fit ?? 0}%` }} /></div>
              </div>
            ))}
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Match metrics</h2>
            <p className="muted">
              Averaged across every clip this student was identified in, weighted by how
              long they were tracked. Distance and speed are in body-heights so they stay
              comparable across camera setups.
            </p>
          </div>
        </div>
        {matchMetrics.every(m => m.value === null)
          ? <p className="muted">No tracked footage attributed to this student yet.</p>
          : (
            <div className="split" style={{ alignItems: 'start' }}>
              <div>{matchMetrics.map(m => <MetricRow key={m.key} metric={m} />)}</div>
              <Radar points={matchMetrics.map(m => ({
                label: m.label, score: m.score, lines: wrapLabel(shortLabel(m.label)),
              }))} />
            </div>
          )}
      </div>

      {clips.length > 0 && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Appearances</h2>
              <p className="muted">Clips this student has been identified in.</p>
            </div>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Clip</th><th className="num">Tracked</th><th className="num">Distance</th>
                  <th className="num">Top speed</th><th className="num">Sprints</th>
                  <th className="num">Active</th>
                </tr>
              </thead>
              <tbody>
                {clips.map(c => (
                  <tr key={`${c.clipId}-${c.trackId}`}>
                    <td>
                      {c.label || c.originalName}
                      <div className="muted">
                        track #{c.trackId}
                        {c.context?.approxMetres != null && ` · ≈${c.context.approxMetres} m`}
                      </div>
                    </td>
                    <td className="num">{c.context?.trackedSeconds ?? '—'}s</td>
                    <td className="num">{c.metrics?.matchDistance ?? '—'}</td>
                    <td className="num">{c.metrics?.matchTopSpeed ?? '—'}</td>
                    <td className="num">{c.metrics?.matchSprints ?? '—'}</td>
                    <td className="num">{c.metrics?.matchWorkRate ?? '—'}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted" style={{ marginTop: 10 }}>
            Metre figures are approximate — converted from body-heights using the student&apos;s
            height, without camera calibration.
          </p>
        </div>
      )}
    </>
  )
}

function MetricRow({ metric: m, series }) {
  const points = (series ?? []).map(p => ({ t: p.t, v: p.v }))
  return (
    <div className="metric">
      <div className="mtop">
        <span className="mname">
          {m.label}{' '}
          {m.basis && m.basis !== 'estimated' && (
            <span className={`basis ${m.basis}`}
                  title={`${m.authority || ''}${m.note ? ' — ' + m.note : ''}`}>
              {m.basis}
            </span>
          )}
        </span>
        <span className="mval">
          {formatValue(m.value, m)}
          {m.score != null && <> · <b>{m.score}</b>/100 · {bandWord(m.score)}</>}
        </span>
      </div>
      <div className="track"><i className={band(m.score)} style={{ width: `${m.score ?? 0}%` }} /></div>
      <div className="mscale">
        <span>{formatValue(m.poor, m)}</span>
        <span title={m.note || undefined}>
          {m.source === 'profile' ? 'from profile'
            : m.direction === 'lower' ? 'lower is better' : 'higher is better'}
          {m.authority ? ` · ${m.authority}` : ''}
        </span>
        <span>{formatValue(m.elite, m)}</span>
      </div>
      {m.note && <p className="muted" style={{ marginTop: 4 }}>{m.note}</p>}
      {points.length > 1 && (
        <div style={{ marginTop: 10, maxWidth: 360 }}>
          <Sparkline series={points} unit={m.unit} lowerIsBetter={m.direction === 'lower'} />
        </div>
      )}
    </div>
  )
}

function PositionRow({ pos: p }) {
  return (
    <details className="pos">
      <summary>
        <span className="pname">{p.position}</span>
        <span className="pbar">
          <span className="track"><i style={{ width: `${p.fit ?? 0}%` }} /></span>
        </span>
        <span className="pnum">{p.fit ?? '—'}</span>
      </summary>
      <div className="body">
        <p className="why" style={{ marginTop: 0 }}>{p.why}</p>
        {(p.drivers.length > 0 || p.drags.length > 0) && (
          <div className="chips">
            {p.drivers.map(d => (
              <span className="pill good" key={`+${d.key}`}><i className="dot" />{d.label} {d.score}</span>
            ))}
            {p.drags.map(d => (
              <span className="pill bad" key={`-${d.key}`}><i className="dot" />{d.label} {d.score}</span>
            ))}
          </div>
        )}
        <table className="data" style={{ marginTop: 12 }}>
          <thead><tr><th>Metric</th><th className="num">Weight</th><th className="num">Score</th></tr></thead>
          <tbody>
            {[...p.drivers, ...p.drags].map(d => (
              <tr key={d.key}>
                <td>{d.label}</td>
                <td className="num">{d.weight}</td>
                <td className="num">{d.score}</td>
              </tr>
            ))}
            {p.missing.map(m => (
              <tr key={m.key}>
                <td>{m.label}</td>
                <td className="num">{m.weight}</td>
                <td className="num muted">not measured</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="muted" style={{ marginTop: 8 }}>
          {Math.round(p.coverage * 100)}% of this role&apos;s weight is backed by data ({p.confidence} confidence).
        </p>
      </div>
    </details>
  )
}

function Training({ plan, drills, role, hasVideo }) {
  return (
    <>
      <div className="card">
        <div className="card-head">
          <div>
            <h2>What to work on</h2>
            <p className="muted">From the test results, ordered by how much it matters for {role ?? 'the top role'}.</p>
          </div>
        </div>
        {plan.length === 0
          ? <p className="muted">Nothing scored below 40/100 — no priority weak point from the tests.</p>
          : <ul className="advice">
              {plan.map(p => (
                <li key={p.key}>
                  <div className="head">
                    {p.label}
                    <span className="pill bad"><i className="dot" />{p.score}/100</span>
                    {p.relevance > 0 && <span className="pill">weight {p.relevance}</span>}
                  </div>
                  <p className="do">{p.tip}</p>
                </li>
              ))}
            </ul>}
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>From the video</h2>
            <p className="muted">Movement faults the pose analysis picked up, and the fix for each.</p>
          </div>
        </div>
        {!hasVideo
          ? <p className="empty"><b>No clips yet</b>Movement work appears here once drill footage has been analysed.</p>
          : drills.length === 0
            ? <p className="muted">Nothing in the uploaded clips crossed a coaching threshold.</p>
            : <ul className="advice">
                {drills.map((d, i) => (
                  <li key={i}>
                    <div className="head">
                      {d.finding}
                      {d.metric && <span className="pill warn"><i className="dot" />{d.value}</span>}
                    </div>
                    <p className="why">{d.why}</p>
                    <p className="do">{d.drill}</p>
                  </li>
                ))}
              </ul>}
      </div>
    </>
  )
}
