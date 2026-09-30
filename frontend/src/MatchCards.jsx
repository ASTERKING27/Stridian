import { useEffect, useMemo, useState } from 'react'
import { api, authedImage, openAuthed, parseValue } from './api'
import Icon from './Icon'
import { shrinkImage } from './people'
import BlankCard from './BlankCard'

const MARK_INDEX = { '+': 0, '0': 1, '-': 2 }
const MARK_SHOW = { '+': '+', '0': '0', '-': '−' }
const TEXT_HEADER = [
  ['tournament', 'Tournament'], ['round', 'Round / Stage'], ['venue', 'Venue'], ['opponent', 'Opponent'],
  ['recorded_by', 'Recorded by'], ['coach', 'Coach'], ['match_no', 'Match No.'],
]

const digits = v => String(v ?? '').replace(/[^0-9]/g, '').slice(0, 3)
const decimal = v => String(v ?? '').replace(/[^0-9.]/g, '').slice(0, 6)
const num = v => (v === '' || v == null ? null : Number(v))
const who = (squad, line) => {
  const s = squad.find(p => p.id === line.student_id)
  return s ? `${s.jersey != null ? `#${s.jersey} ` : ''}${s.name}` : `${line.jersey != null ? `#${line.jersey} ` : ''}${line.name ?? ''}`.trim()
}

/* The sport's match cards: a list, a new card, the editor, and the blank card to print. */
export default function MatchCards({ coach, version, onChanged }) {
  const [list, setList] = useState(null)
  const [openId, setOpenId] = useState(null)
  const [mode, setMode] = useState('list')
  const [error, setError] = useState('')

  const load = () => api.cards().then(setList).catch(e => setError(e.message))
  useEffect(() => { load() }, [version]) // eslint-disable-line react-hooks/exhaustive-deps

  if (openId) {
    return <CardEditor id={openId} onBack={() => { setOpenId(null); load() }} onChanged={onChanged} />
  }
  if (mode === 'print') return <PrintSetup sport={coach.sport} onBack={() => setMode('list')} />

  return (
    <>
      <div className="pagehead">
        <h1>Match cards</h1>
        <p className="lede">
          The {coach.sport} card the scorer fills in during a match. Print it blank with the squad&apos;s
          names and jersey numbers already on it; afterwards, type it in or photograph it here. A finished
          card feeds each player&apos;s report, their position suggestion and the sheets.
        </p>
      </div>

      <div className="card">
        <div className="row">
          <button className="btn" onClick={() => setMode(mode === 'new' ? 'list' : 'new')}>
            <Icon name="plus" size={15} /> New card
          </button>
          <button className="btn sec" onClick={() => setMode('print')}>Print blank card</button>
        </div>
        {mode === 'new' && (
          <NewCard onCancel={() => setMode('list')}
                   onCreated={card => { setMode('list'); setOpenId(card.id) }} />
        )}
      </div>

      {error && <div className="banner bad">{error}</div>}
      {!list ? <div className="skeleton">Loading…</div> : list.length === 0 ? (
        <div className="card empty">
          <b>No cards yet</b>
          Start one after a match, or print a blank card for the scorer first.
        </div>
      ) : (
        <div className="card flush rows">
          {list.map(c => (
            <button key={c.id} className="rowitem" onClick={() => setOpenId(c.id)}>
              <div className="who">
                <b>{c.tournament || 'Untitled match'}{c.opponent ? ` vs ${c.opponent}` : ''}</b>
                <span>
                  {c.date ? new Date(`${c.date}T00:00`).toLocaleDateString() : 'No date'}
                  {c.match_no ? ` · Match ${c.match_no}` : ''}{c.result ? ` · ${c.result}` : ''}
                  {` · ${c.category === 'M' ? 'Men' : 'Women'} · ${c.players} player${c.players === 1 ? '' : 's'}`}
                  {c.photos ? ` · ${c.photos} photo${c.photos === 1 ? '' : 's'}` : ''}
                </span>
              </div>
              <span className={`pill ${c.status === 'final' ? 'good' : 'warn'}`}>
                <i className="dot" />{c.status === 'final' ? 'Finished' : 'Draft'}
              </span>
            </button>
          ))}
        </div>
      )}
    </>
  )
}

/* ------------------------------------------------------------------ new card */

