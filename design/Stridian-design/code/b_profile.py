from build import *
from icons import UI
U = dict(UI)
from b_states import tabbar

extra_css = """
.sw{all:unset;box-sizing:border-box;position:relative;width:48px;height:28px;border:1.5px solid var(--ink);cursor:pointer;flex-shrink:0;transition:background .18s}
.sw span{position:absolute;top:3px;width:18px;height:18px;transition:left .22s cubic-bezier(.5,0,.2,1),background .18s}
.sw:focus-visible{outline:2px solid var(--ink);outline-offset:3px}
.row{display:flex;align-items:center;gap:14px;padding:13px 0;border-top:1px solid var(--line)}
.lbl{flex-grow:1;display:flex;flex-direction:column;gap:3px;min-width:0}
"""
TILE = 'M19 0H72V64L53 80H0V16Z'
CHEV = icon(U['Next'], 18, 1.6)
LOCK = icon(U['Lock'], 16, 1.6)

def rec(label, value, locked=False):
    right = f'<span style="color: var(--ink2)">{LOCK}</span>' if locked else ''
    return f'<div class="row"><div class="lbl"><span class="mono" style="font-size: 10px; letter-spacing: .1em; color: var(--ink2)">{label}</span><span style="font-size: 15px">{value}</span></div>{right}</div>'

p1 = phone('01 · PROFILE', f'''        <div class="pad" style="gap: 18px">
          HEADER_PLACEHOLDER
          <div style="display: flex; gap: 16px; align-items: center">
            <div style="position: relative; width: 72px; height: 80px; flex-shrink: 0">
              <svg viewBox="-1 -1 74 82" width="72" height="80" aria-hidden="true"><path d="{TILE}" style="fill: var(--ink)"></path></svg>
              <span class="wm" style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--bg); font-size: 18px; letter-spacing: .08em">AM</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px">
              <span style="font-size: 24px; font-weight: 600; font-stretch: 112%">Aarav Menon</span>
              <span class="mono" style="font-size: 10.5px; letter-spacing: .08em; color: var(--ink2)">WINGER · MEN’S TEAM · VERIFIED</span>
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px">
            <div style="display: flex; justify-content: space-between"><span class="eyebrow">PROFILE 90% COMPLETE</span><span class="mono" style="font-size: 10.5px; letter-spacing: .08em">9 / 10</span></div>
            <div style="display: flex; gap: 3px">{''.join(f'<span style="flex: 1; height: 6px; background: {"var(--ink)" if i < 9 else "transparent"}; border: 1px {"solid" if i < 9 else "dashed"} var(--ink); box-sizing: border-box"></span>' for i in range(10))}</div>
            <button class="opt" style="display: flex; align-items: center; justify-content: space-between; padding: 10px 12px; border: 1px dashed var(--ink); font: 500 14px/1.3 Archivo, sans-serif">Add a parent’s mobile number {CHEV}</button>
          </div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding-bottom: 4px">UNIVERSITY RECORD</span>
            {rec('RA NUMBER', 'RA2211003010214', True)}
            {rec('DATE OF BIRTH', '14 Mar 2005 · 21 years', True)}
            {rec('AADHAAR', 'XXXX XXXX 4821', True)}
            {rec('HIGHEST LEVEL PLAYED', 'Zonal')}
          </div>
          <span class="mono" style="font-size: 10px; line-height: 1.6; color: var(--ink2)">LOCKED FIELDS ARE CHANGED BY AN ADMIN.</span>
        </div>
        {tabbar(3)}''')

