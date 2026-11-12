from build import *
CAM = 'M4 8h3l2-3h6l2 3h3v11H4V8Zm8 9a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z'
GAL = 'M4 5h16v14H4V5Zm0 10 5-5 4 4 3-3 4 4M15.5 9.5h.01'
RETRY = 'M4 12a8 8 0 0 1 14-5.3M20 4v4h-4M20 12a8 8 0 0 1-14 5.3M4 20v-4h4'
ALERT = 'M12 3 2 21h20L12 3ZM12 10v5M12 17.5v.5'
CLOSE = 'M6 6l12 12M18 6 6 18'

p1 = phone('01 · PICK OR RECORD', f'''        <div class="pad">
          {BACK('Drill videos')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">NEW DRILL CLIP</span>
            <h1 class="h1">Add a video</h1>
          </div>
          <label style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">WHICH DRILL</span>
            <select class="fld" style="appearance: none; -webkit-appearance: none; cursor: pointer">
              <option>Countermovement jump</option>
              <option>30m Sprint</option>
              <option>Agility T-test</option>
            </select>
          </label>
          <div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 10px">
            <button class="opt" style="height: 150px; background: var(--ink); color: var(--bg); padding: 18px; display: flex; flex-direction: column; justify-content: space-between">
              {icon(CAM, 30, 1.5)}
              <span style="display: flex; flex-direction: column; gap: 5px"><span style="font-size: 17px; font-weight: 600">Record</span><span class="mono" style="font-size: 10px; letter-spacing: .08em; opacity: .75">OPENS THE CAMERA</span></span>
            </button>
            <button class="opt" style="height: 150px; border: 1px solid var(--ink); padding: 18px; display: flex; flex-direction: column; justify-content: space-between">
              {icon(GAL, 30, 1.5)}
              <span style="display: flex; flex-direction: column; gap: 5px"><span style="font-size: 17px; font-weight: 600">From gallery</span><span class="mono" style="font-size: 10px; letter-spacing: .08em; color: var(--ink2)">PICK A SAVED CLIP</span></span>
            </button>
          </div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding-bottom: 6px">FOR A CLEAN READING</span>
            <div style="display: flex; gap: 14px; padding: 11px 0; border-top: 1px solid var(--line)"><span class="mono" style="font-size: 11px; color: var(--ink2); padding-top: 2px">01</span><span style="font-size: 14.5px">Film side-on, whole body in frame</span></div>
            <div style="display: flex; gap: 14px; padding: 11px 0; border-top: 1px solid var(--line)"><span class="mono" style="font-size: 11px; color: var(--ink2); padding-top: 2px">02</span><span style="font-size: 14.5px">One athlete only</span></div>
            <div style="display: flex; gap: 14px; padding: 11px 0; border-top: 1px solid var(--line)"><span class="mono" style="font-size: 11px; color: var(--ink2); padding-top: 2px">03</span><span style="font-size: 14.5px">Keep the phone still — prop it up</span></div>
            <div style="display: flex; gap: 14px; padding: 11px 0; border-top: 1px solid var(--line)"><span class="mono" style="font-size: 11px; color: var(--ink2); padding-top: 2px">04</span><span style="font-size: 14.5px">Up to 200 MB · MP4, MOV, AVI, MKV, WEBM, M4V</span></div>
          </div>
          <span class="mono" style="font-size: 10.5px; line-height: 1.6; color: var(--ink2)">VIDEOS ARE DELETED AFTER 30 DAYS.<br>YOUR MEASUREMENTS ARE KEPT.</span>
        </div>''')

p2 = phone('02 · UPLOADING', f'''        <div class="pad">
          <button class="back" aria-label="Cancel upload">{icon(CLOSE)}Cancel</button>
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">{{{{up.eyebrow}}}}</span>
            <h1 class="h1">Countermovement jump</h1>
          </div>
          <div class="hatch" style="position: relative; height: 196px; border: 1px solid var(--line); display: flex; align-items: flex-end; padding: 12px; box-sizing: border-box">
            <span class="mono" style="font-size: 10.5px; letter-spacing: .06em; background: var(--bg); padding: 4px 7px">CMJ_SIDE.MOV · 86 MB · 0:14</span>
          </div>
          <div style="display: flex; align-items: flex-end; justify-content: space-between">
            <span class="mono" style="font-size: 64px; font-weight: 500; line-height: .9">{{{{up.pct}}}}<span style="font-size: 26px">%</span></span>
            <span class="mono" style="font-size: 11px; letter-spacing: .08em; color: var(--ink2); padding-bottom: 4px">{{{{up.pieceText}}}}</span>
          </div>
          <div style="display: flex; gap: 3px">
            <sc-for list="{{{{up.pieces}}}}" as="pc" hint-placeholder-count="22">
              <span style="flex: 1; height: 14px; box-sizing: border-box; border: 1px solid var(--ink); background: {{{{pc.bg}}}}"></span>
            </sc-for>
          </div>
          <span style="font-size: 14px; line-height: 1.45; color: var(--ink2)">{{{{up.note}}}}</span>
          <div style="margin-top: auto; padding-bottom: 34px; display: flex; flex-direction: column">
            <sc-if value="{{{{up.done}}}}" hint-placeholder-val="{{{{false}}}}"><button class="btn">See it in the queue</button></sc-if>
            <sc-if value="{{{{up.going}}}}" hint-placeholder-val="{{{{true}}}}"><button class="btn2">Cancel upload</button></sc-if>
          </div>
        </div>''')