function NewCard({ onCreated, onCancel }) {
  const [cfg, setCfg] = useState(null)
  const [form, setForm] = useState({ category: 'W', format: '', tournament: '', opponent: '',
                                     date: new Date().toISOString().slice(0, 10) })
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { api.cardsConfig().then(setCfg).catch(e => setError(e.message)) }, [])
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }))

  async function create(e) {
    e.preventDefault()
    setBusy(true)
    setError('')
    try {
      onCreated(await api.createCard({
        category: form.category, format: form.format || cfg?.format || null,
        header: { tournament: form.tournament, opponent: form.opponent, date: form.date },
      }))
    } catch (err) {
      setError(err.message)
      setBusy(false)
    }
  }

  return (
    <form onSubmit={create} style={{ marginTop: 16 }}>
      <div className="grid3">
        <div className="field">
          <label>Team</label>
          <div className="seg" style={{ marginBottom: 0 }}>
            {[['W', 'Women'], ['M', 'Men']].map(([k, label]) => (
              <button type="button" key={k} aria-pressed={form.category === k} onClick={() => set('category', k)}>{label}</button>
            ))}
          </div>
        </div>
        {cfg?.formats.length > 0 && (
          <div className="field">
            <label htmlFor="nc-format">Format</label>
            <select id="nc-format" value={form.format || cfg.format} onChange={e => set('format', e.target.value)}>
              {cfg.formats.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
          </div>
        )}
        <div className="field">
          <label htmlFor="nc-date">Date</label>
          <input id="nc-date" type="date" value={form.date} onChange={e => set('date', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="nc-t">Tournament</label>
          <input id="nc-t" maxLength={120} value={form.tournament} onChange={e => set('tournament', e.target.value)} />
        </div>
        <div className="field">
          <label htmlFor="nc-o">Opponent</label>
          <input id="nc-o" maxLength={120} value={form.opponent} onChange={e => set('opponent', e.target.value)} />
        </div>
      </div>
      <div className="row">
        <button className="btn" disabled={busy || !cfg}>{busy ? 'Starting…' : 'Start the card'}</button>
        <button type="button" className="btn sec" onClick={onCancel}>Cancel</button>
      </div>
      {error && <div className="note err">{error}</div>}
    </form>
  )
}

/* ------------------------------------------------------------------- editor */

let nextKey = 1
const blankTally = () => ['', '', '']
const clock = s => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}`

function toDraft(card, cfg) {
  const seconds = new Set([...cfg.fields, ...cfg.teamFields].filter(f => f.kind === 'seconds').map(f => f.key))
  const text = (k, v) => (seconds.has(k) ? clock(v) : String(v))
  const parts = cfg?.score.parts.length ?? 0
  const score = Array.from({ length: parts }, (_, i) => (card.header.score?.[i] ?? [null, null]).map(v => v ?? ''))
  return {
    category: card.category,
    format: card.format ?? '',
    header: { ...card.header, score },
    team: Object.fromEntries(Object.entries(card.team ?? {}).map(([k, v]) => [k, text(k, v)])),
    lines: card.lines.map(l => ({
      key: nextKey++, student_id: l.student_id, jersey: l.jersey, name: l.name, position: l.position ?? '',
      tallies: Object.fromEntries(Object.entries(l.tallies).map(([k, v]) => [k, v.map(String)])),
      fields: Object.fromEntries(Object.entries(l.fields).map(([k, v]) => [k, text(k, v)])),
      zones: l.zones ?? {}, unread: [], coord: l.coord ?? '', overall: l.overall ?? '',
      strength: l.strength ?? '', improve: l.improve ?? '', remarks: l.remarks ?? '',
    })),
  }
}

function toBody(draft, cfg, final) {
  const fieldKind = Object.fromEntries(cfg.fields.map(f => [f.key, f.kind]))
  return {
    category: draft.category,
    format: draft.format || null,
    header: { ...draft.header, score: draft.header.score.map(pair => pair.map(num)) },
    team: Object.fromEntries(Object.entries(draft.team).filter(([, v]) => v !== '')
      .map(([k, v]) => [k, parseValue(v)])),
    lines: draft.lines.map(l => ({
      student_id: l.student_id ?? null, jersey: l.jersey ?? null, name: l.name ?? null,
      position: l.position || null,
      tallies: Object.fromEntries(Object.entries(l.tallies).map(([k, v]) => [k, v.map(x => num(x) ?? 0)])),
      fields: Object.fromEntries(Object.entries(l.fields).filter(([, v]) => v !== '')
        .map(([k, v]) => [k, fieldKind[k] === 'seconds' ? parseValue(v) : num(v)])),
      zones: l.zones, coord: num(l.coord), overall: num(l.overall),
      strength: l.strength || null, improve: l.improve || null, remarks: l.remarks || null,
    })),
    final,
  }
}

function CardEditor({ id, onBack, onChanged }) {
  const [card, setCard] = useState(null)
  const [cfg, setCfg] = useState(null)
  const [draft, setDraft] = useState(null)
  const [saved, setSaved] = useState('')        // the draft as last saved, to spot changes
  const [status, setStatus] = useState(null)
  const [busy, setBusy] = useState('')
  const [zonesOpen, setZonesOpen] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.card(id).then(async c => {
      const conf = await api.cardsConfig(c.category, c.format ?? '')
      const d = toDraft(c, conf)
      setCard(c)
      setCfg(conf)
      setDraft(d)
      setSaved(JSON.stringify(d))
    }).catch(e => setError(e.message))
  }, [id])

  // the targets (and cricket's phases) follow the team and format
  useEffect(() => {
    if (!draft || !cfg || (draft.category === cfg.category && (draft.format || cfg.format) === cfg.format)) return
    api.cardsConfig(draft.category, draft.format).then(setCfg).catch(() => {})
  }, [draft?.category, draft?.format]) // eslint-disable-line react-hooks/exhaustive-deps

  if (error) return <div className="banner bad">{error}</div>
  if (!card || !cfg || !draft) return <div className="skeleton">Opening the card…</div>

  // someone on this card who has since moved sport stays on it
  const squad = [...cfg.squad, ...card.formerPlayers.map(p => ({ ...p, gone: true }))]
  const dirty = JSON.stringify(draft) !== saved
  const update = fn => setDraft(d => fn(structuredClone(d)))
  const setHeader = (k, v) => update(d => { d.header[k] = v; return d })
  const setLine = (key, fn) => update(d => { d.lines = d.lines.map(l => (l.key === key ? fn(l) : l)); return d })
  const onCard = new Set(draft.lines.map(l => l.student_id).filter(Boolean))

  function addPlayers(students) {
    update(d => {
      for (const s of students) {
        d.lines.push({ key: nextKey++, student_id: s.id, jersey: s.jersey, name: s.name,
                       position: cfg.positions.includes(s.position) ? s.position : '',
                       tallies: {}, fields: {}, zones: {}, unread: [], coord: '', overall: '', strength: '',
                       improve: '', remarks: '' })
      }
      return d
    })
  }

  async function save(final) {
    setBusy(final ? 'final' : 'draft')
    setStatus(null)
    try {
      const c = await api.saveCard(id, toBody(draft, cfg, final))
      const d = toDraft(c, cfg)
      setCard(c)
      setDraft(d)
      setSaved(JSON.stringify(d))
      setStatus({ ok: true, text: final ? 'Saved. It now counts towards each player’s report.' : 'Draft saved.' })
      onChanged?.()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy('')
    }
  }

  async function remove() {
    if (!confirm('Delete this card and its photos? This can’t be undone.')) return
    try {
      await api.deleteCard(id)
      onChanged?.()
      onBack()
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    }
  }

  function applyReading(reading, n) {
    const cell = v => (v == null ? '' : String(v))
    const unmatched = reading.players.filter(p => !p.student_id).length
    const unreadable = reading.players.reduce((sum, p) =>
      sum + Object.values(p.tallies).flat().filter(v => v == null).length, 0)
    update(d => {
      for (const [k, v] of Object.entries(reading.header)) {
        if (k === 'score') {
          v.forEach((pair, i) => {
            if (d.header.score[i] && d.header.score[i].every(x => x === '')) d.header.score[i] = pair.map(cell)
          })
        } else if (v != null && !d.header[k]) {
          d.header[k] = v
        }
      }
      if (reading.category && d.lines.length === 0) d.category = reading.category
      for (const p of reading.players) {
        const tallies = Object.fromEntries(Object.entries(p.tallies).map(([k, v]) => [k, v.map(cell)]))
        const unread = Object.entries(p.tallies).flatMap(([k, v]) => v.flatMap((x, i) => (x == null ? [`${k}${i}`] : [])))
        const fields = Object.fromEntries(Object.entries(p.fields).map(([k, v]) => [k, cell(v)]))
        const same = d.lines.find(l => (p.student_id ? l.student_id === p.student_id
                                                      : !l.student_id && l.jersey != null && l.jersey === p.jersey))
        if (same) {
          same.tallies = { ...same.tallies, ...tallies }
          same.fields = { ...same.fields, ...fields }
          same.unread = [...new Set([...same.unread, ...unread])]
        } else {
          const s = squad.find(x => x.id === p.student_id)
          d.lines.push({ key: nextKey++, student_id: p.student_id, jersey: p.jersey ?? s?.jersey ?? null,
                         name: p.name ?? s?.name ?? null,
                         position: cfg.positions.includes(s?.position) ? s.position : '',
                         tallies, fields, zones: {}, unread, coord: '', overall: '', strength: '', improve: '',
                         remarks: '' })
        }
      }
      return d
    })
    setStatus({
      ok: true,
      text: `Read ${reading.players.length} player${reading.players.length === 1 ? '' : 's'} off photo ${n + 1}.` +
            `${unmatched ? ` Pick the student for ${unmatched} row${unmatched === 1 ? '' : 's'}.` : ''}` +
            `${unreadable ? ` ${unreadable} cell${unreadable === 1 ? '' : 's'} couldn’t be read — they’re outlined.` : ''}` +
            ' Check every number against the paper, then save.',
    })
  }

  const sheetFields = cfg.fields.filter(f => f.sheet)
  const reviewFields = cfg.fields.filter(f => !f.sheet)
  const final = card.status === 'final'

  return (
    <>
      <button className="linkbtn" onClick={() => (dirty && !confirm('Leave without saving?') ? null : onBack())}
              style={{ marginBottom: 12 }}>
        <Icon name="back" size={13} /> All cards
      </button>

      <div className="pagehead row" style={{ justifyContent: 'space-between' }}>
        <div>
          <h1>{draft.header.tournament || 'Match card'}{draft.header.opponent ? ` vs ${draft.header.opponent}` : ''}</h1>
          <p className="muted" style={{ margin: 0 }}>
            {cfg.sport} · {draft.category === 'M' ? 'Men' : 'Women'}
            {cfg.formats.length > 0 && ` · ${cfg.formats.find(f => f.key === (draft.format || cfg.format))?.label}`}
            {' · '}<span className={`pill ${final ? 'good' : 'warn'}`}><i className="dot" />{final ? 'Finished' : 'Draft'}</span>
          </p>
        </div>
        <button className="linkbtn danger" onClick={remove}>Delete card</button>
      </div>

      <HeaderForm cfg={cfg} draft={draft} setHeader={setHeader} update={update} />

      <Photos card={card} cfg={cfg} onCard={setCard} onReading={applyReading} setStatus={setStatus} />

      <div className="card">
        <div className="card-head">
          <div>
            <h2>Part A — live match sheet</h2>
            <p className="muted">
              One row per player, the + / 0 / − count for every skill, as on the paper.
              {cfg.layout === 'player' ? ' Racket cards score one player per row.' : ''}
            </p>
          </div>
          <AddPlayers squad={squad} onCard={onCard} onAdd={addPlayers} />
        </div>
        {draft.lines.length === 0 ? (
          <p className="muted">No players yet — add them from the squad, or read a photo of the card.</p>
        ) : (
          <div className="sheetwrap">
            <table className="sheetgrid">
              <thead>
                <tr>
                  <th rowSpan={2} className="stick">Player</th>
                  {cfg.skills.map(s => (
                    <th key={s.key} colSpan={s.marks.length} title={s.label}>
                      {s.sheet}
                      <small>{s.legend.filter(Boolean).join(' · ')}</small>
                    </th>
                  ))}
                  {sheetFields.map(f => <th key={f.key} rowSpan={2} title={f.label}>{f.short}</th>)}
                  <th rowSpan={2}><span className="sr">Remove</span></th>
                </tr>
                <tr>
                  {cfg.skills.flatMap(s => [...s.marks].map(m => <th key={s.key + m} className="mark">{MARK_SHOW[m]}</th>))}
                </tr>
              </thead>
              <tbody>
                {draft.lines.map(l => (
                  <tr key={l.key} className={l.student_id ? '' : 'unmatched'}>
                    <td className="stick">
                      <PlayerPick squad={squad} line={l} onCard={onCard}
                                  onPick={s => setLine(l.key, x => ({ ...x, student_id: s?.id ?? null, jersey: s?.jersey ?? x.jersey,
                                                                      position: x.position || (cfg.positions.includes(s?.position) ? s.position : '') }))} />
                    </td>
                    {cfg.skills.flatMap(s => [...s.marks].map(m => (
                      <td key={s.key + m}>
                        <input className={`cell${l.unread.includes(`${s.key}${MARK_INDEX[m]}`) ? ' unread' : ''}`}
                               inputMode="numeric" aria-label={`${who(squad, l)} ${s.label} ${MARK_SHOW[m]}`}
                               value={(l.tallies[s.key] ?? blankTally())[MARK_INDEX[m]]}
                               onChange={e => setLine(l.key, x => {
                                 const t = [...(x.tallies[s.key] ?? blankTally())]
                                 t[MARK_INDEX[m]] = digits(e.target.value)
                                 return { ...x, tallies: { ...x.tallies, [s.key]: t },
                                          unread: x.unread.filter(u => u !== `${s.key}${MARK_INDEX[m]}`) }
                               })} />
                      </td>
                    )))}
                    {sheetFields.map(f => (
                      <td key={f.key}>
                        <input className={`cell${f.kind === 'seconds' ? ' wide' : ''}`} aria-label={`${who(squad, l)} ${f.label}`}
                               inputMode={f.kind === 'seconds' ? 'text' : 'numeric'}
                               placeholder={f.kind === 'seconds' ? 'm:ss' : ''}
                               value={l.fields[f.key] ?? ''}
                               onChange={e => setLine(l.key, x => ({ ...x, fields: { ...x.fields,
                                 [f.key]: f.kind === 'seconds' ? e.target.value.replace(/[^0-9:]/g, '').slice(0, 6) : digits(e.target.value) } }))} />
                      </td>
                    ))}
                    <td>
                      <button className="linkbtn danger" aria-label={`Remove ${who(squad, l)}`}
                              onClick={() => update(d => { d.lines = d.lines.filter(x => x.key !== l.key); return d })}>✕</button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
        {cfg.sheetNote && <p className="muted" style={{ marginTop: 10 }}>{cfg.sheetNote}</p>}
      </div>

      {draft.lines.length > 0 && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Part C — the coach&apos;s review</h2>
              <p className="muted">Position, the two 1–5 ratings, and a word on each player. The numbers work themselves out.</p>
            </div>
          </div>
          <div className="sheetwrap">
            <table className="data review">
              <thead>
                <tr>
                  <th>Player</th><th>Position</th>
                  {reviewFields.map(f => <th key={f.key}>{f.short}</th>)}
                  <th>Coordination</th><th>Overall</th><th>Key strength</th><th>Area to improve</th><th>Remarks</th>
                </tr>
              </thead>
              <tbody>
                {draft.lines.map(l => (
                  <tr key={l.key}>
                    <td>{who(squad, l) || '—'}</td>
                    <td>
                      <select value={l.position} aria-label={`${who(squad, l)} position`}
                              onChange={e => setLine(l.key, x => ({ ...x, position: e.target.value }))}>
                        <option value="">—</option>
                        {cfg.positions.map(p => <option key={p}>{p}</option>)}
                      </select>
                    </td>
                    {reviewFields.map(f => (
                      <td key={f.key}>
                        <input className="cell" inputMode="numeric" aria-label={`${who(squad, l)} ${f.label}`}
                               value={l.fields[f.key] ?? ''}
                               onChange={e => setLine(l.key, x => ({ ...x, fields: { ...x.fields, [f.key]: digits(e.target.value) } }))} />
                      </td>
                    ))}
                    {['coord', 'overall'].map(k => (
                      <td key={k}>
                        <select value={l[k]} aria-label={`${who(squad, l)} ${k === 'coord' ? 'coordination' : 'overall'}`}
                                onChange={e => setLine(l.key, x => ({ ...x, [k]: e.target.value }))}>
                          <option value="">—</option>
                          {cfg.rating.map(r => <option key={r.value} value={r.value}>{r.value} {r.word}</option>)}
                        </select>
                      </td>
                    ))}
                    {['strength', 'improve', 'remarks'].map(k => (
                      <td key={k}>
                        <input maxLength={300} value={l[k]} aria-label={`${who(squad, l)} ${k}`}
                               onChange={e => setLine(l.key, x => ({ ...x, [k]: e.target.value }))} />
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h3 style={{ marginTop: 18 }}>{cfg.teamTitle}: what the coach adds</h3>
          <div className="teamfields">
            {cfg.teamFields.map(f => (
              <div className="field" key={f.key}>
                <label htmlFor={`tf-${f.key}`}>{f.label}{f.elite ? ' *' : ''}</label>
                <input id={`tf-${f.key}`} inputMode={f.kind === 'count' ? 'numeric' : 'decimal'}
                       placeholder={f.kind === 'seconds' ? 'm:ss' : f.kind === 'percent' ? '%' : ''}
                       value={draft.team[f.key] ?? ''}
                       onChange={e => update(d => {
                         d.team[f.key] = f.kind === 'seconds' ? e.target.value.replace(/[^0-9:]/g, '').slice(0, 6)
                           : f.kind === 'percent' ? decimal(e.target.value) : digits(e.target.value).slice(0, 5)
                         return d
                       })} />
              </div>
            ))}
          </div>
          {cfg.teamNote && <p className="muted">{cfg.teamNote}</p>}
        </div>
      )}

      {draft.lines.length > 0 && cfg.zones.some(z => !z.print_only) && (
        <div className="card">
          <div className="card-head">
            <div>
              <h2>Player card (optional)</h2>
              <p className="muted">
                Attempts, successes and errors by zone — mainly for elite-level players. On paper each cell
                holds jersey numbers; here, type how many each player had.
              </p>
            </div>
          </div>
          <div className="row" style={{ gap: 6 }}>
            {draft.lines.map(l => (
              <button key={l.key} className={`btn sm ${zonesOpen === l.key ? '' : 'sec'}`}
                      onClick={() => setZonesOpen(zonesOpen === l.key ? null : l.key)}>
                {who(squad, l) || 'Player'}{Object.keys(l.zones).length ? ' ✓' : ''}
              </button>
            ))}
          </div>
          {draft.lines.filter(l => l.key === zonesOpen).map(l => (
            <ZoneEditor key={l.key} zones={cfg.zones} value={l.zones}
                        onChange={zones => setLine(l.key, x => ({ ...x, zones }))} />
          ))}
        </div>
      )}

      <div className="card savebar">
        <div className="row">
          <button className="btn" disabled={!!busy} onClick={() => save(true)}>
            {busy === 'final' ? 'Saving…' : final ? 'Save changes' : 'Finish card'}
          </button>
          <button className="btn sec" disabled={!!busy} onClick={() => save(false)}>
            {busy === 'draft' ? 'Saving…' : final ? 'Move back to draft' : 'Save draft'}
          </button>
          {dirty && <span className="muted">Unsaved changes</span>}
        </div>
        <p className="muted" style={{ margin: '8px 0 0' }}>
          {final ? 'This card counts towards the players’ reports and the sheets.'
            : 'A draft counts for nothing yet. Finishing it needs every row matched to a student.'}
        </p>
        {status && <div className={`note ${status.ok ? 'ok' : 'err'}`}>{status.text}</div>}
      </div>

      {card.partC.rows.length > 0 && <PartC part={card.partC} stale={dirty} />}
    </>
  )
}

function HeaderForm({ cfg, draft, setHeader, update }) {
  const h = draft.header
  return (
    <div className="card">
      <div className="card-head"><div><h2>Match details</h2><p className="muted">The header of Part A.</p></div></div>
      <div className="grid3">
        <div className="field">
          <label>Team</label>
          <div className="seg" style={{ marginBottom: 0 }}>
            {cfg.categories.map(c => (
              <button type="button" key={c.key} aria-pressed={draft.category === c.key}
                      onClick={() => update(d => { d.category = c.key; return d })}>{c.label}</button>
            ))}
          </div>
        </div>
        {cfg.formats.length > 0 && (
          <div className="field">
            <label htmlFor="h-format">Format</label>
            <select id="h-format" value={draft.format || cfg.format}
                    onChange={e => update(d => { d.format = e.target.value; return d })}>
              {cfg.formats.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
            </select>
          </div>
        )}
        <div className="field">
          <label htmlFor="h-date">Date</label>
          <input id="h-date" type="date" value={h.date ?? ''} onChange={e => setHeader('date', e.target.value || null)} />
        </div>
        {TEXT_HEADER.map(([k, label]) => (
          <div className="field" key={k}>
            <label htmlFor={`h-${k}`}>{label}</label>
            <input id={`h-${k}`} maxLength={k === 'match_no' ? 20 : 120} value={h[k] ?? ''}
                   onChange={e => setHeader(k, e.target.value)} />
          </div>
        ))}
        <div className="field">
          <label htmlFor="h-level">Level</label>
          <select id="h-level" value={h.level ?? ''} onChange={e => setHeader('level', e.target.value || null)}>
            <option value="">—</option>
            {cfg.levels.map(l => <option key={l}>{l}</option>)}
          </select>
        </div>
        <div className="field">
          <label htmlFor="h-result">Result</label>
          <select id="h-result" value={h.result ?? ''} onChange={e => setHeader('result', e.target.value || null)}>
            <option value="">—</option>
            {cfg.results.map(r => <option key={r}>{r}</option>)}
          </select>
        </div>
        {cfg.headerExtra.map(x => (
          <div className="field" key={x.key}>
            <label htmlFor={`h-${x.key}`}>{x.label}</label>
            {x.choices ? (
              <select id={`h-${x.key}`} value={h[x.key] ?? ''} onChange={e => setHeader(x.key, e.target.value || null)}>
                <option value="">—</option>
                {x.choices.map(c => <option key={c}>{c}</option>)}
              </select>
            ) : (
              <input id={`h-${x.key}`} inputMode="numeric" value={h[x.key] ?? ''}
                     onChange={e => setHeader(x.key, digits(e.target.value) || null)} />
            )}
          </div>
        ))}
      </div>
      <label>{cfg.score.label} <span className="muted">(us – them)</span></label>
      <div className="scorebox">
        {cfg.score.parts.map((part, i) => (
          <span key={part}>
            <b>{part}</b>
            {[0, 1].map(side => (
              <input key={side} className="cell" inputMode="decimal" aria-label={`${part} ${side ? 'them' : 'us'}`}
                     value={h.score[i]?.[side] ?? ''}
                     onChange={e => update(d => { d.header.score[i][side] = decimal(e.target.value); return d })} />
            ))}
          </span>
        ))}
      </div>
    </div>
  )
}

function PlayerPick({ squad, line, onCard, onPick }) {
  const s = squad.find(p => p.id === line.student_id)
  return (
    <select value={line.student_id ?? ''} className={line.student_id ? '' : 'needs'}
            aria-label={line.student_id ? `Player: ${s?.name}` : `Who is ${line.jersey != null ? `#${line.jersey} ` : ''}${line.name ?? ''}?`}
            onChange={e => onPick(squad.find(p => p.id === Number(e.target.value)) ?? null)}>
      {!line.student_id && (
        <option value="">
          {`Who is ${line.jersey != null ? `#${line.jersey}` : ''}${line.name ? ` ${line.name}` : ''}?`}
        </option>
      )}
      {squad.filter(p => !p.gone || p.id === line.student_id).map(p => (
        <option key={p.id} value={p.id} disabled={p.id !== line.student_id && onCard.has(p.id)}>
          {p.jersey != null ? `#${p.jersey} ` : ''}{p.name}{p.gone ? ' (now in another sport)' : ''}
        </option>
      ))}
    </select>
  )
}

