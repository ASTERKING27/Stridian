from build import *
from haptics_data import *

LEFT = 150
def fmt(v): return f'{v:.1f}'

def curve_pts(x0, x1, i0, i1, kind, base, H, sx):
    pts = []
    for k in range(21):
        f = k / 20
        g = f * f if kind == 'accel' else f
        pts.append((x0 + (x1 - x0) * f, base - (i0 + (i1 - i0) * g) * H))
    return f'{fmt(x0)},{base} ' + ' '.join(f'{fmt(x)},{fmt(y)}' for x, y in pts) + f' {fmt(x1)},{base}'

def draw_events(evs, base, H, X):
    out = ''
    for e in evs:
        if e[0] == 'c':
            _, a, b, i0, i1, kind = e
            out += f'<polygon points="{curve_pts(X(a), X(b), i0, i1, kind, base, H, 1)}" stroke-width="1.2" stroke-linejoin="miter" style="fill: var(--soft); stroke: var(--ink)"></polygon>'
        elif e[0] == 's':
            _, a, ln, amp = e
            out += f'<rect x="{fmt(X(a))}" y="{fmt(base - amp * H)}" width="{fmt(X(a + ln) - X(a) - 1)}" height="{fmt(amp * H)}" style="fill: var(--ink)" fill-opacity=".85"></rect>'
    for e in evs:
        if e[0] == 't':
            _, t, i = e
            out += f'<rect x="{fmt(X(t) - 1.5)}" y="{fmt(base - i * H)}" width="3" height="{fmt(i * H)}" style="fill: var(--ink)"></rect>'
    return out

def text(x, y, s, anchor='start', size=10, color='var(--ink2)', weight=400):
    return f'<text x="{fmt(x)}" y="{fmt(y)}" text-anchor="{anchor}" style="font: {weight} {size}px \'IBM Plex Mono\', monospace; letter-spacing: .06em; fill: {color}">{s}</text>'

