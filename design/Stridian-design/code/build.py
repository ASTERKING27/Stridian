import sys, os
LOGO_D = 'M8.0 52.3L58.8 58.1L27.1 83.3L4.7 78.8L4.2 79.2L28.6 94.7L97.0 47.9L27.7 39.6L32.0 24.0L53.0 20.7L68.6 7.6L22.6 12.9ZM81.8 16.0L88.0 25.3L88.7 24.6L88.5 5.3L72.9 7.1L57.6 19.9Z'
HELMET = """<helmet>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&amp;family=IBM+Plex+Mono:wght@400;500&amp;display=swap">
<style>
body{margin:0}
a{color:#55544F}a:hover{color:#121211}
.t-white{--bg:#F3F2EE;--ink:#121211;--ink2:#55544F;--line:rgba(18,18,17,.14);--soft:rgba(18,18,17,.07);--glass:rgba(246,245,241,.56);--glassEdge:rgba(18,18,17,.10);--hi:rgba(255,255,255,.8);--shadow:0 14px 34px rgba(18,18,17,.16)}
.t-dark{--bg:#0F0F0E;--ink:#EEEDE8;--ink2:#9D9C96;--line:rgba(238,237,232,.16);--soft:rgba(238,237,232,.08);--glass:rgba(34,34,32,.5);--glassEdge:rgba(238,237,232,.12);--hi:rgba(255,255,255,.09);--shadow:0 14px 34px rgba(0,0,0,.55)}
.mono{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace}
.wm{font-family:Archivo,'Helvetica Neue',sans-serif;font-stretch:125%;font-weight:620;letter-spacing:.2em}
.eyebrow{font-family:'IBM Plex Mono',ui-monospace,Menlo,monospace;font-size:10.5px;letter-spacing:.14em;color:var(--ink2)}
.h1{margin:0;font-size:30px;line-height:1.06;font-weight:600;font-stretch:112%;letter-spacing:-.015em;text-wrap:balance}
.phone{width:410px;height:864px;box-sizing:border-box;padding:10px;border-radius:58px;background:#0A0A09;box-shadow:0 30px 60px rgba(18,18,17,.18);flex-shrink:0}
.scr{position:relative;width:390px;height:844px;border-radius:48px;overflow:hidden;background:var(--bg);color:var(--ink);font-family:Archivo,'Helvetica Neue',sans-serif}
.pad{position:absolute;inset:0;padding:56px 22px 0;box-sizing:border-box;display:flex;flex-direction:column;gap:20px}
.cap{font:500 11px/1 'IBM Plex Mono',ui-monospace,monospace;letter-spacing:.14em;color:#55544F}
.back{all:unset;box-sizing:border-box;display:flex;align-items:center;gap:8px;height:44px;font:500 14px/1 Archivo,sans-serif;cursor:pointer;color:var(--ink);align-self:flex-start}
.btn{all:unset;box-sizing:border-box;height:52px;display:flex;align-items:center;justify-content:center;gap:10px;background:var(--ink);color:var(--bg);font:600 15px/1 Archivo,'Helvetica Neue',sans-serif;letter-spacing:.01em;cursor:pointer;text-align:center}
.btn2{all:unset;box-sizing:border-box;height:52px;display:flex;align-items:center;justify-content:center;gap:10px;border:1px solid var(--ink);color:var(--ink);font:600 15px/1 Archivo,'Helvetica Neue',sans-serif;cursor:pointer;text-align:center}
.btn3{all:unset;box-sizing:border-box;height:44px;display:flex;align-items:center;justify-content:center;color:var(--ink2);font:500 14px/1 Archivo,sans-serif;cursor:pointer}
.btn:focus-visible,.btn2:focus-visible,.btn3:focus-visible,.back:focus-visible,.opt:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.fld{font:400 16px/1.2 Archivo,'Helvetica Neue',sans-serif;color:var(--ink);background:transparent;border:0;border-bottom:1px solid var(--ink);border-radius:0;padding:0 0 9px;width:100%;box-sizing:border-box;outline:none}
.fld::placeholder{color:var(--ink2)}
.fld:focus{border-bottom-width:2px;padding-bottom:8px}
.fld.bad{border-bottom:2px dashed var(--ink);padding-bottom:8px}
.hatch{background:repeating-linear-gradient(135deg,var(--line) 0 1px,transparent 1px 9px)}
.opt{all:unset;box-sizing:border-box;cursor:pointer}
.tab{all:unset;box-sizing:border-box;position:absolute;top:3px;height:52px;display:flex;align-items:center;justify-content:center;font:600 12.5px/1 Archivo,'Helvetica Neue',sans-serif;border-radius:26px}
.stripes{background:repeating-linear-gradient(135deg,var(--ink) 0 6px,transparent 6px 12px);background-size:17px 17px;animation:stripes .8s linear infinite}
@keyframes stripes{to{background-position:17px 0}}
.blink{animation:blink 1.2s steps(2) infinite}
@keyframes blink{50%{opacity:.25}}
.ctl{font:500 12px/1 'IBM Plex Mono',ui-monospace,monospace;letter-spacing:.06em;height:40px;padding:0 14px;border:1px solid #121211;background:transparent;color:#121211;border-radius:20px;cursor:pointer}
.ctl:hover{background:rgba(18,18,17,.06)}
.ctl.on{background:#121211;color:#F3F2EE}
EXTRA_CSS
</style>
</helmet>"""

