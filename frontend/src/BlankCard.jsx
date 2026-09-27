/* The printable card: Parts A to D and the player card, laid out as the Directorate of
   Sports' volleyball hardcopy is, for whichever sport. Players picked in the print
   dialog are already written in; everything else is left for the scorer's pen. */

const ORG = 'SRM Directorate of Sports'
const BOX = on => (on ? '☑' : '☐')
const MARK_SHOW = { '+': '+', '0': '0', '-': '–' }
const name = p => `${p.jersey != null ? `#${p.jersey}  ` : ''}${p.name}`

// the hardcopy leaves room for 14 players; a bigger squad gets two spare rows
const rowsFor = players => [...players.map(name), ...Array(Math.max(14 - players.length, 2)).fill('')]
const chunk = (list, size) => Array.from({ length: Math.ceil(list.length / size) }, (_, i) => list.slice(i * size, i * size + size))

function legend(s) {
  return [...s.marks].map(m => s.legend[{ '+': 0, '0': 1, '-': 2 }[m]] && `${MARK_SHOW[m]} ${s.legend[{ '+': 0, '0': 1, '-': 2 }[m]]}`)
    .filter(Boolean).join('  ·  ')
}

function Sheet({ footer, children }) {
  return (
    <section className="cardsheet">
      {children}
      <footer className="ct-foot">{footer}</footer>
    </section>
  )
}

function Masthead({ cfg, team, part }) {
  return (
    <div className="ct-mast">
      <div className="inst">SRM INSTITUTE OF SCIENCE AND TECHNOLOGY</div>
      <div className="dir">DIRECTORATE OF SPORTS</div>
      <div className="db">{cfg.sport.toUpperCase()} {team.toUpperCase()} TEAM – INDIVIDUAL PLAYERS PERFORMANCE DATABASE</div>
      <div className="part">{part}</div>
    </div>
  )
}

function MatchHeader({ cfg }) {
  const pick = (list, chosen) => list.map(x => (
    <span key={x.key ?? x} className="ct-box">{BOX(chosen === (x.key ?? x))} {x.label ?? x}</span>
  ))
  const extra = [
    ['Team', pick(cfg.categories, cfg.category)],
    ...(cfg.formats.length ? [['Format', pick(cfg.formats, cfg.format)]] : []),
    ...cfg.headerExtra.map(x => [x.label, x.choices ? pick(x.choices, null) : null]),
  ]
  return (
    <table className="ct-head">
      <tbody>
        <tr><th>Tournament</th><td /><th>Round / Stage</th><td /><th>Level</th><td>{pick(cfg.levels, null)}</td></tr>
        <tr><th>Date</th><td /><th>Venue</th><td /><th>Opponent</th><td /></tr>
        <tr>
          <th>Result</th><td>{pick(cfg.results, null)}</td>
          <th>{cfg.score.label}</th>
          <td colSpan={3}>
            {cfg.score.parts.map(p => <span key={p} className="ct-score">{p} ____ – ____</span>)}
          </td>
        </tr>
        <tr><th>Recorded by</th><td /><th>Coach</th><td /><th>Match No.</th><td /></tr>
        <tr>
          {extra.map(([label, value]) => [<th key={`${label}h`}>{label}</th>, <td key={`${label}v`}>{value}</td>])}
          {extra.length < 3 && <td colSpan={2 * (3 - extra.length)} className="ct-none" />}
        </tr>
      </tbody>
    </table>
  )
}

function PartAGrid({ cfg, players }) {
  const fields = cfg.fields.filter(f => f.sheet)
  return (
    <table className="ct-grid">
      <thead>
        <tr>
          <th rowSpan={2} className="ct-name">Player Name</th>
          {cfg.skills.map(s => (
            <th key={s.key} colSpan={s.merged ? 1 : s.marks.length} rowSpan={s.merged ? 2 : 1}
                className={s.merged ? 'ct-merged' : ''}>{s.sheet}<small>{legend(s)}</small></th>
          ))}
          {fields.map(f => <th key={f.key} rowSpan={2} className="ct-field">{f.short}</th>)}
        </tr>
        <tr>
          {cfg.skills.flatMap(s => (s.merged ? []
            : [...s.marks].map(m => <th key={s.key + m} className="ct-mark">{MARK_SHOW[m]}</th>)))}
        </tr>
      </thead>
      <tbody>
        {rowsFor(players).map((who, i) => (
          <tr key={i}>
            <td className="ct-name">{who}</td>
            {cfg.skills.flatMap(s => (s.merged ? [<td key={s.key} />] : [...s.marks].map(m => <td key={s.key + m} />)))}
            {fields.map(f => <td key={f.key} />)}
          </tr>
        ))}
      </tbody>
    </table>
  )
}