def timeline(T, W, phases, tracks, step=200, ph_hole=None):
    X = lambda t: LEFT + t * (W - LEFT - 20) / T
    out = []
    y = 20
    for t in range(0, T + 1, step):
        out.append(f'<line x1="{fmt(X(t))}" y1="{y + 6}" x2="{fmt(X(t))}" y2="{y + 6 + 66 + 124 * len(tracks)}" stroke-width="1" style="stroke: var(--line)"></line>')
        out.append(text(X(t), y, f'{t}', 'middle', 9.5))
    out.append(text(0, 50, 'ANIMATION', 'start', 10, 'var(--ink)', 500))
    for label, a, b, lane in phases:
        yy = 34 + lane * 28
        out.append(f'<rect x="{fmt(X(a))}" y="{yy}" width="{fmt(max(2, X(b) - X(a)))}" height="22" stroke-width="1" style="fill: var(--bg); stroke: var(--ink)"></rect>')
        out.append(text(X(a) + 6, yy + 15, label.upper(), 'start', 9.5, 'var(--ink)'))
    top = 34 + 2 * 28 + 18
    for n, (label, sub, kind, data, labels) in enumerate(tracks):
        base = top + 124 * n + 100
        H = 78
        out.append(f'<line x1="{LEFT}" y1="{base}" x2="{W - 20}" y2="{base}" stroke-width="1" style="stroke: var(--ink)"></line>')
        out.append(text(0, base - 58, label, 'start', 10.5, 'var(--ink)', 500))
        out.append(text(0, base - 42, sub, 'start', 9.5))
        if kind in ('ios', 'strength'):
            out.append(draw_events(data, base, H, X))
        elif kind == 'android':
            ticks = [d for d in data if d[0] == 'TICK']
            for name, t, sc, ln in data:
                if name in ('SLOW_RISE', 'QUICK_RISE'):
                    x0, x1 = X(t), X(t + ln)
                    out.append(f'<polygon points="{fmt(x0)},{base} {fmt(x1)},{fmt(base - sc * H)} {fmt(x1)},{base}" stroke-width="1.2" stroke-dasharray="4 3" style="fill: var(--soft); stroke: var(--ink)"></polygon>')
                    out.append(text(x0 + 4, base + 16, name, 'start', 9.5, 'var(--ink)'))
                else:
                    w = {'TICK': 2, 'LOW_TICK': 2, 'CLICK': 4, 'THUD': 9}[name]
                    h = sc * H * (.7 if name in ('TICK', 'LOW_TICK') else 1)
                    out.append(f'<rect x="{fmt(X(t) - w / 2)}" y="{fmt(base - h)}" width="{w}" height="{fmt(h)}" style="fill: var(--ink)"></rect>')
                    if name != 'TICK':
                        out.append(text(X(t) + 6, base + 16, name, 'start', 9.5, 'var(--ink)'))
            if ticks:
                out.append(text(X(ticks[0][1]), base + 16, f'{len([d for d in data if d[0] == "TICK" and d[1] < 1200])} × TICK', 'start', 9.5, 'var(--ink)'))
        elif kind == 'onoff':
            for t, d in data:
                out.append(f'<rect x="{fmt(X(t))}" y="{base - H * .7}" width="{fmt(max(2.5, X(t + d) - X(t)))}" height="{fmt(H * .7)}" style="fill: var(--ink)"></rect>')
                out.append(text(X(t) + (X(t + d) - X(t)) / 2, base + 16, f'{d}', 'middle', 9))
        for t, s in labels:
            out.append(text(X(t), base - H - 8, s, 'start', 9.5, 'var(--ink)'))
    h = top + 124 * len(tracks) + 10
    svg = f'<svg viewBox="0 0 {W} {h}" width="{W}" height="{h}" aria-hidden="true">{"".join(out)}</svg>'
    ph = ''
    if ph_hole:
        ph = f'<span style="position: absolute; top: 26px; bottom: 10px; width: 2px; background: var(--ink); left: {{{{{ph_hole}}}}}px; opacity: {{{{{ph_hole}O}}}}"></span>'
    return f'<div style="position: relative; width: {W}px; height: {h}px">{svg}{ph}</div>', X

def mini(evs, dur, W=300, Hh=62):
    X = lambda t: 4 + t * (W - 8) / dur
    base = Hh - 6
    inner = draw_events(evs, base, Hh - 14, X)
    return f'<svg viewBox="0 0 {W} {Hh}" width="{W}" height="{Hh}" aria-hidden="true"><line x1="0" y1="{base}" x2="{W}" y2="{base}" stroke-width="1" style="stroke: var(--line)"></line>{inner}</svg>'

def section(eyebrow, title, inner, extra=''):
    return f'''<section style="background: var(--bg); color: var(--ink); padding: 26px 28px; display: flex; flex-direction: column; gap: 18px; {extra}">
        <div style="display: flex; flex-direction: column; gap: 8px"><span class="eyebrow">{eyebrow}</span><span class="h1" style="font-size: 26px">{title}</span></div>
        {inner}
      </section>'''

def chips(items):
    return '<div style="display: flex; flex-wrap: wrap; gap: 8px">' + ''.join(f'<span class="mono" style="font-size: 10.5px; letter-spacing: .1em; padding: 7px 10px; border: 1px solid var(--ink)">{c}</span>' for c in items) + '</div>'

W = 1704
# ------------------------------------------------ RICH BOARD
tl_launch, _ = timeline(2800, W, LAUNCH_PHASES, [
    ('IPHONE', 'CORE HAPTICS · LAYERED', 'ios', LAUNCH_IOS, LAUNCH_LABELS_IOS),
    ('ANDROID', 'COMPOSITION · IN SEQUENCE', 'android', LAUNCH_ANDROID, [(1140, 'Charge'), (1520, 'Ignite'), (1620, 'Dive'), (2420, 'Land')]),
], ph_hole='ph1')
tl_level, _ = timeline(2400, W, LEVEL_PHASES, [
    ('IPHONE', 'ONE AHAP FILE', 'ios', LEVEL_IOS, LEVEL_LABELS),
], ph_hole='ph2')

