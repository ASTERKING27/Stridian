from build import *
from icons import UI
U = dict(UI)
TILE = 'M19 0H72V64L53 80H0V16Z'

extra_css = """
.lap{animation:lap 1s linear infinite}
@keyframes lap{to{stroke-dashoffset:-100}}
.draw{stroke-dasharray:30;stroke-dashoffset:30;animation:draw 4s cubic-bezier(.5,0,.2,1) infinite}
@keyframes draw{0%{stroke-dashoffset:30}18%,100%{stroke-dashoffset:0}}
.b{all:unset;box-sizing:border-box;height:46px;display:flex;align-items:center;justify-content:center;gap:8px;font:600 14px/1 Archivo,'Helvetica Neue',sans-serif;cursor:pointer;position:relative;transition:transform .08s}
.b:focus-visible{outline:2px solid var(--ink);outline-offset:3px}
.b.p{background:var(--ink);color:var(--bg)}
.b.p.pr,.b.p:active{box-shadow:inset 0 0 0 2px var(--ink),inset 0 0 0 4px var(--bg);transform:scale(.97)}
.b.s{border:1px solid var(--ink);color:var(--ink)}
.b.s.pr,.b.s:active{background:var(--ink);color:var(--bg);transform:scale(.97)}
.b.t{color:var(--ink);padding:0 10px}
.b.t.pr,.b.t:active{background:var(--soft);text-decoration:underline;text-underline-offset:4px}
.b.i{width:46px;border:1px solid var(--ink);color:var(--ink)}
.b.i.pr,.b.i:active{background:var(--ink);color:var(--bg);transform:scale(.94)}
.b.off{cursor:not-allowed;transform:none;box-shadow:none}
.b.p.off{background:repeating-linear-gradient(135deg,var(--line) 0 1px,transparent 1px 6px);border:1px dashed var(--ink2);color:var(--ink2)}
.b.s.off,.b.i.off{border:1px dashed var(--ink2);color:var(--ink2);background:transparent}
.b.t.off{color:var(--ink2)}
.cell{display:flex;flex-direction:column;gap:8px}
.tag{font:500 9.5px/1 'IBM Plex Mono',monospace;letter-spacing:.1em;color:var(--ink2)}
"""

def lap(color, size=18):
    return f'<svg viewBox="-4 -4 108 108" width="{size}" height="{size}" aria-hidden="true"><path d="{LOGO_D}" pathLength="100" class="lap" fill="none" stroke-width="8" stroke-linejoin="miter" stroke-miterlimit="12" style="stroke: {color}; stroke-dasharray: 26 74"></path></svg>'

CHECK = icon(U['Check'], 18, 2)
rows = [
  ('PRIMARY', lambda st: {'default': '<button class="b p" style="width: 100%">Save results</button>',
                         'pressed': '<button class="b p pr" style="width: 100%">Save results</button>',
                         'disabled': '<button class="b p off" aria-disabled="true" style="width: 100%">Save results</button>',
                         'loading': f'<button class="b p" aria-busy="true" style="width: 100%">{lap("var(--bg)")}Saving</button>'}),
  ('SECONDARY', lambda st: {'default': '<button class="b s" style="width: 100%">Cancel upload</button>',
                           'pressed': '<button class="b s pr" style="width: 100%">Cancel upload</button>',
                           'disabled': '<button class="b s off" aria-disabled="true" style="width: 100%">Cancel upload</button>',
                           'loading': '<button class="b s" aria-busy="true" style="width: 100%; overflow: hidden">Uploading 42%<span style="position: absolute; left: 0; bottom: 0; height: 3px; width: 42%; background: var(--ink)"></span></button>'}),
  ('TEXT', lambda st: {'default': '<button class="b t">Make a new code</button>',
                      'pressed': '<button class="b t pr">Make a new code</button>',
                      'disabled': '<button class="b t off" aria-disabled="true">Make a new code</button>',
                      'loading': '<button class="b t" aria-busy="true">Sending<span class="blink">…</span></button>'}),
  ('ICON', lambda st: {'default': f'<button class="b i" aria-label="Add">{icon(U["Add"], 20, 1.8)}</button>',
                      'pressed': f'<button class="b i pr" aria-label="Add">{icon(U["Add"], 20, 1.8)}</button>',
                      'disabled': f'<button class="b i off" aria-label="Add" aria-disabled="true">{icon(U["Add"], 20, 1.8)}</button>',
                      'loading': f'<button class="b i" aria-label="Adding" aria-busy="true">{lap("var(--ink)")}</button>'}),
]
matrix = '<div style="display: grid; grid-template-columns: 96px repeat(4, minmax(0, 1fr)); column-gap: 14px; row-gap: 16px; align-items: center">'
matrix += '<span></span>' + ''.join(f'<span class="tag">{h}</span>' for h in ['DEFAULT', 'PRESSED', 'DISABLED', 'LOADING'])
for name, f in rows:
    d = f(None)
    matrix += f'<span class="tag" style="color: var(--ink)">{name}</span>' + ''.join(f'<div>{d[k]}</div>' for k in ['default', 'pressed', 'disabled', 'loading'])
