from build import *
TILE = 'M19 0H72V64L53 80H0V16Z'
W, H = 150, 184

extra_css = """
.stage{position:relative;width:150px;height:184px;overflow:hidden;background:var(--bg);border:1px solid var(--line);box-sizing:border-box;flex-shrink:0}
.blk{position:absolute;left:12px;background:var(--line)}
.lap{animation:lap 1s linear infinite}
@keyframes lap{to{stroke-dashoffset:-100}}
.sk{position:absolute;left:12px;overflow:hidden;background:var(--soft)}
.sk.on::after{content:'';position:absolute;top:-60%;bottom:-60%;width:30px;left:-60px;background:var(--line);transform:rotate(40deg);animation:skw 1.6s cubic-bezier(.5,0,.2,1) infinite}
@keyframes skw{0%{left:-60px}70%,100%{left:calc(100% + 30px)}}
.spk{position:absolute;left:0;top:0;height:2px;background:var(--ink);clip-path:polygon(0 50%,70% 0,100% 50%,70% 100%)}
.lbl2{font:500 9.5px/1 'IBM Plex Mono',monospace;letter-spacing:.12em;color:var(--ink2)}
"""

def app_blocks():
    return ''.join(f'<span class="blk" style="top: {y}px; width: {w}px; height: {h}px"></span>' for y, w, h in [(20, 60, 6), (34, 118, 10), (50, 90, 10), (74, 124, 40), (124, 124, 8), (140, 124, 8), (156, 80, 8)])

def logo(size, style):
    return f'<svg viewBox="0 0 100 100" width="{size}" height="{size}" aria-hidden="true" style="position: absolute; left: {(W-2-size)/2}px; top: {(H-2-size)/2}px; {style}"><path d="{LOGO_D}" style="fill: var(--ink)"></path></svg>'

def S(k, v):  # hole helper
    return '{{' + k + '.' + v + '}}'