vocab = '<div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 14px">'
for name, evs, dur, ios, andr, used in RICH_VOCAB:
    vocab += f'''<div style="border: 1px solid var(--line); padding: 14px; display: flex; flex-direction: column; gap: 10px">
          <div style="display: flex; justify-content: space-between; align-items: baseline"><span style="font-size: 17px; font-weight: 600; font-stretch: 112%">{name}</span><span class="mono" style="font-size: 9.5px; color: var(--ink2)">{dur} MS</span></div>
          {mini(evs, dur)}
          <div style="display: flex; flex-direction: column; gap: 3px"><span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">IPHONE</span><span style="font-size: 12px; line-height: 1.35">{ios}</span></div>
          <div style="display: flex; flex-direction: column; gap: 3px"><span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">ANDROID</span><span class="mono" style="font-size: 11px; line-height: 1.4">{andr}</span></div>
          <div style="display: flex; flex-direction: column; gap: 3px; padding-top: 8px; border-top: 1px solid var(--line)"><span style="font-size: 12px; line-height: 1.35; color: var(--ink2)">{used}</span></div>
        </div>'''
vocab += '</div>'

def table(groups, cols, cells):
    out = ''
    for g, rows in groups:
        out += f'<div style="display: flex; flex-direction: column"><span class="eyebrow" style="padding: 6px 0 8px; color: var(--ink)">{g}</span>'
        out += f'<div style="display: grid; grid-template-columns: {cols}; column-gap: 14px; padding: 0 0 6px"><span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">MOMENT</span><span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">WHEN</span>' + ''.join(f'<span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">{h}</span>' for h, _ in cells) + '</div>'
        for r in rows:
            vals = ''.join(f'<span class="{"mono" if mono else ""}" style="font-size: {11 if mono else 12.5}px; line-height: 1.35; color: {"var(--ink2)" if r[idx] in ("—", "none") else "var(--ink)"}; font-weight: {600 if idx == 2 else 400}">{r[idx]}</span>' for (h, (idx, mono)) in cells)
            out += f'<div style="display: grid; grid-template-columns: {cols}; column-gap: 14px; padding: 9px 0; border-top: 1px solid var(--line); align-items: baseline"><span style="font-size: 12.5px; line-height: 1.35">{r[0]}</span><span class="mono" style="font-size: 10.5px; line-height: 1.4; color: var(--ink2)">{r[1]}</span>{vals}</div>'
        out += '</div>'
    return out

rich_cells = [('PATTERN', (2, False)), ('IPHONE', (3, True)), ('ANDROID', (4, True))]
rich_cols = 'minmax(0, 1.5fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1fr) minmax(0, 1.25fr)'
left_groups, right_groups = PLACEMENT[:3], PLACEMENT[3:]
placement = f'''<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 40px">
          <div style="display: flex; flex-direction: column; gap: 18px">{table(left_groups, rich_cols, rich_cells)}</div>
          <div style="display: flex; flex-direction: column; gap: 18px">{table(right_groups, rich_cols, rich_cells)}</div>
        </div>'''

def notes(items):
    return ''.join(f'<div style="display: flex; gap: 14px; padding: 10px 0; border-top: 1px solid var(--line)"><span class="mono" style="font-size: 10px; letter-spacing: .1em; width: 150px; flex-shrink: 0; padding-top: 2px">{a}</span><span style="font-size: 13px; line-height: 1.45">{b}</span></div>' for a, b in items)