matrix += '</div>'

rules = ''.join(f'<div style="display: flex; gap: 12px; padding: 9px 0; border-top: 1px solid var(--line)"><span class="tag" style="width: 80px; flex-shrink: 0; padding-top: 2px; color: var(--ink)">{a}</span><span style="font-size: 13px; line-height: 1.4">{b}</span></div>' for a, b in [
  ('PRESSED', 'Shrinks 3% and shows an inner paper ring — outlined buttons fill with ink. Instant: no delay on touch.'),
  ('DISABLED', 'Hatched fill and dashed edge, never just faded — it still reads on e-ink and to colour-blind eyes. Says why nearby.'),
  ('LOADING', 'The logo’s lap loader replaces the icon. The label says what is happening, and the button keeps its size.')])

sheet = f'''    <section style="width: 820px; flex-shrink: 0; background: var(--bg); color: var(--ink); padding: 28px 30px; box-sizing: border-box; display: flex; flex-direction: column; gap: 22px; height: 950px">
      <div style="display: flex; flex-direction: column; gap: 8px"><span class="eyebrow">FEEDBACK · BUTTON STATES</span><span class="h1">Every button, every state</span></div>
      {matrix}
      <div style="display: flex; flex-direction: column">{rules}</div>
      <div style="display: flex; flex-direction: column; gap: 10px">
        <span class="eyebrow">TRY IT · PRESS AND HOLD</span>
        <div style="display: flex; gap: 12px; align-items: center"><button class="b p" style="width: 180px">Save results</button><button class="b s" style="width: 180px">Cancel</button><button class="b t">Text action</button><button class="b i" aria-label="Add">{icon(U["Add"], 20, 1.8)}</button></div>
      </div>
      <div style="display: flex; flex-direction: column; gap: 12px">
        <span class="eyebrow">SUCCESS · FOUR SIZES</span>
        <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px">
          <div class="cell"><span class="tag">TOAST · 3 S, WITH UNDO</span>
            <div role="status" style="position: relative; background: var(--ink); color: var(--bg); padding: 13px 14px; display: flex; align-items: center; gap: 12px; overflow: hidden">{CHECK}<span style="flex-grow: 1; font-size: 14px">Aarav verified · Winger</span><span class="mono" style="font-size: 10.5px; letter-spacing: .12em; text-decoration: underline; text-underline-offset: 3px">UNDO</span><span style="position: absolute; left: 0; bottom: 0; height: 2px; width: 64%; background: var(--bg)"></span></div></div>
          <div class="cell"><span class="tag">BUTTON · BECOMES THE CONFIRMATION</span><button class="b p" style="width: 100%">{CHECK}Saved</button></div>
          <div class="cell"><span class="tag">INLINE · NEXT TO WHAT CHANGED</span>
            <div style="display: flex; flex-direction: column; gap: 6px"><span style="display: flex; justify-content: space-between"><span class="eyebrow">MOBILE</span><span class="mono" style="font-size: 10px; letter-spacing: .1em; display: flex; align-items: center; gap: 4px">{icon(U["Check"], 12, 2.2)}SAVED</span></span><span style="font-size: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--ink)">98765 43210</span></div></div>
          <div class="cell"><span class="tag">CHIP · ON A LIST ROW</span><div style="display: flex; align-items: center; gap: 12px; padding: 8px 0; border-top: 1px solid var(--line); border-bottom: 1px solid var(--line)"><span style="flex-grow: 1; font-size: 15px">State championship</span><span class="mono" style="font-size: 9.5px; letter-spacing: .1em; padding: 5px 7px; background: var(--ink); color: var(--bg); display: flex; align-items: center; gap: 5px">{icon(U["Check"], 11, 2.4)}VERIFIED</span></div></div>
        </div>
      </div>
    </section>'''

