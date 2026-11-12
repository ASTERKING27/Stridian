from build import *

I = {
  'target': 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Zm0-4a5 5 0 1 0 0-10 5 5 0 0 0 0 10Zm0-4a1 1 0 1 0 0-2 1 1 0 0 0 0 2Z',
  'card': 'M5 3h10l4 4v14H5V3ZM15 3v4h4M8 11h8M8 15h8M8 19h5',
  'medal': 'M8 3h8l-2 6h-4L8 3Zm4 6a6 6 0 1 0 0 12 6 6 0 0 0 0-12Z',
  'person': 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM4.5 20.5c.8-3.6 3.8-6 7.5-6s6.7 2.4 7.5 6',
  'film': 'M3 6a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2v12a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V6ZM3 10h18M3 15h18M8 4v16M16 4v16',
  'wifioff': 'M2 8.5a15 15 0 0 1 20 0M5.5 12a10 10 0 0 1 13 0M9 15.5a5 5 0 0 1 6 0M12 19h.01M3 3l18 18',
  'server': 'M4 4h16v6H4V4Zm0 10h16v6H4v-6ZM7 7h.01M7 17h.01M11 7h5M11 17h5',
  'alert': 'M12 3 2 21h20L12 3ZM12 10v5M12 17.5v.5',
  'retry': 'M4 12a8 8 0 0 1 14-5.3M20 4v4h-4M20 12a8 8 0 0 1-14 5.3M4 20v-4h4',
  'check': 'M5 12.5 10 17 19 7',
}
TABS = [('Dashboard', 'Dashboard', I['target']), ('My report', 'Report', I['card']), ('Achievements', 'Achievements', I['medal']), ('Profile', 'Profile', I['person'])]

def tabbar(active):
    short = TABS[active][1]
    aw = max(len(short) * 7 + 46, 96); iw = (360 - aw) / 3
    x = 4; out = []
    for i, (label, sh, ic) in enumerate(TABS):
        on = i == active; w = aw if on else iw
        col = 'var(--bg)' if on else 'var(--ink)'
        lab = f'<span style="overflow: hidden; white-space: nowrap">{sh}</span>' if on else ''
        cur = ' aria-current="page"' if on else ''
        out.append(f'<button class="tab" aria-label="{label}"{cur} style="left: {x:.2f}px; width: {w:.2f}px; gap: {7 if on else 0}px; color: {col}">{icon(ic, 20, 1.6)}{lab}</button>')
        if on: ind = (x, w)
        x += w
    return f'''<nav aria-label="Sections" style="position: absolute; left: 10px; right: 10px; bottom: 18px; height: 60px; border-radius: 30px; background: var(--glass); backdrop-filter: blur(18px) saturate(1.3); -webkit-backdrop-filter: blur(18px) saturate(1.3); border: 1px solid var(--glassEdge); box-shadow: var(--shadow), inset 0 1px 0 var(--hi); box-sizing: border-box">
          <span style="position: absolute; top: 3px; height: 52px; border-radius: 26px; background: var(--ink); left: {ind[0]:.2f}px; width: {ind[1]:.2f}px"></span>
          {''.join(out)}
        </nav>'''

HEADER = '''<div style="display: flex; align-items: center; justify-content: space-between">
            <div style="display: flex; align-items: center; gap: 9px">
              <svg viewBox="0 0 100 100" width="22" height="22" aria-hidden="true"><path d="{{logoD}}" style="fill: var(--ink)"></path></svg>
              <span class="wm" style="font-size: 12px">STRIDIAN</span>
            </div>
            <span class="mono" style="font-size: 10.5px; letter-spacing: .1em; color: var(--ink2)">FOOTBALL · MEN</span>
          </div>'''

def tile(ic, dashed=True, size=132):
    h = round(size * 80 / 72)
    st = 'fill: none; stroke: var(--ink); stroke-dasharray: 4 3' if dashed else 'fill: var(--ink)'
    col = 'var(--ink)' if dashed else 'var(--bg)'
    return f'''<div style="position: relative; width: {size}px; height: {h}px; flex-shrink: 0">
              <svg viewBox="-1 -1 74 82" width="{size}" height="{h}" aria-hidden="true"><path d="M19 0H72V64L53 80H0V16Z" stroke-width="1.2" style="{st}"></path></svg>
              <span style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: {col}">{icon(ic, round(size * .42), 1.3)}</span>
            </div>'''

