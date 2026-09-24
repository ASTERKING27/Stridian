import { useEffect, useMemo, useRef, useState } from 'react'
import { api, authedImage, inFlight, statusPill, statusWord, usePoll, utc } from './api'
import Icon from './Icon'
import { UploadButton, WorkerNote } from './VideoCard'

/* The YOLO lane. A clip belongs to the squad rather than to one student: every player
   in it is detected and followed, and the coach then says which track is whose by
   clicking the player on a keyframe. */

export default function Matches({ version, onChanged }) {
  const [clips, setClips] = useState(null)
  const [openId, setOpenId] = useState(null)
  const [error, setError] = useState('')

  const load = () => api.matches().then(c => { setClips(c); setError('') }).catch(e => setError(e.message))
  useEffect(() => { load() }, [version]) // eslint-disable-line react-hooks/exhaustive-deps
  usePoll((clips ?? []).some(c => inFlight(c.status)), load)

  if (error) return <div className="banner bad">{error}</div>
  if (!clips) return <div className="skeleton">Loading match clips…</div>

  if (openId) {
    return (
      <ClipDetail id={openId} onBack={() => { setOpenId(null); load() }}
                  onChanged={onChanged}
                  onDeleted={() => { setOpenId(null); load(); onChanged() }} />
    )
  }

  return (
    <>
      <div className="pagehead">
        <h1>Match footage</h1>
        <p className="lede">
          Upload a full match or a snippet with several players visible. Every player is
          detected and followed; you then click your student once and their movement data
          attaches to them. This runs alongside the single-player drill clips — the report
          scores each source separately and reconciles them.
        </p>
      </div>

      <MatchUploader onUploaded={() => { load(); onChanged() }} />

      <div className="card flush">
        {clips.length === 0 ? (
          <p className="empty">
            <b>No match clips yet</b>
            Upload one above to start identifying players.
          </p>
        ) : (
          <div className="rows">
            {clips.map(c => (
              <button key={c.id} className="rowitem" onClick={() => setOpenId(c.id)}>
                <span className="who">
                  <b>{c.label || c.original_name}</b>
                  <span>
                    {c.duration_sec ? `${Math.round(c.duration_sec)}s` : 'length unknown'}
                    {' · '}attacking {c.attack_direction}
                    {' · '}{utc(c.created_at).toLocaleDateString()}
                  </span>
                </span>
                <span className={`pill ${statusPill(c.status)}`}>
                  <i className="dot" />{statusWord(c.status)}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </>
  )
}

function MatchUploader({ onUploaded }) {
  const [file, setFile] = useState(null)
  const [label, setLabel] = useState('')
  const [direction, setDirection] = useState('right')
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState(null)

  async function upload() {
    if (!file) return
    setBusy(true)
    setProgress(0)
    setStatus(null)
    try {
      await api.uploadMatch(file, { label, attackDirection: direction }, setProgress)
      setFile(null)
      setLabel('')
      setStatus({ ok: true, text: 'Uploaded and queued. Players appear in the list below once the analysis computer has tracked them.' })
      onUploaded()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>Upload a clip</h2>
          <p className="muted">
            A wide, steady shot works best — players need to be a reasonable size in frame.
            Tracking runs at 5 fps over the first 3 minutes.
          </p>
        </div>
      </div>

      <WorkerNote need="match" />

      <div className="grid2">
        <div className="field">
          <label htmlFor="mlabel">Label (optional)</label>
          <input id="mlabel" placeholder="e.g. Inter-dept semi-final, 2nd half"
                 value={label} onChange={e => setLabel(e.target.value)} />
        </div>
        <div className="field">
          <label id="dirlbl">Which way is your team attacking?</label>
          <div className="toggles" role="group" aria-labelledby="dirlbl">
            <button type="button" aria-pressed={direction === 'left'} onClick={() => setDirection('left')}>
              ← Left
            </button>
            <button type="button" aria-pressed={direction === 'right'} onClick={() => setDirection('right')}>
              Right →
            </button>
          </div>
          <p className="muted" style={{ marginTop: 6 }}>
            Positioning is measured against where the other players are, so this is all the
            calibration it needs.
          </p>
        </div>
      </div>

      <UploadButton file={file} onPick={setFile} onUpload={upload} busy={busy}
                    progress={progress} label="Upload match" />
      {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
    </div>
  )
}

// seconds -> "1:05"
const clock = s => `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`

function ClipDetail({ id, onBack, onChanged, onDeleted }) {
  const [clip, setClip] = useState(null)
  const [students, setStudents] = useState([])
  const [frame, setFrame] = useState(null)
  const [selected, setSelected] = useState(null)
  const [choice, setChoice] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [preset, setPreset] = useState(null)
  const [calPoints, setCalPoints] = useState([])
  const [calNote, setCalNote] = useState(null)
  // calibrating on a still other than the keyframe: which one, and its image once loaded
  const [frameAt, setFrameAt] = useState(null)
  const [shot, setShot] = useState(null)
  const shots = useRef({})

  const loadClip = () => api.match(id).then(c => { setClip(c); setError('') }).catch(e => setError(e.message))
  useEffect(() => {
    loadClip()
    api.students().then(setStudents).catch(() => {})
  }, [id]) // eslint-disable-line react-hooks/exhaustive-deps
  usePoll(inFlight(clip?.status), loadClip)

  const ready = clip?.status === 'done'
  useEffect(() => {
    if (!ready) return undefined
    let dead = false
    let url
    authedImage(`/api/matches/${id}/keyframe`)
      .then(u => { if (dead) URL.revokeObjectURL(u); else { url = u; setFrame(u) } })
      .catch(() => {})
    return () => { dead = true; if (url) URL.revokeObjectURL(url) }
  }, [id, ready])

  useEffect(() => {
    if (frameAt === null) return undefined
    let dead = false
    const have = shots.current[frameAt]
    if (have) {
      setShot({ at: frameAt, url: have })
      return undefined
    }
    authedImage(`/api/matches/${id}/frames/${frameAt}`)
      .then(url => { shots.current[frameAt] = url; if (!dead) setShot({ at: frameAt, url }) })
      .catch(() => {})
    return () => { dead = true }
  }, [id, frameAt])
  useEffect(() => () => Object.values(shots.current).forEach(u => URL.revokeObjectURL(u)), [])

  const byTrack = useMemo(
    () => Object.fromEntries((clip?.tracks ?? []).map(t => [t.trackId, t])),
    [clip]
  )

  if (error) return <div className="banner bad">{error}</div>
  if (!clip) return <div className="skeleton">Loading clip…</div>

  async function assign() {
    if (!selected || !choice) return
    setBusy(true)
    try {
      setClip(await api.assignTrack(id, selected, Number(choice)))
      setSelected(null)
      setChoice('')
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function unassign(trackId) {
    setBusy(true)
    try {
      setClip(await api.unassignTrack(id, trackId))
      if (selected === trackId) setSelected(null)
      onChanged()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    if (!confirm('Delete this clip and every identification made on it?')) return
    await api.deleteMatch(id)
    onDeleted()
  }

  const frames = clip.frames ?? []
  const scrubbing = preset && frames.length > 1
  const shotReady = !scrubbing || shot?.at === frameAt    // don't mark points on the old still
  const shown = scrubbing ? (shot?.url ?? frame) : frame

  function startCalibrating(p) {
    setPreset(p)
    setCalPoints([])
    setSelected(null)
    if (frames.length > 1) setFrameAt(clip.framesStart ?? 0)
  }

  function stopCalibrating() {
    setPreset(null)
    setCalPoints([])
    setFrameAt(null)
  }

  function markPoint(event) {
    if (!preset || calPoints.length >= 4 || !shotReady) return
    const box = event.currentTarget.getBoundingClientRect()
    setCalPoints(p => [...p, {
      x: Math.min(1, Math.max(0, (event.clientX - box.left) / box.width)),
      y: Math.min(1, Math.max(0, (event.clientY - box.top) / box.height)),
    }])
  }

  async function applyCalibration() {
    setBusy(true)
    setCalNote(null)
    try {
      const res = await api.calibrate(id, {
        image_points: calPoints,
        world_points: preset.world.map(([x, y]) => ({ x, y })),
        preset: preset.key,
        label: preset.label,
      })
      setClip(res)
      stopCalibrating()
      setCalNote({ ok: true, text: res.message })
      onChanged()
    } catch (err) {
      setCalNote({ ok: false, text: err.message })
      setCalPoints([])
    } finally {
      setBusy(false)
    }
  }

  async function dropCalibration() {
    setBusy(true)
    try {
      const res = await api.clearCalibration(id)
      setClip(res)
      setCalNote({ ok: true, text: res.message })
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  const boxes = clip.keyframeBoxes ?? []
  // a student is one player per clip: picking them for another box moves them there
  const trackOf = Object.fromEntries(
    clip.tracks.filter(t => t.assignedTo).map(t => [t.assignedTo.studentId, t.trackId]))
  const selectedWho = selected ? byTrack[selected]?.assignedTo : null
  const assignedCount = clip.tracks.filter(t => t.assignedTo).length

  return (
    <>
      <button className="linkbtn" onClick={onBack} style={{ marginBottom: 12 }}>
        <Icon name="back" size={13} /> All clips
      </button>

      <div className="pagehead">
        <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <h1>{clip.label || clip.original_name}</h1>
            <p className="muted">
              {clip.tracks.length} players followed · {assignedCount} identified ·{' '}
              {clip.duration_sec ? `${Math.round(clip.duration_sec)}s` : 'length unknown'} ·
              attacking {clip.attack_direction}
            </p>
          </div>
          <button className="linkbtn danger" onClick={remove}>Delete clip</button>
        </div>
      </div>

      {inFlight(clip.status) && (
        <div className="banner warn">
          {clip.message} This page refreshes by itself when the players have been tracked.
        </div>
      )}
      {!inFlight(clip.status) && clip.status !== 'done' && <div className="banner bad">{clip.message}</div>}
      {clip.video_deleted_at && (
        <div className="banner">
          The video file was removed 30 days after upload. Every track, identification and
          calibration below is kept.
        </div>
      )}
      {clip.status === 'done' && clip.tracks.length === 0 && (
        <div className="banner warn">{clip.message}</div>
      )}

      {boxes.length > 0 && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Who is who</h2>
              <p className="muted">
                Click your student on the frame, then pick their name. Green boxes are
                already identified.
              </p>
            </div>
          </div>

          <div className={`frame ${preset ? 'calibrating' : ''}`}
               onClick={preset ? markPoint : undefined}>
            {shown
              ? <img src={shown} alt="Frame from the match clip with every tracked player boxed"
                     style={shotReady ? undefined : { opacity: 0.5 }} />
              : <div className="skeleton">Loading frame…</div>}

            {preset && calPoints.map((p, i) => (
              <span className="calpoint" key={i}
                    style={{ left: `${p.x * 100}%`, top: `${p.y * 100}%` }}>{i + 1}</span>
            ))}

            {frame && !preset && boxes.map(b => {
              const track = byTrack[b.trackId]
              const who = track?.assignedTo
              return (
                <button key={b.trackId}
                        className={`tbox ${who ? 'assigned' : ''} ${selected === b.trackId ? 'sel' : ''}`}
                        style={{
                          left: `${b.x * 100}%`, top: `${b.y * 100}%`,
                          width: `${b.w * 100}%`, height: `${b.h * 100}%`,
                        }}
                        title={who ? who.name : `Player ${b.trackId} — click to identify`}
                        onClick={() => { setSelected(b.trackId); setChoice(String(who?.studentId ?? '')) }}>
                  <b>{who ? who.name : `#${b.trackId}`}</b>
                </button>
              )
            })}
          </div>

          {preset && (
            <div className="banner warn" style={{ marginTop: 14, marginBottom: 0 }}>
              <b>{preset.label}</b> — click each corner in order.
              {scrubbing && (
                <div className="field" style={{ margin: '10px 0 0' }}>
                  <label htmlFor="calframe">
                    Frame at {clock(frames[frameAt].t)} — move this until every corner is in view
                  </label>
                  <input id="calframe" type="range" min="0" max={frames.length - 1} step="1"
                         value={frameAt}
                         onChange={e => { setFrameAt(Number(e.target.value)); setCalPoints([]) }} />
                  <p className="muted" style={{ marginTop: 4 }}>
                    The metres are worked out for the camera position in this frame, so they
                    are only right if the camera stayed still for the whole clip.
                  </p>
                </div>
              )}
              <ol className="calsteps">
                {preset.corners.map((corner, i) => (
                  <li key={corner}
                      className={i < calPoints.length ? 'done' : i === calPoints.length ? 'now' : ''}>
                    {corner}
                  </li>
                ))}
              </ol>
              <div className="row" style={{ marginTop: 8 }}>
                <button className="btn sm" onClick={applyCalibration}
                        disabled={calPoints.length < 4 || busy}>
                  {busy ? 'Recalculating…' : 'Apply calibration'}
                </button>
                <button className="linkbtn" onClick={() => setCalPoints([])}
                        disabled={!calPoints.length}>Start over</button>
                <button className="linkbtn" onClick={stopCalibrating}>Cancel</button>
              </div>
            </div>
          )}

          {selected && !preset && (
            <div className="banner" style={{ marginTop: 14, marginBottom: 0 }}>
              <div className="row" style={{ gap: 10 }}>
                <strong>Player #{selected} is</strong>
                <select value={choice} onChange={e => setChoice(e.target.value)}
                        style={{ width: 'auto', minWidth: 190 }} aria-label="Student">
                  <option value="">Choose a student…</option>
                  {students.map(s => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                      {trackOf[s.id] && trackOf[s.id] !== selected ? ` — now #${trackOf[s.id]}, moves here` : ''}
                    </option>
                  ))}
                </select>
                <button className="btn sm" onClick={assign}
                        disabled={!choice || busy || Number(choice) === selectedWho?.studentId}>
                  {busy ? 'Saving…' : 'Identify'}
                </button>
                {selectedWho && (
                  <button className="linkbtn danger" onClick={() => unassign(selected)} disabled={busy}>
                    Not {selectedWho.name} — remove
                  </button>
                )}
                <button className="linkbtn" onClick={() => setSelected(null)}>Cancel</button>
              </div>
            </div>
          )}
        </div>
      )}

      {clip.tracks.length > 0 && (clip.calibrationPresets ?? []).length > 0 && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Pitch calibration</h2>
              <p className="muted">
                Mark out something you know the size of and every number becomes real
                metres and km/h — directly comparable to a GPS report, including distance
                above the international high-speed-running and sprint thresholds. Without
                it the metrics still work, but only against other players in this clip.
              </p>
            </div>
            <span className={`pill ${clip.calibration ? 'good' : 'warn'}`}>
              <i className="dot" />{clip.calibration ? 'Calibrated' : 'Not calibrated'}
            </span>
          </div>

          {clip.calibration ? (
            <div className="row">
              <span className="muted">
                Using <b>{clip.calibration.label || clip.calibration.preset}</b>.
              </span>
              <button className="linkbtn danger" onClick={dropCalibration} disabled={busy}>
                Remove calibration
              </button>
            </div>
          ) : preset ? (
            <p className="muted">Clicking corners on the frame above.</p>
          ) : (
            <>
              <p className="muted" style={{ marginBottom: 8 }}>
                Pick a marking you can see all four corners of — you can move through the
                clip to find a frame where it is fully in view:
              </p>
              <div className="toggles">
                {clip.calibrationPresets.map(p => (
                  <button key={p.key} type="button" onClick={() => startCalibrating(p)}>
                    {p.label}
                  </button>
                ))}
              </div>
            </>
          )}
          {calNote && <div className={`note ${calNote.ok ? 'ok' : 'err'}`}>{calNote.text}</div>}
        </div>
      )}

      {clip.tracks.length > 0 && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>What each player did</h2>
              <p className="muted">
                {clip.calibration
                  ? 'Real metres and km/h, from the pitch markings you set. Per-minute rates only appear for players tracked long enough for the rate to mean anything.'
                  : 'Distance and speed are in body-heights, so they compare across zoom levels. Calibrate above to get metres and km/h.'}
              </p>
            </div>
          </div>

          <div style={{ overflowX: 'auto' }}>
            <table className="data">
              <thead>
                <tr>
                  <th>Player</th>
                  <th className="num">Tracked</th>
                  <th className="num">{clip.calibration ? 'Distance (m)' : 'Distance'}</th>
                  <th className="num">{clip.calibration ? 'Top speed (km/h)' : 'Top speed'}</th>
                  {clip.calibration && <th className="num">Sprint (m)</th>}
                  <th className="num">Active</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {clip.tracks.map(t => (
                  <tr key={t.trackId}>
                    <td>
                      {t.assignedTo
                        ? <span className="pill good"><i className="dot" />{t.assignedTo.name}</span>
                        : <>#{t.trackId}</>}
                    </td>
                    <td className="num">{t.context.trackedSeconds}s</td>
                    <td className="num">
                      {clip.calibration
                        ? (t.context.totalMetres ?? '—')
                        : (t.metrics.matchDistance ?? '—')}
                    </td>
                    <td className="num">
                      {clip.calibration
                        ? (t.metrics.matchTopSpeedKmh ?? '—')
                        : (t.metrics.matchTopSpeed ?? '—')}
                    </td>
                    {clip.calibration && <td className="num">{t.context.sprintMetres ?? '—'}</td>}
                    <td className="num">{t.metrics.matchWorkRate ?? '—'}%</td>
                    <td className="num">
                      {t.assignedTo
                        ? <button className="linkbtn danger" onClick={() => unassign(t.trackId)}>Unlink</button>
                        : <button className="linkbtn" onClick={() => { setSelected(t.trackId); setChoice('') }}>Identify</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </>
  )
}
