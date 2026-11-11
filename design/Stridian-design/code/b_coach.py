from build import *
ALERT = 'M12 3 2 21h20L12 3ZM12 10v5M12 17.5v.5'
SEARCH = 'M10.5 17a6.5 6.5 0 1 0 0-13 6.5 6.5 0 0 0 0 13ZM15.5 15.5 20 20'

extra_css = """
.rng{-webkit-appearance:none;appearance:none;width:100%;height:28px;background:transparent;margin:0;cursor:pointer}
.rng::-webkit-slider-runnable-track{height:4px;background:linear-gradient(to right,var(--ink) 0 var(--p),var(--line) var(--p) 100%)}
.rng::-moz-range-track{height:4px;background:var(--line)}
.rng::-moz-range-progress{height:4px;background:var(--ink)}
.rng::-webkit-slider-thumb{-webkit-appearance:none;width:18px;height:18px;margin-top:-7px;background:var(--ink);border:3px solid var(--bg);outline:1px solid var(--ink);transform:rotate(45deg)}
.rng::-moz-range-thumb{width:14px;height:14px;background:var(--ink);border:3px solid var(--bg);border-radius:0;transform:rotate(45deg)}
.rng:focus-visible{outline:2px solid var(--ink);outline-offset:4px}
.brk{position:absolute;width:10px;height:10px;border-color:var(--ink);border-style:solid;border-width:0}
.pick{animation:pick .5s cubic-bezier(.2,.8,.2,1)}
@keyframes pick{from{transform:scale(1.35);opacity:0}to{transform:scale(1);opacity:1}}
"""

p7 = phone('07 · RESULT ENTRY · VALIDATION', f'''        <div class="pad" style="gap: 16px">
          {BACK('Squad')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">RECORD RESULTS · 30 SEP 2026</span>
            <h1 class="h1">Coach Entry</h1>
          </div>
          <div style="display: flex; align-items: center; gap: 12px; padding: 10px 12px; border: 1px solid var(--line)">
            <span class="mono" style="width: 36px; height: 36px; background: var(--ink); color: var(--bg); display: flex; align-items: center; justify-content: center; font-size: 12px">AM</span>
            <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 3px"><span style="font-size: 15px; font-weight: 600">Aarav Menon</span><span class="mono" style="font-size: 10px; letter-spacing: .06em; color: var(--ink2)">WINGER · RA2211003010214</span></div>
            <button class="btn3" style="height: 36px">Change</button>
          </div>
          <div role="alert" style="background: var(--ink); color: var(--bg); padding: 12px 14px; display: flex; gap: 12px; align-items: flex-start">
            {icon(ALERT, 20, 1.6)}
            <span style="font-size: 13.5px; line-height: 1.4"><b style="font-weight: 600">2 things to fix</b> before these results can be saved.</span>
          </div>
          <label style="display: flex; flex-direction: column; gap: 7px">
            <span class="eyebrow" style="color: var(--ink)">30M SPRINT · SECONDS</span>
            <input class="fld bad" value="38" aria-invalid="true">
            <span style="display: flex; align-items: center; justify-content: space-between; gap: 10px"><span style="font-size: 12.5px; line-height: 1.35">Between 3.00 and 8.00 s. Did you mean 3.8?</span><button class="opt mono" style="font-size: 10.5px; letter-spacing: .08em; padding: 6px 9px; border: 1px solid var(--ink); flex-shrink: 0">USE 3.8</button></span>
          </label>
          <label style="display: flex; flex-direction: column; gap: 7px">
            <span class="eyebrow">COUNTERMOVEMENT JUMP · CM</span>
            <input class="fld" value="36">
          </label>
          <label style="display: flex; flex-direction: column; gap: 7px">
            <span class="eyebrow" style="color: var(--ink)">AGILITY T-TEST · SECONDS</span>
            <input class="fld bad" value="" placeholder="—" aria-invalid="true">
            <span style="font-size: 12.5px">Needed — or mark it as not tested today.</span>
          </label>
          <label style="display: flex; flex-direction: column; gap: 7px">
            <span class="eyebrow">YO-YO IR1 · LEVEL</span>
            <input class="fld" value="18.9">
          </label>
          <button class="btn" aria-disabled="true" style="opacity: .35; cursor: not-allowed">Save results</button>
        </div>''')

