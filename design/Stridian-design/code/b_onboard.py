from build import *
CAM = 'M4 8h3l2-3h6l2 3h3v11H4V8Zm8 9a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z'
GAL = 'M4 5h16v14H4V5Zm0 10 5-5 4 4 3-3 4 4M15.5 9.5h.01'
BELL = 'M6 17V11a6 6 0 1 1 12 0v6l2 2H4l2-2ZM10 21h4'
STUDENT = 'M12 3 2 8l10 5 10-5-10-5ZM5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5'
WHISTLE = 'M3 10h10a5 5 0 1 1-5 5V10M13 10l7-3'

extra_css = """
.caret{animation:blink 1s steps(2) infinite}
.sweep{position:absolute;height:10px;border-radius:5px;background:var(--ink);transform:rotate(140deg)}
"""

def primer(cap, step, ic, title, reasons, allow):
    rs = ''.join(f'''<div style="display: flex; gap: 14px; padding: 12px 0; border-top: 1px solid var(--line)"><span class="mono" style="font-size: 11px; color: var(--ink2); padding-top: 3px">0{i+1}</span><span style="font-size: 15px; line-height: 1.4">{r}</span></div>''' for i, r in enumerate(reasons))
    segs = ''.join(f'<span style="flex: 1; height: 3px; background: {"var(--ink)" if i <= step else "var(--line)"}"></span>' for i in range(3))
    return phone(cap, f'''        <div class="pad" style="gap: 22px; padding-bottom: 34px">
          <div style="display: flex; align-items: center; gap: 14px; height: 44px">
            <div style="display: flex; gap: 4px; width: 90px">{segs}</div>
            <span class="mono" style="font-size: 10.5px; letter-spacing: .12em; color: var(--ink2)">{step+1} OF 3</span>
            <span style="flex-grow: 1"></span>
            <button class="btn3" style="height: 44px">Skip</button>
          </div>
          <div style="position: relative; height: 200px; display: flex; align-items: center">
            <div style="position: relative; width: 150px; height: 167px">
              <svg viewBox="0 0 72 80" width="150" height="167" aria-hidden="true"><path d="M19 0H72V64L53 80H0V16Z" style="fill: var(--ink)"></path></svg>
              <span style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--bg)">{icon(ic, 64, 1.3)}</span>
            </div>
            <span class="sweep" style="left: 176px; top: 58px; width: 150px"></span>
            <span class="sweep" style="left: 206px; top: 96px; width: 110px; height: 8px"></span>
            <span class="sweep" style="left: 236px; top: 128px; width: 70px; height: 6px"></span>
          </div>
          <h1 class="h1" style="font-size: 32px">{title}</h1>
          <div style="display: flex; flex-direction: column">{rs}</div>
          <div style="margin-top: auto; display: flex; flex-direction: column; gap: 8px">
            <span class="mono" style="font-size: 10px; letter-spacing: .08em; color: var(--ink2); text-align: center; padding-bottom: 6px">YOU CAN CHANGE THIS LATER IN SETTINGS</span>
            <button class="btn">{allow}</button>
            <button class="btn3">Not now</button>
          </div>
        </div>''')

p11 = phone('11 · WELCOME · WHO ARE YOU', f'''        <div class="pad" style="gap: 20px; padding-bottom: 34px">
          <div style="display: flex; flex-direction: column; align-items: flex-start; gap: 18px; padding-top: 40px">
            <svg viewBox="0 0 100 100" width="96" height="96" aria-hidden="true"><path d="{{{{logoD}}}}" style="fill: var(--ink)"></path></svg>
            <span class="wm" style="font-size: 26px">STRIDIAN</span>
            <span style="font-size: 20px; line-height: 1.3; font-weight: 450; color: var(--ink2)">Sport-specific talent profiling — and a second coach in your pocket.</span>
          </div>
          <span class="eyebrow" style="padding-top: 18px">WHO’S SIGNING IN?</span>
          <div role="radiogroup" aria-label="Role" style="display: flex; flex-direction: column; gap: 10px">
            <sc-for list="{{{{roles}}}}" as="r" hint-placeholder-count="2">
              <button class="opt" role="radio" aria-checked="{{{{r.on}}}}" onClick="{{{{r.pick}}}}" style="display: flex; align-items: center; gap: 16px; padding: 18px 16px; border: 1px solid var(--ink); background: {{{{r.bg}}}}; color: {{{{r.fg}}}}">
                <svg viewBox="0 0 24 24" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.4" aria-hidden="true" style="flex-shrink: 0"><path d="{{{{r.icon}}}}"></path></svg>
                <span style="flex-grow: 1; display: flex; flex-direction: column; gap: 4px; text-align: left"><span style="font-size: 18px; font-weight: 600">{{{{r.label}}}}</span><span style="font-size: 12.5px; opacity: .75">{{{{r.sub}}}}</span></span>
                <span style="width: 16px; height: 16px; box-sizing: border-box; border: 1.5px solid currentColor; transform: rotate(45deg); display: flex; align-items: center; justify-content: center"><span style="width: 6px; height: 6px; background: {{{{r.dot}}}}"></span></span>
              </button>
            </sc-for>
          </div>
          <button class="btn" style="margin-top: auto">Continue as {{{{roleLower}}}}</button>
        </div>''')