function AddPlayers({ squad, onCard, onAdd }) {
  const left = squad.filter(p => !onCard.has(p.id))
  if (left.length === 0) return null
  return (
    <div className="row">
      <select aria-label="Add a player" value="" onChange={e => onAdd(left.filter(p => p.id === Number(e.target.value)))}>
        <option value="">Add a player…</option>
        {left.map(p => <option key={p.id} value={p.id}>{p.jersey != null ? `#${p.jersey} ` : ''}{p.name}</option>)}
      </select>
      <button className="btn sec sm" onClick={() => onAdd(left.filter(p => p.jersey != null).length
        ? left.filter(p => p.jersey != null) : left)}>
        Add everyone{left.some(p => p.jersey != null) ? ' with a jersey number' : ''}
      </button>
    </div>
  )
}

function ZoneEditor({ zones, value, onChange }) {
  const set = (zone, r, c, v) => {
    const grid = value[zone.key]?.map(row => [...row]) ?? zone.rows.map(() => zone.cols.map(() => 0))
    grid[r][c] = Number(digits(v) || 0)
    onChange({ ...value, [zone.key]: grid })
  }
  return (
    <div style={{ marginTop: 14 }}>
      {zones.filter(z => !z.print_only).map(z => (
        <div key={z.key} className="sheetwrap" style={{ marginBottom: 12 }}>
          <h3>{z.title}</h3>
          <table className="data zonegrid">
            <thead><tr><th>{z.rowhead}</th>{z.cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>
              {z.rows.map((row, r) => (
                <tr key={row}>
                  <td>{row}</td>
                  {z.cols.map((col, c) => (
                    <td key={col}>
                      <input className="cell" inputMode="numeric" aria-label={`${z.title} ${row} ${col}`}
                             value={value[z.key]?.[r]?.[c] || ''} onChange={e => set(z, r, c, e.target.value)} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
    </div>
  )
}

const isNum = cell => /^[-+]?[\d.:%—]+$/.test(cell)

function PartC({ part, stale }) {
  // a column of numbers (blanks allowed) is right-aligned, heading included, so the
  // heading sits over its numbers
  const numeric = part.columns.map((_, j) => part.rows.some(r => isNum(r[j])) && part.rows.every(r => !r[j] || isNum(r[j])))
  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>Part C — worked out</h2>
          <p className="muted">{stale ? 'As of the last save — save to update it.' : 'From the last save.'}</p>
        </div>
      </div>
      <div className="sheetwrap">
        <table className="data">
          <thead><tr>{part.columns.map((c, j) => <th key={c} className={numeric[j] ? 'num' : undefined}>{c}</th>)}</tr></thead>
          <tbody>
            {part.rows.map((row, i) => (
              <tr key={i}>{row.map((cell, j) => <td key={j} className={numeric[j] ? 'num' : undefined}>{cell}</td>)}</tr>
            ))}
          </tbody>
        </table>
      </div>
      <h3 style={{ marginTop: 16 }}>{part.teamTitle}</h3>
      <div className="tiles">
        {part.team.map(t => (
          <div className="tile" key={t.key}>
            <div className="k">{t.label}</div>
            <div className={t.value.length > 12 ? 's' : 'v'}>{t.value}</div>
          </div>
        ))}
      </div>
      {part.teamNote && <p className="muted">{part.teamNote}</p>}
    </div>
  )
}

/* ------------------------------------------------------------------- photos */

function Thumb({ cardId, photo }) {
  const [src, setSrc] = useState(null)
  useEffect(() => {
    if (photo.mime === 'application/pdf') return undefined
    let live = true
    let made = null
    authedImage(`/api/cards/${cardId}/photos/${photo.n}?v=${photo.v}`)
      .then(u => { made = u; if (live) setSrc(u); else URL.revokeObjectURL(u) })
      .catch(() => {})
    return () => { live = false; if (made) URL.revokeObjectURL(made) }
  }, [cardId, photo.n, photo.v, photo.mime])
  return photo.mime === 'application/pdf'
    ? <span className="thumb pdf">PDF</span>
    : src ? <img className="thumb" src={src} alt={`Photo ${photo.n + 1} of the card`} /> : <span className="thumb" />
}

function Photos({ card, cfg, onCard, onReading, setStatus }) {
  const [busy, setBusy] = useState('')
  const photos = card.photos

  async function add(e) {
    const file = e.target.files?.[0]
    e.target.value = ''
    if (!file) return
    const pdf = file.type === 'application/pdf' || /\.pdf$/i.test(file.name)
    if (pdf && file.size > 4 * 1024 * 1024) {
      setStatus({ ok: false, text: 'That PDF is over 4 MB — take a photo of the card instead.' })
      return
    }
    setBusy('upload')
    try {
      // big enough for the AI to read the smallest tally mark, small enough to upload fast
      onCard(await api.addCardPhoto(card.id, pdf ? file : await shrinkImage(file, 2400, 0.85)))
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy('')
    }
  }

  async function read(p) {
    setBusy(`read${p.n}`)
    setStatus(null)
    try {
      onReading(await api.readCardPhoto(card.id, p.n, p.v), p.n)
      onCard(c => ({ ...c, photos: c.photos.map(x => (x.v === p.v ? { ...x, read: true } : x)) }))
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    } finally {
      setBusy('')
    }
  }

  async function remove(p) {
    if (!confirm('Delete this photo?')) return
    try {
      onCard(await api.deleteCardPhoto(card.id, p.n, p.v))
    } catch (err) {
      setStatus({ ok: false, text: err.message })
    }
  }

  return (
    <div className="card">
      <div className="card-head">
        <div>
          <h2>Photos of the card</h2>
          <p className="muted">
            {cfg.aiOn ? 'Photograph Part A flat and in good light; the AI reads the header and every row, and you check it before saving.'
              : 'Kept with the card for reference. (Reading photos needs the AI switched on — type the card in below.)'}
          </p>
        </div>
        {photos.length < 4 && (
          <label className={`btn sec sm${busy ? ' disabled' : ''}`} style={{ margin: 0 }}>
            {busy === 'upload' ? 'Uploading…' : 'Add a photo'}
            <input type="file" accept="image/*,application/pdf" hidden disabled={!!busy} onChange={add} />
          </label>
        )}
      </div>
      {photos.length === 0 ? <p className="muted">None yet.</p> : (
        <div className="thumbs">
          {photos.map(p => (
            <div key={p.v} className="thumbbox">
              <Thumb cardId={card.id} photo={p} />
              <div className="row" style={{ gap: 10 }}>
                {cfg.aiOn && (
                  <button className="linkbtn" disabled={!!busy} onClick={() => read(p)}>
                    {busy === `read${p.n}` ? 'Reading…' : p.read ? 'Read again' : 'Read with AI'}
                  </button>
                )}
                <button className="linkbtn" onClick={() => openAuthed(`/api/cards/${card.id}/photos/${p.n}?v=${p.v}`)
                  .catch(err => setStatus({ ok: false, text: err.message }))}>Open</button>
                <button className="linkbtn danger" disabled={!!busy} onClick={() => remove(p)}>Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* --------------------------------------------------------------- blank card */

function PrintSetup({ sport, onBack }) {
  const [category, setCategory] = useState('W')
  const [format, setFormat] = useState('')
  const [cfg, setCfg] = useState(null)
  const [picked, setPicked] = useState(null)
  const [parts, setParts] = useState({ A: true, B: true, C: true, card: true, D: true })
  const [error, setError] = useState('')

  useEffect(() => {
    api.cardsConfig(category, format).then(c => {
      setCfg(c)
      // a racket card is one player's: nobody is ticked until the coach picks
      setPicked(p => p ?? new Set(c.layout === 'player' ? [] : c.squad.filter(s => s.jersey != null).map(s => s.id)))
    }).catch(e => setError(e.message))
  }, [category, format])

  const players = useMemo(() => (cfg && picked ? cfg.squad.filter(s => picked.has(s.id)) : []), [cfg, picked])
  if (error) return <div className="banner bad">{error}</div>
  if (!cfg || !picked) return <div className="skeleton">Loading the card…</div>
  const toggle = id => setPicked(p => { const n = new Set(p); if (n.has(id)) n.delete(id); else n.add(id); return n })

  return (
    <>
      <div className="noprint">
        <button className="linkbtn" onClick={onBack} style={{ marginBottom: 12 }}><Icon name="back" size={13} /> All cards</button>
        <div className="pagehead">
          <h1>Print a blank card</h1>
          <p className="lede">
            Parts A to D and the player card, with the players you tick already on it. Part D prints one
            page per player. Print it on A4, landscape.
          </p>
        </div>
        <div className="card">
          <div className="grid3">
            <div className="field">
              <label>Team</label>
              <div className="seg" style={{ marginBottom: 0 }}>
                {cfg.categories.map(c => (
                  <button key={c.key} aria-pressed={category === c.key} onClick={() => setCategory(c.key)}>{c.label}</button>
                ))}
              </div>
            </div>
            {cfg.formats.length > 0 && (
              <div className="field">
                <label htmlFor="p-format">Format</label>
                <select id="p-format" value={format || cfg.format} onChange={e => setFormat(e.target.value)}>
                  {cfg.formats.map(f => <option key={f.key} value={f.key}>{f.label}</option>)}
                </select>
              </div>
            )}
          </div>
          <h3>Pages</h3>
          <div className="toggles" style={{ marginBottom: 14 }}>
            {[['A', 'Part A'], ['B', 'Part B'], ['C', 'Part C'], ['card', 'Player card'], ['D', 'Part D']].map(([k, label]) => (
              <button key={k} aria-pressed={parts[k]} onClick={() => setParts(p => ({ ...p, [k]: !p[k] }))}>{label}</button>
            ))}
          </div>
          <h3>Players on the card</h3>
          {cfg.squad.length === 0 ? <p className="muted">Nobody in the squad yet — the card prints with blank rows.</p> : (
            <div className="toggles" style={{ marginBottom: 14 }}>
              {cfg.squad.map(s => (
                <button key={s.id} aria-pressed={picked.has(s.id)} onClick={() => toggle(s.id)}>
                  {s.jersey != null ? `#${s.jersey} ` : ''}{s.name}
                </button>
              ))}
            </div>
          )}
          {cfg.squad.some(s => s.jersey == null) && (
            <p className="muted">Players without a jersey number print without one — set it on their Profile tab.</p>
          )}
          <button className="btn" onClick={() => window.print()}>Print</button>
        </div>
      </div>
      <div className="cardpreview">
        <BlankCard cfg={cfg} players={players} parts={parts} />
      </div>
    </>
  )
}
