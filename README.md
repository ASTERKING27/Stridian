# Stridian

*Sports talent intelligence.*

Sport-specific talent profiling for students. A student registers themselves, their
coach records test results, and the app scores them against every position in that
sport, ranks them, and explains *why* — then adds pose-based video analysis, a
training plan and a diet plan on top.

- **Backend:** FastAPI + SQLAlchemy — Postgres (Neon) online, SQLite on one computer
- **Drill video:** MediaPipe Pose + OpenCV — one athlete, technique
- **Match video:** YOLO11n-pose + ByteTrack — every player, what they did in the game
- **Frontend:** React + Vite — no UI kit, no chart library, no router
- **Auth:** coach accounts, PBKDF2 passwords, bearer-token sessions (stdlib only)
- **Online:** website on Vercel, videos in Google Drive, heavy lifting on a worker
  computer (the laptop now, the lab iMac later), a live Google Sheet of the squad

Sports covered: Football, Basketball, Volleyball, Cricket, Badminton/Tennis, Kho-Kho.

---

## Who sees what

| | Needs an account | Scope |
|---|---|---|
| Student Entry | no | anyone can register themselves for any sport |
| Coach Entry, Dashboard, Weights | yes | **only the coach's own sport** |

A coach signs up once and picks their sport. From then on every list, report, video
and weight they can reach belongs to that sport — a football coach asking for a
basketball student gets a 404, and asking for basketball weights gets a 403. Students
never need an account: they pick their sport on the form and land in that coach's
squad automatically.

Passwords are PBKDF2-SHA256 with a per-user salt at 240k iterations. Session tokens
are 256-bit random strings and only their SHA-256 is stored, so a database dump does
not hand anyone a live session.

---

## How the pieces fit

```
  students & coaches                       Google (one login, drive.file scope)
        │ browser                           ┌──────────────────────────────┐
        ▼                                   │ Drive: "Stridian videos"     │
  ┌───────────────────┐   4 MB chunks ────► │   (kept 30 days)             │
  │ Vercel            │                     │ Sheet: Pending | Verified    │
  │  React site (CDN) │   row push   ─────► └──────────────▲───────────────┘
  │  FastAPI /api/*   │                                    │ download / thumbnails
  └────────┬──────────┘                                    │
           │ DATABASE_URL           ┌──────────────────────┴───────┐
           ▼                        │ worker.py — laptop / iMac    │
  ┌───────────────────┐  queue &    │  MediaPipe + YOLO analysis   │
  │ Neon Postgres     │◄──results── │  training, 30-day clean-up,  │
  │ (Singapore)       │             │  sheet repair                │
  └───────────────────┘             └──────────────────────────────┘
```

The website never runs a vision model — that is what lets it live on a free
serverless host. An upload goes to Drive and becomes a **queued** job in the database.
The worker, whenever it is switched on, claims queued jobs, analyses them, writes the
results back, then retrains the model and tidies up. Switch it off mid-job and the job
is handed back automatically after 30 minutes; nothing is lost, and the next session
carries on with yesterday's data plus whatever arrived since.

---

## Requirements

- **Python 3.11 or 3.12** — MediaPipe 0.10.14 has no wheels for 3.13+. Check with `python --version`.
- **Node 20+** for the frontend.

## Running it

**Terminal 1 — backend** (from `backend`):

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

On WSL2/Linux: `python3.12 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn main:app --reload`

**Match analysis is an optional extra**, because it pulls in PyTorch (a few hundred MB).
Everything else works without it; match clips simply wait in the queue until a worker
with it installed comes along.

```powershell
# CPU-only torch first, otherwise pip fetches the much larger CUDA build
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements-match.txt
```

The YOLO weights (~6 MB) download themselves on first use and are cached in
`backend/models/`. The worker says at startup which lanes it can run, and only picks
up jobs it can finish — the rest wait for a computer that can.

**Terminal 2 — the worker** (from `backend`, same virtual environment):

```powershell
python worker.py            # runs until Ctrl+C; add --once for a single pass
```

Uploads wait in the queue until this runs. Settings (database, Google) come from a
`.env` file in the project folder — copy `.env.example`. With no `.env` at all, both
processes use a local SQLite file and the `backend/uploads` folder, which is all you
need to try things on one computer.