SWEEP = '''<span class="sweep" style="left: {x}px; top: {y}px; width: {w}px; height: {h}px; opacity: {o}"></span>'''
def sweeps(x0, y0):
    return ''.join(SWEEP.format(x=x0 + i * 30, y=y0 + i * 36, w=w, h=h, o=o) for i, (w, h, o) in enumerate([(130, 9, 1), (96, 7, .6), (60, 5, .3)]))

extra_css = """
.sweep{position:absolute;border-radius:6px;background:var(--ink);transform:rotate(140deg)}
.sk{position:relative;overflow:hidden;background:var(--soft)}
.sk::after{content:'';position:absolute;top:-60%;bottom:-60%;width:46px;left:-80px;background:var(--line);transform:rotate(40deg);animation:skw 1.6s cubic-bezier(.5,0,.2,1) infinite;animation-delay:inherit}
@keyframes skw{0%{left:-90px}70%,100%{left:calc(100% + 40px)}}
.lap{animation:lap 1s linear infinite}
@keyframes lap{to{stroke-dashoffset:-100}}
.dim{opacity:.4;pointer-events:none}
.pulse{animation:pulse 1.2s ease-in-out infinite}
@keyframes pulse{50%{opacity:.25}}
"""

# ---------------- empty states ----------------
e1 = phone('01 · EMPTY · NO VIDEOS YET', f'''        <div class="pad" style="gap: 20px; padding-bottom: 34px">
          {BACK('My report')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">DRILL VIDEOS</span>
            <h1 class="h1">Your clips</h1>
          </div>
          <div style="position: relative; height: 170px; display: flex; align-items: center">
            {tile(I['film'])}
            {sweeps(170, 44)}
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <span style="font-size: 22px; font-weight: 600; font-stretch: 112%">No clips yet</span>
            <span style="font-size: 15px; line-height: 1.45; color: var(--ink2)">Film one drill side-on and Stridian reads your technique — jump height, knee angles, left–right balance.</span>
          </div>
          <div style="display: flex; flex-direction: column">
            <div style="display: flex; justify-content: space-between; padding: 11px 0; border-top: 1px solid var(--line)"><span style="font-size: 14px">Takes about</span><span class="mono" style="font-size: 13px">10 SECONDS OF VIDEO</span></div>
            <div style="display: flex; justify-content: space-between; padding: 11px 0; border-top: 1px solid var(--line)"><span style="font-size: 14px">Results in</span><span class="mono" style="font-size: 13px">THE NEXT SESSION</span></div>
          </div>
          <div style="margin-top: auto; display: flex; flex-direction: column; gap: 6px">
            <button class="btn">{icon('M12 5v14M5 12h14', 20, 1.8)}Add your first video</button>
            <button class="btn3">What makes a good clip?</button>
          </div>
        </div>''')

e2 = phone('02 · EMPTY · NO RESULTS YET', f'''        <div class="pad" style="gap: 18px">
          {HEADER}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">MY REPORT</span>
            <h1 class="h1" style="font-size: 26px; font-weight: 500; line-height: 1.18">Your coach hasn’t verified you yet. Once they log your tests, your full breakdown unlocks right here.</h1>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px; padding: 14px; border: 1px dashed var(--ink2)">
            <div style="display: flex; justify-content: space-between; align-items: center"><span class="eyebrow">BEST POSITION</span><span class="mono" style="font-size: 20px; color: var(--ink2)">— —</span></div>
            <div style="height: 92px; border: 1px dashed var(--line); display: flex; align-items: center; justify-content: center"><span class="mono" style="font-size: 10px; letter-spacing: .12em; color: var(--ink2)">YOUR POSITION ON THE PITCH</span></div>
          </div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding-bottom: 6px">WHAT HAPPENS NEXT</span>
            <div style="display: flex; align-items: center; gap: 12px; padding: 11px 0; border-top: 1px solid var(--line)"><span style="width: 22px; height: 22px; background: var(--ink); color: var(--bg); display: flex; align-items: center; justify-content: center">{icon(I['check'], 14, 2)}</span><span style="flex-grow: 1; font-size: 14.5px">You enrolled with the squad code</span></div>
            <div style="display: flex; align-items: center; gap: 12px; padding: 11px 0; border-top: 1px solid var(--line)"><span class="pulse" style="width: 22px; height: 22px; box-sizing: border-box; border: 1.5px solid var(--ink)"></span><span style="flex-grow: 1; font-size: 14.5px">Your coach verifies your position</span><span class="mono" style="font-size: 10px; letter-spacing: .08em; color: var(--ink2)">WAITING</span></div>
            <div style="display: flex; align-items: center; gap: 12px; padding: 11px 0; border-top: 1px solid var(--line)"><span style="width: 22px; height: 22px; box-sizing: border-box; border: 1px dashed var(--ink2)"></span><span style="flex-grow: 1; font-size: 14.5px; color: var(--ink2)">Your first tests are logged</span></div>
          </div>
          <button class="btn2">Finish your profile meanwhile</button>
        </div>
        {tabbar(1)}''')