p12 = phone('12 · SIGN IN', f'''        <div class="pad" style="gap: 20px; padding-bottom: 34px">
          {BACK('Back')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">{{{{signin.eyebrow}}}}</span>
            <h1 class="h1">Sign in</h1>
          </div>
          <label style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">{{{{signin.emailLabel}}}}</span>
            <input class="fld" type="email" placeholder="{{{{signin.emailPh}}}}">
          </label>
          <label style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">STRIDIAN PASSWORD</span>
            <input class="fld" type="password" value="••••••••••">
            <span style="font-size: 12.5px; line-height: 1.4; color: var(--ink2)">{{{{signin.help}}}}</span>
          </label>
          <div style="display: flex; flex-direction: column; gap: 6px">
            <button class="btn">Sign in</button>
            <button class="btn3">Forgot your password?</button>
          </div>
          <div style="display: flex; align-items: center; gap: 12px"><span style="flex: 1; height: 1px; background: var(--line)"></span><span class="mono" style="font-size: 10px; letter-spacing: .12em; color: var(--ink2)">NEW HERE</span><span style="flex: 1; height: 1px; background: var(--line)"></span></div>
          <button class="btn2">{{{{signin.newCta}}}}</button>
          <span style="margin-top: auto; font-size: 12px; line-height: 1.5; color: var(--ink2); text-align: center">By continuing you agree to the <a href="/terms.html">Terms of use</a> and <a href="/privacy.html">Privacy policy</a>.</span>
        </div>''')

p13 = phone('13 · EMAIL CODE', f'''        <div class="pad" style="gap: 22px; padding-bottom: 34px">
          {BACK('Back')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">PROVE IT’S YOUR EMAIL</span>
            <h1 class="h1">Check your university inbox</h1>
          </div>
          <span style="font-size: 15px; line-height: 1.45; color: var(--ink2)">We sent a 6-digit code to <span style="color: var(--ink); font-weight: 600">aarav.m@srmist.edu.in</span>. It works for 15 minutes.</span>
          <div role="group" aria-label="6-digit code" style="display: flex; gap: 8px">
            <sc-for list="{{{{code}}}}" as="d" hint-placeholder-count="6">
              <span class="mono" style="flex: 1; height: 62px; box-sizing: border-box; border: 1px solid var(--ink); border-bottom-width: {{{{d.bw}}}}px; display: flex; align-items: center; justify-content: center; font-size: 26px; font-weight: 500">{{{{d.ch}}}}<sc-if value="{{{{d.caret}}}}" hint-placeholder-val="{{{{false}}}}"><span class="caret" style="width: 2px; height: 28px; background: var(--ink)"></span></sc-if></span>
            </sc-for>
          </div>
          <label style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">NEW STRIDIAN PASSWORD</span>
            <input class="fld" type="password" placeholder="At least 8 characters">
          </label>
          <button class="btn" aria-disabled="true" style="opacity: .35">Set password and sign in</button>
          <span class="mono" style="font-size: 11px; letter-spacing: .08em; color: var(--ink2); text-align: center">SEND AGAIN IN 0:42</span>
          <span style="margin-top: auto; font-size: 12.5px; line-height: 1.5; color: var(--ink2)">Five wrong tries and the code stops working — just ask for a new one.</span>
        </div>''')

p14 = primer('14 · CAMERA · WHY WE ASK', 0, CAM, 'Record drills right here', [
    'Film a drill and send it straight for pose analysis.',
    'The camera is only on while you’re recording.',
    'Your clips are seen by you and your sport’s coaches.'], 'Allow camera')
p15 = primer('15 · GALLERY · WHY WE ASK', 1, GAL, 'Pick clips and photos', [
    'Upload drill videos you’ve already filmed.',
    'Add photos of certificates for your coach to verify.',
    'Stridian only sees the files you choose.'], 'Allow photo access')
p16 = primer('16 · NOTIFICATIONS · WHY WE ASK', 2, BELL, 'Know when it’s ready', [
    'Analysis runs on your coach’s computer — we’ll tell you when a video is done.',
    'Hear when your coach verifies you or an achievement.',
    'A nudge for this week’s focus, so the streak keeps going.'], 'Turn on notifications')

script = f"""
const R = {{ student: ['Student', 'Sign in with your university email', '{STUDENT}'], coach: ['Coach', 'For coaches and admins of a sport', '{WHISTLE}'] }};
class Component extends DCLogic {{
  constructor(props) {{ super(props); this.state = {{ theme: 'white', role: 'student' }}; }}
  renderVals() {{
    const st = this.state;
    const roles = Object.keys(R).map(k => ({{ label: R[k][0], sub: R[k][1], icon: R[k][2], on: st.role === k,
      bg: st.role === k ? 'var(--ink)' : 'transparent', fg: st.role === k ? 'var(--bg)' : 'var(--ink)', dot: st.role === k ? 'currentColor' : 'transparent',
      pick: () => this.setState({{ role: k }}) }}));
    const signin = st.role === 'student'
      ? {{ eyebrow: 'STUDENT', emailLabel: 'UNIVERSITY EMAIL', emailPh: 'name@srmist.edu.in', help: 'Your password for Stridian — not your university one. Stridian never sees that.', newCta: 'Sign up with a code' }}
      : {{ eyebrow: 'COACH', emailLabel: 'EMAIL', emailPh: 'you@example.com', help: 'Coaches pick their sport once, when they sign up.', newCta: 'Create a coach account' }};
    const code = ['4', '8', '1', '7', '', ''].map((ch, i) => ({{ ch, caret: i === 4, bw: i === 4 ? 3 : 1 }}));
    return {{ theme: st.theme, logoD: LOGO_D, roles, roleLower: R[st.role][0].toLowerCase(), signin, code, THEMES_JS }};
  }}
}}"""
build('Onboarding.dc.html', 'Stridian onboarding', 2780, 1050, 'ONBOARDING · ROLE, SIGN IN, PERMISSIONS', '\n'.join([p11, p12, p13, p14, p15, p16]), script, extra_css=extra_css)
print('ok')