p8 = phone('08 · SQUAD · PENDING / VERIFIED', f'''        <div class="pad" style="gap: 16px">
          <div style="display: flex; align-items: center; justify-content: space-between">
            <div style="display: flex; align-items: center; gap: 9px">
              <svg viewBox="0 0 100 100" width="22" height="22" aria-hidden="true"><path d="{{{{logoD}}}}" style="fill: var(--ink)"></path></svg>
              <span class="wm" style="font-size: 12px">STRIDIAN</span>
            </div>
            <span class="mono" style="font-size: 10.5px; letter-spacing: .1em; color: var(--ink2)">FOOTBALL · COACH</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">21 PLAYERS</span>
            <h1 class="h1">Squad</h1>
          </div>
          <label style="display: flex; align-items: center; gap: 10px; border-bottom: 1px solid var(--ink); padding-bottom: 8px">
            {icon(SEARCH, 18, 1.6)}
            <input aria-label="Search players" placeholder="Name or RA number" style="all: unset; flex-grow: 1; font: 400 15px Archivo, sans-serif; color: var(--ink)">
          </label>
          <div style="display: flex; border: 1px solid var(--ink)">
            <sc-for list="{{{{filters}}}}" as="f" hint-placeholder-count="3">
              <button class="opt" onClick="{{{{f.pick}}}}" aria-pressed="{{{{f.on}}}}" style="flex: 1; height: 40px; display: flex; align-items: center; justify-content: center; gap: 6px; font: 500 11px/1 'IBM Plex Mono', monospace; letter-spacing: .08em; background: {{{{f.bg}}}}; color: {{{{f.fg}}}}">{{{{f.label}}}}</button>
            </sc-for>
          </div>
          <div style="display: flex; flex-direction: column">
            <sc-for list="{{{{players}}}}" as="pl" hint-placeholder-count="6">
              <div style="display: flex; align-items: center; gap: 12px; padding: 11px 0; border-top: 1px solid var(--line)">
                <span class="mono" style="width: 38px; height: 38px; flex-shrink: 0; border: 1px solid var(--ink); display: flex; align-items: center; justify-content: center; font-size: 11.5px">{{{{pl.ini}}}}</span>
                <div style="flex-grow: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px"><span style="font-size: 15px">{{{{pl.name}}}}</span><span class="mono" style="font-size: 10px; letter-spacing: .05em; color: var(--ink2)">{{{{pl.meta}}}}</span></div>
                <span class="mono" style="font-size: 9.5px; letter-spacing: .1em; padding: 5px 7px; white-space: nowrap; border: 1px {{{{pl.bs}}}} var(--ink); background: {{{{pl.bg}}}}; color: {{{{pl.fg}}}}">{{{{pl.status}}}}</span>
              </div>
            </sc-for>
          </div>
        </div>
        <nav aria-label="Sections" style="position: absolute; left: 10px; right: 10px; bottom: 18px; height: 60px; border-radius: 30px; background: var(--glass); backdrop-filter: blur(18px) saturate(1.3); -webkit-backdrop-filter: blur(18px) saturate(1.3); border: 1px solid var(--glassEdge); box-shadow: var(--shadow), inset 0 1px 0 var(--hi); box-sizing: border-box">
          <span style="position: absolute; top: 3px; height: 52px; border-radius: 26px; background: var(--ink); left: {{{{ind.l}}}}px; width: {{{{ind.w}}}}px"></span>
          <sc-for list="{{{{tabs}}}}" as="t" hint-placeholder-count="6">
            <button class="tab" aria-label="{{{{t.label}}}}" aria-current="{{{{t.current}}}}" style="left: {{{{t.l}}}}px; width: {{{{t.w}}}}px; gap: {{{{t.gap}}}}px; color: {{{{t.color}}}}">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true" style="flex-shrink: 0"><path d="{{{{t.icon}}}}"></path></svg>
              <span style="overflow: hidden; white-space: nowrap; max-width: {{{{t.lw}}}}px">{{{{t.short}}}}</span>
            </button>
          </sc-for>
        </nav>''')