e3 = phone('03 · EMPTY · NO ACHIEVEMENTS YET', f'''        <div class="pad" style="gap: 18px">
          {HEADER}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">ACHIEVEMENTS · 0 / 13</span>
            <h1 class="h1">Nothing here yet</h1>
          </div>
          <span style="font-size: 15px; line-height: 1.45; color: var(--ink2)">Badges unlock as you go. The first one, <span style="color: var(--ink); font-weight: 600">First rep</span>, arrives with your first test result.</span>
          <div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px 10px; padding: 4px 0">
            <sc-for list="{{{{locked}}}}" as="b" hint-placeholder-count="8">
              <div style="display: flex; justify-content: center; opacity: {{{{b.o}}}}">
                <svg viewBox="-1 -1 74 82" width="62" height="69" aria-hidden="true"><path d="M19 0H72V64L53 80H0V16Z" fill="none" stroke-width="1.4" stroke-dasharray="4 3" style="stroke: var(--ink2)"></path><g transform="translate(20 24) scale(1.35)"><path d="{{{{b.icon}}}}" fill="none" stroke-width="1.6" style="stroke: var(--ink2)"></path></g></svg>
              </div>
            </sc-for>
          </div>
          <div style="border: 1px solid var(--ink); padding: 14px 16px; display: flex; flex-direction: column; gap: 10px">
            <span class="eyebrow">A HEAD START</span>
            <span style="font-size: 15px; line-height: 1.4">Played at a zonal or state event? Add the certificate — once your coach verifies it, it counts.</span>
            <button class="btn" style="height: 46px">Add a certificate</button>
          </div>
        </div>
        {tabbar(2)}''')

# ---------------- loading skeletons ----------------
def sk(w, h, d, extra=''):
    return f'<div class="sk" style="width: {w}; height: {h}px; animation-delay: {d}ms; {extra}"></div>'

l1 = phone('04 · LOADING · DASHBOARD', f'''        <div class="pad" style="gap: 22px">
          <div style="display: flex; align-items: center; justify-content: space-between">
            <div style="display: flex; align-items: center; gap: 9px">
              <svg viewBox="-4 -4 108 108" width="22" height="22" aria-hidden="true"><path d="{{{{logoD}}}}" pathLength="100" class="lap" fill="none" stroke-width="7" stroke-linejoin="miter" stroke-miterlimit="12" style="stroke: var(--ink); stroke-dasharray: 26 74"></path></svg>
              <span class="wm" style="font-size: 12px">STRIDIAN</span>
            </div>
            <span class="mono" style="font-size: 10.5px; letter-spacing: .1em; color: var(--ink2)">LOADING</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            {sk('140px', 10, 0)}
            {sk('100%', 26, 60)}
            {sk('92%', 26, 120)}
            {sk('58%', 26, 180)}
          </div>
          <div style="display: flex; align-items: center; gap: 24px; padding-top: 18px; border-top: 1px solid var(--line)">
            <div class="sk" style="width: 112px; height: 112px; border-radius: 56px; animation-delay: 240ms; flex-shrink: 0"></div>
            <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 10px">{sk('100%', 11, 260)}{sk('100%', 11, 290)}{sk('100%', 11, 320)}{sk('100%', 11, 350)}{sk('100%', 11, 380)}</div>
          </div>
          <div style="border: 1px solid var(--line); padding: 14px 16px; display: flex; flex-direction: column; gap: 9px">{sk('120px', 10, 420)}{sk('140px', 18, 460)}{sk('180px', 10, 500)}</div>
          <div style="display: flex; flex-direction: column; gap: 0">
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-top: 1px solid var(--line)"><div style="display: flex; flex-direction: column; gap: 7px; width: 60%">{sk('100%', 13, 560)}{sk('60%', 9, 580)}</div>{sk('56px', 15, 600)}</div>
            <div style="display: flex; justify-content: space-between; align-items: center; padding: 14px 0; border-top: 1px solid var(--line)"><div style="display: flex; flex-direction: column; gap: 7px; width: 70%">{sk('100%', 13, 640)}{sk('50%', 9, 660)}</div>{sk('56px', 15, 680)}</div>
          </div>
        </div>
        {tabbar(0)}''')