rich_notes = f'''<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 40px">
          <div>{notes([
            ('WHO GETS THIS', 'iPhone 8 and later (every iPhone on iOS 16+): CHHapticEngine.capabilitiesForHardware().supportsHaptics. Android 12+ where vibrator.areAllPrimitivesSupported(TICK, CLICK, LOW_TICK, THUD, QUICK_RISE, SLOW_RISE, QUICK_FALL) is true. Everyone else gets the budget plan.'),
            ('IPHONE', 'One AHAP file per signature moment (launch, level, badge, streak restored). Start the haptic engine when the app starts — before the splash — so the first spark isn’t late. Call prepare() on the feedback generators on touch-down.'),
            ('ANDROID', 'Primitives play one after another, so the sparks and the charge run in sequence instead of layered. Read the real primitive lengths with getPrimitiveDurations() and time each one to end where the animation expects. Use performHapticFeedback for taps and ticks — it follows the phone’s Touch feedback setting.'),
          ])}</div>
          <div>{notes([
            ('SYNC', 'Start every pattern on the same frame as its animation, from the same timeline numbers. Target under 10 ms drift.'),
            ('ONE CHANGE', 'Level reached: start the count-up at 1400 ms instead of 1250 so its ticks don’t land on top of the letter stamps.'),
            ('REDUCE MOTION', 'Haptics go quiet with the animations: no Crackle, Charge, Dive, Sweep, Stamp, Draw or Rise. Taps, ticks, switches and Success / Warning / Error stay. The launch becomes a single Land when the app appears.'),
            ('SETTINGS', 'Add Settings › Haptics: Full · Light · Off. Light keeps taps and results only. Off means nothing plays, whatever the phone can do.'),
          ])}</div>
        </div>'''

rich_body = f'''    <div style="display: flex; flex-direction: column; gap: 20px; width: 100%">
      {section('HAPTICS · MID-RANGE AND HIGH-END PHONES', 'Every haptic in Stridian, placed', chips(['EVERY HAPTIC MATCHES SOMETHING ON SCREEN', 'LIGHTEST FOR WHAT YOU DO MOST', 'RICHEST FOR RARE MOMENTS', 'NEVER FOR THINGS YOU DIDN’T DO', 'ERRORS ALWAYS COME WITH WORDS', 'QUIET WHEN REDUCE MOTION IS ON']))}
      {section('01 · OPENING THE APP · 0 – 2800 MS', 'Sparks crackle, the logo charges, fires, and the “S” dives in', tl_launch + '<span style="font-size: 13px; line-height: 1.45; color: var(--ink2)">Bar height is strength. Shaded shapes are continuous rumbles. On iPhone the sparks sit on top of the charge; on Android they come first, then the charge — the dive is a slow rise handing over to a quick rise for the final rush.</span>')}
      {section('02 · LEVEL REACHED · 0 – 2400 MS', 'The biggest moment after launch', tl_level)}
      {section('03 · THE VOCABULARY', '20 patterns — everything in the app is built from these', vocab)}
      {section('04 · WHERE EACH ONE GOES', 'Every interaction on the canvas', placement)}
      {section('05 · BUILDING IT', 'Notes for whoever implements this', rich_notes)}
    </div>'''

script = r"""
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', t: 0 }; this.raf = null; this.t0 = 0; }
  componentDidMount() { this.t0 = performance.now(); const step = () => { this.setState({ t: performance.now() - this.t0 }); this.raf = requestAnimationFrame(step); }; this.raf = requestAnimationFrame(step); }
  componentWillUnmount() { if (this.raf) cancelAnimationFrame(this.raf); }
  renderVals() {
    const X = (t, T) => 150 + t * (1704 - 170) / T;
    const a = this.state.t % 3600, b = this.state.t % 3200;
    return { theme: this.state.theme, ph1: Math.round(X(Math.min(a, 2800), 2800)), ph1O: a <= 2800 ? 1 : 0,
      ph2: Math.round(X(Math.min(b, 2400), 2400)), ph2O: b <= 2400 ? 1 : 0, THEMES_JS };
  }
}"""
build('Haptics.dc.html', 'Stridian haptics plan', 1840, 4600, 'HAPTICS · RICH', rich_body, script)

