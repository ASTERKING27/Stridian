/* Part A of the sport's card — the live recording sheet the scorer fills in and the AI
   reads — as printable HTML, laid out as the website prints it (frontend/BlankCard.jsx).
   `players` are written in; the rest is left for the scorer's pen. Nothing here imports
   the app, so scripts/check.mjs can run it. */

const ORG = 'SRM Directorate of Sports'
const MARK_SHOW = { '+': '+', 0: '0', '-': '–' }
const MARK_AT = { '+': 0, 0: 1, '-': 2 }
const esc = v => String(v ?? '').replace(/[&<>"]/g, ch => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[ch])
const box = on => (on ? '☑' : '☐')
const nameOf = p => `${p.jersey != null ? `#${p.jersey}&nbsp;&nbsp;` : ''}${esc(p.name)}`
// the hardcopy leaves room for 14 players; a bigger squad gets two spare rows
const rowsFor = players => [...players.map(nameOf), ...Array(Math.max(14 - players.length, 2)).fill('')]
const legend = s => [...s.marks].map(m => s.legend[MARK_AT[m]] && `${MARK_SHOW[m]} ${esc(s.legend[MARK_AT[m]])}`).filter(Boolean).join('&nbsp; · &nbsp;')
const pick = (list, chosen) => list.map(x => `<span class="box">${box(chosen != null && chosen === (x.key ?? x))} ${esc(x.label ?? x)}</span>`).join('')

function header(cfg) {
  const extra = [
    ['Team', pick(cfg.categories, cfg.category)],
    ...(cfg.formats.length ? [['Format', pick(cfg.formats, cfg.format)]] : []),
    ...cfg.headerExtra.map(x => [x.label, x.choices ? pick(x.choices, null) : '']),
  ]
  return `<table class="head"><tbody>
    <tr><th>Tournament</th><td></td><th>Round / Stage</th><td></td><th>Level</th><td>${pick(cfg.levels, null)}</td></tr>
    <tr><th>Date</th><td></td><th>Venue</th><td></td><th>Opponent</th><td></td></tr>
    <tr><th>Result</th><td>${pick(cfg.results, null)}</td><th>${esc(cfg.score.label)}</th>
        <td colspan="3">${cfg.score.parts.map(p => `<span class="score">${esc(p)} ____ – ____</span>`).join('')}</td></tr>
    <tr><th>Recorded by</th><td></td><th>Coach</th><td></td><th>Match No.</th><td></td></tr>
    <tr>${extra.map(([label, value]) => `<th>${esc(label)}</th><td>${value}</td>`).join('')}${
      extra.length < 3 ? `<td colspan="${2 * (3 - extra.length)}" class="none"></td>` : ''}</tr>
  </tbody></table>`
}

function grid(cfg, players) {
  const fields = cfg.fields.filter(f => f.sheet)
  const cells = s => (s.merged ? '<td></td>' : [...s.marks].map(() => '<td></td>').join(''))
  return `<table class="grid"><thead>
    <tr><th rowspan="2" class="name">Player Name</th>${cfg.skills.map(s => `<th colspan="${s.merged ? 1 : s.marks.length}" rowspan="${
      s.merged ? 2 : 1}"${s.merged ? ' class="merged"' : ''}>${esc(s.sheet)}<small>${legend(s)}</small></th>`).join('')}${
      fields.map(f => `<th rowspan="2">${esc(f.short)}</th>`).join('')}</tr>
    <tr>${cfg.skills.filter(s => !s.merged).map(s => [...s.marks].map(m => `<th class="mark">${MARK_SHOW[m]}</th>`).join('')).join('')}</tr>
  </thead><tbody>${rowsFor(players).map(who => `<tr><td class="name">${who}</td>${cfg.skills.map(cells).join('')}${
    fields.map(() => '<td></td>').join('')}</tr>`).join('')}</tbody></table>`
}

// racket sports: one player per sheet
function racket(cfg, player) {
  const fields = cfg.fields.filter(f => f.sheet)
  const pairs = Array.from({ length: Math.ceil(fields.length / 2) }, (_, i) => fields.slice(i * 2, i * 2 + 2))
  return `<table class="head" style="margin-top:6px"><tbody>
    <tr><th>Player</th><td>${player ? nameOf(player) : ''}</td><th>Partner (doubles)</th><td></td><th>Formation</th><td></td></tr>
  </tbody></table>
  <div class="racket">
    <table class="grid"><thead><tr><th class="name">Skill</th><th>+</th><th>0</th><th>–</th></tr></thead><tbody>${
      cfg.skills.map(s => `<tr><td class="name"><b>${esc(s.sheet)}</b><small>${legend(s)}</small></td><td></td><td${
        s.marks.includes('0') ? '' : ' class="none"'}></td><td></td></tr>`).join('')}</tbody></table>
    <table class="grid"><thead><tr><th class="name">Count</th><th>Total</th><th class="name">Count</th><th>Total</th></tr></thead><tbody>${
      pairs.map(pair => `<tr>${pair.map(f => `<td class="name">${esc(f.label)}</td><td></td>`).join('')}${
        pair.length === 1 ? '<td colspan="2" class="none"></td>' : ''}</tr>`).join('')}</tbody></table>
  </div>`
}

export function blankCardHtml(cfg, players = []) {
  const team = cfg.categories.find(x => x.key === cfg.category)?.label ?? 'Men'
  const each = cfg.layout === 'player' ? (players.length ? players : [null]) : [null]
  // more players than the hardcopy's 14 rows: full-height rows, running onto a second page
  const long = cfg.layout !== 'player' && players.length > 14
  const sheets = each.map(player => `<section${long ? ' class="long"' : ''}>
    <div class="mast">
      <div class="inst">SRM INSTITUTE OF SCIENCE AND TECHNOLOGY</div>
      <div class="dir">DIRECTORATE OF SPORTS</div>
      <div class="db">${esc(cfg.sport.toUpperCase())} ${esc(team.toUpperCase())} TEAM – INDIVIDUAL PLAYERS PERFORMANCE DATABASE</div>
      <div class="part">PART A – LIVE MATCH RECORDING SHEET (fill during the match)</div>
    </div>
    ${header(cfg)}
    <div class="fill">${cfg.layout === 'player' ? racket(cfg, player) : grid(cfg, players)}</div>
    ${cfg.sheetNote ? `<p class="note">${esc(cfg.sheetNote)}</p>` : ''}
    <footer>${ORG}&nbsp; | &nbsp;${esc(cfg.sport)} ${esc(team)} Team – Individual Players Performance Database</footer>
  </section>`).join('')
  return `<!doctype html><html><head><meta charset="utf-8"><style>
@page { size: A4 landscape; margin: 8mm; }
body { margin: 0; color: #000; font: 8.5pt/1.3 'Times New Roman', Times, serif; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
/* one sheet a page, whatever the phone's fonts: Part A's rows share out what the page has left */
section { height: 190mm; display: flex; flex-direction: column; break-after: page; page-break-after: always; }
.fill { flex: 1; min-height: 0; } .fill > .grid { height: 100%; }
section.long { height: auto; min-height: 190mm; } section.long .fill { flex: none; }
section.long .fill > .grid { height: auto; } section.long .grid td { height: 6.5mm; }
section:last-child { break-after: auto; page-break-after: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { border: 1px solid #000; padding: 2px 4px; vertical-align: middle; }
th { background: #d9d9d9; font-weight: 700; text-align: center; font-size: 8pt; }
.mast { text-align: center; margin-bottom: 4px; line-height: 1.2; }
.inst { font-size: 7.5pt; letter-spacing: .08em; } .dir { font-size: 13pt; font-weight: 700; }
.db, .part { font-size: 10.5pt; font-weight: 700; } .part { margin: 2px 0 6px; }
.head { margin-bottom: 5px; } .head th { width: 11%; text-align: left; } .head td { height: 6.2mm; }
.box { margin-right: 10px; white-space: nowrap; } .score { margin-right: 14px; white-space: nowrap; }
.grid td { height: 4mm; } .grid th small, .grid td.name small { display: block; font-weight: 400; font-size: 6.5pt; }
.grid .name { text-align: left; width: 17%; } .grid .merged { width: 11%; } .grid th.mark { width: 6mm; }
.none { background: #eee; }
.racket { display: grid; grid-template-columns: 1.2fr 1fr; gap: 5mm; align-items: start; } .racket td { height: 9mm; }
.note { font-size: 7.5pt; font-style: italic; margin: 3px 0 5px; }
footer { margin-top: auto; padding-top: 3mm; font-size: 7pt; color: #333; }
</style></head><body>${sheets}</body></html>`
}

/* Who goes on the sheet when the coach prints the names: that team's players with shirt
   numbers, as the website ticks them (or the whole team, if nobody has a number yet) —
   numbers first, in order. A student with no team set goes on either. */
export function printedSquad(students, category) {
  const team = students.filter(s => !s.category || s.category === category)
    .map(s => ({ name: s.name, jersey: s.jersey_number ?? null }))
    .sort((a, b) => (a.jersey == null) - (b.jersey == null) || (a.jersey ?? 0) - (b.jersey ?? 0) || a.name.localeCompare(b.name))
  return team.some(p => p.jersey != null) ? team.filter(p => p.jersey != null) : team
}