l2 = phone('05 · LOADING · MY REPORT', f'''        <div class="pad" style="gap: 20px">
          <div style="display: flex; align-items: center; justify-content: space-between">
            <div style="display: flex; align-items: center; gap: 9px">
              <svg viewBox="-4 -4 108 108" width="22" height="22" aria-hidden="true"><path d="{{{{logoD}}}}" pathLength="100" class="lap" fill="none" stroke-width="7" stroke-linejoin="miter" stroke-miterlimit="12" style="stroke: var(--ink); stroke-dasharray: 26 74"></path></svg>
              <span class="wm" style="font-size: 12px">STRIDIAN</span>
            </div>
            <span class="mono" style="font-size: 10.5px; letter-spacing: .1em; color: var(--ink2)">LOADING</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            {sk('150px', 10, 0)}
            <div style="display: flex; justify-content: space-between; align-items: flex-end">{sk('180px', 34, 60)}{sk('48px', 30, 90)}</div>
            {sk('100%', 12, 140)}{sk('80%', 12, 170)}
          </div>
          <div class="sk" style="width: 346px; height: 222px; animation-delay: 220ms; flex-shrink: 0">
            <svg viewBox="0 0 100 64" width="346" height="222" aria-hidden="true" style="position: absolute; inset: 0"><rect x="2" y="2" width="96" height="60" fill="none" stroke-width=".5" style="stroke: var(--line)"></rect><line x1="50" y1="2" x2="50" y2="62" stroke-width=".5" style="stroke: var(--line)"></line><circle cx="50" cy="32" r="8" fill="none" stroke-width=".5" style="stroke: var(--line)"></circle></svg>
          </div>
          <div style="display: flex; flex-direction: column">
            {sk('90px', 10, 320, 'margin-bottom: 10px')}
            <div style="display: flex; align-items: center; gap: 14px; padding: 13px 0; border-top: 1px solid var(--line)">{sk('45%', 14, 360)}<span style="flex-grow: 1"></span>{sk('90px', 5, 380)}{sk('24px', 14, 400)}</div>
            <div style="display: flex; align-items: center; gap: 14px; padding: 13px 0; border-top: 1px solid var(--line)">{sk('55%', 14, 440)}<span style="flex-grow: 1"></span>{sk('90px', 5, 460)}{sk('24px', 14, 480)}</div>
          </div>
        </div>
        {tabbar(1)}''')