pA = phone('LIVE · SAVE → CONFIRM', f'''        <div class="pad" style="gap: 18px">
          {BACK('Squad')}
          <div style="display: flex; flex-direction: column; gap: 8px"><span class="eyebrow">RECORD RESULTS · AARAV MENON</span><h1 class="h1">Coach Entry</h1></div>
          <sc-for list="{{{{fields}}}}" as="f" hint-placeholder-count="4">
            <label style="display: flex; flex-direction: column; gap: 7px">
              <span style="display: flex; justify-content: space-between"><span class="eyebrow">{{{{f.label}}}}</span><span class="mono" style="font-size: 10px; letter-spacing: .1em; display: flex; align-items: center; gap: 4px; opacity: {{{{f.o}}}}">{icon(U["Check"], 12, 2.2)}SAVED</span></span>
              <input class="fld" value="{{{{f.v}}}}">
            </label>
          </sc-for>
          <div style="margin-top: auto; padding-bottom: 34px">
            <button class="b p {{{{btn.cls}}}}" aria-busy="{{{{btn.busy}}}}" style="width: 100%; height: 52px; font-size: 15px">
              <sc-if value="{{{{btn.loading}}}}" hint-placeholder-val="{{{{false}}}}">{lap("var(--bg)")}</sc-if>
              <sc-if value="{{{{btn.done}}}}" hint-placeholder-val="{{{{false}}}}"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M5 12.5 10 17 19 7" pathLength="30" style="stroke-dasharray: 30; stroke-dashoffset: {{{{btn.dash}}}}"></path></svg></sc-if>
              {{{{btn.label}}}}
            </button>
          </div>
        </div>
        <div role="status" style="position: absolute; left: 12px; right: 12px; top: 52px; background: var(--ink); color: var(--bg); padding: 14px 16px; display: flex; align-items: center; gap: 12px; overflow: hidden; transform: translateY({{{{toast.y}}}}px)">
          {CHECK}
          <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 3px"><span style="font-size: 14.5px; font-weight: 600">Results saved</span><span class="mono" style="font-size: 10px; letter-spacing: .06em; opacity: .75">4 MEASURES · AARAV MENON</span></div>
          <span class="mono" style="font-size: 10.5px; letter-spacing: .12em; text-decoration: underline; text-underline-offset: 3px">UNDO</span>
          <span style="position: absolute; left: 0; bottom: 0; height: 2px; background: var(--bg); width: {{{{toast.w}}}}%"></span>
        </div>''')