**Terminal 3 — frontend** (from `frontend`):

```bash
npm install
npm run dev
```

Open **http://localhost:5173**. Vite proxies `/api` to port 8000, so the browser only
ever sees one origin and CORS never comes into it.

Interactive API docs: **http://127.0.0.1:8000/docs**

### You never need to delete the database

`create_all` only creates tables that are missing entirely — it will not touch one that
already exists. So an older `ppanalyzer.db` used to keep working right up until something
wrote a newly added field, then fail with a 500 on a form submit, which is a miserable
way to find out. `migrate.py` now runs on every startup: it compares the models against
what is actually on disk and adds whatever columns are missing. It only ever *adds* —
nothing is dropped, renamed or retyped, existing rows are untouched, and against an
up-to-date database it does nothing at all. Anything it cannot add in place is named in
the server log rather than swallowed.

The same repair runs against Postgres, so the hosted database picks up new columns the
first time a new version of the site starts.

### Single-port deployment

`npm run build` writes `frontend/dist`, and the backend serves that folder at `/`
automatically when it exists. Build once, then run only uvicorn and open
http://127.0.0.1:8000.

---

## Going online

Everything below is free for a university squad. Order matters: the database first,
then Google, then Vercel, because each step produces a value the next one needs.

1. **Code on GitHub.** Push this folder to a repository of your own. `.gitignore`
   already keeps out `.env`, the database, uploads and model weights — check that
   `.env` is not listed by `git status` before your first push.