# ---------------- errors ----------------
r1 = phone('06 · NO INTERNET', f'''        <div role="status" style="position: absolute; left: 0; right: 0; top: 0; padding: 52px 22px 12px; background: var(--ink); color: var(--bg); display: flex; align-items: center; gap: 12px; z-index: 2">
          {icon(I['wifioff'], 20, 1.6)}
          <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 3px"><span style="font-size: 14px; font-weight: 600">You’re offline</span><span class="mono" style="font-size: 10px; letter-spacing: .06em; opacity: .75">SHOWING WHAT WAS SAVED AT 18:40</span></div>
          <button class="opt mono" style="font-size: 10.5px; letter-spacing: .1em; padding: 8px 10px; border: 1px solid var(--bg)">RETRY</button>
        </div>
        <div class="pad" style="gap: 22px; padding-top: 128px">
          <div style="display: flex; flex-direction: column; gap: 10px">
            <span class="eyebrow">YOUR SECOND COACH</span>
            <h1 style="margin: 0; font-size: 27px; line-height: 1.16; font-weight: 500; letter-spacing: -.012em">Zonal level, locked in. 3/5 of what matters is already at State.</h1>
          </div>
          <div style="border: 1px solid var(--ink); padding: 14px 16px; display: flex; align-items: center; justify-content: space-between">
            <div style="display: flex; flex-direction: column; gap: 5px"><span class="eyebrow">THIS WEEK'S FOCUS</span><span style="font-size: 18px; font-weight: 600">30m Sprint</span><span style="font-size: 12px; color: var(--ink2)">2 of 3 sessions</span></div>
            <button class="opt dim mono" aria-disabled="true" style="font-size: 10.5px; letter-spacing: .08em; padding: 9px 11px; border: 1px solid var(--ink)">LOG SESSION</button>
          </div>
          <div style="display: flex; gap: 12px; padding: 12px 14px; border: 1px dashed var(--ink)">
            {icon(I['alert'], 18, 1.6)}
            <span style="font-size: 13px; line-height: 1.45">Logging sessions and uploading videos need a connection. Everything else you can still read.</span>
          </div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding-bottom: 8px">NEXT LEVEL</span>
            <div style="display: flex; justify-content: space-between; padding: 12px 0; border-top: 1px solid var(--line)"><span style="font-size: 15px">30m Sprint</span><span class="mono" style="font-size: 15px">4.38 s</span></div>
            <div style="display: flex; justify-content: space-between; padding: 12px 0; border-top: 1px solid var(--line)"><span style="font-size: 15px">Countermovement jump</span><span class="mono" style="font-size: 15px">36 cm</span></div>
          </div>
        </div>
        {tabbar(0)}''')

r2 = phone('07 · SERVER DOWN', f'''        <div class="pad" style="gap: 22px; padding-bottom: 34px">
          <div style="height: 44px"></div>
          <div style="position: relative; height: 170px; display: flex; align-items: center">
            {tile(I['server'])}
            {sweeps(170, 44)}
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <span class="eyebrow">SERVER NOT ANSWERING</span>
            <h1 class="h1">Can’t reach Stridian right now</h1>
            <span style="font-size: 15px; line-height: 1.45; color: var(--ink2)">This one’s on our side, not your phone. Your data is safe — nothing you saved is lost.</span>
          </div>
          <div style="display: flex; flex-direction: column; gap: 8px">
            <div style="display: flex; justify-content: space-between"><span class="mono" style="font-size: 10.5px; letter-spacing: .1em">TRYING AGAIN BY ITSELF</span><span class="mono" style="font-size: 10.5px; letter-spacing: .1em">0:{{{{countdown}}}}</span></div>
            <div style="height: 4px; background: var(--line)"><div style="height: 4px; background: var(--ink); width: {{{{countPct}}}}%"></div></div>
          </div>
          <div style="margin-top: auto; display: flex; flex-direction: column; gap: 6px">
            <button class="btn">{icon(I['retry'], 20, 1.7)}Try now</button>
            <span class="mono" style="font-size: 10px; letter-spacing: .08em; color: var(--ink2); text-align: center; padding-top: 8px">LAST CHECKED 18:42</span>
          </div>
        </div>''')

r3 = phone('08 · SOMETHING WENT WRONG', f'''        <div class="pad" style="gap: 22px; padding-bottom: 34px">
          {BACK('Back')}
          <div style="position: relative; height: 170px; display: flex; align-items: center">
            <div style="position: relative; width: 150px; height: 150px">
              <svg viewBox="0 0 100 100" width="150" height="150" aria-hidden="true" style="position: absolute; left: 0; top: 0; clip-path: polygon(0 0, 100% 0, 100% 22%, 0 78%)"><path d="{{{{logoD}}}}" style="fill: var(--ink)"></path></svg>
              <svg viewBox="0 0 100 100" width="150" height="150" aria-hidden="true" style="position: absolute; left: 10px; top: 12px; clip-path: polygon(0 84%, 100% 28%, 100% 100%, 0 100%)"><path d="{{{{logoD}}}}" style="fill: var(--ink)"></path></svg>
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <span class="eyebrow">UNEXPECTED ERROR</span>
            <h1 class="h1">Something went wrong</h1>
            <span style="font-size: 15px; line-height: 1.45; color: var(--ink2)">This screen hit a problem we didn’t expect. Going back and trying again usually fixes it.</span>
          </div>
          <details style="border-top: 1px solid var(--line); border-bottom: 1px solid var(--line); padding: 12px 0">
            <summary class="mono" style="font-size: 10.5px; letter-spacing: .1em; cursor: pointer">DETAILS FOR YOUR COACH</summary>
            <span class="mono" style="display: block; padding-top: 10px; font-size: 11px; line-height: 1.6; color: var(--ink2)">ERROR 500 · /api/student/coach<br>30 SEP 2026 · 18:42 · REF 7F3A</span>
          </details>
          <div style="margin-top: auto; display: flex; flex-direction: column; gap: 10px">
            <button class="btn">{icon(I['retry'], 20, 1.7)}Try again</button>
            <button class="btn2">Go to Dashboard</button>
          </div>
        </div>''')