p2 = phone('02 · EDIT PROFILE', f'''        <div class="pad" style="gap: 18px">
          <div style="display: flex; align-items: center; justify-content: space-between">
            {BACK('Profile')}
            <button class="btn3" style="color: var(--ink); font-weight: 600">Save</button>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">EDIT PROFILE</span>
            <h1 class="h1">Your details</h1>
          </div>
          <div style="display: flex; align-items: center; gap: 14px">
            <div class="hatch" style="width: 64px; height: 64px; border: 1px solid var(--ink); display: flex; align-items: center; justify-content: center">{icon(U['Camera'], 24, 1.5)}</div>
            <div style="display: flex; flex-direction: column; gap: 3px"><button class="opt" style="font: 600 14px/1 Archivo, sans-serif; text-decoration: underline; text-underline-offset: 3px">Change photo</button><span class="mono" style="font-size: 10px; letter-spacing: .06em; color: var(--ink2)">SHRUNK ON YOUR PHONE BEFORE UPLOAD</span></div>
          </div>
          <label style="display: flex; flex-direction: column; gap: 7px"><span class="eyebrow">MOBILE</span><input class="fld" value="98765 43210"></label>
          <label style="display: flex; flex-direction: column; gap: 7px"><span class="eyebrow">PERSONAL EMAIL</span><input class="fld" value="aarav.menon@gmail.com"></label>
          <label style="display: flex; flex-direction: column; gap: 7px"><span class="eyebrow">BLOOD GROUP</span><select class="fld" style="appearance: none; -webkit-appearance: none"><option>B+</option><option>A+</option><option>O+</option></select></label>
          <label style="display: flex; flex-direction: column; gap: 7px"><span class="eyebrow">PARENT’S MOBILE</span><input class="fld" placeholder="Needed — one parent’s number" value=""><span style="font-size: 12px; color: var(--ink2)">Any common format works — we store ten digits.</span></label>
          <div style="margin-top: auto; padding-bottom: 34px"><button class="btn" style="width: 100%">Save changes</button></div>
        </div>''')

def toggle_row(title, sub, key):
    return f'''<div class="row"><div class="lbl"><span style="font-size: 15px">{title}</span><span style="font-size: 12px; color: var(--ink2)">{sub}</span></div>
              <button class="sw" role="switch" aria-checked="{{{{{key}.on}}}}" aria-label="{title}" onClick="{{{{{key}.flip}}}}" style="background: {{{{{key}.bg}}}}"><span style="left: {{{{{key}.x}}}}px; background: {{{{{key}.knob}}}}"></span></button></div>'''

def seg(key, label):
    return f'''<div style="display: flex; flex-direction: column; gap: 8px; padding: 12px 0; border-top: 1px solid var(--line)">
              <span style="font-size: 15px">{label}</span>
              <div style="display: flex; border: 1px solid var(--ink)">
                <sc-for list="{{{{{key}}}}}" as="o" hint-placeholder-count="3"><button class="opt" onClick="{{{{o.pick}}}}" aria-pressed="{{{{o.on}}}}" style="flex: 1; height: 38px; display: flex; align-items: center; justify-content: center; gap: 6px; font: 500 11px/1 'IBM Plex Mono', monospace; letter-spacing: .08em; background: {{{{o.bg}}}}; color: {{{{o.fg}}}}">{{{{o.label}}}}</button></sc-for>
              </div>
            </div>'''

p3 = phone('03 · SETTINGS', f'''        <div class="pad" style="gap: 14px">
          {BACK('Profile')}
          <div style="display: flex; flex-direction: column; gap: 8px"><span class="eyebrow">SETTINGS</span><h1 class="h1">Settings</h1></div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding: 4px 0 4px">APPEARANCE</span>
            {seg('themeOpts', 'Theme')}
            {seg('motionOpts', 'Motion')}
          </div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding: 8px 0 4px">NOTIFICATIONS</span>
            {toggle_row('Video analysed', 'When a clip is ready', 'n1')}
            {toggle_row('Coach updates', 'Verification and achievements', 'n2')}
            {toggle_row('Weekly focus nudge', 'One reminder before the week ends', 'n3')}
          </div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding: 8px 0 4px">ACCOUNT</span>
            <button class="opt row" style="display: flex">{icon(U['Lock'], 20)}<span class="lbl" style="font-size: 15px">Change password</span>{CHEV}</button>
            <button class="opt row" style="display: flex">{icon(U['Sign out'], 20)}<span class="lbl" style="font-size: 15px">Sign out</span></button>
          </div>
          <div style="display: flex; gap: 16px; padding-top: 4px"><a href="/privacy.html" class="mono" style="font-size: 10.5px; letter-spacing: .08em">PRIVACY POLICY</a><a href="/terms.html" class="mono" style="font-size: 10.5px; letter-spacing: .08em">TERMS OF USE</a><span style="flex-grow: 1"></span><span class="mono" style="font-size: 10.5px; color: var(--ink2)">V 1.0</span></div>
        </div>''')