pB = phone('SUCCESS SCREEN · BIG MOMENTS', f'''        <div class="pad" style="gap: 22px; padding-bottom: 34px">
          <button class="back" aria-label="Close">{icon(U["Close"], 20)}Close</button>
          <div style="position: relative; height: 180px; display: flex; align-items: center">
            <div style="position: relative; width: 140px; height: 156px">
              <svg viewBox="-1 -1 74 82" width="140" height="156" aria-hidden="true"><path d="{TILE}" style="fill: var(--ink)"></path></svg>
              <svg viewBox="0 0 24 24" width="70" height="70" aria-hidden="true" style="position: absolute; left: 35px; top: 43px"><path class="draw" d="M5 12.5 10 17 19 7" pathLength="30" fill="none" stroke-width="2" stroke-linecap="butt" stroke-linejoin="miter" style="stroke: var(--bg)"></path></svg>
            </div>
            <span class="sweep" style="left: 170px; top: 50px; width: 130px; height: 9px"></span>
            <span class="sweep" style="left: 200px; top: 86px; width: 96px; height: 7px; opacity: .6"></span>
            <span class="sweep" style="left: 230px; top: 122px; width: 60px; height: 5px; opacity: .3"></span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px"><span class="eyebrow">VERIFIED</span><h1 class="h1">Aarav is in the squad</h1><span style="font-size: 15px; line-height: 1.45; color: var(--ink2)">He can now see his full report. His position is confirmed as Winger.</span></div>
          <div style="display: flex; flex-direction: column">
            <div style="display: flex; justify-content: space-between; padding: 11px 0; border-top: 1px solid var(--line)"><span style="font-size: 14px">Position</span><span class="mono" style="font-size: 13px">WINGER</span></div>
            <div style="display: flex; justify-content: space-between; padding: 11px 0; border-top: 1px solid var(--line)"><span style="font-size: 14px">Still to verify</span><span class="mono" style="font-size: 13px">2 PLAYERS</span></div>
          </div>
          <div style="margin-top: auto; display: flex; flex-direction: column; gap: 10px">
            <button class="b p" style="width: 100%; height: 52px; font-size: 15px">Next pending player{icon(U["Next"], 18, 1.8)}</button>
            <button class="b s" style="width: 100%; height: 52px; font-size: 15px">Done</button>
          </div>
        </div>''')

script = r"""
const cl = v => v < 0 ? 0 : v > 1 ? 1 : v;
const eOut = t => 1 - Math.pow(1 - t, 3);
const eIn = t => t * t * t;
const r2 = v => Math.round(v * 100) / 100;
const F = [['30M SPRINT · SECONDS', '4.38'], ['COUNTERMOVEMENT JUMP · CM', '36'], ['AGILITY T-TEST · SECONDS', '9.95'], ['YO-YO IR1 · LEVEL', '18.9']];
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', t: 0 }; this.raf = null; this.t0 = 0; }
  componentDidMount() { this.t0 = performance.now(); const step = () => { this.setState({ t: performance.now() - this.t0 }); this.raf = requestAnimationFrame(step); }; this.raf = requestAnimationFrame(step); }
  componentWillUnmount() { if (this.raf) cancelAnimationFrame(this.raf); }
  renderVals() {
    const t = this.state.t % 7000;
    const pressed = t >= 1000 && t < 1160, loading = t >= 1160 && t < 2400, done = t >= 2400 && t < 6000;
    const btn = { cls: pressed ? 'pr' : '', busy: loading, loading, done, dash: r2(30 * (1 - eOut(cl((t - 2400) / 350)))),
      label: loading ? 'Saving' : done ? 'Saved' : 'Save results' };
    const inY = eOut(cl((t - 2400) / 320)), outY = eIn(cl((t - 5400) / 280));
    const toast = { y: r2(-140 + 140 * inY - 140 * outY), w: r2(100 * (1 - cl((t - 2400) / 3000))) };
    const fields = F.map(([label, v], i) => ({ label, v, o: done ? r2(cl((t - 2450 - i * 90) / 200)) : 0 }));
    return { theme: this.state.theme, btn, toast, fields, THEMES_JS };
  }
}"""
build('Feedback.dc.html', 'Stridian feedback states', 1840, 1090, 'SYSTEM · FEEDBACK', '\n'.join([sheet, pA, pB]), script,
      extra_css=extra_css + '.sweep{position:absolute;border-radius:6px;background:var(--ink);transform:rotate(140deg)}')
print('ok')