# ---------------- streak edge cases ----------------
def streak_phone(cap, v):
    return phone(cap, f'''        <div class="pad" style="gap: 20px">
          {BACK('Dashboard')}
          <div style="display: flex; justify-content: space-between; align-items: baseline"><span class="eyebrow">FOCUS STREAK · 30M SPRINT</span><span class="mono" style="font-size: 10.5px; letter-spacing: .1em; color: var(--ink2)">{{{{{v}.when}}}}</span></div>
          <div style="position: relative; display: flex; align-items: flex-end; gap: 14px">
            <div style="height: 110px; overflow: hidden">
              <div style="display: flex; flex-direction: column; transform: translateY({{{{{v}.numY}}}}px)">
                <span style="font-size: 110px; line-height: 110px; font-weight: 700; font-stretch: 125%; color: {{{{{v}.numC}}}}">{{{{{v}.n1}}}}</span>
                <span style="font-size: 110px; line-height: 110px; font-weight: 700; font-stretch: 125%">{{{{{v}.n2}}}}</span>
              </div>
            </div>
            <div style="display: flex; flex-direction: column; gap: 6px; padding-bottom: 14px">
              <span style="font-size: 17px; font-weight: 600; font-stretch: 112%">{{{{{v}.unit}}}}</span>
              <span class="mono" style="font-size: 10.5px; color: var(--ink2)">{{{{{v}.best}}}}</span>
            </div>
            <sc-for list="{{{{{v}.sparks}}}}" as="s" hint-placeholder-count="0"><span style="position: absolute; left: 0; top: 0; height: 2px; background: var(--ink); clip-path: polygon(0 50%,70% 0,100% 50%,70% 100%); width: {{{{s.w}}}}px; opacity: {{{{s.o}}}}; transform: translate({{{{s.x}}}}px, {{{{s.y}}}}px) rotate({{{{s.r}}}}deg)"></span></sc-for>
          </div>
          <div role="status" style="padding: 14px 16px; display: flex; gap: 12px; align-items: flex-start; background: {{{{{v}.bannerBg}}}}; color: {{{{{v}.bannerFg}}}}; border: 1px {{{{{v}.bannerBs}}}} var(--ink)">
            <span class="{{{{{v}.dotCls}}}}" style="width: 10px; height: 10px; margin-top: 5px; flex-shrink: 0; background: currentColor; transform: rotate(45deg)"></span>
            <div style="display: flex; flex-direction: column; gap: 4px"><span style="font-size: 16px; font-weight: 600">{{{{{v}.title}}}}</span><span style="font-size: 13.5px; line-height: 1.45; opacity: .85">{{{{{v}.body}}}}</span></div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <span class="eyebrow">LAST 8 WEEKS</span>
            <div style="display: flex; gap: 8px">
              <sc-for list="{{{{{v}.weeks}}}}" as="w" hint-placeholder-count="8">
                <div style="flex: 1; display: flex; flex-direction: column; gap: 8px; align-items: center">
                  <div class="{{{{w.cls}}}}" style="position: relative; width: 100%; height: 60px; clip-path: polygon(38% 0, 100% 0, 62% 100%, 0 100%); background: var(--line)">
                    <div style="position: absolute; inset: 0; background: var(--ink); transform: translateY({{{{w.fy}}}}%)"></div>
                  </div>
                  <span class="mono" style="font-size: 9.5px; letter-spacing: .04em; color: {{{{w.lc}}}}">{{{{w.label}}}}</span>
                </div>
              </sc-for>
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <span class="eyebrow">{{{{{v}.sessHead}}}}</span>
            <div style="display: flex; gap: 10px">
              <sc-for list="{{{{{v}.sessions}}}}" as="se" hint-placeholder-count="3">
                <div style="flex: 1; height: 50px; box-sizing: border-box; border: 1px {{{{se.bs}}}} var(--ink); position: relative; display: flex; align-items: center; justify-content: center; overflow: hidden">
                  <div style="position: absolute; inset: 0; background: var(--ink); transform: scale({{{{se.s}}}})"></div>
                  <span class="mono" style="position: relative; font-size: 11px; letter-spacing: .12em; color: {{{{se.c}}}}">{{{{se.day}}}}</span>
                </div>
              </sc-for>
            </div>
          </div>
          <button class="btn" style="margin-top: 4px">{{{{{v}.cta}}}}</button>
        </div>''')

