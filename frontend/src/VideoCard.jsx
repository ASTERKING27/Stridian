import { useEffect, useState } from 'react'
import { ago, api, authedImage, inFlight, statusPill, statusWord } from './api'

/* The thumbnail sits behind the same bearer token as the rest of the API, and an
   <img src> can't carry a header — so fetch it and hand the element a blob URL. */
function Thumb({ videoId }) {
  const [url, setUrl] = useState(null)

  useEffect(() => {
    let revoked = false
    let objectUrl
    authedImage(`/api/videos/${videoId}/thumbnail`)
      .then(u => { if (revoked) URL.revokeObjectURL(u); else { objectUrl = u; setUrl(u) } })
      .catch(() => {})
    return () => { revoked = true; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [videoId])

  if (!url) return null
  return <img src={url} alt="Detected body position at the highest point of the clip" />
}

export default function VideoCard({ video, onDelete }) {
  const m = video.metrics ?? {}
  const values = m.values ?? {}
  const keys = Object.keys(values)
  const rate = m.detectionRate
  const drills = m.drills ?? []
  const sport = m.sportSpecific
  const done = video.status === 'done'

  return (
    <div className="clip">
      <div className="row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ minWidth: 0 }}>
          <b style={{ fontSize: '.92rem' }}>{video.original_name}</b>
          <div className="muted">
            {done ? (
              <>
                {video.duration_sec ? `${video.duration_sec}s · ` : ''}
                pose found in {video.frames_detected ?? 0} of {m.framesSampled ?? '?'} sampled frames
                {rate != null && ` (${Math.round(rate * 100)}%)`}
              </>
            ) : video.message}
          </div>
          {video.video_deleted_at && (
            <div className="muted">Video file removed after 30 days — the results below are kept.</div>
          )}
        </div>
        <div className="row" style={{ gap: 8 }}>
          <span className={`pill ${statusPill(video.status)}`}>
            <i className="dot" />{statusWord(video.status)}
          </span>
          {onDelete && <button type="button" className="linkbtn danger" onClick={onDelete}>Remove</button>}
        </div>
      </div>

      {inFlight(video.status) && (
        <p className="muted" style={{ marginTop: 10 }}>
          The analysis computer picks this up next time it runs; the results appear here by themselves.
        </p>
      )}

      {rate != null && rate < 0.5 && (
        <div className="banner warn" style={{ marginTop: 12, marginBottom: 0 }}>
          Only part of the clip was usable. Film side-on, whole body in frame, steady camera,
          good light, one person visible.
        </div>
      )}

      {keys.length > 0 && (
        <table className="data" style={{ marginTop: 12 }}>
          <thead>
            <tr><th>Measurement</th><th className="num">Value</th></tr>
          </thead>
          <tbody>
            {keys.map(k => (
              <tr key={k}>
                <td title={m.explain?.[k]}>{m.labels?.[k] ?? k}</td>
                <td className="num"><b>{values[k]}</b> <span className="muted">{m.units?.[k]}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {sport?.metrics && Object.keys(sport.metrics).length > 0 && (
        <>
          <h3 style={{ marginTop: 16 }}>{sport.sport} technique</h3>
          <table className="data">
            <tbody>
              {Object.entries(sport.metrics).map(([k, v]) => (
                <tr key={k}>
                  <td>{sport.labels?.[k] ?? k}</td>
                  <td className="num">
                    {typeof v === 'boolean'
                      ? <span className={`pill ${v ? 'good' : 'bad'}`}><i className="dot" />{v ? 'yes' : 'no'}</span>
                      : <><b>{v}</b> <span className="muted">{sport.units?.[k]}</span></>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted" style={{ marginTop: 8 }}>{sport.note}</p>
        </>
      )}

      {drills.length > 0 && (
        <>
          <h3 style={{ marginTop: 16 }}>Training from this clip</h3>
          <ul className="advice">
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
          </ul>
        </>
      )}

      {drills.length === 0 && keys.length > 0 && (
        <p className="muted" style={{ marginTop: 12 }}>
          Nothing in this clip crossed a coaching threshold — movement quality looks fine here.
        </p>
      )}

      {done && video.has_thumbnail && <Thumb videoId={video.id} />}
    </div>
  )
}

// Is the analysis computer on? Asked fresh each time an uploader appears.
export function useWorker() {
  const [worker, setWorker] = useState(null)
  useEffect(() => { api.health().then(h => setWorker(h.worker)).catch(() => {}) }, [])
  return worker
}

export function WorkerNote({ need }) {
  const worker = useWorker()
  if (!worker) return null
  if (!worker.seen) {
    return (
      <div className="banner warn">
        The analysis computer hasn&apos;t connected yet. Uploads are kept safely and analysed
        the first time it runs <code>python worker.py</code>.
      </div>
    )
  }
  if (worker.online && worker[need] === false) {
    return (
      <div className="banner warn">
        The analysis computer ({worker.host}) is on, but it can&apos;t run this kind of
        analysis yet — see the setup notes. Uploads wait until it can.
      </div>
    )
  }
  if (worker.online) return null
  return (
    <div className="banner">
      The analysis computer is off (last seen {ago(worker.secondsAgo)}). Upload anyway —
      clips queue up and are analysed next time it&apos;s switched on.
    </div>
  )
}

export function UploadButton({ file, onPick, onUpload, busy, progress, label, accept = 'video/*' }) {
  return (
    <>
      <div className="row">
        <input type="file" accept={accept} aria-label="Choose a video file"
               onChange={e => onPick(e.target.files?.[0] ?? null)}
               style={{ flex: '1 1 240px', width: 'auto' }} />
        <button type="button" className="btn" onClick={onUpload} disabled={!file || busy}>
          {busy ? `Uploading ${Math.round(progress * 100)}%` : label}
        </button>
      </div>
      {busy && (
        <div className="progress" role="progressbar" aria-valuemin={0} aria-valuemax={100}
             aria-valuenow={Math.round(progress * 100)}>
          <span style={{ width: `${progress * 100}%` }} />
        </div>
      )}
    </>
  )
}

export function VideoUploader({ studentId, onUploaded }) {
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [progress, setProgress] = useState(0)
  const [status, setStatus] = useState(null)

  async function upload() {
    if (!file) return
    setBusy(true)
    setProgress(0)
    setStatus(null)
    try {
      await api.uploadVideo(studentId, file, setProgress)
      setFile(null)
      setStatus({ ok: true, text: 'Uploaded. It is queued for analysis — the result appears below when it is ready.' })
      onUploaded()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <WorkerNote need="pose" />
      <UploadButton file={file} onPick={setFile} onUpload={upload} busy={busy}
                    progress={progress} label="Upload" />
      {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
    </>
  )
}