TOP = """<div style="display: flex; align-items: center; gap: 8px">
    <span class="mono" style="font-size: 12px; letter-spacing: .12em; color: #55544F">BOARD_TITLE</span>
    <span style="flex-grow: 1"></span>
    EXTRA_CONTROLS
    <sc-for list="{{themes}}" as="th" hint-placeholder-count="2">
      <button class="ctl {{th.cls}}" onClick="{{th.pick}}" aria-pressed="{{th.on}}">{{th.label}}</button>
    </sc-for>
  </div>"""

THEMES_JS = "themes: [['white', 'White'], ['dark', 'Dark']].map(([k, label]) => ({ label, on: this.state.theme === k, cls: this.state.theme === k ? 'on' : '', pick: () => this.setState({ theme: k }) }))"

def build(name, title, w, h, board_title, body, script, extra_css='', extra_controls=''):
    top = TOP.replace('BOARD_TITLE', board_title).replace('EXTRA_CONTROLS', extra_controls)
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
{HELMET.replace('EXTRA_CSS', extra_css)}
<div style="width: {w}px; height: {h}px; box-sizing: border-box; padding: 34px 40px 40px; background: #E6E5E0; color: #121211; font-family: Archivo, 'Helvetica Neue', sans-serif; display: flex; flex-direction: column; gap: 22px">
  {top}
  <div class="t-{{{{theme}}}}" style="display: flex; gap: 48px">
{body}
  </div>
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{w},"height":{h}}}}}'>
const LOGO_D = '{LOGO_D}';
{script.replace('THEMES_JS', THEMES_JS)}
</script>
</body>
</html>
"""
    open(os.path.join(os.path.dirname(__file__), 'stridian/project', name), 'w').write(html)

def phone(cap, inner):
    return f"""    <div style="display: flex; flex-direction: column; gap: 12px">
      <span class="cap">{cap}</span>
      <div class="phone"><div class="scr">
{inner}
      </div></div>
    </div>"""

BACK = lambda label: f'''<button class="back" aria-label="Back"><svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true"><path d="M15 18l-6-6 6-6"></path></svg>{label}</button>'''
def icon(d, size=20, sw=1.6, extra=''):
    return f'<svg viewBox="0 0 24 24" width="{size}" height="{size}" fill="none" stroke="currentColor" stroke-width="{sw}" stroke-linecap="butt" stroke-linejoin="miter" aria-hidden="true" style="flex-shrink: 0{extra}"><path d="{d}"></path></svg>'