s1 = streak_phone('09 · STREAK · ABOUT TO BREAK', 'a')
s2 = streak_phone('10 · STREAK · BROKEN', 'b')
s3 = streak_phone('11 · STREAK · RESTORED', 'c')

LOCKED_ICONS = ['M9 4h6M9 4a2 2 0 0 0-2 2H6a2 2 0 0 0-2 2v11a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-1a2 2 0 0 0-2-2M8 12h8M8 16h5',
  'M12 3 4 6v6c0 5 3.5 8 8 9 4.5-1 8-4 8-9V6l-8-3Z', 'M12 3 2 8l10 5 10-5-10-5ZM5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5',
  I['card'], 'M3 10h10a5 5 0 1 1-5 5V10M13 10l7-3', 'M6 20V14M12 20V9M18 20V4', I['target'],
  'M12 3c1 3.5 5 5.5 5 10a5 5 0 0 1-10 0c0-2 1-3.5 2-4.5 0 2 1 3 2 3 0-3-1-5.5 1-8.5Z']

common = r"""
const cl = v => v < 0 ? 0 : v > 1 ? 1 : v;
const eIO = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const eOut = t => 1 - Math.pow(1 - t, 3);
const r2 = v => Math.round(v * 100) / 100;
function burst(u, cx, cy, n, dist) {
  if (u < 0 || u > 1) return [];
  return Array.from({ length: n }, (_, i) => { const a = (i / n) * Math.PI * 2 + (i % 2) * .2, dd = (dist + (i % 3) * 8) * eOut(u), w = (8 + (i % 4) * 3) * (1 - .5 * u);
    return { w: r2(w), o: r2(1 - u), x: r2(cx + Math.cos(a) * dd - w / 2), y: r2(cy + Math.sin(a) * dd - 1), r: r2(a * 180 / Math.PI) }; });
}
"""

states_script = common + f"""
const LOCKED = {LOCKED_ICONS!r};
class Component extends DCLogic {{
  constructor(props) {{ super(props); this.state = {{ theme: 'white' }}; }}
  renderVals() {{
    return {{ theme: this.state.theme, logoD: LOGO_D, locked: LOCKED.map((icon, i) => ({{ icon, o: r2(1 - i * .09) }})), THEMES_JS }};
  }}
}}"""

errors_script = common + r"""
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', t: 0 }; this.timer = null; }
  componentDidMount() { this.timer = setInterval(() => this.setState({ t: this.state.t + 1 }), 1000); }
  componentWillUnmount() { clearInterval(this.timer); }
  renderVals() {
    const left = 30 - (this.state.t % 31);
    return { theme: this.state.theme, logoD: LOGO_D, countdown: String(left).padStart(2, '0'), countPct: r2((30 - left) / 30 * 100), THEMES_JS };
  }
}"""