p3 = phone('03 · UPLOAD FAILED', f'''        <div class="pad">
          {BACK('Drill videos')}
          <div style="display: flex; flex-direction: column; gap: 8px">
            <span class="eyebrow">UPLOAD STOPPED</span>
            <h1 class="h1">Couldn’t finish the upload</h1>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <div style="display: flex; gap: 3px">
              <sc-for list="{{{{failPieces}}}}" as="pc" hint-placeholder-count="22">
                <span style="flex: 1; height: 14px; box-sizing: border-box; border: 1px {{{{pc.style}}}} var(--ink); background: {{{{pc.bg}}}}"></span>
              </sc-for>
            </div>
            <span class="mono" style="font-size: 11px; letter-spacing: .08em; color: var(--ink2)">STOPPED AT 58% · PIECE 13 OF 22</span>
          </div>
          <div role="alert" style="background: var(--ink); color: var(--bg); padding: 16px; display: flex; gap: 14px">
            {icon(ALERT, 22, 1.6)}
            <div style="display: flex; flex-direction: column; gap: 5px">
              <span style="font-size: 16px; font-weight: 600">Connection lost</span>
              <span style="font-size: 13.5px; line-height: 1.45; opacity: .8">Check your Wi-Fi or mobile data, then try again. Your video is still on your phone.</span>
            </div>
          </div>
          <div style="display: flex; flex-direction: column; gap: 10px">
            <button class="btn">{icon(RETRY, 20, 1.7)}Try again</button>
            <button class="btn2">Choose a different video</button>
          </div>
          <div style="display: flex; flex-direction: column">
            <span class="eyebrow" style="padding-bottom: 6px">OTHER REASONS IT CAN STOP</span>
            <div style="display: flex; flex-direction: column; gap: 3px; padding: 11px 0; border-top: 1px solid var(--line)"><span style="font-size: 14.5px">Over 200 MB</span><span style="font-size: 12.5px; color: var(--ink2)">Trim the clip, or record a shorter one.</span></div>
            <div style="display: flex; flex-direction: column; gap: 3px; padding: 11px 0; border-top: 1px solid var(--line)"><span style="font-size: 14.5px">Not a video file</span><span style="font-size: 12.5px; color: var(--ink2)">MP4, MOV, AVI, MKV, WEBM or M4V.</span></div>
          </div>
        </div>''')

p4 = phone('04 · QUEUED → PROCESSING → READY', f'''        <div class="pad" style="gap: 16px">
          {BACK('My report')}
          <div style="display: flex; align-items: flex-end; justify-content: space-between">
            <div style="display: flex; flex-direction: column; gap: 8px">
              <span class="eyebrow">DRILL VIDEOS</span>
              <h1 class="h1">Your clips</h1>
            </div>
            <button class="opt" aria-label="Add a video" style="width: 44px; height: 44px; background: var(--ink); color: var(--bg); display: flex; align-items: center; justify-content: center">{icon('M12 5v14M5 12h14', 22, 1.8)}</button>
          </div>
          <div style="display: flex; gap: 12px; align-items: flex-start; padding: 12px 14px; border: 1px dashed var(--ink)">
            <span class="blink" style="width: 8px; height: 8px; background: var(--ink); margin-top: 5px; flex-shrink: 0"></span>
            <span style="font-size: 13px; line-height: 1.45">Clips are analysed on your coach’s computer. They wait in line and run in its next session — no need to keep the app open.</span>
          </div>
          <sc-for list="{{{{clips}}}}" as="c" hint-placeholder-count="4">
            <div style="display: flex; flex-direction: column; gap: 10px; padding-top: 13px; border-top: 1px solid var(--line)">
              <div style="display: flex; gap: 12px; align-items: center">
                <span class="hatch" style="width: 44px; height: 44px; flex-shrink: 0; border: 1px solid var(--line)"></span>
                <div style="flex-grow: 1; display: flex; flex-direction: column; gap: 4px; min-width: 0">
                  <span style="font-size: 15px; font-weight: 600">{{{{c.name}}}}</span>
                  <span class="mono" style="font-size: 10.5px; letter-spacing: .06em; color: var(--ink2)">{{{{c.meta}}}}</span>
                </div>
                <span class="mono" style="font-size: 10px; letter-spacing: .1em; padding: 5px 8px; border: 1px solid var(--ink); background: {{{{c.chipBg}}}}; color: {{{{c.chipFg}}}}">{{{{c.state}}}}</span>
              </div>
              <div style="display: flex; gap: 4px">
                <sc-for list="{{{{c.steps}}}}" as="s" hint-placeholder-count="3">
                  <div style="flex: 1; display: flex; flex-direction: column; gap: 5px">
                    <span class="{{{{s.cls}}}}" style="height: 4px; background-color: {{{{s.bg}}}}"></span>
                    <span class="mono" style="font-size: 9px; letter-spacing: .1em; color: {{{{s.fg}}}}">{{{{s.label}}}}</span>
                  </div>
                </sc-for>
              </div>
              <div style="display: flex; justify-content: space-between">
                <span class="mono" style="font-size: 10px; letter-spacing: .06em; color: var(--ink2)">{{{{c.detail}}}}</span>
                <span class="mono" style="font-size: 10px; letter-spacing: .06em; color: {{{{c.expFg}}}}">{{{{c.expiry}}}}</span>
              </div>
            </div>
          </sc-for>
        </div>''')