p9 = phone('09 · WEIGHT EDITOR', f'''        <div class="pad" style="gap: 16px">
          {BACK('Squad')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">SCORING WEIGHTS · FOOTBALL</span>
            <h1 class="h1">Weights</h1>
          </div>
          <div style="display: flex; flex-wrap: wrap; gap: 6px">
            <sc-for list="{{{{wpos}}}}" as="wp" hint-placeholder-count="6">
              <button class="opt" onClick="{{{{wp.pick}}}}" aria-pressed="{{{{wp.on}}}}" style="height: 34px; padding: 0 11px; font: 500 12px/1 Archivo, sans-serif; border: 1px solid var(--ink); background: {{{{wp.bg}}}}; color: {{{{wp.fg}}}}">{{{{wp.name}}}}</button>
            </sc-for>
          </div>
          <div style="display: flex; flex-direction: column; gap: 14px">
            <sc-for list="{{{{sliders}}}}" as="sl" hint-placeholder-count="5">
              <label style="display: flex; flex-direction: column; gap: 4px">
                <span style="display: flex; justify-content: space-between; font-size: 14.5px"><span>{{{{sl.label}}}}</span><span class="mono" style="font-size: 14px; font-weight: 500">{{{{sl.v}}}}%</span></span>
                <input class="rng" type="range" min="0" max="60" step="5" value="{{{{sl.v}}}}" onChange="{{{{sl.set}}}}" style="--p: {{{{sl.p}}}}%">
              </label>
            </sc-for>
          </div>
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 12px 0; border-top: 1px solid var(--ink)">
            <span class="mono" style="font-size: 11px; letter-spacing: .12em">TOTAL</span>
            <span class="mono" style="font-size: 12px; letter-spacing: .06em; padding: 5px 8px; background: {{{{tot.bg}}}}; color: {{{{tot.fg}}}}; border: 1px solid var(--ink)">{{{{tot.text}}}}</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 6px">
            <button class="btn" aria-disabled="{{{{tot.off}}}}" style="opacity: {{{{tot.op}}}}">Save weights</button>
            <button class="btn3" onClick="{{{{resetW}}}}">Reset to the built-in weights</button>
          </div>
        </div>''')

p10 = phone('10 · TAP A PLAYER TO FOCUS', f'''        <div class="pad" style="gap: 14px">
          {BACK('Match Footage')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">MATCH 14 · SECOND HALF · 45:00</span>
            <h1 class="h1">Who’s who?</h1>
          </div>
          <div style="position: relative; width: 346px; height: 236px; background: #151514; overflow: hidden">
            <svg viewBox="0 0 346 236" width="346" height="236" aria-hidden="true" style="position: absolute; inset: 0">
              <path d="M-20 214 L366 214 M40 40 L306 40 M40 40 L-20 214 M306 40 L366 214 M173 40 L173 214 M150 214 A40 22 0 0 1 196 214" fill="none" stroke="#EEEDE8" stroke-opacity=".28" stroke-width="1.2"></path>
              <ellipse cx="173" cy="118" rx="44" ry="22" fill="none" stroke="#EEEDE8" stroke-opacity=".28" stroke-width="1.2"></ellipse>
            </svg>
            <sc-for list="{{{{tracks}}}}" as="tr" hint-placeholder-count="9">
              <button class="opt" onClick="{{{{tr.pick}}}}" aria-label="Track {{{{tr.id}}}}" aria-pressed="{{{{tr.on}}}}" style="position: absolute; left: {{{{tr.x}}}}px; top: {{{{tr.y}}}}px; width: {{{{tr.w}}}}px; height: {{{{tr.h}}}}px; opacity: {{{{tr.op}}}}">
                <span style="position: absolute; inset: 0; border: 1px {{{{tr.bs}}}} rgba(238,237,232,{{{{tr.ba}}}})"></span>
                <span style="position: absolute; left: 50%; top: 18%; width: 6px; height: 6px; margin-left: -3px; background: #EEEDE8"></span>
                <span style="position: absolute; left: 50%; top: 32%; bottom: 10%; width: 2px; margin-left: -1px; background: #EEEDE8"></span>
                <span class="mono" style="position: absolute; left: 0; top: -15px; font-size: 9px; letter-spacing: .06em; color: #EEEDE8; white-space: nowrap">{{{{tr.tag}}}}</span>
                <sc-if value="{{{{tr.on}}}}" hint-placeholder-val="{{{{false}}}}">
                  <span class="pick" style="position: absolute; inset: -6px">
                    <span class="brk" style="left: 0; top: 0; border-left-width: 2px; border-top-width: 2px; border-color: #EEEDE8"></span>
                    <span class="brk" style="right: 0; top: 0; border-right-width: 2px; border-top-width: 2px; border-color: #EEEDE8"></span>
                    <span class="brk" style="left: 0; bottom: 0; border-left-width: 2px; border-bottom-width: 2px; border-color: #EEEDE8"></span>
                    <span class="brk" style="right: 0; bottom: 0; border-right-width: 2px; border-bottom-width: 2px; border-color: #EEEDE8"></span>
                  </span>
                </sc-if>
              </button>
            </sc-for>
            <span class="mono" style="position: absolute; right: 10px; bottom: 8px; font-size: 9.5px; letter-spacing: .1em; color: #9D9C96">TAP A PLAYER</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 4px">
            <span class="eyebrow">{{{{sel.head}}}}</span>
            <span style="font-size: 17px; font-weight: 600">{{{{sel.title}}}}</span>
          </div>
          <div style="display: flex; flex-direction: column">
            <sc-for list="{{{{roster}}}}" as="rs" hint-placeholder-count="4">
              <button class="opt" onClick="{{{{rs.pick}}}}" aria-pressed="{{{{rs.on}}}}" style="display: flex; align-items: center; gap: 12px; padding: 10px 0; border-top: 1px solid var(--line)">
                <span style="width: 18px; height: 18px; box-sizing: border-box; border: 1px solid var(--ink); display: flex; align-items: center; justify-content: center; transform: rotate(45deg); flex-shrink: 0"><span style="width: 8px; height: 8px; background: {{{{rs.dot}}}}"></span></span>
                <span style="flex-grow: 1; font-size: 15px">{{{{rs.name}}}}</span>
                <span class="mono" style="font-size: 10px; letter-spacing: .06em; color: var(--ink2)">{{{{rs.pos}}}}</span>
              </button>
            </sc-for>
          </div>
          <button class="btn" onClick="{{{{assign}}}}" style="opacity: {{{{assignOp}}}}">{{{{assignLabel}}}}</button>
        </div>''')