# ------------------------------------------------ BUDGET BOARD
tl_budget, _ = timeline(2800, W, LAUNCH_PHASES, [
    ('ON / OFF MOTOR', 'TIMINGS ONLY · MS ON', 'onoff', BUDGET_ONOFF, [(600, 'Sparks × 3'), (1520, 'Thump'), (1760, 'Pulses closing in'), (2420, 'Land')]),
    ('CAN VARY STRENGTH', 'createWaveform · AMPLITUDES', 'strength', BUDGET_STRENGTH, [(430, '7 spikes'), (1140, 'Steps up'), (1520, 'Thump'), (1560, '14 steps, 60 ms each'), (2420, 'Land')]),
], ph_hole='ph1')

detect = '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px">' + ''.join(f'''<div style="border: 1px {bs} var(--ink); padding: 16px; display: flex; flex-direction: column; gap: 8px">
          <span class="mono" style="font-size: 10px; letter-spacing: .12em; color: var(--ink2)">{tag}</span><span style="font-size: 17px; font-weight: 600; font-stretch: 112%">{t}</span>
          <span class="mono" style="font-size: 11px; line-height: 1.5">{check}</span><span style="font-size: 13px; line-height: 1.45; color: var(--ink2)">{what}</span></div>''' for tag, t, check, what, bs in [
    ('CASE A', 'Can vary strength', 'hasVibrator() · hasAmplitudeControl() = true · composition primitives missing', 'Waveforms with amplitudes. Short spikes feel like sparks, and 60 ms steps fake a rise.', 'solid'),
    ('CASE B', 'On / off motor only', 'hasVibrator() = true · hasAmplitudeControl() = false', 'Timings only. Few, short, well-spaced pulses — the rhythm carries the feeling, not the strength.', 'solid'),
    ('CASE C', 'No motor, or haptics off', 'hasVibrator() = false · or Settings › Haptics is Off', 'Nothing plays. Every haptic already has a visual twin, so nothing is lost.', 'dashed')]) + '</div>'

bvocab = '<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 14px">' + ''.join(f'''<div style="border: 1px solid var(--line); padding: 14px; display: flex; flex-direction: column; gap: 10px">
          <span style="font-size: 17px; font-weight: 600; font-stretch: 112%">{n}</span>
          <div style="display: grid; grid-template-columns: 120px minmax(0, 1fr); row-gap: 7px; column-gap: 10px; align-items: baseline">
            <span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">FIRST CHOICE</span><span class="mono" style="font-size: 11px">{sysc}</span>
            <span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">ON / OFF</span><span class="mono" style="font-size: 11px">{onoff}</span>
            <span class="mono" style="font-size: 9px; letter-spacing: .12em; color: var(--ink2)">WITH STRENGTH</span><span class="mono" style="font-size: 11px">{st}</span>
          </div>
          <span style="font-size: 12px; line-height: 1.35; color: var(--ink2); padding-top: 8px; border-top: 1px solid var(--line)">{used}</span></div>''' for n, sysc, onoff, st, used in BUDGET_VOCAB) + '</div>'

bcells = [('BUDGET', (5, False))]
bcols = 'minmax(0, 1.4fr) minmax(0, 1fr) minmax(0, .9fr)'
g = PLACEMENT
bplacement = f'''<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); column-gap: 32px">
          <div style="display: flex; flex-direction: column; gap: 18px">{table(g[:2], bcols, bcells)}</div>
          <div style="display: flex; flex-direction: column; gap: 18px">{table(g[2:4], bcols, bcells)}</div>
          <div style="display: flex; flex-direction: column; gap: 18px">{table(g[4:], bcols, bcells)}</div>
        </div>'''