def stages(k):
    # returns dict variant -> stage inner markup, holes under k.std / k.red
    out = {}
    for v in ['std', 'red']:
        h = lambda x: S(f'{k}.{v}', x)
        if k == 'launch':
            inner = app_blocks() + f'''<div style="position: absolute; inset: 0; background: var(--bg); opacity: {h('splashO')}"></div>
              {logo(40, f"transform: scale({h('logoS')}); opacity: {h('logoO')}")}
              <sc-for list="{h('sparks')}" as="s" hint-placeholder-count="0"><span class="spk" style="width: {{{{s.w}}}}px; opacity: {{{{s.o}}}}; transform: translate({{{{s.x}}}}px, {{{{s.y}}}}px) rotate({{{{s.r}}}}deg)"></span></sc-for>'''
        elif k == 'tab':
            layer = lambda title, st: f'''<div style="position: absolute; inset: 0; background: var(--bg); {st}"><span style="position: absolute; left: 12px; top: 16px; font: 700 15px/1 Archivo, sans-serif; font-stretch: 112%">{title}</span>{app_blocks().replace('top: 20px', 'top: 200px')}</div>'''
            inner = layer('Dashboard', '') + layer('Report', f"{h('clip')}; opacity: {h('bO')}") + f'''<sc-for list="{h('lines')}" as="l" hint-placeholder-count="0"><span style="position: absolute; left: 0; top: 0; background: var(--ink); width: {{{{l.len}}}}px; height: {{{{l.th}}}}px; border-radius: {{{{l.rad}}}}px; transform: translate({{{{l.x}}}}px, {{{{l.y}}}}px) rotate(140deg)"></span></sc-for>'''
        elif k == 'pill':
            inner = app_blocks() + f'''<div style="position: absolute; left: 8px; right: 8px; bottom: 14px; height: 32px; border-radius: 16px; border: 1px solid var(--line); background: var(--soft)">
                <span style="position: absolute; top: 2px; height: 26px; border-radius: 13px; background: var(--ink); left: {h('l')}px; width: {h('w')}px"></span></div>'''
        elif k == 'pull':
            inner = f'''<div style="position: absolute; left: 0; right: 0; top: 0; height: {h('d')}px; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; gap: 4px; padding-bottom: 6px; box-sizing: border-box; overflow: hidden">
                <svg viewBox="-4 -4 108 108" width="20" height="20" aria-hidden="true"><path d="{LOGO_D}" pathLength="100" class="{h('lapCls')}" fill="none" stroke-width="8" style="stroke: var(--ink); stroke-dasharray: {h('dash')}"></path></svg>
                <span class="lbl2" style="font-size: 7.5px">{h('cap')}</span></div>
              <div style="position: absolute; inset: 0; background: var(--bg); transform: translateY({h('d')}px); filter: {h('filter')}">{app_blocks()}</div>'''
        elif k == 'ach':
            inner = app_blocks() + f'''<div style="position: absolute; inset: 0; background: var(--line); opacity: {h('scrim')}"></div>
              <div style="position: absolute; left: 14px; right: 14px; top: 34px; height: 116px; background: var(--ink); color: var(--bg); {h('clip')}; opacity: {h('cardO')}; display: flex; flex-direction: column; justify-content: center; padding: 0 12px; gap: 6px; overflow: hidden">
                <span class="lbl2" style="color: inherit; opacity: .7; font-size: 7.5px">NEW LEVEL</span>
                <div style="display: flex; height: 30px; overflow: hidden"><sc-for list="{h('letters')}" as="c" hint-placeholder-count="5"><span style="font: 700 26px/30px Archivo, sans-serif; font-stretch: 125%; display: inline-block; transform: translateY({{{{c.y}}}}px)">{{{{c.ch}}}}</span></sc-for></div>
                <span class="mono" style="font-size: 11px">{h('val')}</span></div>'''
        elif k == 'badge':
            inner = f'''<div style="position: absolute; left: 39px; top: 38px; width: 72px; height: 80px">
                <svg viewBox="-1 -1 74 82" width="72" height="80" aria-hidden="true" style="position: absolute; inset: 0"><path d="{TILE}" pathLength="100" fill="none" stroke-width="1.6" style="stroke: var(--ink); stroke-dasharray: {h('dash')}"></path></svg>
                <svg viewBox="-1 -1 74 82" width="72" height="80" aria-hidden="true" style="position: absolute; inset: 0; {h('clip')}; opacity: {h('fillO')}"><path d="{TILE}" style="fill: var(--ink)"></path></svg>
                <sc-for list="{h('sparks')}" as="s" hint-placeholder-count="0"><span class="spk" style="width: {{{{s.w}}}}px; opacity: {{{{s.o}}}}; transform: translate({{{{s.x}}}}px, {{{{s.y}}}}px) rotate({{{{s.r}}}}deg)"></span></sc-for>
              </div>
              <span class="mono" style="position: absolute; left: 50%; top: 132px; transform: translateX(-50%); font-size: 8.5px; letter-spacing: .12em; padding: 3px 5px; border: 1px solid var(--ink); opacity: {h('newO')}">NEW</span>'''
        elif k == 'streak':
            inner = f'''<div style="position: absolute; left: 20px; top: 50px; height: 64px; overflow: hidden">
                <div style="display: flex; flex-direction: column; transform: translateY({h('y')}px)">
                  <span style="font: 700 64px/64px Archivo, sans-serif; font-stretch: 125%; opacity: {h('o1')}">3</span>
                  <span style="font: 700 64px/64px Archivo, sans-serif; font-stretch: 125%; opacity: {h('o2')}; margin-top: {h('mt')}px">4</span>
                </div></div>
              <span class="lbl2" style="position: absolute; left: 20px; top: 124px">WEEKS IN A ROW</span>'''
        elif k == 'skel':
            inner = ''.join(f'<span class="sk {h("cls")}" style="top: {y}px; width: {w}px; height: {hh}px"></span>' for y, w, hh in [(20, 60, 6), (34, 118, 10), (50, 90, 10), (74, 124, 40), (124, 124, 8), (140, 124, 8), (156, 80, 8)])
        elif k == 'toast':
            inner = app_blocks() + f'''<div style="position: absolute; left: 8px; right: 8px; top: 10px; height: 36px; background: var(--ink); color: var(--bg); display: flex; align-items: center; gap: 8px; padding: 0 10px; transform: translateY({h('y')}px); opacity: {h('o')}">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.4" aria-hidden="true"><path d="M5 12.5 10 17 19 7" pathLength="30" style="stroke-dasharray: 30; stroke-dashoffset: {h('dash')}"></path></svg>
                <span style="font: 600 11px/1 Archivo, sans-serif">Results saved</span></div>'''
        out[v] = inner
    return out