script = r"""
const r2 = v => Math.round(v * 100) / 100;
const PLAYERS = [
  ['Aarav Menon', 'RA…0214 · WINGER', 'PENDING'], ['Kabir Rao', 'RA…0187 · CENTRE-BACK', 'VERIFIED'], ['Ishaan Pillai', 'RA…0342 · STRIKER', 'VERIFIED'],
  ['Rohan Das', 'RA…0099 · —', 'NO TEAM'], ['Vivaan Shah', 'RA…0265 · FULL-BACK', 'PENDING'], ['Arjun Nair', 'RA…0311 · GOALKEEPER', 'VERIFIED'],
  ['Dev Iyer', 'RA…0150 · CENTRAL MIDFIELDER', 'PENDING'], ['Neel Bose', 'RA…0228 · WINGER', 'VERIFIED']
];
// built-in weights from backend/sports_config.py (football), in the order below
const METRICS = ['30m Sprint', 'Countermovement jump', 'Agility T-test', 'Yo-Yo IR1', 'Height'];
const BUILT = { 'Goalkeeper': [10, 30, 25, 5, 30], 'Centre-back': [20, 25, 10, 15, 30], 'Full-back': [30, 10, 25, 30, 5], 'Central Midfielder': [20, 10, 25, 40, 5], 'Winger': [40, 10, 30, 15, 5], 'Striker': [30, 25, 20, 10, 15] };
const TRACKS = [[40, 150, 22, 44], [92, 118, 20, 40], [140, 160, 22, 44], [176, 96, 18, 36], [214, 138, 22, 44], [252, 104, 18, 36], [286, 162, 22, 44], [120, 70, 16, 32], [230, 64, 16, 32]];
const ROSTER = [['Aarav Menon', 'WINGER'], ['Neel Bose', 'WINGER'], ['Vivaan Shah', 'FULL-BACK'], ['Dev Iyer', 'MIDFIELD']];
const I = {
  clipboard: 'M9 4h6M9 4a2 2 0 0 0-2 2H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-1a2 2 0 0 0-2-2M8 12h8M8 16h5',
  film: 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6ZM3 10h18M3 15h18M8 4v16M16 4v16',
  card: 'M5 3h10l4 4v14H5V3ZM15 3v4h4M8 11h8M8 15h8M8 19h5', chart: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  sliders: 'M4 6h10M18 6h2M4 12h4M12 12h8M4 18h12M14 4v4M8 10v4M16 16v4',
  cpu: 'M9 3v3M15 3v3M9 18v3M15 18v3M3 9h3M3 15h3M18 9h3M18 15h3M7 6h10a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1ZM10 10h4v4h-4Z'
};
const CTABS = [['Coach Entry', 'Entry', I.clipboard], ['Match Footage', 'Footage', I.film], ['Match Cards', 'Cards', I.card], ['Dashboard', 'Squad', I.chart], ['Weights', 'Weights', I.sliders], ['AI Training', 'AI', I.cpu]];
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', filter: 'all', pos: 'Winger', w: BUILT['Winger'].slice(), track: 3, who: null, named: {} }; }
  renderVals() {
    const st = this.state;
    const counts = { pending: PLAYERS.filter(p => p[2] === 'PENDING').length, verified: PLAYERS.filter(p => p[2] === 'VERIFIED').length };
    const filters = [['pending', 'PENDING · ' + counts.pending], ['verified', 'VERIFIED · ' + counts.verified], ['all', 'ALL']].map(([k, label]) => ({ label, on: st.filter === k,
      bg: st.filter === k ? 'var(--ink)' : 'transparent', fg: st.filter === k ? 'var(--bg)' : 'var(--ink)', pick: () => this.setState({ filter: k }) }));
    const players = PLAYERS.filter(p => st.filter === 'all' || p[2] === st.filter.toUpperCase()).map(([name, meta, status]) => ({
      name, meta, status, ini: name.split(' ').map(s => s[0]).join(''),
      bg: status === 'VERIFIED' ? 'var(--ink)' : 'transparent', fg: status === 'VERIFIED' ? 'var(--bg)' : 'var(--ink)', bs: status === 'NO TEAM' ? 'dashed' : 'solid' }));

    const inner = 360, active = 3, aw = 5 * 7 + 46, iw = (inner - aw) / 5;
    let x = 4;
    const tabs = CTABS.map(([label, short, icon], i) => { const on = i === active, w = on ? aw : iw; const o = { label, short, icon, l: r2(x), w: r2(w), gap: on ? 7 : 0, lw: on ? 110 : 0, color: on ? 'var(--bg)' : 'var(--ink)', current: on ? 'page' : undefined }; x += w; return o; });

    const wpos = Object.keys(BUILT).map(name => ({ name: name === 'Central Midfielder' ? 'Midfielder' : name, on: st.pos === name,
      bg: st.pos === name ? 'var(--ink)' : 'transparent', fg: st.pos === name ? 'var(--bg)' : 'var(--ink)', pick: () => this.setState({ pos: name, w: BUILT[name].slice() }) }));
    const sliders = METRICS.map((label, i) => ({ label, v: st.w[i], p: r2(st.w[i] / 60 * 100),
      set: e => { const w = st.w.slice(); w[i] = Number(e.target.value); this.setState({ w }); } }));
    const total = st.w.reduce((a, b) => a + b, 0);
    const ok = total === 100;
    const tot = { text: ok ? '100% · READY TO SAVE' : total + '% · ' + (total < 100 ? (100 - total) + '% LEFT TO GIVE' : (total - 100) + '% TOO MUCH'),
      bg: ok ? 'transparent' : 'var(--ink)', fg: ok ? 'var(--ink)' : 'var(--bg)', off: !ok, op: ok ? 1 : .35 };

    const tracks = TRACKS.map(([x0, y0, w, h], i) => { const on = st.track === i, id = i + 3; const nm = st.named[i];
      return { id, x: x0, y: y0, w, h, on, op: st.track == null || on ? 1 : .55, bs: nm ? 'solid' : 'dashed', ba: on ? '.9' : '.45',
        tag: nm ? nm.split(' ')[0].toUpperCase() : '#' + id, pick: () => this.setState({ track: i, who: null }) }; });
    const selName = st.track == null ? null : st.named[st.track];
    const sel = st.track == null ? { head: 'NO PLAYER PICKED', title: 'Tap a player in the frame' }
      : { head: 'TRACK #' + (st.track + 3) + ' · 38 MIN IN VIEW', title: selName ? 'This is ' + selName : 'Who is this?' };
    const roster = ROSTER.map(([name, pos]) => ({ name, pos, on: st.who === name, dot: st.who === name || selName === name ? 'var(--ink)' : 'transparent',
      pick: () => this.setState({ who: name }) }));
    const canAssign = st.track != null && st.who;
    return { theme: st.theme, logoD: LOGO_D, filters, players, tabs, ind: { l: tabs[active].l, w: tabs[active].w }, wpos, sliders, tot,
      resetW: () => this.setState({ w: BUILT[st.pos].slice() }),
      tracks, sel, roster, assignOp: canAssign ? 1 : .35, assignLabel: canAssign ? 'Assign to ' + st.who.split(' ')[0] : 'Pick a name',
      assign: () => { if (canAssign) this.setState({ named: { ...st.named, [st.track]: st.who } }); }, THEMES_JS };
  }
}"""
build('Coach.dc.html', 'Stridian coach screens', 1864, 1050, 'COACH · ENTRY, SQUAD, WEIGHTS, FOOTAGE', '\n'.join([p7, p8, p9, p10]), script, extra_css=extra_css)
print('ok')