p4 = phone('04 · COACH · YOUR DETAILS', f'''        <div class="pad" style="gap: 18px">
          {BACK('Squad')}
          <div style="display: flex; gap: 16px; align-items: center">
            <div style="position: relative; width: 72px; height: 80px; flex-shrink: 0">
              <svg viewBox="-1 -1 74 82" width="72" height="80" aria-hidden="true"><path d="{TILE}" style="fill: none; stroke: var(--ink)" stroke-width="1.4"></path></svg>
              <span class="wm" style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 18px; letter-spacing: .08em">RK</span>
            </div>
            <div style="display: flex; flex-direction: column; gap: 5px">
              <span style="font-size: 24px; font-weight: 600; font-stretch: 112%">R. Krishnan</span>
              <span class="mono" style="font-size: 10.5px; letter-spacing: .08em; color: var(--ink2)">HEAD COACH · FOOTBALL</span>
            </div>
          </div>
          <div style="background: var(--ink); color: var(--bg); padding: 16px; display: flex; align-items: center; justify-content: space-between">
            <div style="display: flex; flex-direction: column; gap: 6px"><span class="mono" style="font-size: 10px; letter-spacing: .12em; opacity: .75">ENROLMENT CODE · FOOTBALL</span><span class="mono" style="font-size: 30px; font-weight: 500; letter-spacing: .2em">K7QM3X</span></div>
            <button class="opt" aria-label="Share code" style="width: 44px; height: 44px; border: 1px solid var(--bg); display: flex; align-items: center; justify-content: center">{icon(U['Share'], 20)}</button>
          </div>
          <button class="btn3" style="align-self: flex-start; height: 32px; color: var(--ink); text-decoration: underline; text-underline-offset: 3px">Make a new code</button>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding-bottom: 4px">YOUR DETAILS</span>
            {rec('EMPLOYEE ID', 'SRM-SP-0412')}
            {rec('EMAIL', 'krishnan.r@srmist.edu.in')}
            {rec('MOBILE', '94440 12345')}
            {rec('SPORT', 'Football', True)}
          </div>
          <div style="display: flex; gap: 10px">
            <button class="btn2" style="flex: 1">{icon(U['Download'], 18)}Squad as Excel</button>
            <button class="btn2" style="width: 52px" aria-label="Settings">{icon(U['Settings'], 20)}</button>
          </div>
        </div>''')

HEADER = '''<div style="display: flex; align-items: center; justify-content: space-between">
            <div style="display: flex; align-items: center; gap: 9px">
              <svg viewBox="0 0 100 100" width="22" height="22" aria-hidden="true"><path d="{{logoD}}" style="fill: var(--ink)"></path></svg>
              <span class="wm" style="font-size: 12px">STRIDIAN</span>
            </div>
            <button class="opt" aria-label="Settings" style="width: 44px; height: 44px; display: flex; align-items: center; justify-content: flex-end">''' + icon(U['Settings'], 22) + '''</button>
          </div>'''
p1 = p1.replace('HEADER_PLACEHOLDER', HEADER).replace('LOCK_INLINE', '')

script = r"""
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', mode: 'white', motion: 'system', n1: true, n2: true, n3: false }; }
  renderVals() {
    const st = this.state;
    const opts = (key, list) => list.map(([k, label]) => ({ label, on: st[key] === k, bg: st[key] === k ? 'var(--ink)' : 'transparent', fg: st[key] === k ? 'var(--bg)' : 'var(--ink)',
      pick: () => this.setState(key === 'mode' ? { mode: k, theme: k === 'system' ? 'white' : k } : { [key]: k }) }));
    const sw = k => ({ on: st[k], bg: st[k] ? 'var(--ink)' : 'transparent', knob: st[k] ? 'var(--bg)' : 'var(--ink)', x: st[k] ? 23 : 3, flip: () => this.setState({ [k]: !st[k] }) });
    return { theme: st.theme, logoD: LOGO_D,
      themeOpts: opts('mode', [['white', 'WHITE'], ['dark', 'DARK'], ['system', 'SYSTEM']]),
      motionOpts: opts('motion', [['system', 'SYSTEM'], ['full', 'FULL'], ['reduced', 'REDUCED']]),
      n1: sw('n1'), n2: sw('n2'), n3: sw('n3'),
      themes: [['white', 'White'], ['dark', 'Dark']].map(([k, label]) => ({ label, on: st.theme === k, cls: st.theme === k ? 'on' : '', pick: () => this.setState({ theme: k, mode: k }) })) };
  }
}"""
build('Profile.dc.html', 'Stridian profile and settings', 1864, 1050, 'PROFILE AND SETTINGS', '\n'.join([p1, p2, p3, p4]), script, extra_css=extra_css)
print('ok')