CARDS = [
  ('launch', 'Launch', 'Sparks and the runner-shaped zoom are gone. The logo fades up, then the app fades in.'),
  ('tab', 'Tab change', 'No diagonal lines, no slide. The new tab fades in over 150 ms.'),
  ('pill', 'Tab pill', 'The pill jumps straight to the new tab — no stretch.'),
  ('pull', 'Pull to refresh', 'Content still follows your finger. No lap loop and no black-and-white flash — the caption does the work.'),
  ('ach', 'Level reached', 'The card fades in with the final numbers already there. No sweep, no rising letters, no count.'),
  ('badge', 'Badge earned', 'No drawing and no sparks. The badge swaps to filled and the NEW tag appears.'),
  ('streak', 'Streak count', 'The number changes in place with a short fade instead of rolling.'),
  ('skel', 'Loading', 'Placeholder blocks stay still. The diagonal shimmer is switched off.'),
  ('toast', 'Confirmation', 'The toast appears where it lands, with the tick already drawn.'),
]

cards_html = ''
for k, title, rule in CARDS:
    st = stages(k)
    cards_html += f'''<div style="background: var(--bg); color: var(--ink); padding: 18px 18px 18px 18px; display: flex; gap: 16px">
          <div style="display: flex; flex-direction: column; gap: 6px"><span class="lbl2">STANDARD</span><div class="stage">{st['std']}</div></div>
          <div style="display: flex; flex-direction: column; gap: 6px"><span class="lbl2" style="color: var(--ink)">REDUCED</span><div class="stage" style="border-color: var(--ink)">{st['red']}</div></div>
          <div style="display: flex; flex-direction: column; gap: 8px; padding-top: 16px"><span style="font-size: 17px; font-weight: 600; font-stretch: 112%">{title}</span><span style="font-size: 13px; line-height: 1.45; color: var(--ink2)">{rule}</span></div>
        </div>'''

rules = ''.join(f'<span class="mono" style="font-size: 10.5px; letter-spacing: .1em; padding: 7px 10px; border: 1px solid var(--ink)">{r}</span>' for r in
   ['NO ZOOMS', 'NO SWEEPS OR SLIDES', 'NO SPARKS', 'NO FLASHES', 'FADES ≤ 200 MS', 'NOTHING IS SAID ONLY BY MOTION'])

body = f'''    <div style="display: flex; flex-direction: column; gap: 20px; width: 100%">
      <section style="background: var(--bg); color: var(--ink); padding: 24px 28px; display: flex; gap: 40px; align-items: center">
        <div style="display: flex; flex-direction: column; gap: 8px; width: 520px; flex-shrink: 0"><span class="eyebrow">REDUCED MOTION</span><span class="h1">Every animation has a quiet twin</span>
          <span style="font-size: 14px; line-height: 1.45; color: var(--ink2)">Turns on when the phone’s Reduce Motion or Remove animations setting is on — or from Settings › Motion in Stridian.</span></div>
        <div style="display: flex; flex-wrap: wrap; gap: 8px">{rules}</div>
      </section>
      <div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 16px">{cards_html}</div>
    </div>'''

