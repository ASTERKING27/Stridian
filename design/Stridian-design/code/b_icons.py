from build import *
from icons import SPORTS, UI

def ic(d, size, sw=1.6):
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="{sw}" stroke-linecap="butt" stroke-linejoin="miter" aria-hidden="true" style="flex-shrink: 0"><path d="{d}"></path></svg>'

TILE = 'M19 0H72V64L53 80H0V16Z'
sport_cells = ''
for i, (name, d) in enumerate(SPORTS):
    filled = i == 0
    fill = 'fill: var(--ink)' if filled else 'fill: none; stroke: var(--ink)'
    col = 'var(--bg)' if filled else 'var(--ink)'
    sport_cells += f'''<div style="display: flex; flex-direction: column; align-items: center; gap: 12px">
          <div style="position: relative; width: 100px; height: 111px">
            <svg viewBox="-1 -1 74 82" width="100" height="111" aria-hidden="true"><path d="{TILE}" stroke-width="1.2" style="{fill}"></path></svg>
            <span style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: {col}">{ic(d, 48, 1.4)}</span>
          </div>
          <span style="font-size: 14px; font-weight: 600">{name}</span>
          <div style="display: flex; gap: 12px; align-items: center; color: var(--ink)">{ic(d, 24)}{ic(d, 16, 1.8)}</div>
        </div>'''

chips = ''.join(f'<span style="height: 40px; padding: 0 14px 0 11px; display: flex; align-items: center; gap: 8px; border: 1px solid var(--ink); {"background: var(--ink); color: var(--bg);" if i == 0 else ""} font: 500 13px/1 Archivo, sans-serif">{ic(d, 18)}{n}</span>' for i, (n, d) in enumerate(SPORTS))

ui_cells = ''.join(f'''<div style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 10px; height: 86px; border-right: 1px solid var(--line); border-bottom: 1px solid var(--line)">
          {ic(d, 26)}<span class="mono" style="font-size: 9.5px; letter-spacing: .06em; color: var(--ink2); text-align: center">{n.upper()}</span></div>''' for n, d in UI)

grid_lines = ''.join(f'<line x1="{i}" y1="0" x2="{i}" y2="24" stroke-width=".03" style="stroke: var(--ink2)"></line><line x1="0" y1="{i}" x2="24" y2="{i}" stroke-width=".03" style="stroke: var(--ink2)"></line>' for i in range(25))
construction = f'''<svg viewBox="0 0 24 24" width="216" height="216" aria-hidden="true">
            {grid_lines}
            <rect x="2" y="2" width="20" height="20" fill="none" stroke-width=".06" stroke-dasharray=".4 .3" style="stroke: var(--ink)"></rect>
            <path d="{SPORTS[0][1]}" fill="none" stroke-width="1.6" stroke-linecap="butt" stroke-linejoin="miter" style="stroke: var(--ink)"></path>
          </svg>'''

rules = ''.join(f'<div style="display: flex; justify-content: space-between; gap: 16px; padding: 10px 0; border-top: 1px solid var(--line)"><span style="font-size: 13.5px">{a}</span><span class="mono" style="font-size: 11.5px; text-align: right">{b}</span></div>' for a, b in [
    ('Grid', '24 × 24 · 2 PX SAFE AREA'), ('Stroke', '1.6 AT 24 PX · 1.4 AT 48 PX'), ('Ends and corners', 'BUTT ENDS · MITRED'),
    ('Curves', 'ONLY WHERE THE THING IS ROUND'), ('Colour', 'INK ONLY · INVERTS ON INK'), ('Sizes', '16 · 20 · 24 · 48')])

body = f'''    <div style="display: flex; flex-direction: column; gap: 22px; width: 100%">
      <div style="display: flex; gap: 22px">
        <section style="flex: 1.15; background: var(--bg); color: var(--ink); padding: 28px 30px; display: flex; flex-direction: column; gap: 24px">
          <div style="display: flex; flex-direction: column; gap: 8px"><span class="eyebrow">SPORTS · 7</span><span class="h1">One mark per sport</span></div>
          <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); row-gap: 26px; column-gap: 12px">{sport_cells}</div>
          <div style="display: flex; flex-direction: column; gap: 10px"><span class="eyebrow">IN USE · SPORT PICKER</span><div style="display: flex; flex-wrap: wrap; gap: 6px">{chips}</div></div>
        </section>
        <section style="flex: 1; background: var(--bg); color: var(--ink); padding: 28px 30px; display: flex; flex-direction: column; gap: 22px">
          <div style="display: flex; flex-direction: column; gap: 8px"><span class="eyebrow">INTERFACE · {len(UI)}</span><span class="h1">UI icons</span></div>
          <div style="display: grid; grid-template-columns: repeat(8, minmax(0, 1fr)); border-top: 1px solid var(--line); border-left: 1px solid var(--line); color: var(--ink)">{ui_cells}</div>
        </section>
      </div>
      <section style="background: var(--bg); color: var(--ink); padding: 26px 30px; display: flex; gap: 40px; align-items: center">
        {construction}
        <div style="flex: 1; display: flex; flex-direction: column; gap: 8px">
          <span class="eyebrow">CONSTRUCTION</span>
          <span class="h1" style="font-size: 24px">Drawn like the logo — straight, sharp, one weight</span>
          <div style="display: flex; flex-direction: column; padding-top: 8px">{rules}</div>
        </div>
      </section>
    </div>'''

script = r"""
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white' }; }
  renderVals() { return { theme: this.state.theme, THEMES_JS }; }
}"""
build('Icons.dc.html', 'Stridian icon set', 1800, 1150, 'SYSTEM · ICON SET', body, script)
print('ok')