2. **Database — Neon.** Create a project in the **AWS Asia Pacific (Singapore)**
   region, copy the connection string, and put it in `.env` as `DATABASE_URL=`.
   (Neon's free tier suspends when idle and wakes in about a second; data is kept.)
3. **Google.** In Google Cloud: create a project, enable the **Google Drive API** and
   **Google Sheets API**, set up the OAuth consent screen (External), add the
   `.../auth/drive.file` scope, then **publish the app** — in "Testing" mode Google
   expires the login after 7 days. Create an OAuth client of type **Desktop app** and
   put its ID and secret in `.env`. Then run `python backend/setup_google.py`: it opens
   a browser, you sign in with the account whose Drive should hold the videos, and it
   creates the video folder and the squad sheet and writes the rest of `.env` itself.
4. **Vercel.** Import the GitHub repository. `vercel.json` already sets the build, the
   Python function and the Singapore region. Under Settings → Environment Variables add
   `DATABASE_URL`, `COACH_SIGNUP_CODE`, `STORAGE=drive`, and the five `GOOGLE_*` values
   from your `.env`. Deploy.
5. **Worker.** On the laptop (later the iMac): same `.env`, `pip install -r
   backend/requirements.txt` (plus the YOLO extras), then `python backend/worker.py`.

`COACH_SIGNUP_CODE` matters once the site is public: without it anyone could create a
coach account and read a squad's details, including allergies and blood groups — so on
Vercel, sign-up stays closed until it is set. Share the code only with your coaches.
The squad sheet covers **every** sport, so keep it to yourself (and anyone allowed to
see all sports); a coach who is only meant to see football should use the website.

---

## How the AI learns from the coaches

The position engine below starts from expert weights. Every time a coach **verifies**
a student — confirms the position they actually play, from the card at the top of the
report — that becomes a labelled example. The worker then asks, for each position:
*which measurements set the players a coach put here apart from the rest of the
squad?* and moves that position's weights towards them.

- **It stays explainable.** Only the weights change; every report can still say
  exactly which results drove a recommendation.
- **Small squads can't wreck it.** The starting weights count as 8 verified students,
  so a position with two labels barely moves and one with forty is mostly learned.
  Tests-vs-footage balance per position is preserved.
- **It must prove itself.** Each candidate is scored leave-one-out — every student
  predicted by a model that never saw them — and goes live only if it beats the
  current model on the same students. Otherwise it is recorded and kept out.
- **Nothing is rewritten.** Every model, every coach's weight edit and every reset is
  a version in the history, and any of them can be put back live from the **AI
  Training** page, which also shows what the model has learned in plain words, how
  often it agrees with the coaches, whether the worker is on, the queue, and the sheet.

Training starts once a sport has 6 verified students across at least two positions,
and only reruns when the verified data has actually changed.

The video models themselves (MediaPipe, YOLO) are not retrained — they already find
bodies well. What is learned is what those measurements *mean* for positions in your
university's squads, which is the part no pretrained model knows.

---

## The squad sheet

A Google Sheet with two tabs, **Pending** and **Verified**, rewritten whenever anything
changes — a student enrols, a coach records results, verifies someone, identifies them
in match footage, or edits weights. Each row carries the student's details, status,
who verified them and when, the verified and recommended positions and whether they
agree, strengths, weak links, the diet targets, allergies and notes.

Each student's row is computed when their data changes and cached, so a push is two
API calls however big the squad gets. Every push rewrites both tabs completely, so a
push that fails (Google briefly down) is simply repaired by the next one; the worker
also pushes on every pass. Values are written as plain text, so a formula typed into a
form stays text.

---

## How the prediction works

Everything rests on one idea, so the output is always explainable.

1. **Normalise.** Each measurement is scored 0–100 against a `poor → elite` reference
   range defined per sport in `sports_config.py`. A 30 m sprint of 5.20 s scores 0,
   3.90 s scores 100. Timed tests need no special case — `poor` is simply the larger
   number, so the same arithmetic runs both directions.
2. **Weight.** Each position is a weight profile over those metrics. A football winger
   is `sprint30m 0.40, agilityTtest 0.30, yoyoLevel 0.15, cmj 0.10, heightCm 0.05`.
3. **Rank.** Position fit = weighted average of the scores that have values.
4. **Explain.** The engine tracks `weight × (score − 50)` per metric — how far each one
   pulled the fit away from average. Biggest positives become *drivers*, biggest
   negatives *drags*, and those become the "why" sentence.

`coverage` reports how much of a position's weight was actually backed by data, and
`confidence` turns that into high / medium / low. One test filled in still produces a
ranking, clearly marked low-confidence.

### Three passes, not one

Every metric carries a `source`: `test` (the battery), `profile` (height and weight), or
`match` (derived from footage). The engine takes a `sources` filter, so the same code
runs three times per report:

| Pass | Sources | Answers |
|---|---|---|
| Tests | `test` + `profile` | what their body and their testing say |
| Match | `match` only | what they actually did in a game |
| Combined | everything | the headline verdict |

Weights are normalised so each source carries the same total weight — neither drowns the
other in the combined pass — and a filtered pass only counts the weights it could
possibly satisfy, so a tests-only verdict isn't reported as half-covered just because the
position also has match weights.

`reconciliation` then says plainly whether the two agree, nearly agree (each ranks the
other's pick in its own top three), or disagree — and what a disagreement usually means.

### Editing the weights

Defaults live in `sports_config.py`, but they are **seeded into the database on first
run and read from there afterwards** — so changing them is a normal app action on the
Weights tab, not a code edit. A coach only ever edits their own sport.

| Method | Endpoint |
|---|---|
| `GET` | `/api/sports/{sport}/weights` — current weights plus the built-in defaults |
| `PUT` | `/api/sports/{sport}/weights` — set weights for one or more positions |
| `POST` | `/api/sports/{sport}/weights/reset` — back to defaults |

`{sport}` accepts the full name or a slug (`football`, `badminton-tennis`). Weights do
not have to sum to 1 — the engine divides by the total it actually used.

---

## Are these international standards?

Partly, and the app says which is which rather than leaving you to guess. Every metric
carries a `basis`, shown as a badge next to it:

| Badge | Means | Examples |
|---|---|---|
| **standard** | The number itself is an official threshold from a governing body | BCCI's Yo-Yo 17.1 bar and 2 km trial targets; the ICC's 15° elbow limit; the 19.8 / 25.2 km/h high-speed-running and sprint thresholds |
| **published** | Drawn from widely reported norms for the level concerned — good enough to judge against, not an official pass mark | Yo-Yo IR1 level 20–21 for professional outfield players; NBA Combine anthropometrics and agility; FIVB-aligned touch heights; elite match distance around 105–120 m/min and top speeds of 33–36 km/h |
| **estimated** | A sensible starting point set for this app | Most agility-test ranges, and every scale-free match metric |

The **protocols** are the real ones everywhere — Yo-Yo IR1, CMJ, the T-test, the NBA
Combine's lane agility and ¾-court sprint, FIVB block and spike touch, the BCCI 2 km
trial. What varies is how confident the poor → elite *range* is, and that is exactly
what the badge tells you.

Two things worth being blunt about:

* **Anything marked `estimated` should be retuned from the Weights tab** once you have
  results from your own squad and your own timing gates. Shipping a number is not the
  same as validating it.
* **Uncalibrated match metrics are not comparable to anything outside the clip.** They
  are in body-heights because pixels have no scale. Calibrate the pitch and they become
  metres and km/h, which is when they start meaning what a scout means by them.

---

## Two video lanes

They answer different questions and neither replaces the other.

| | Drill lane | Match lane |
|---|---|---|
| Model | MediaPipe Pose | YOLO11n-pose + ByteTrack |
| Input | one athlete, one movement | full match or snippet, everyone visible |
| Belongs to | a student | the squad, until a coach identifies players |
| Measures | technique — joint angles, symmetry, trunk stability | output — distance, speed, sprints, positioning |
| Feeds | corrective drills | the match-source position verdict |

### Drill lane (MediaPipe)

A drill clip (mp4, mov, avi, mkv, webm or m4v, up to 200 MB) is uploaded in 4 MB
pieces and queued. The worker samples up to 300 frames, runs MediaPipe Pose over them,
and derives:

| Metric | Meaning |
|---|---|
| `jumpHeightCm` | peak rise of the hips above their grounded position |
| `airtimeSec` | time spent near the top of the jump |
| `kneeFlexionMinDeg` / `kneeExtensionMaxDeg` | loading depth and take-off extension |
| `elbowFlexionMinDeg` / `elbowExtensionMaxDeg` | throwing / spiking / bowling arm action |
| `kneeSymmetryPct`, `armSymmetryPct` | left vs right working evenly |
| `trunkLeanAvgDeg`, `trunkStabilityPct` | torso posture and steadiness |
| `movementSpeedMps`, `movementBodySpansPerSec` | horizontal travel rate |
| `strideCadencePerSec` | steps per second |

Real-world units need the student's height on file; the `body-spans` versions work
without it. A skeleton-overlay thumbnail of the peak frame is saved and served from
`/api/videos/{id}/thumbnail`.

**Those numbers then become drills.** `video.py` holds a rule table — low leg symmetry
→ single-leg work; unstable trunk → anti-rotation core; shallow knee bend → tempo
squats and ankle mobility; low cadence → metronome runs — and each firing rule produces
a finding, why it matters, and what to do about it. They appear on the report's
Training tab beside the test-based plan. If detection was too poor to trust, the only
advice returned is how to re-film.

**Filming:** side-on, whole body in frame, steady camera, decent light, one person
visible. The app reports a `detectionRate` and warns when it is low.

#### Sport-specific technique

On top of the general movement measures, `pose_sports.py` finds the moment that matters
— the frame where the ankle is fastest, or the wrist is highest — and measures the
things only that sport cares about.

| Sport | Measured at the key frame |
|---|---|
| **Football** | striking foot, plant-foot distance, knee angle at contact, trunk lean at contact and while running |
| **Volleyball** | contact height above the head, elbow extension and shoulder angle at contact, how much of the reach came from the approach jump |
| **Basketball** | release elbow angle, release height, knee bend in the set, whether the follow-through holds |
| **Cricket** | bowling arm, elbow angle when the arm reaches horizontal and again at release, the extension between them, front-knee angle, trunk lean |

Each fires its own drills — a narrow plant foot, an arm that isn't extended at contact, a
collapsing follow-through, a front leg giving way at release.

**On the ICC 15° rule.** The cricket analyser measures elbow extension through the
delivery swing and compares it to the ICC's 15-degree limit. Read that number as a
*prompt to arrange a proper test*, never as a verdict: official adjudication uses 3D
motion capture in an accredited lab, and this is a single-camera 2D estimate. In testing
it reads low rather than high — a designed 28° action measured 20° — which is the safe
direction for a flag of this kind, but it means a marginal action can slip past. The app
states all of this next to the result.

**All these angles are 2D.** They are only accurate when the movement happens roughly
side-on to the lens; rotate the athlete 45 degrees and the same angle reads several
degrees off. Film square to the action.

The pinned MediaPipe version ships the pose model inside the wheel, so nothing is
downloaded at runtime. A worker without MediaPipe installed leaves drill clips queued
rather than failing them — the rest of the app keeps working.

### Match lane (YOLO)

A match clip (up to 600 MB) is uploaded the same way, with a label and which way the
team attacks, and queued for the worker. YOLO
detects every person, ByteTrack follows them at 5 fps over the first three minutes, and
each track that survives (seen for 2+ seconds in 6%+ of frames) becomes a candidate
player. The app then serves a keyframe — the moment with the most players visible — and
the coach clicks their student once. That track's numbers attach to that student, and
several students can be identified in the same clip.

**Units are body-heights, not metres.** Pixels mean nothing across zooms and angles, so
every distance is divided by that player's own bounding-box height. A zoomed-in clip and
a wide shot then produce comparable numbers with no calibration. Metres are also shown,
converted using the student's real height, and labelled approximate everywhere.

| Metric | Meaning |
|---|---|
| `matchDistance` | ground covered, body-heights per minute |
| `matchTopSpeed` | 95th-percentile speed, body-heights per second |
| `matchSprints` | high-intensity bursts per minute |
| `matchWorkRate` / `matchStationary` | share of time moving / held in position |
| `matchWidth` | how much of the frame's width they used |
| `matchAdvanced` / `matchDeepness` | how far forward they sat **relative to the other players on screen** |

That last pair is why the coach only has to name the attacking direction: positioning is
measured against where everyone else is, not against a pitch the app can't see. It is
carried only for Football and Kho-Kho, where play genuinely runs along one axis in normal
footage; for court sports that swap ends every few seconds it would be noise with a
number attached, so it is left out.

The `matchStationary` mirror exists for one reason: being deep *and* still is what
separates a goalkeeper from a centre-back, who is deep and covers ground.

**Per-minute rates need at least 45 seconds of tracking.** A ten-second highlight of
somebody sprinting extrapolates to several hundred metres per minute and would score a
perfect 100 against an elite benchmark. Below the threshold those metrics are simply not
reported — the engine treats them as unmeasured and lowers confidence, which is the
correct answer rather than a flattering one. Peak speed is exempt: a peak is a peak
however short the clip.

**A caveat worth repeating to whoever uses this:** ByteTrack will occasionally swap two
players who cross closely, and the reference ranges in `sports_config.py` were set for
typical wide footage. Retune them from the Weights tab once you have clips from your own
camera — framing shifts these numbers more than the players do.

### Pitch calibration — getting real metres

Click one marking you know the size of and everything becomes real. On the same keyframe
used for identification, pick a preset (penalty area, six-yard box, full pitch, FIBA
court, volleyball court, cricket pitch, badminton or tennis court, Kho-Kho field), click
the four corners in the order the app lists them, and a homography maps every tracked
position onto the ground plane in metres.

What that unlocks:

| Metric | |
|---|---|
| `matchMetresPerMin` | distance covered, directly comparable to a GPS report |
| `matchTopSpeedKmh` | peak speed, 95th percentile rather than a single jittery frame |
| `matchHsrPerMin` | metres above the high-speed threshold — **19.8 km/h** for football |
| `matchSprintMetresPerMin` | metres above the sprint threshold — **25.2 km/h** for football |
| `matchAccelPerMin` | efforts above 3 m/s² |

Court sports use lower thresholds (14.4 / 18.0 km/h) because the distances and speeds
are smaller; those are widely used rather than officially fixed, and the app labels them
accordingly.

Calibration is applied *after* tracking. The per-frame samples are kept on the clip
precisely so marking out the pitch re-derives every metric instantly — no second upload,
no model re-run — and any identifications already made pick up the new units. It can be
removed again if the four points were clicked badly.

### Why there is no ball tracking

An earlier version ran a second detector for the ball. It is gone: the coach clicking
the player they care about is more reliable than a general-purpose detector guessing
at a small, fast, often-hidden object, and it halves the work per frame. Old databases
keep their ball-metric weights on disk; they are simply ignored.

### Video retention

Video files are deleted 30 days after upload (`VIDEO_RETENTION_DAYS` changes it). The
measurements, tracks, keyframes and thumbnails are kept, so identifying players and
calibrating the pitch still work on an old clip.

---

## Diet plans

Energy is derived per kilogram of bodyweight from the sport's demand profile (endurance
sports carry more carbohydrate, power sports more protein), adjusted for training hours
and for athletes still growing. Fat is held inside 22–30% of energy and carbohydrate
absorbs the difference, so the three macros always add back up to the calorie target.

Meals are drawn from a food table tagged by diet level (vegan ⊂ vegetarian ⊂
eggetarian ⊂ non-veg) and by allergen, then filtered against what the student declared
on their form. Anything they marked — milk, egg, peanut, tree nuts, gluten, soy, fish,
shellfish — disappears from every suggestion.

The plan also gives a hydration target, protein distribution across the day, and
recovery timing. `GET /api/students/{id}/diet`, or the Diet tab on the report.

> This is general sports-nutrition guidance for training support, not medical or
> individual dietetic advice — the API returns that disclaimer with every plan and the
> UI shows it. A qualified sports dietitian should sign off on anything significant.

---

## API reference

| Method | Path | Auth | Purpose |
|---|---|---|---|
| `GET` | `/api/health` | — | status, storage, whether the worker is online |
| `POST` | `/api/auth/signup` `/login` | — | create a coach account (needs the sign-up code) / sign in |
| `GET` `POST` | `/api/auth/me` `/logout` | coach | current account, revoke this token |
| `GET` | `/api/sports`, `/api/sports/{sport}` | — | metric batteries and positions |
| `GET` `PUT` `POST` | `/api/sports/{sport}/weights[/reset]` | own sport | read / edit / reset weights |
| `POST` | `/api/students` | — | student registers themselves |
| `GET` | `/api/students` | coach | roster, already scoped to their sport |
| `GET` `PATCH` `DELETE` | `/api/students/{id}` | own sport | one student |
| `GET` `PUT` | `/api/students/{id}/results` | own sport | read / record test results |
| `GET` | `/api/students/{id}/history` | own sport | every measurement ever recorded |
| `GET` | `/api/students/{id}/analysis` | own sport | **the report** — ranking, why, plan, diet |
| `GET` | `/api/students/{id}/diet` | own sport | the diet plan on its own |
| `POST` `DELETE` | `/api/students/{id}/verify` | own sport | confirm the position they play / undo |
| `GET` | `/api/nutrition/options` | — | allergen and diet-preference lists |
| `POST` `GET` | `/api/students/{id}/videos` | own sport | announce an upload (name, size) / list drill clips |
| `PUT` | `/api/videos/{id}/upload` | own sport | one piece, with `X-Chunk-Range: bytes a-b/total` |
| `GET` | `/api/videos/{id}/thumbnail` | own sport | skeleton keyframe |
| `DELETE` | `/api/videos/{id}` | own sport | remove a drill clip |
| `POST` `GET` | `/api/matches` | own sport | announce a match upload / list clips |
| `PUT` | `/api/matches/{id}/upload` | own sport | one piece of the match video |
| `GET` | `/api/matches/{id}` | own sport | tracks, metrics and clickable keyframe boxes |
| `GET` | `/api/matches/{id}/keyframe` | own sport | the frame the coach identifies players on |
| `POST` | `/api/matches/{id}/assign` | own sport | "track 7 is this student" |
| `DELETE` | `/api/matches/{id}/assign/{track}` | own sport | undo an identification |
| `POST` `DELETE` | `/api/matches/{id}/calibrate` | own sport | mark out the pitch / remove it |
| `DELETE` | `/api/matches/{id}` | own sport | remove a match clip |
| `GET` | `/api/training` | coach | the AI Training page: labels, versions, worker, queue, sheet |
| `POST` | `/api/training/versions/{id}/rollback` | own sport | put an older model back live |

Every piece of an upload is answered with how many bytes are really stored, and the
browser carries on from there — so a dropped connection costs one piece, and a piece
sent twice is recognised rather than stored twice.

Test results are **appended, never overwritten** — `/history` returns the full series
for the progress sparklines, while the analysis always uses the newest value per metric.

---

## The interface

Six screens behind a rail on desktop and a bottom tab bar on phones, with a
light / dark / follow-system theme toggle that persists.

The report itself is tabbed: **Overview** (best-fit position, the reasoning, the radar,
standouts and weak links, and the two-source panel with its reconciliation),
**Measurements** (every test metric with its reference range and a progress sparkline once
there are two readings), **Positions** (all of them ranked, each expanding to the weight
table behind its score), **Match** (the footage-only verdict, match metrics with their own
radar, and every clip the student appears in), **Training**, **Diet**, **Video**.

Uploads show a progress bar, then the clip waits as **waiting → analysing → done**; the
page refreshes itself while anything is in the queue, and says plainly when the
analysis computer is off. The Dashboard filters Pending / Verified, and the report
opens with the verification card.

Identifying players is a frame with the detected boxes laid over it — click a box, pick a
name. Identified boxes turn green and carry the student's name.

Charts are inline SVG written by hand — a radar for the athlete profile, sparklines for
progress, a stacked bar for the macro split. Colours come from CSS custom properties, so
light and dark are two value sets rather than two stylesheets, and the palette was run
through a colour-vision-deficiency check rather than eyeballed. Every chart value is
also readable as text, so nothing depends on colour alone.

---

## Project layout

```
api/index.py        Vercel's entry point — imports backend/main.py
vercel.json         build, Python function, Singapore region, /api rewrite
requirements.txt    the website's (light) Python packages — what Vercel installs
.env.example        every setting, documented

backend/
  main.py           FastAPI app — all routes, uploads, verification, sheet sync
  worker.py         the worker: queue, analysis, training, retention, sheet repair
  trainer.py        learns position weights from verified students (pure logic)
  storage.py        videos in Google Drive or a local folder, chunked uploads
  sheets.py         the Pending / Verified Google Sheet
  gapi.py           the one Google login both of those use
  setup_google.py   one-time: Google sign-in, creates the folder and the sheet
  auth.py           password hashing + bearer-token sessions
  db.py             Postgres (DATABASE_URL) or SQLite engine + session
  migrate.py        adds missing columns on startup
  models.py         coaches, students, test results, weights, videos, match clips,
                    model versions, app state
  schemas.py        request/response validation
  sports_config.py  sports, metrics, reference ranges, default weights, match
                    archetypes, nutrition profiles
  scoring.py        the prediction engine (no DB access — pure logic)
  nutrition.py      diet engine + food table
  video.py          MediaPipe drill pipeline, metric maths, drill rules
  pose_sports.py    sport-specific technique: strike, spike, shot, bowling action
  match_video.py    YOLO + ByteTrack match pipeline (worker only)
  match_metrics.py  track metrics + homography, numpy only (website and worker)
  requirements.txt  everything for the laptop / iMac
  requirements-match.txt   optional — the YOLO lane
  models/           YOLO weights, downloaded on first use

frontend/src/
  App.jsx           app shell, nav, theme, auth state
  Login.jsx         sign in / create account
  StudentForm.jsx   public student self-entry
  CoachEntry.jsx    roster, test results, drill-video upload
  Matches.jsx       match clips, the click-to-identify frame, per-player table
  Dashboard.jsx     squad overview + roster
  Report.jsx        the tabbed report, both source verdicts, reconciliation
  Diet.jsx          fuelling targets and the day's menu
  VideoCard.jsx     clip metrics, drills, skeleton thumbnail
  Weights.jsx       weight editor
  Training.jsx      the AI Training page
  charts.jsx        radar, sparkline, macro bar — all inline SVG
  api.js            fetch wrapper, token handling, shared formatting
  styles.css        the whole design system
```

`scoring.py` takes weights as an argument and never touches the database, so the
built-in defaults and a coach's edited weights run through identical code.