script = """
const cl = v => v < 0 ? 0 : v > 1 ? 1 : v;
const eIO = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const N = 22;
const CLIPS = [
  { name: 'Countermovement jump', meta: 'TODAY · 0:14', state: 'QUEUED', at: 0, detail: '2ND IN LINE', expiry: 'DELETES IN 30 DAYS' },
  { name: 'Sprint start', meta: '28 SEP · 0:09', state: 'PROCESSING', at: 1, detail: 'FRAME 184 OF 300', expiry: 'DELETES IN 28 DAYS' },
  { name: 'Agility T-test', meta: '22 SEP · 0:21', state: 'READY', at: 2, detail: 'VIEW ANALYSIS →', expiry: 'DELETES IN 22 DAYS' },
  { name: '30m Sprint', meta: '31 AUG · 0:07', state: 'READY', at: 2, detail: 'VIEW ANALYSIS →', expiry: 'VIDEO DELETED · RESULTS KEPT' }
];
class Component extends DCLogic {
  constructor(props) { super(props); this.state = { theme: 'white', t: 0 }; this.raf = null; this.t0 = 0; }
  componentDidMount() { this.t0 = performance.now(); const step = () => { this.setState({ t: performance.now() - this.t0 }); this.raf = requestAnimationFrame(step); }; this.raf = requestAnimationFrame(step); }
  componentWillUnmount() { if (this.raf) cancelAnimationFrame(this.raf); }
  renderVals() {
    const cyc = this.state.t % 7200;
    const p = eIO(cl((cyc - 400) / 5000));
    const done = cyc > 5600;
    const sent = Math.floor(p * N + 1e-6);
    const up = {
      pct: Math.round(p * 100), done, going: !done,
      eyebrow: done ? 'UPLOADED · IN THE QUEUE' : 'UPLOADING',
      pieceText: done ? '22 OF 22 PIECES' : 'PIECE ' + Math.min(N, sent + 1) + ' OF 22 · 4 MB',
      note: done ? 'It will be analysed in the next session on your coach’s computer. We’ll let you know when it’s ready.' : 'Keep Stridian open until the upload finishes.',
      pieces: Array.from({ length: N }, (_, i) => ({ bg: i < sent ? 'var(--ink)' : 'transparent' }))
    };
    const failPieces = Array.from({ length: N }, (_, i) => ({ bg: i < 12 ? 'var(--ink)' : 'transparent', style: i < 12 ? 'solid' : 'dashed' }));
    const clips = CLIPS.map(c => ({ ...c,
      chipBg: c.at === 2 ? 'var(--ink)' : 'transparent', chipFg: c.at === 2 ? 'var(--bg)' : 'var(--ink)',
      expFg: c.expiry.startsWith('VIDEO') ? 'var(--ink)' : 'var(--ink2)',
      steps: ['QUEUED', 'PROCESSING', 'READY'].map((label, i) => ({ label,
        cls: i === 1 && c.at === 1 ? 'stripes' : '',
        bg: i < c.at || (i === c.at && c.at !== 1) ? 'var(--ink)' : i === c.at ? 'transparent' : 'var(--line)',
        fg: i <= c.at ? 'var(--ink)' : 'var(--ink2)' })) }));
    return { theme: this.state.theme, up, failPieces, clips, THEMES_JS };
  }
}"""
build('Upload.dc.html', 'Stridian video upload', 1864, 1050, 'VIDEO · UPLOAD AND PROCESSING', '\n'.join([p1, p2, p3, p4]), script)
print('ok')