streak_script = common + r"""
const LABELS = ['W35', 'W36', 'W37', 'W38', 'W39', 'W40', 'W41', 'W42'];
const wk = (fills, cur, curCls) => LABELS.map((label, i) => ({ label, fy: r2(100 * (1 - fills[i])), cls: i === 7 ? curCls : '', lc: i === 7 ? 'var(--ink)' : 'var(--ink2)' }));
const sess = (vals, bs) => ['MON', 'WED', 'FRI'].map((day, i) => ({ day, s: r2(vals[i]), c: vals[i] > .5 ? 'var(--bg)' : 'var(--ink)', bs: bs[i] }));
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', t: 0 }; this.raf = null; this.t0 = 0; }
  componentDidMount() { this.t0 = performance.now(); const step = () => { this.setState({ t: performance.now() - this.t0 }); this.raf = requestAnimationFrame(step); }; this.raf = requestAnimationFrame(step); }
  componentWillUnmount() { if (this.raf) cancelAnimationFrame(this.raf); }
  renderVals() {
    const t = this.state.t % 6000;
    // about to break: 4 weeks going, this week 1 of 3 done, week ends Sunday
    const a = { when: 'SATURDAY', best: 'BEST · 4 WEEKS', n1: '4', n2: '4', numY: 0, numC: 'var(--ink)', unit: 'weeks in a row', sparks: [],
      title: 'Ends Sunday night', body: 'Two sessions still to do this week. Miss them and the streak starts again from zero.',
      bannerBg: 'var(--ink)', bannerFg: 'var(--bg)', bannerBs: 'solid', dotCls: 'pulse',
      weeks: wk([0, 0, 0, 1, 1, 1, 1, .33], 7, 'pulse'), sessHead: 'THIS WEEK · 1 OF 3 · 1 DAY LEFT',
      sessions: sess([1, 0, 0], ['solid', 'dashed', 'dashed']), cta: 'Log today’s session' };
    // broken: the count drops 4 → 0 once, the missed week stays open
    const drop = eIO(cl((t - 700) / 700));
    const b = { when: 'MONDAY', best: 'BEST · 4 WEEKS', n1: '4', n2: '0', numY: r2(-110 * drop), numC: 'var(--ink2)', unit: 'weeks in a row', sparks: [],
      title: 'The streak reset', body: 'Last week ended at 1 of 3. Your best stays at 4 weeks — and badges you earned are yours to keep.',
      bannerBg: 'transparent', bannerFg: 'var(--ink)', bannerBs: 'dashed', dotCls: '',
      weeks: wk([0, 0, 1, 1, 1, 1, .33, 0], 7, ''), sessHead: 'NEW WEEK · 0 OF 3',
      sessions: sess([0, 0, 0], ['solid', 'solid', 'solid']), cta: 'Start a new streak' };
    // restored: the coach logs the missed session late, the gap fills and the count rolls back 0 → 5
    const fill = eIO(cl((t - 600) / 700)), roll = eIO(cl((t - 1200) / 700));
    const c = { when: 'TUESDAY', best: roll > .5 ? 'NEW BEST · 5 WEEKS' : 'BEST · 4 WEEKS', n1: '0', n2: '5', numY: r2(-110 * roll), numC: 'var(--ink2)', unit: 'weeks — back on', sparks: burst((t - 1800) / 560, 60, 55, 12, 64),
      title: 'Streak restored', body: 'Your coach logged Friday’s session late, so last week counts. You’re at 5 weeks — a new best.',
      bannerBg: 'var(--ink)', bannerFg: 'var(--bg)', bannerBs: 'solid', dotCls: '',
      weeks: wk([0, 0, 1, 1, 1, 1, .33 + .67 * fill, 0], 7, ''), sessHead: 'LAST WEEK · 3 OF 3 · FRI ADDED BY COACH',
      sessions: sess([1, 1, fill], ['solid', 'solid', 'dashed']), cta: 'Keep it going' };
    c.weeks[6].lc = 'var(--ink)';
    return { theme: this.state.theme, a, b, c, THEMES_JS };
  }
}"""

if __name__ == "__main__": build('States.dc.html', 'Stridian empty and loading states', 2322, 1050, 'STATES · EMPTY AND LOADING', '\n'.join([e1, e2, e3, l1, l2]), states_script, extra_css=extra_css)
if __name__ == "__main__": build('Errors.dc.html', 'Stridian error states', 1406, 1050, 'STATES · ERRORS', '\n'.join([r1, r2, r3]), errors_script, extra_css=extra_css)
if __name__ == "__main__": build('Streaks.dc.html', 'Stridian streak states', 1406, 1050, 'FOCUS STREAK · EDGE CASES', '\n'.join([s1, s2, s3]), streak_script, extra_css=extra_css)
if __name__ == '__main__': print('ok')