brules = f'''<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 40px">
          <div>{notes([
            ('SHORTEST PULSE', '20–30 ms. Anything shorter often isn’t felt on a cheap motor — so selection ticks mostly disappear, on purpose.'),
            ('GAPS', 'At least 80 ms between pulses. Closer than that and a spinning-weight motor smears them into one buzz.'),
            ('LIMITS', 'No pulse over 80 ms. At most 6 pulses and 400 ms of vibration in one moment. Never loop, never during loading or uploads.'),
            ('ONE AT A TIME', 'Cancel the pattern that’s playing before starting a new one — cheap motors can’t mix.'),
          ])}</div>
          <div>{notes([
            ('SYSTEM FIRST', 'Prefer VIRTUAL_KEY, CLOCK_TICK, CONFIRM and REJECT through performHapticFeedback. Each phone maker tunes these to its own motor, and they follow the Touch feedback setting.'),
            ('WHAT’S CUT', 'Crackle becomes 3 pulses. Charge, Draw, Rise, Fall, Sweep and Stamp are dropped. Slider steps, scrub stills and outline ticks are dropped. Level reached keeps two moments: the logo pop and the finish.'),
            ('IPHONE', 'No budget iPhones to plan for: every iPhone that runs iOS 16 or later has the full haptic engine.'),
            ('WEB BUILD', 'If Stridian ships as the current website: iPhone browsers can’t vibrate at all, and Android Chrome only does on / off (navigator.vibrate). That makes Case B the ceiling on the web — the rich plan needs the native app.'),
          ])}</div>
        </div>'''

budget_body = f'''    <div style="display: flex; flex-direction: column; gap: 20px; width: 100%">
      {section('HAPTICS · BUDGET PHONES', 'Same moments, fewer and simpler pulses', chips(['FEWER, SHORTER, FURTHER APART', 'SYSTEM HAPTICS FIRST', 'RHYTHM INSTEAD OF STRENGTH', 'NOTHING IS LOST WITHOUT IT']))}
      {section('01 · WHICH PHONE GETS WHAT', 'Checked once, when the app starts', detect)}
      {section('02 · OPENING THE APP · 0 – 2800 MS', 'The launch, rebuilt from pulses', tl_budget + '<span style="font-size: 13px; line-height: 1.45; color: var(--ink2)">On / off: three spark pulses, a 60 ms thump when the logo fires, then four pulses closing in (250 → 90 ms apart) so the zoom still feels like it’s speeding up, ending on a 45 ms land. 300 ms of vibration in total. With strength control the sparks, charge and dive come back as spikes and 60 ms steps.</span>')}
      {section('03 · THE BUDGET VOCABULARY', '6 patterns instead of 20', bvocab)}
      {section('04 · WHERE EACH ONE GOES', 'Same rows as the rich plan — a dash means nothing plays', bplacement)}
      {section('05 · RULES FOR CHEAP MOTORS', 'Why the budget plan looks the way it does', brules)}
    </div>'''

bscript = r"""
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', t: 0 }; this.raf = null; this.t0 = 0; }
  componentDidMount() { this.t0 = performance.now(); const step = () => { this.setState({ t: performance.now() - this.t0 }); this.raf = requestAnimationFrame(step); }; this.raf = requestAnimationFrame(step); }
  componentWillUnmount() { if (this.raf) cancelAnimationFrame(this.raf); }
  renderVals() {
    const a = this.state.t % 3600;
    return { theme: this.state.theme, ph1: Math.round(150 + Math.min(a, 2800) * (1704 - 170) / 2800), ph1O: a <= 2800 ? 1 : 0, THEMES_JS };
  }
}"""
build('HapticsBudget.dc.html', 'Stridian haptics plan budget', 1840, 3150, 'HAPTICS · BUDGET', budget_body, bscript)
print('ok')