script = r"""
const cl = v => v < 0 ? 0 : v > 1 ? 1 : v;
const lerp = (a, b, t) => a + (b - a) * t;
const eIO = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const eOut = t => 1 - Math.pow(1 - t, 3);
const r2 = v => Math.round(v * 100) / 100;
const seg = (p, a, b) => cl((p - a) / (b - a));
const W = 148, H = 182;
const PHI = 50 * Math.PI / 180, NX = Math.cos(PHI), NY = Math.sin(PHI), UX = -Math.sin(PHI), UY = Math.cos(PHI);
function half(b, behind, w, h) {
  const T = 800, s = behind ? -1 : 1;
  return 'clip-path: polygon(' + [[b, -T], [b, T], [b + s * T, T], [b + s * T, -T]].map(([c, t]) => r2(NX * c + UX * t) + 'px ' + r2(NY * c + UY * t) + 'px').join(', ') + ')';
}
function lines(c0, w, h) {
  const out = [];
  [[7, 0], [5, 12], [4, 22]].forEach(([th, off]) => {
    const c = c0 - off, x0 = NX * c, y0 = NY * c;
    const lo = Math.max((x0 - w) / (-UX), -y0 / UY), hi = Math.min(x0 / (-UX), (h - y0) / UY);
    if (hi - lo <= 0) return;
    const t1 = lo + .05 * (hi - lo), t2 = lo + .9 * (hi - lo), mid = (t1 + t2) / 2, len = t2 - t1 + th;
    out.push({ len: r2(len), th, rad: th / 2, x: r2(NX * c + UX * mid - len / 2), y: r2(NY * c + UY * mid - th / 2) });
  });
  return out;
}
function burst(u, cx, cy, n, dist) {
  if (u <= 0 || u >= 1) return [];
  return Array.from({ length: n }, (_, i) => { const a = i / n * Math.PI * 2, d = dist * eOut(u), w = 7 * (1 - .5 * u);
    return { w: r2(w), o: r2(1 - u), x: r2(cx + Math.cos(a) * d - w / 2), y: r2(cy + Math.sin(a) * d - 1), r: r2(a * 180 / Math.PI) }; });
}
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', t: 0 }; this.raf = null; this.t0 = 0; }
  componentDidMount() { this.t0 = performance.now(); const step = () => { this.setState({ t: performance.now() - this.t0 }); this.raf = requestAnimationFrame(step); }; this.raf = requestAnimationFrame(step); }
  componentWillUnmount() { if (this.raf) cancelAnimationFrame(this.raf); }
  renderVals() {
    const p = (this.state.t % 3600) / 3600;
    const CM = W * NX + H * NY;
    // launch
    const zoom = seg(p, .62, .82);
    const launch = {
      std: { splashO: p < .8 ? 1 : r2(1 - seg(p, .8, .86)), logoS: r2(p < .15 ? .6 + .4 * eOut(seg(p, 0, .15)) : p < .62 ? 1 : Math.pow(16, zoom * zoom)), logoO: p < .86 ? 1 : 0,
        sparks: burst(seg(p, .25, .55), 74, 91, 8, 44) },
      red: { splashO: r2(1 - seg(p, .55, .61)), logoS: 1, logoO: r2(seg(p, 0, .06) * (1 - seg(p, .55, .61))), sparks: [] } };
    // tab change
    const tu = seg(p, .25, .5), lead = lerp(-10, CM + 10, eIO(tu));
    const tab = {
      std: { clip: p < .25 ? half(-50, true) : p < .5 ? half(lead, true) : '', bO: p < .92 ? 1 : 0, lines: p > .25 && p < .5 ? lines(lead, W, H) : [] },
      red: { clip: '', bO: r2(seg(p, .3, .34) * (1 - seg(p, .92, .96))), lines: [] } };
    // pill
    const X = [6, 50, 94], PW = 132, ws = 38;
    const idx = p < .12 ? 0 : p < .45 ? 1 : p < .78 ? 2 : 0;
    const from = p < .12 ? 2 : p < .45 ? 0 : p < .78 ? 1 : 2, t0 = p < .12 ? -.21 : p < .45 ? .12 : p < .78 ? .45 : .78;
    const u = seg(p, t0, t0 + .14), dir = X[idx] > X[from] ? 1 : -1;
    const fast = eOut(cl(u * 1.5)), slow = eIO(u);
    const L = lerp(X[from], X[idx], dir > 0 ? slow : fast), R = lerp(X[from] + ws, X[idx] + ws, dir > 0 ? fast : slow);
    const pill = { std: { l: r2(L), w: r2(R - L) }, red: { l: X[idx], w: ws } };
    // pull
    const d = p < .05 ? 0 : p < .3 ? 46 * eOut(seg(p, .05, .3)) : p < .62 ? 46 : 46 * (1 - eIO(seg(p, .62, .8)));
    const loading = p >= .3 && p < .6;
    const pull = {
      std: { d: r2(d), lapCls: loading ? 'lap' : '', dash: loading ? '24 76' : r2(Math.min(1, d / 46) * 100) + ' 100', cap: loading ? 'UPDATING' : 'PULL', filter: p > .6 && p < .63 ? 'invert(1)' : 'none' },
      red: { d: r2(d), lapCls: '', dash: '100 0', cap: loading ? 'UPDATING…' : p >= .6 && p < .85 ? 'UPDATED' : 'PULL', filter: 'none' } };
    // achievement
    const inU = seg(p, .1, .3), outU = seg(p, .85, .97);
    const letters = ch => 'STATE'.split('').map((c, i) => ({ ch: c, y: ch ? r2(32 * (1 - eOut(seg(p, .3 + i * .03, .42 + i * .03)))) : 0 }));
    const ach = {
      std: { scrim: r2(seg(p, .08, .16) * (1 - seg(p, .9, .97))), clip: p < .1 ? half(-50, true) : p < .3 ? half(lerp(-10, 150, eIO(inU)), true) : p < .85 ? '' : half(lerp(-10, 150, eIO(outU)), false), cardO: 1, letters: letters(true), val: (4.38 - Math.round(5 * eOut(seg(p, .4, .6))) * .01).toFixed(2) + ' s' },
      red: { scrim: r2(seg(p, .1, .16) * (1 - seg(p, .85, .91))), clip: '', cardO: r2(seg(p, .1, .16) * (1 - seg(p, .85, .91))), letters: letters(false), val: '4.33 s' } };
    // badge
    const bu = seg(p, .2, .36);
    const badge = {
      std: { dash: r2(eOut(seg(p, .08, .24)) * 100) + ' 100', clip: p < .2 ? 'clip-path: polygon(0 0, 0 0, 0 0)' : half(lerp(-10, 120, eIO(bu)), true), fillO: p < .92 ? 1 : 0, sparks: burst(seg(p, .34, .52), 36, 40, 8, 40), newO: r2(seg(p, .4, .45) * (p < .92 ? 1 : 0)) },
      red: { dash: '100 0', clip: '', fillO: r2(seg(p, .2, .26) * (p < .92 ? 1 : 0)), sparks: [], newO: r2(seg(p, .26, .3) * (p < .92 ? 1 : 0)) } };
    // streak
    const ru = eIO(seg(p, .3, .45)), back = p > .92;
    const streak = {
      std: { y: back ? 0 : r2(-64 * ru), o1: 1, o2: 1, mt: 0 },
      red: { y: 0, o1: back ? 1 : r2(1 - seg(p, .3, .34)), o2: back ? 0 : r2(seg(p, .32, .36)), mt: -64 } };
    const skel = { std: { cls: 'on' }, red: { cls: '' } };
    const tu2 = seg(p, .2, .3);
    const toast = {
      std: { y: r2(p < .85 ? -50 + 50 * eOut(tu2) : -50 * eIO(seg(p, .85, .93))), o: 1, dash: r2(30 * (1 - eOut(seg(p, .3, .38)))) },
      red: { y: 0, o: r2(seg(p, .2, .26) * (1 - seg(p, .85, .9))), dash: 0 } };
    return { theme: this.state.theme, launch, tab, pill, pull, ach, badge, streak, skel, toast, THEMES_JS };
  }
}"""
build('Motion.dc.html', 'Stridian reduced motion', 1800, 1060, 'SYSTEM · REDUCED MOTION', body, script, extra_css=extra_css)
print('ok')
