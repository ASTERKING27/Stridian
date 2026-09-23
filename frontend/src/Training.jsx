import { useEffect, useState } from 'react'
import { ago, api, usePoll, utc } from './api'

const pct = v => (v == null ? '—' : `${Math.round(v * 100)}%`)

/* What the model has learned from the coaches, how sure it is, and whether the
   analysis computer, the video queue and the squad sheet are all keeping up. */
export default function Training({ coach }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  // a failed poll keeps the last good data on screen and just says so
  const load = () => api.training().then(d => { setData(d); setError('') }).catch(e => setError(e.message))
  useEffect(() => { load() }, []) // eslint-disable-line react-hooks/exhaustive-deps
  usePoll(true, load, 30000)

  if (!data) return error ? <div className="banner bad">{error}</div> : <div className="skeleton">Loading…</div>

  const { labels, live, worker, queue, sheet, agreement } = data
  const counts = labels.positions.map(p => [p, labels.byPosition[p] ?? 0])
  const most = Math.max(1, ...counts.map(([, n]) => n))
  const liveId = live?.id

  async function rollback(v) {
    if (!confirm(`Put version #${v.id}'s weights back live? The current model stays in the history.`)) return
    setBusy(true)
    try {
      setData(await api.rollback(v.id))
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      {error && <div className="banner warn">Couldn&apos;t refresh just now ({error}) — showing the last update.</div>}
      <div className="pagehead">
        <h1>AI training — {coach.sport}</h1>
        <p className="lede">
          Every student you verify is a lesson: the model looks at what sets the players you
          put in each position apart, and adjusts that position&apos;s weights. A new model only
          goes live if it predicts your verified students better than the current one.
        </p>
      </div>

      <div className="tiles">
        <div className="tile">
          <div className="k">Verified students</div>
          <div className="v">{labels.verified}</div>
          <div className="s">
            {labels.verified >= data.minLabels
              ? `${labels.pending} still pending`
              : `${data.minLabels - labels.verified} more before training starts`}
          </div>
        </div>
        <div className="tile">
          <div className="k">Agrees with you</div>
          <div className="v">{agreement.judged ? pct(agreement.agree / agreement.judged) : '—'}</div>
          <div className="s">
            {agreement.judged ? `${agreement.agree} of ${agreement.judged} verified` : 'nothing verified yet'}
          </div>
        </div>
        <div className="tile">
          <div className="k">Live model</div>
          <div className="v">{live ? `#${live.id}` : 'Default'}</div>
          <div className="s">
            {live?.kind === 'trained' ? `trained on ${live.labels} students`
              : live ? 'weights set by a coach' : 'built-in starting weights'}
          </div>
        </div>
        <div className="tile">
          <div className="k">Analysis computer</div>
          <div className="v" style={{ color: worker.online ? 'var(--good)' : 'var(--ink-3)' }}>
            {worker.online ? 'On' : 'Off'}
          </div>
          <div className="s">
            {worker.seen ? `${worker.host} · ${worker.online && worker.doing !== 'idle' ? worker.doing : `seen ${ago(worker.secondsAgo)}`}`
              : 'has never connected'}
          </div>
        </div>
      </div>

      <div className="grid2">
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Where verified students play</h2>
              <p className="muted">The model can only learn a position it has examples of.</p>
            </div>
          </div>
          {counts.map(([position, n]) => (
            <div className="hbar" key={position}>
              <span>{position}</span>
              <span className="track"><span style={{ width: `${(n / most) * 100}%` }} /></span>
              <b>{n}</b>
            </div>
          ))}
        </div>

        <div className="card">
          <div className="card-head">
            <div>
              <h2>What it has learned</h2>
              <p className="muted">The biggest weight changes the live model made, per position.</p>
            </div>
          </div>
          {data.learned.length === 0 ? (
            <p className="muted">
              {live?.kind === 'trained'
                ? 'The live model barely differs from its starting weights.'
                : 'Nothing yet — the starting weights are in use until a trained model beats them.'}
            </p>
          ) : (
            <ul className="advice">
              {data.learned.map(item => (
                <li key={item.position}>
                  <div className="head">{item.position}</div>
                  <p className="why">
                    {item.changes.map(c => (
                      `${c.label} ${c.to > c.from ? 'up' : 'down'} ${pct(c.from)} → ${pct(c.to)}`
                    )).join(' · ')}
                  </p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Model history</h2>
            <p className="muted">
              Accuracy is measured on students the model did not learn from. Put any
              version back live if you prefer it.
            </p>
          </div>
        </div>
        {data.versions.length === 0 ? (
          <p className="muted">
            No training runs yet. They happen on the analysis computer once
            {` ${data.minLabels}`} students are verified across at least two positions.
          </p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data">
              <thead>
                <tr>
                  <th>#</th><th>When</th><th>What</th><th className="num">Students</th>
                  <th className="num">Accuracy</th><th className="num">Old model</th><th />
                </tr>
              </thead>
              <tbody>
                {data.versions.map(v => (
                  <tr key={v.id} title={v.note ?? ''}>
                    <td>{v.id}</td>
                    <td>{utc(v.createdAt).toLocaleString()}</td>
                    <td>
                      {v.id === liveId
                        ? <span className="pill good"><i className="dot" />Live</span>
                        : v.kind === 'trained' && !v.deployed
                          ? <span className="pill warn"><i className="dot" />Kept out</span>
                          : <span className="pill"><i className="dot" />{v.kind === 'trained' ? 'Trained' : 'Set by coach'}</span>}
                      <div className="muted" style={{ marginTop: 4 }}>{v.note}</div>
                    </td>
                    <td className="num">{v.labels || '—'}</td>
                    <td className="num">{pct(v.accuracy)}</td>
                    <td className="num">{pct(v.liveAccuracy)}</td>
                    <td className="num">
                      {v.id !== liveId && (
                        <button className="linkbtn" disabled={busy} onClick={() => rollback(v)}>
                          Use this
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div className="card">
        <div className="card-head"><div><h2>Pipeline</h2></div></div>
        <table className="data">
          <tbody>
            <tr>
              <td>Videos waiting for analysis</td>
              <td className="num"><b>{queue.videos}</b> drill · <b>{queue.matches}</b> match</td>
            </tr>
            <tr>
              <td>Video storage</td>
              <td className="num">{data.storage === 'drive' ? 'Google Drive (kept 30 days)' : 'This computer'}</td>
            </tr>
            <tr>
              <td>Squad sheet</td>
              <td className="num">
                {!sheet.configured ? 'Not connected'
                  : <a href={sheet.url} target="_blank" rel="noreferrer">Open sheet</a>}
                {sheet.at && (
                  <div className={`muted ${sheet.ok ? '' : 'err'}`}>
                    {sheet.ok ? `synced ${utc(sheet.at).toLocaleString()}` : `last sync failed: ${sheet.error}`}
                  </div>
                )}
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </>
  )
}