function RacketBlock({ cfg, player }) {
  const fields = cfg.fields.filter(f => f.sheet)
  return (
    <>
      <table className="ct-head" style={{ marginTop: 6 }}>
        <tbody>
          <tr><th>Player</th><td>{player ? name(player) : ''}</td><th>Partner (doubles)</th><td /><th>Formation</th><td /></tr>
        </tbody>
      </table>
      <div className="ct-racket">
        <table className="ct-grid">
          <thead><tr><th className="ct-name">Skill</th><th>+</th><th>0</th><th>–</th></tr></thead>
          <tbody>
            {cfg.skills.map(s => (
              <tr key={s.key}>
                <td className="ct-name"><b>{s.sheet}</b><small>{legend(s)}</small></td>
                <td /><td className={s.marks.includes('0') ? '' : 'ct-none'} /><td />
              </tr>
            ))}
          </tbody>
        </table>
        <table className="ct-grid">
          <thead><tr><th className="ct-name">Count</th><th>Total</th><th className="ct-name">Count</th><th>Total</th></tr></thead>
          <tbody>
            {chunk(fields, 2).map(pair => (
              <tr key={pair[0].key}>
                {pair.map(f => [<td key={f.key} className="ct-name">{f.label}</td>, <td key={`${f.key}v`} />])}
                {pair.length === 1 && <td colSpan={2} className="ct-none" />}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}

function PartB({ cfg, team }) {
  const format = cfg.formats.find(f => f.key === cfg.format)?.label
  const [coordWord, coordText] = cfg.coordination.split(' = ')
  return (
    <>
      <div className="ct-part">PART B – SCORING KEY &amp; RECORDING GUIDE</div>
      <p className="ct-sub">Keep this page beside the recorder so that every scorer marks the same action the same way.</p>
      <h3>B1. What counts as + / 0 / –</h3>
      <table className="ct-grid ct-text">
        <thead>
          <tr><th>Skill</th><th>+ (Positive)</th><th>0 (Neutral)</th><th>– (Negative)</th><th>{cfg.b1Head}</th></tr>
        </thead>
        <tbody>
          {cfg.b1.map(s => (
            <tr key={s.key}><td><b>{s.label}</b></td><td>{s.plus}</td><td>{s.zero}</td><td>{s.minus}</td><td>{s.who}</td></tr>
          ))}
        </tbody>
      </table>
      <h3>B2. Post-match calculations (Part C and Part D)</h3>
      <table className="ct-grid ct-text">
        <thead>
          <tr><th>Measure</th><th>Formula</th><th>Worked example</th><th>University target</th><th>Elite target</th></tr>
        </thead>
        <tbody>
          {cfg.b2.map(r => (
            <tr key={r.label}><td><b>{r.label}</b></td><td>{r.formula}</td><td>{r.example}</td><td>{r.uni}</td><td>{r.elite}</td></tr>
          ))}
        </tbody>
      </table>
      <p className="ct-note">
        Targets are Stridian&apos;s suggested starting benchmarks for the {team.toLowerCase()}&apos;s team
        {format ? ` (${format})` : ''}; the worked examples use imaginary numbers. {cfg.b2Note}
      </p>
      <h3>B3. Rating scale for Overall Performance and Coordination (1–5)</h3>
      <table className="ct-grid ct-text">
        <thead><tr>{cfg.rating.map(r => <th key={r.value}>{r.value} – {r.word}</th>)}</tr></thead>
        <tbody><tr>{cfg.rating.map(r => <td key={r.value} style={{ textAlign: 'center' }}>{r.text}</td>)}</tr></tbody>
      </table>
      <p className="ct-note ct-plain"><b>{coordWord}</b> = {coordText}</p>
      <h3>B4. Optional add-ons for Elite-level players</h3>
      <ul className="ct-list">{cfg.b4.map(x => <li key={x}>{x}</li>)}</ul>
    </>
  )
}

function MatchLine() {
  return (
    <div className="ct-line">
      <span>Tournament / Match: <i /></span><span>Opponent: <i /></span>
      <span>Date: <i /></span><span>Match No.: <i className="short" /></span>
    </div>
  )
}

function PartC({ cfg, players }) {
  return (
    <>
      <div className="ct-part">PART C – POST-MATCH PLAYER REVIEW (for the Coach)</div>
      <MatchLine />
      <table className="ct-grid ct-review">
        <thead><tr><th className="ct-name">Player Name</th>{cfg.partC.columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {rowsFor(players).map((who, i) => (
            <tr key={i}><td className="ct-name">{who}</td>{cfg.partC.columns.map(c => <td key={c} />)}</tr>
          ))}
        </tbody>
      </table>
      <h3>{cfg.teamTitle}</h3>
      {chunk(cfg.team, 9).map((labels, i) => (
        <table key={i} className="ct-grid ct-team">
          <thead><tr>{labels.map(l => <th key={l}>{l}</th>)}</tr></thead>
          <tbody><tr>{labels.map(l => <td key={l} />)}</tr></tbody>
        </table>
      ))}
      {cfg.teamNote && <p className="ct-note">{cfg.teamNote}</p>}
    </>
  )
}

function PlayerCard({ cfg }) {
  return (
    <>
      <div className="ct-part">UNIVERSAL PLAYER MATCH CARD</div>
      <MatchLine />
      {cfg.zones.map(z => (
        <div key={z.key} className="ct-zone">
          <div className="ct-zonetitle">{z.title}</div>
          <table className="ct-grid">
            <thead><tr><th className="ct-name">{z.rowhead}</th>{z.cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
            <tbody>
              {[...z.rows, ...(z.total ? ['TOTAL'] : [])].map(r => (
                <tr key={r}><td className="ct-name">{r}</td>{z.cols.map(c => <td key={c} />)}</tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <p className="ct-plain">Coordination rating (coach, after set/match): 1 &nbsp; 2 &nbsp; 3 &nbsp; 4 &nbsp; 5</p>
      <p className="ct-plain"><b>*Note: For all the Attempt, Successful, Error – Mention the Jersey Number of the player</b></p>
    </>
  )
}

function PartD({ cfg, player }) {
  const cols = cfg.partD.columns
  return (
    <>
      <div className="ct-part">PART D – PLAYER PROGRESS TRACKER (one sheet per player, per tournament / season)</div>
      <table className="ct-head">
        <tbody>
          <tr>
            <th>Player Name</th><td>{player?.name ?? ''}</td>
            <th>Jersey No.</th><td>{player?.jersey ?? ''}</td>
            <th>Position</th><td>{player?.position ?? ''}</td>
          </tr>
          <tr>
            <th>Tournament / Season</th><td />
            <th>Level</th><td><span className="ct-box">☐ University</span><span className="ct-box">☐ Elite</span></td>
            <th>Coach</th><td />
          </tr>
        </tbody>
      </table>
      <table className="ct-grid ct-review" style={{ marginTop: 6 }}>
        <thead><tr>{cols.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {Array.from({ length: 12 }, (_, i) => <tr key={i}>{cols.map(c => <td key={c} />)}</tr>)}
          <tr className="ct-total">
            <td colSpan={3}><b>AVERAGE / TOTAL</b></td>
            {cols.slice(3).map(c => <td key={c} />)}
          </tr>
        </tbody>
      </table>
      <p className="ct-note">
        Use the trend column to compare each match with the previous one; review the whole sheet with the
        player at the end of the tournament / season.
      </p>
    </>
  )
}

export default function BlankCard({ cfg, players, parts }) {
  const team = cfg.categories.find(c => c.key === cfg.category)?.label ?? 'Women'
  const footer = `${ORG}  |  ${cfg.sport} ${team} Team – Individual Players Performance Database`
  const racket = cfg.layout === 'player'
  const sheets = []

  if (parts.A) {
    for (const player of racket ? (players.length ? players : [null]) : [null]) {
      sheets.push(
        <Sheet key={`A${player?.id ?? ''}`} footer={footer}>
          <Masthead cfg={cfg} team={team} part="PART A – LIVE MATCH RECORDING SHEET (fill during the match)" />
          <MatchHeader cfg={cfg} />
          {racket ? <RacketBlock cfg={cfg} player={player} /> : <PartAGrid cfg={cfg} players={players} />}
          {cfg.sheetNote && <p className="ct-note">{cfg.sheetNote}</p>}
        </Sheet>,
      )
    }
  }
  if (parts.B) sheets.push(<Sheet key="B" footer={footer}><PartB cfg={cfg} team={team} /></Sheet>)
  if (parts.C) sheets.push(<Sheet key="C" footer={footer}><PartC cfg={cfg} players={players} /></Sheet>)
  if (parts.card) sheets.push(<Sheet key="card" footer={footer}><PlayerCard cfg={cfg} /></Sheet>)
  if (parts.D) {
    for (const player of players.length ? players : [null]) {
      sheets.push(<Sheet key={`D${player?.id ?? ''}`} footer={footer}><PartD cfg={cfg} player={player} /></Sheet>)
    }
  }
  return <div className="cardprint">{sheets}</div>
}
