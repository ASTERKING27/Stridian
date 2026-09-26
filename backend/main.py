"""
Stridian — API.

Run from this folder:  uvicorn main:app --reload
Interactive docs:      http://127.0.0.1:8000/docs

Access model: students sign in with their university email (proved by an emailed
code) and enrol with an enrolment code their coach hands out. Their portal holds their
details, photo and achievements, and their report once a coach has verified them.
Everything else is coach-only, and a coach is locked to one sport — a football coach
never sees basketball students, their weights, or their videos. Admins (ADMIN_EMAILS)
are coaches who can switch sport, add students by hand, change anyone's personal
details and open the Google Sheets.

This process never runs a vision model. Uploaded videos are queued, and the worker
(worker.py, on the laptop or the lab iMac) analyses them whenever it is switched on.
That is what lets this API run on a free serverless host.
"""

import hashlib
import hmac
import logging
import os
import re
import secrets
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

import auth
import docreader
import export
import mailer
import match_metrics
import migrate
import nutrition
import scoring
import sheets
import sports_config as sc
import storage
import trainer
from db import Base, SessionLocal, engine, get_db
from models import (LEVELS, Achievement, AppState, Coach, MatchAssignment, MatchClip,
                    ModelVersion, PositionWeight, Student, StudentAccount, StudentSession,
                    TestResult, VideoAnalysis)
from models import _now as utcnow
from models import admin_emails
from schemas import (ADMIN_ONLY, STUDENT_ONCE, AchievementIn, AchievementOut, CalibrationIn, CoachDetails,
                     CoachLogin, CoachOut, CoachSignup, MatchAssignIn, MatchClipOut,
                     MatchUploadIn, ResultsIn, ReviewIn, SportIn, StudentCodeIn, StudentCreate,
                     StudentEnrol, StudentListItem, StudentLogin, StudentOut, StudentSelfUpdate,
                     StudentUpdate, StudentVerifyIn, TokenOut, UploadIn, VerifyIn, VideoOut,
                     WeightsIn)

log = logging.getLogger("stridian")

ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".m4v"}
MAX_VIDEO_BYTES = 200 * 1024 * 1024   # 200 MB — drill clips
MAX_MATCH_BYTES = 600 * 1024 * 1024   # 600 MB — match footage is longer
WORKER_ONLINE_SECONDS = 120           # the worker says hello at least this often when idle


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def require_sport(name_or_slug: str) -> str:
    name = name_or_slug if sc.get_sport(name_or_slug) else sc.name_for_slug(name_or_slug)
    if not name:
        raise HTTPException(404, f"Unknown sport: {name_or_slug}")
    return name


def seed_weights(db: Session, sport_name: str, force: bool = False):
    """Make sure every default (position, metric) weight exists in the database.

    It tops up whatever is missing and leaves every existing row alone, so a coach's
    edits survive (including a weight deliberately set to 0 — that row exists, so it is
    never re-seeded). `force` wipes and reseeds, for Reset to defaults.
    """
    if force:
        db.query(PositionWeight).filter(PositionWeight.sport == sport_name).delete()
        db.commit()

    present = {
        (row.position, row.metric_key)
        for row in db.scalars(select(PositionWeight).where(PositionWeight.sport == sport_name))
    }
    missing = [
        PositionWeight(sport=sport_name, position=position,
                       metric_key=metric_key, weight=float(weight))
        for position, weights in sc.default_weights(sport_name).items()
        for metric_key, weight in weights.items()
        if (position, metric_key) not in present
    ]
    if missing:
        db.add_all(missing)
        db.commit()


def load_weights(db: Session, sport_name: str) -> dict:
    seed_weights(db, sport_name)
    valid = sc.metric_map(sport_name)
    rows = db.scalars(select(PositionWeight).where(PositionWeight.sport == sport_name)).all()
    out: dict[str, dict[str, float]] = {}
    for row in rows:
        # a metric retired from the config (the old ball-tracking ones) keeps its rows in
        # older databases; counting them would read as permanently missing data
        if row.metric_key in valid:
            out.setdefault(row.position, {})[row.metric_key] = row.weight
    ordered = {p: out.pop(p) for p in sc.get_sport(sport_name)["positions"] if p in out}
    ordered.update(out)
    return ordered


def apply_weights(db: Session, sport_name: str, weights: dict):
    """Make `weights` the live ones for a sport (caller commits)."""
    existing = {
        (r.position, r.metric_key): r
        for r in db.scalars(select(PositionWeight).where(PositionWeight.sport == sport_name))
    }
    for position, per_metric in weights.items():
        for metric_key, weight in per_metric.items():
            row = existing.get((position, metric_key))
            if row is None:
                db.add(PositionWeight(sport=sport_name, position=position,
                                      metric_key=metric_key, weight=float(weight)))
            else:
                row.weight = float(weight)


def record_baseline(db: Session, sport_name: str, note: str):
    """Weights a person chose become a version too — the starting point for training."""
    db.add(ModelVersion(sport=sport_name, kind="baseline", weights=load_weights(db, sport_name),
                        deployed=True, note=note))


def history_rows(db: Session, student_id: int) -> list:
    """Every recorded measurement, oldest first, for progress-over-time charts."""
    rows = db.scalars(
        select(TestResult).where(TestResult.student_id == student_id)
        .order_by(TestResult.recorded_at.asc(), TestResult.id.asc())
    ).all()
    return [{"metric_key": r.metric_key, "value": r.value, "recorded_at": r.recorded_at} for r in rows]


def latest_results(db: Session, student_id: int) -> dict:
    rows = db.scalars(
        select(TestResult)
        .where(TestResult.student_id == student_id)
        .order_by(TestResult.recorded_at.asc(), TestResult.id.asc())
    ).all()
    return {row.metric_key: row.value for row in rows}  # later rows win


def metric_rows(db: Session, student: Student) -> list:
    """A student's 0-100 score on every metric — what the trainer learns from."""
    match_values = match_metrics.aggregate(
        [a.metrics for a in student.match_assignments if a.metrics])
    values = scoring.build_metric_values(
        student.sport, {"height_cm": student.height_cm, "weight_kg": student.weight_kg},
        latest_results(db, student.id), match_values)
    return scoring.score_metrics(student.sport, values)


def coach_student(student_id: int, coach: Coach, db: Session) -> Student:
    """Fetch a student, 404ing for anyone outside the coach's own sport (for an admin,
    the sport they have switched to)."""
    student = db.get(Student, student_id)
    if student is None or student.sport != coach.sport:
        raise HTTPException(404, "Student not found")
    return student


def require_admin(coach: Coach) -> None:
    if not coach.is_admin:
        raise HTTPException(403, "Only an admin can do that.")


def check_ra_free(db: Session, ra_number: str | None, student_id: int | None = None) -> None:
    if ra_number and db.scalar(select(Student.id).where(Student.ra_number == ra_number,
                                                        Student.id != (student_id or 0))):
        raise HTTPException(409, "That RA number is already registered — if it's yours, tell your coach.")


def summarise(report: dict) -> dict:
    """The small shape the UI needs for a single-source verdict panel."""
    return {
        "available": report.get("recommended") is not None,
        "recommended": report.get("recommended"),
        "overallScore": report.get("overallScore"),
        "margin": report.get("margin"),
        "positions": [
            {"position": p["position"], "fit": p["fit"], "confidence": p["confidence"],
             "coverage": p["coverage"]}
            for p in report["positions"]
        ],
    }


def reconcile(test_report: dict, match_report: dict) -> dict:
    """Say plainly whether the testing data and the match footage tell the same story."""
    t = test_report.get("recommended")
    m = match_report.get("recommended")

    if not t and not m:
        return {"agreement": "none",
                "text": "No test results and no match footage yet — nothing to compare."}
    if not m:
        return {"agreement": "tests-only", "testPosition": t["position"],
                "text": f"Based on testing data alone. Assign this student in a match clip "
                        f"to check whether {t['position']} holds up in a real game."}
    if not t:
        return {"agreement": "match-only", "matchPosition": m["position"],
                "text": f"Based on match footage alone. Record the test battery to confirm "
                        f"the physical profile behind {m['position']}."}

    if t["position"] == m["position"]:
        return {
            "agreement": "agree", "testPosition": t["position"], "matchPosition": m["position"],
            "text": f"Both agree on {t['position']} — the testing profile and what actually "
                    f"happened on the pitch point the same way, which is the strongest signal "
                    f"this report can give.",
        }

    match_rank = next((i for i, p in enumerate(match_report["positions"])
                       if p["position"] == t["position"]), 99)
    test_rank = next((i for i, p in enumerate(test_report["positions"])
                      if p["position"] == m["position"]), 99)

    if match_rank <= 2 and test_rank <= 2:
        return {
            "agreement": "near", "testPosition": t["position"], "matchPosition": m["position"],
            "text": f"Close but not identical: the tests favour {t['position']}, the footage "
                    f"favours {m['position']}, and each one ranks the other's pick in its own "
                    f"top three. Either role suits them; the choice is tactical, not physical.",
        }

    return {
        "agreement": "disagree", "testPosition": t["position"], "matchPosition": m["position"],
        "text": f"The two disagree: physically they test as a {t['position']}, but in the footage "
                f"they played like a {m['position']}. That usually means they are being deployed "
                f"out of position, or the clip caught an unusual game — worth a second clip before "
                f"acting on it.",
    }


def build_report(db: Session, student: Student) -> dict:
    profile = {"height_cm": student.height_cm, "weight_kg": student.weight_kg}
    tests = latest_results(db, student.id)
    weights = load_weights(db, student.sport)
    match_values = match_metrics.aggregate(
        [a.metrics for a in student.match_assignments if a.metrics]
    )

    def run(sources):
        return scoring.analyse(student.sport, profile, tests, weights,
                               match_values=match_values, sources=sources)

    report = run(None)                          # the headline, all evidence together
    test_report = run({"test", "profile"})      # the battery, plus height/weight
    match_report = run({"match"})               # what the footage alone says

    report["bySource"] = {"test": summarise(test_report), "match": summarise(match_report)}
    report["reconciliation"] = reconcile(test_report, match_report)
    report["matchValues"] = match_values
    report["matchClips"] = [
        {"clipId": a.clip_id, "trackId": a.track_id, "label": a.clip.label,
         "originalName": a.clip.original_name, "metrics": a.metrics, "context": a.context,
         "createdAt": a.clip.created_at}
        for a in sorted(student.match_assignments, key=lambda a: a.created_at, reverse=True)
    ]
    report["student"] = StudentOut.model_validate(student).model_dump()
    if student.declared_position:
        report["declaredPositionFit"] = next(
            (p for p in report["positions"] if p["position"] == student.declared_position), None
        )
    report["videos"] = [
        {"id": v.id, "original_name": v.original_name, "status": v.status,
         "message": v.message, "duration_sec": v.duration_sec,
         "frames_detected": v.frames_detected, "metrics": v.metrics,
         "has_thumbnail": v.has_thumbnail,
         "video_deleted_at": v.video_deleted_at, "created_at": v.created_at}
        for v in sorted(student.videos, key=lambda x: x.created_at, reverse=True)
        if v.status != "uploading"
    ]
    report["diet"] = nutrition.plan(
        StudentOut.model_validate(student).model_dump(),
        student.sport,
        report["recommended"]["position"] if report.get("recommended") else None,
    )
    return report


# ------------------------------- shared state ------------------------------ #

def get_state(db: Session, key: str) -> dict:
    row = db.get(AppState, key)
    return dict(row.value or {}) if row else {}


def set_state(db: Session, key: str, value: dict):
    row = db.get(AppState, key)
    if row is None:
        db.add(AppState(key=key, value=value))
    else:
        row.value = value
        row.updated_at = utcnow()
    db.commit()


def worker_status(db: Session) -> dict:
    w = get_state(db, "worker")
    if not w.get("lastSeen"):
        return {"seen": False, "online": False}
    age = (utcnow() - datetime.fromisoformat(w["lastSeen"])).total_seconds()
    busy = w.get("doing", "idle") != "idle"
    # a long match clip keeps the worker quiet for minutes; that is still "online"
    online = age < WORKER_ONLINE_SECONDS or (busy and age < 1800)
    return {**w, "seen": True, "online": online, "secondsAgo": round(age)}


def sync_sheet(db: Session, students=()):
    """Recompute these students' sheet rows, then push the whole sheet.

    Called after every change a coach or student makes. Never raises: a Google hiccup
    must not turn a saved enrolment into an error page. The worker pushes again on its
    next pass, so a missed push repairs itself.
    """
    try:
        # a row cached before a sheet column was added would land in the wrong columns;
        # rebuild those instead of pushing them
        width = len(sheets.HEADER)
        stale = [s for s in db.scalars(select(Student)) if s.sheet_row and len(s.sheet_row) != width]
        for student in {*students, *stale}:
            student.sheet_row = sheets.row_for(build_report(db, student), student)
        db.commit()
        if sheets.configured():
            status = sheets.push(db.scalars(select(Student)).all())
            set_state(db, "sheet", {**status, "at": utcnow().isoformat()})
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("sheet sync failed")


def sync_people(db: Session, *keys):
    """Rewrite the admin's people spreadsheets (all of them, or just `keys`), creating any
    that don't exist yet. Never raises, like sync_sheet, and the worker repeats it."""
    if not sheets.gapi.configured():
        return
    rows = {
        "profiles": lambda: [sheets.profile_row(s) for s in
                             db.scalars(select(Student).order_by(Student.sport, Student.name))],
        "achievements": lambda: [sheets.achievement_row(a) for a in
                                 db.scalars(select(Achievement).where(Achievement.status != "draft")
                                            .order_by(Achievement.id.desc()))],
        "coaches": lambda: [sheets.coach_row(c) for c in db.scalars(select(Coach).order_by(Coach.id))],
    }
    for key in keys or sheets.PEOPLE:
        title, tab, header = sheets.PEOPLE[key]
        registry = get_state(db, "people_sheets")
        entry = dict(registry.get(key) or {})
        try:
            if not entry.get("id"):
                # ponytail: two first-ever pushes at the same moment could each make one;
                # the spare is simply never written to again
                entry["id"] = sheets.create(title, tab, header)
                set_state(db, "people_sheets", {**registry, key: entry})
            sheets.write(entry["id"], {tab: [header] + rows[key]()})
            entry.update(ok=True, error=None)
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            log.exception("people sheet %s failed", key)
            entry.update(ok=False, error=str(exc)[:300])
        entry["at"] = utcnow().isoformat()
        set_state(db, "people_sheets", {**get_state(db, "people_sheets"), key: entry})


def people_sheets(db: Session) -> list:
    """Links to the admin's people spreadsheets, and how their last push went."""
    registry = get_state(db, "people_sheets")
    return [
        {"key": key, "title": title, **(registry.get(key) or {}),
         "url": f"https://docs.google.com/spreadsheets/d/{registry[key]['id']}"
                if (registry.get(key) or {}).get("id") else None}
        for key, (title, _tab, _header) in sheets.PEOPLE.items()
    ]


def sport_students(db: Session, sport_name: str):
    return db.scalars(select(Student).where(Student.sport == sport_name)).all()


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

def init_db():
    """Tables, missing columns, default weights. Safe to run on every start."""
    Base.metadata.create_all(bind=engine)
    # create_all won't touch a table that already exists, so a database made before a
    # column was added keeps working until something writes that field. Close the gap
    # here rather than making anyone delete their data to pick up a new feature.
    migrate.run(engine, Base.metadata)
    try:
        # one student per RA number, even if two enrolments race (the app checks first,
        # for a friendly message); partial, because most rows predate RA numbers
        with engine.begin() as conn:
            conn.exec_driver_sql("CREATE UNIQUE INDEX IF NOT EXISTS uq_students_ra_number "
                                 "ON students (ra_number) WHERE ra_number IS NOT NULL")
    except Exception:  # noqa: BLE001 — a duplicate already in the data; the app check still runs
        log.warning("could not add the RA number index", exc_info=True)
    db = SessionLocal()
    try:
        for sport_name in sc.sport_names():
            seed_weights(db, sport_name)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Stridian API", version="3.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173",
                   "http://localhost:4173", "http://127.0.0.1:4173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health(db: Session = Depends(get_db)):
    return {
        "status": "ok",
        "sports": len(sc.sport_names()),
        "storage": storage.backend(),
        "worker": worker_status(db),
        "chunkSize": storage.CHUNK,
        "studentDomain": student_domain(),
        "documentAI": docreader.configured(),
    }


# ----------------------------------- auth ---------------------------------- #

@app.post("/api/auth/signup", response_model=TokenOut, status_code=201)
def signup(payload: CoachSignup, db: Session = Depends(get_db)):
    required = os.environ.get("COACH_SIGNUP_CODE", "").strip()
    if not required and os.environ.get("VERCEL"):
        # on the public internet an open sign-up would let anyone read a squad's details
        raise HTTPException(503, "Coach sign-up is closed until COACH_SIGNUP_CODE is set on the server.")
    typed = (payload.signup_code or "").strip()
    if required and not hmac.compare_digest(typed.encode(), required.encode()):
        raise HTTPException(403, "That sign-up code is not right — ask whoever runs this site.")
    sport = require_sport(payload.sport)
    email = payload.email.strip().lower()
    if db.scalar(select(Coach).where(func.lower(Coach.email) == email)):
        raise HTTPException(409, "An account already uses that email")
    if email in admin_emails():
        prove_admin_email(db, email, payload.email_code)
    coach = Coach(name=payload.name, email=email, sport=sport, employee_id=payload.employee_id,
                  phone=payload.phone, designation=payload.designation,
                  password_hash=auth.hash_password(payload.password))
    db.add(coach)
    db.commit()
    db.refresh(coach)
    token = auth.issue_token(db, coach)
    sync_people(db, "coaches")
    return TokenOut(token=token, coach=CoachOut.model_validate(coach))


def prove_admin_email(db: Session, email: str, typed: str | None) -> None:
    """An ADMIN_EMAILS address gets an account only once its owner has typed a code
    emailed to it — otherwise whoever typed a listed address first would be an admin.
    Without a code this sends one and answers 428; with one it checks it."""
    key = "admincode:" + hashlib.sha256(email.encode()).hexdigest()[:24]
    row = db.scalar(select(AppState).where(AppState.key == key).with_for_update())
    state = dict(row.value or {}) if row else {}
    sent = datetime.fromisoformat(state["sentAt"]) if state.get("sentAt") else None
    age = (utcnow() - sent).total_seconds() if sent else None

    if typed and typed.strip():
        tries = state.get("tries", 0)
        if (age is not None and age <= auth.CODE_MINUTES * 60 and tries < auth.CODE_TRIES
                and hmac.compare_digest(state.get("hash", ""), auth.code_hash(email, typed.strip()))):
            set_state(db, key, {})        # used up
            return
        set_state(db, key, {**state, "tries": tries + 1})
        raise HTTPException(400, "That code is wrong or has expired — clear it and create the "
                                 "account again for a new one.")
    if age is None or age >= auth.CODE_RESEND_SECONDS:
        code = f"{secrets.randbelow(1_000_000):06d}"
        try:
            mailer.send_code(email, code)
        except mailer.MailError as exc:
            db.rollback()
            raise HTTPException(503, str(exc)) from exc
        set_state(db, key, {"hash": auth.code_hash(email, code), "sentAt": utcnow().isoformat(),
                            "tries": 0})
    else:
        db.rollback()                     # release the lock; the last code still stands
    raise HTTPException(428, f"This is an admin address, so a 6-digit code has been emailed to "
                             f"{email}. Type it in to finish creating the account.")


@app.post("/api/auth/login", response_model=TokenOut)
def login(payload: CoachLogin, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    coach = db.scalar(select(Coach).where(func.lower(Coach.email) == email))
    # same message and the same hashing time either way, so neither can be used to
    # probe which emails have accounts
    stored = coach.password_hash if coach else auth.dummy_hash()
    if not auth.verify_password(payload.password, stored) or coach is None:
        raise HTTPException(401, "Email or password is incorrect")
    return TokenOut(token=auth.issue_token(db, coach), coach=CoachOut.model_validate(coach))


@app.get("/api/auth/me", response_model=CoachOut)
def me(coach: Coach = Depends(auth.current_coach)):
    return coach


@app.patch("/api/auth/me", response_model=CoachOut)
def update_me(payload: CoachDetails, db: Session = Depends(get_db),
              coach: Coach = Depends(auth.current_coach)):
    """A coach's own details — how accounts from before sign-up asked for them catch up."""
    data = payload.model_dump(exclude_unset=True)
    emptied = [k for k in ("name", "employee_id", "phone") if k in data and data[k] is None]
    if emptied:
        raise HTTPException(400, f"These can't be left empty: {', '.join(emptied)}")
    for field, value in data.items():
        setattr(coach, field, value)
    db.commit()
    db.refresh(coach)
    sync_people(db, "coaches")
    return coach


@app.patch("/api/auth/sport", response_model=CoachOut)
def switch_sport(payload: SportIn, db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    """An admin looks at one sport at a time, and can switch between them."""
    require_admin(coach)
    coach.sport = require_sport(payload.sport)
    db.commit()
    db.refresh(coach)
    return coach


@app.get("/api/coaches", response_model=list[CoachOut])
def list_coaches(db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    require_admin(coach)
    return db.scalars(select(Coach).order_by(Coach.sport, Coach.name)).all()


@app.post("/api/auth/logout", status_code=204)
def logout(authorization: str = Header(), db: Session = Depends(get_db),
           coach: Coach = Depends(auth.current_coach)):
    """Revoke just the token that made this call, leaving other devices signed in."""
    auth.revoke_token(db, authorization.split(" ", 1)[1].strip())


# ----------------------------- student accounts ---------------------------- #
#
# Sign-up and "forgot password" are one flow: ask for a code, then send the code with
# the password you want. Whoever can read the inbox sets the password, so a stranger who
# types someone else's email first gains nothing.

def student_domain() -> str:
    return os.environ.get("STUDENT_EMAIL_DOMAIN", "srmist.edu.in").strip().lower().lstrip("@")


CODES_PER_DAY = 300   # all accounts together — stays under Gmail's ~500 emails a day


def university_email(raw: str) -> str:
    email = raw.strip().lower()
    # a plain local part only: anything looser (an "=?q?...?=" encoded word, say) can be
    # decoded by the mail library into a different, outside recipient
    if not re.fullmatch(r"[a-z0-9._%+-]+@" + re.escape(student_domain()), email):
        raise HTTPException(400, f"Use your university email — the one ending in @{student_domain()}.")
    return email


def student_view(account: StudentAccount) -> dict:
    """What a signed-in student sees about themselves. Coach notes stay with the coach."""
    s = account.student
    return {"email": account.email,
            "student": StudentOut.model_validate(s).model_dump(exclude={"coach_notes"}) if s else None}


@app.post("/api/student/code", status_code=202)
def student_code(payload: StudentCodeIn, db: Session = Depends(get_db)):
    """Email a 6-digit code — to create an account, or to reset a forgotten password."""
    email = university_email(payload.email)
    since = utcnow() - timedelta(days=1)
    if (db.scalar(select(func.count()).select_from(StudentAccount)
                  .where(StudentAccount.code_sent_at > since)) or 0) >= CODES_PER_DAY:
        raise HTTPException(429, "Stridian has sent a lot of sign-in codes today — try again "
                                 "tomorrow, or tell your coach.")
    account = db.scalar(select(StudentAccount).where(StudentAccount.email == email))
    if account is None:
        account = StudentAccount(email=email)
        db.add(account)
    elif auth.code_cooling_down(account):
        raise HTTPException(429, "A code was sent less than a minute ago — check your inbox "
                                 "(and spam folder) before asking for another.")
    code = auth.new_code(account)
    try:
        mailer.send_code(email, code)
    except mailer.MailError as exc:
        db.rollback()   # nothing was sent, so don't start the resend timer
        raise HTTPException(503, str(exc)) from exc
    db.commit()
    return {"email": email}


@app.post("/api/student/verify")
def student_verify(payload: StudentVerifyIn, db: Session = Depends(get_db)):
    """The emailed code plus a new password: sets the password and signs the student in."""
    email = payload.email.strip().lower()
    # locked until commit, so guesses sent in parallel still count one at a time
    account = db.scalar(select(StudentAccount).where(StudentAccount.email == email).with_for_update())
    ok = account is not None and auth.use_code(account, payload.code)
    db.commit()     # a wrong guess still counts
    if not ok:
        raise HTTPException(400, "That code is wrong or has expired — ask for a new one.")
    account.password_hash = auth.hash_password(payload.password)
    # a new password signs out every other device
    db.query(StudentSession).filter(StudentSession.account_id == account.id).delete()
    db.commit()
    return {"token": auth.issue_student_token(db, account), "me": student_view(account)}


@app.post("/api/student/login")
def student_login(payload: StudentLogin, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    account = db.scalar(select(StudentAccount).where(StudentAccount.email == email))
    stored = account.password_hash if account and account.password_hash else auth.dummy_hash()
    if not auth.verify_password(payload.password, stored) or not (account and account.password_hash):
        raise HTTPException(401, "Email or password is incorrect")
    return {"token": auth.issue_student_token(db, account), "me": student_view(account)}


@app.get("/api/student/me")
def student_me(account: StudentAccount = Depends(auth.current_student)):
    return student_view(account)


@app.post("/api/student/logout", status_code=204)
def student_logout(authorization: str = Header(), db: Session = Depends(get_db),
                   account: StudentAccount = Depends(auth.current_student)):
    auth.revoke_token(db, authorization.split(" ", 1)[1].strip(), StudentSession)


@app.post("/api/student/enrol", status_code=201)
def student_enrol(payload: StudentEnrol, db: Session = Depends(get_db),
                  account: StudentAccount = Depends(auth.current_student)):
    """A signed-in student joins a sport, using the code that sport's coach gave out."""
    if account.student is not None:
        raise HTTPException(409, f"You're already enrolled in {account.student.sport}.")
    sport = require_sport(payload.sport)
    code = get_state(db, f"enrol:{sport}").get("code", "")
    typed = re.sub(r"[\s-]", "", payload.enrol_code).upper()
    if not code or not hmac.compare_digest(typed.encode(), code.encode()):
        raise HTTPException(403, f"That enrolment code isn't right for {sport} — ask your coach for it.")
    check_ra_free(db, payload.ra_number)
    data = payload.model_dump(exclude={"enrol_code"})
    data["sport"] = sport
    student = Student(**data)
    account.student = student
    db.add(student)
    db.commit()
    sync_sheet(db, [student])
    sync_people(db, "profiles")
    db.refresh(account)
    return student_view(account)


def my_student(account: StudentAccount) -> Student:
    if account.student is None:
        raise HTTPException(409, "Enrol in your sport first.")
    return account.student


@app.patch("/api/student/profile")
def student_update_profile(payload: StudentSelfUpdate, db: Session = Depends(get_db),
                           account: StudentAccount = Depends(auth.current_student)):
    """A student correcting their own details. Their sport stays as enrolled, and their RA
    number and date of birth can be filled in once (students from before these existed)
    but only an admin changes them after that."""
    student = my_student(account)
    data = payload.model_dump(exclude_unset=True)
    for field in STUDENT_ONCE & set(data):
        if getattr(student, field) is not None and data[field] != getattr(student, field):
            raise HTTPException(403, "Your RA number and date of birth can only be changed by an "
                                     "admin — ask your coach.")
    check_ra_free(db, data.get("ra_number"), student.id)
    for field, value in data.items():
        setattr(student, field, value)
    if not (student.father_phone or student.mother_phone):
        db.rollback()
        raise HTTPException(400, "Add at least one parent's mobile number.")
    db.commit()
    sync_sheet(db, [student])
    sync_people(db, "profiles")
    db.refresh(account)
    return student_view(account)


@app.get("/api/student/report")
def student_report(db: Session = Depends(get_db),
                   account: StudentAccount = Depends(auth.current_student)):
    """The student's own report — read-only, and only once a coach has verified them."""
    student = account.student
    if student is None or student.status != "verified":
        raise HTTPException(403, "Your report appears here once your coach has verified you.")
    report = build_report(db, student)
    report["student"].pop("coach_notes", None)
    report["history"] = history_rows(db, student.id)
    return report


# ----------------------- enrolment codes (for coaches) ---------------------- #

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"   # no 0/O or 1/I to misread


def enrol_code(db: Session, sport: str, fresh: bool = False) -> str:
    """This sport's enrolment code, made on first use. `fresh` replaces it, so the old
    one stops working (students already enrolled are unaffected)."""
    key = f"enrol:{sport}"
    code = get_state(db, key).get("code")
    if fresh or not code:
        code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
        set_state(db, key, {"code": code})
    return code


@app.get("/api/enrol-code")
def get_enrol_code(db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    return {"sport": coach.sport, "code": enrol_code(db, coach.sport)}


@app.post("/api/enrol-code/rotate")
def rotate_enrol_code(db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    return {"sport": coach.sport, "code": enrol_code(db, coach.sport, fresh=True)}


# ---------------------------- sports & weights ----------------------------- #

@app.get("/api/sports")
def list_sports():
    return [
        {"name": name, "slug": sc.slug_for(name), "note": sc.get_sport(name)["note"],
         "metrics": sc.get_sport(name)["metrics"],
         "positions": list(sc.get_sport(name)["positions"].keys())}
        for name in sc.sport_names()
    ]


@app.get("/api/sports/{sport}")
def get_sport_detail(sport: str):
    name = require_sport(sport)
    cfg = sc.get_sport(name)
    return {
        "name": name, "slug": sc.slug_for(name), "note": cfg["note"],
        "metrics": cfg["metrics"],
        "positions": [{"name": p, "blurb": cfg["positions"][p]["blurb"]} for p in cfg["positions"]],
    }


@app.get("/api/sports/{sport}/weights")
def get_weights(sport: str, db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    name = require_sport(sport)
    auth.require_own_sport(coach, name)
    return {"sport": name, "weights": load_weights(db, name),
            "defaults": sc.default_weights(name), "metrics": sc.get_sport(name)["metrics"]}


@app.put("/api/sports/{sport}/weights")
def put_weights(sport: str, payload: WeightsIn, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    name = require_sport(sport)
    auth.require_own_sport(coach, name)
    seed_weights(db, name)
    valid = set(sc.metric_map(name))

    for position, weights in payload.weights.items():
        if position not in sc.get_sport(name)["positions"]:
            raise HTTPException(400, f"'{position}' is not a position in {name}")
        for metric_key, weight in weights.items():
            if metric_key not in valid:
                raise HTTPException(400, f"'{metric_key}' is not a metric of {name}")
            if weight < 0:
                raise HTTPException(400, "Weights cannot be negative")
    apply_weights(db, name, payload.weights)
    db.commit()
    record_baseline(db, name, f"Edited by {coach.name}")
    db.commit()
    sync_sheet(db, sport_students(db, name))
    return {"sport": name, "weights": load_weights(db, name)}


@app.post("/api/sports/{sport}/weights/reset")
def reset_weights(sport: str, db: Session = Depends(get_db),
                  coach: Coach = Depends(auth.current_coach)):
    name = require_sport(sport)
    auth.require_own_sport(coach, name)
    seed_weights(db, name, force=True)
    record_baseline(db, name, f"Reset to defaults by {coach.name}")
    db.commit()
    sync_sheet(db, sport_students(db, name))
    return {"sport": name, "weights": load_weights(db, name)}


# --------------------------------- students -------------------------------- #

@app.post("/api/students", response_model=StudentOut, status_code=201)
def create_student(payload: StudentCreate, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    """An admin adding a student by hand, in any sport. Students enrol themselves through
    /api/student/enrol instead."""
    require_admin(coach)
    data = payload.model_dump()
    data["sport"] = require_sport(payload.sport)
    check_ra_free(db, payload.ra_number)
    student = Student(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    sync_sheet(db, [student])
    sync_people(db, "profiles")
    return student


@app.get("/api/students", response_model=list[StudentListItem])
def list_students(db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    students = db.scalars(
        select(Student).where(Student.sport == coach.sport)
        .order_by(Student.created_at.desc(), Student.id.desc())
    ).all()
    return [
        StudentListItem(**StudentOut.model_validate(s).model_dump(),
                        has_results=len(s.results) > 0,
                        video_count=sum(v.status == "done" for v in s.videos),
                        achievements_verified=len(s.verified_achievements),
                        achievements_pending=sum(a.status == "pending" for a in s.achievements))
        for s in students
    ]


@app.get("/api/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    return coach_student(student_id, coach, db)


@app.patch("/api/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    """Coaches edit what they always could (name, notes, measurements); the university's
    record of a student — RA number, date of birth, family, IDs, sport — is admin-only."""
    student = coach_student(student_id, coach, db)
    data = payload.model_dump(exclude_unset=True)
    if ADMIN_ONLY & set(data):
        require_admin(coach)
    check_ra_free(db, data.get("ra_number"), student.id)
    if "sport" in data:
        sport = require_sport(data.pop("sport") or "")
        if sport != student.sport:
            # positions differ between sports, so the old verification means nothing now
            student.sport = sport
            student.status, student.verified_position = "pending", None
            student.verified_by_id, student.verified_at = None, None
    for field, value in data.items():
        setattr(student, field, value)
    if not (student.father_phone or student.mother_phone) and \
            {"father_phone", "mother_phone"} & set(data):
        db.rollback()
        raise HTTPException(400, "Add at least one parent's mobile number.")
    db.commit()
    db.refresh(student)
    sync_sheet(db, [student])
    sync_people(db, "profiles")
    return student


@app.delete("/api/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    for v in student.videos:
        forget_files(v.stored_name, thumb_of(v))
    forget_files(student.photo_key, *(a.cert_key for a in student.achievements))
    db.delete(student)
    db.commit()
    sync_sheet(db)
    sync_people(db, "profiles", "achievements")


@app.post("/api/students/{student_id}/verify", response_model=StudentOut)
def verify_student(student_id: int, payload: VerifyIn, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    """The coach confirms where this student plays. It is also a training label."""
    student = coach_student(student_id, coach, db)
    if payload.position not in sc.get_sport(student.sport)["positions"]:
        raise HTTPException(400, f"'{payload.position}' is not a position in {student.sport}")
    student.status = "verified"
    student.verified_position = payload.position
    student.verified_by_id = coach.id
    student.verified_at = utcnow()
    db.commit()
    db.refresh(student)
    sync_sheet(db, [student])
    return student


@app.delete("/api/students/{student_id}/verify", response_model=StudentOut)
def unverify_student(student_id: int, db: Session = Depends(get_db),
                     coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    student.status = "pending"
    student.verified_position = None
    student.verified_by_id = None
    student.verified_at = None
    db.commit()
    db.refresh(student)
    sync_sheet(db, [student])
    return student


# ------------------------------- test results ------------------------------ #

@app.get("/api/students/{student_id}/results")
def get_results(student_id: int, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    return {"student_id": student.id, "sport": student.sport,
            "results": latest_results(db, student.id),
            "metrics": sc.get_sport(student.sport)["metrics"]}


@app.put("/api/students/{student_id}/results")
def put_results(student_id: int, payload: ResultsIn, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    """Each value is appended as a new dated row, so history is kept."""
    student = coach_student(student_id, coach, db)
    valid = {m["key"] for m in sc.get_sport(student.sport)["metrics"] if m["source"] == "test"}

    saved = 0
    for metric_key, value in payload.results.items():
        if value is None:
            continue
        if metric_key not in valid:
            raise HTTPException(400, f"'{metric_key}' is not a test of {student.sport}")
        db.add(TestResult(student_id=student.id, metric_key=metric_key, value=float(value)))
        saved += 1

    if payload.declared_position is not None:
        student.declared_position = payload.declared_position or None
    if payload.coach_notes is not None:
        student.coach_notes = payload.coach_notes or None
    if payload.sessions_observed is not None:
        student.sessions_observed = payload.sessions_observed

    db.commit()
    sync_sheet(db, [student])
    return {"saved": saved, "results": latest_results(db, student.id)}


@app.get("/api/students/{student_id}/history")
def get_history(student_id: int, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    return history_rows(db, coach_student(student_id, coach, db).id)


# --------------------------------- analysis -------------------------------- #

@app.get("/api/students/{student_id}/analysis")
def get_analysis(student_id: int, db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    return build_report(db, coach_student(student_id, coach, db))


@app.get("/api/students/{student_id}/diet")
def get_diet(student_id: int, db: Session = Depends(get_db),
             coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    report = build_report(db, student)
    return report["diet"]


@app.get("/api/nutrition/options")
def nutrition_options():
    return {"allergens": nutrition.ALLERGENS, "dietPreferences": nutrition.DIET_LABELS}


# --------------------------------- uploads --------------------------------- #
#
# A video is announced first (name + size), which creates its row and opens a storage
# session. The browser then sends it in 4 MiB pieces, each carrying an X-Chunk-Range
# header like "bytes 0-4194303/52428800". Once the last piece lands the row is queued
# for the worker.

CHUNK_RANGE = re.compile(r"bytes (\d+)-(\d+)/(\d+)")


def open_upload(payload: UploadIn, max_bytes: int) -> dict:
    """Validate an announced upload and open its storage session."""
    suffix = Path(payload.filename).suffix.lower()
    if suffix not in ALLOWED_VIDEO_EXT:
        raise HTTPException(
            400, f"Unsupported file type '{suffix}'. Allowed: {', '.join(sorted(ALLOWED_VIDEO_EXT))}")
    if payload.size > max_bytes:
        raise HTTPException(413, f"File is larger than {max_bytes // (1024 * 1024)} MB.")
    if os.environ.get("VERCEL") and storage.backend() == "local":
        # a serverless disk doesn't survive the request, and the worker can't reach it
        raise HTTPException(503, "Video storage isn't set up yet: add STORAGE=drive and the "
                                 "Google settings in Vercel, then redeploy.")
    try:
        session, key = storage.begin(Path(payload.filename).name, payload.size,
                                     payload.content_type or "application/octet-stream")
    except storage.StorageError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"original_name": Path(payload.filename).name, "stored_name": key or "",
            "upload_session": session, "size_bytes": payload.size,
            "bytes_received": 0, "status": "uploading"}


async def take_chunk(record, request: Request, chunk_range: str | None, db: Session) -> dict:
    """Store one piece of an upload. Safe to repeat: a piece that already arrived (its
    reply got lost) is trimmed rather than stored twice, and the reply always says how
    many bytes are really stored so the browser resumes from there."""
    if record.status != "uploading":
        # the last piece landed but its reply was lost, and the browser is asking again
        return {"received": record.size_bytes, "done": True, "status": record.status}
    match = CHUNK_RANGE.fullmatch((chunk_range or "").strip())
    if not match:
        raise HTTPException(400, "Missing or malformed X-Chunk-Range header.")
    start, end, total = map(int, match.groups())
    data = await request.body()

    if total != record.size_bytes or end - start + 1 != len(data) or len(data) > storage.CHUNK:
        raise HTTPException(400, "Chunk does not match the announced upload.")
    if end + 1 < total and len(data) % storage.GRANULE:
        raise HTTPException(400, "Every chunk but the last must be a multiple of 256 KiB.")

    have = record.bytes_received or 0
    if start > have:
        return {"received": have, "done": False, "status": record.status}
    if start < have:
        data, start = data[have - start:], have
        if not data:
            return {"received": have, "done": False, "status": record.status}

    try:
        received, key = await run_in_threadpool(
            storage.put_chunk, record.upload_session, start, data, total)
    except storage.StorageError as exc:
        raise HTTPException(502, str(exc)) from exc

    record.bytes_received = received
    if key is not None:
        record.stored_name = key
        record.upload_session = None
        record.status = "queued"
        record.message = "Waiting for the analysis computer to pick this up."
    db.commit()
    return {"received": received, "done": key is not None, "status": record.status}


def forget_files(*keys):
    """Best-effort removal from storage. A file that won't delete must not block
    deleting the record — at worst it lingers in the app's Drive folder."""
    for key in keys:
        try:
            storage.delete(key)
        except Exception:  # noqa: BLE001
            log.warning("could not delete stored file %s", key, exc_info=True)


def thumb_of(video: VideoAnalysis):
    if video.thumb_key:
        return video.thumb_key
    # clips from before cloud storage kept their thumbnail next to the video, by name
    if video.stored_name and storage.backend() == "local":
        return f"{Path(video.stored_name).stem}.jpg"
    return None


def keyframe_of(clip: MatchClip):
    if clip.keyframe_key:
        return clip.keyframe_key
    if clip.stored_name and storage.backend() == "local":
        return f"{Path(clip.stored_name).stem}_key.jpg"
    return None


def stored_image(key: str | None, missing: str, mime: str = "image/jpeg") -> Response:
    if not key:
        raise HTTPException(404, missing)
    try:
        return Response(storage.read_bytes(key), media_type=mime,
                        headers={"Cache-Control": "private, max-age=86400",
                                 "X-Content-Type-Options": "nosniff"})
    except FileNotFoundError as exc:
        raise HTTPException(404, missing) from exc
    except storage.StorageError as exc:
        raise HTTPException(502, str(exc)) from exc


# ---------------------------------- videos --------------------------------- #

@app.post("/api/students/{student_id}/videos", status_code=201)
def start_video(student_id: int, payload: UploadIn, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    record = VideoAnalysis(student_id=student.id, **open_upload(payload, MAX_VIDEO_BYTES))
    db.add(record)
    db.commit()
    return {"id": record.id, "chunkSize": storage.CHUNK}


@app.put("/api/videos/{video_id}/upload")
async def upload_video_chunk(video_id: int, request: Request,
                             x_chunk_range: str | None = Header(default=None),
                             db: Session = Depends(get_db),
                             coach: Coach = Depends(auth.current_coach)):
    return await take_chunk(_coach_video(video_id, coach, db), request, x_chunk_range, db)


@app.get("/api/students/{student_id}/videos", response_model=list[VideoOut])
def list_videos(student_id: int, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    return sorted(student.videos, key=lambda v: v.created_at, reverse=True)


def _coach_video(video_id: int, coach: Coach, db: Session) -> VideoAnalysis:
    record = db.get(VideoAnalysis, video_id)
    if record is None or record.student.sport != coach.sport:
        raise HTTPException(404, "Video not found")
    return record


@app.get("/api/videos/{video_id}/thumbnail")
def video_thumbnail(video_id: int, db: Session = Depends(get_db),
                    coach: Coach = Depends(auth.current_coach)):
    record = _coach_video(video_id, coach, db)
    return stored_image(thumb_of(record), "No thumbnail for this clip")


@app.delete("/api/videos/{video_id}", status_code=204)
def delete_video(video_id: int, db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    record = _coach_video(video_id, coach, db)
    student = record.student
    forget_files(record.stored_name, thumb_of(record))
    db.delete(record)
    db.commit()
    sync_sheet(db, [student])


# ------------------------------ match footage ------------------------------ #

def coach_clip(clip_id: int, coach: Coach, db: Session) -> MatchClip:
    clip = db.get(MatchClip, clip_id)
    if clip is None or clip.sport != coach.sport:
        raise HTTPException(404, "Match clip not found")
    return clip


def frame_items(clip: MatchClip) -> list:
    return (clip.calibration_frames or {}).get("items") or []


def clip_detail(clip: MatchClip) -> dict:
    """The clip as the UI needs it. Raw per-frame samples stay on the server — they are
    only there so calibration can re-derive metrics, and they would dwarf the payload."""
    assigned = {a.track_id: a for a in clip.assignments}
    return {
        **MatchClipOut.model_validate(clip).model_dump(),
        "tracks": [
            {**{k: v for k, v in t.items() if k != "samples"},
             "assignedTo": (
                 {"studentId": assigned[t["trackId"]].student_id,
                  "name": assigned[t["trackId"]].student.name}
                 if t["trackId"] in assigned else None
             )}
            for t in (clip.tracks or [])
        ],
        "keyframeBoxes": clip.keyframe_boxes or [],
        "frames": [{"t": f["t"]} for f in frame_items(clip)],
        "framesStart": (clip.calibration_frames or {}).get("start"),
        "calibration": clip.calibration,
        "calibrationPresets": CALIBRATION_PRESETS.get(clip.sport, []),
    }


# Known real-world dimensions a coach can mark out, so nobody has to remember that a
# football pitch's penalty area is 40.32 m wide.
CALIBRATION_PRESETS = {
    "Football": [
        {"key": "penalty-area", "label": "Penalty area (40.32 × 16.5 m)",
         "corners": ["Left edge, goal line", "Right edge, goal line",
                     "Right edge, 18-yard line", "Left edge, 18-yard line"],
         "world": [[0, 0], [40.32, 0], [40.32, 16.5], [0, 16.5]]},
        {"key": "goal-area", "label": "Six-yard box (18.32 × 5.5 m)",
         "corners": ["Left edge, goal line", "Right edge, goal line",
                     "Right edge, 6-yard line", "Left edge, 6-yard line"],
         "world": [[0, 0], [18.32, 0], [18.32, 5.5], [0, 5.5]]},
        {"key": "full-pitch", "label": "Full pitch (105 × 68 m)",
         "corners": ["Near-left corner", "Near-right corner",
                     "Far-right corner", "Far-left corner"],
         "world": [[0, 0], [105, 0], [105, 68], [0, 68]]},
    ],
    "Basketball": [
        {"key": "full-court", "label": "FIBA court (28 × 15 m)",
         "corners": ["Near-left corner", "Near-right corner",
                     "Far-right corner", "Far-left corner"],
         "world": [[0, 0], [28, 0], [28, 15], [0, 15]]},
        {"key": "three-second", "label": "Restricted area (4.9 × 5.8 m)",
         "corners": ["Left edge, baseline", "Right edge, baseline",
                     "Right edge, free-throw line", "Left edge, free-throw line"],
         "world": [[0, 0], [4.9, 0], [4.9, 5.8], [0, 5.8]]},
    ],
    "Volleyball": [
        {"key": "full-court", "label": "Court (18 × 9 m)",
         "corners": ["Near-left corner", "Near-right corner",
                     "Far-right corner", "Far-left corner"],
         "world": [[0, 0], [18, 0], [18, 9], [0, 9]]},
        {"key": "half-court", "label": "One side (9 × 9 m)",
         "corners": ["Left corner at the net", "Right corner at the net",
                     "Right back corner", "Left back corner"],
         "world": [[0, 0], [9, 0], [9, 9], [0, 9]]},
    ],
    "Cricket": [
        {"key": "pitch", "label": "Pitch (20.12 × 3.05 m)",
         "corners": ["Left of the bowler's crease", "Right of the bowler's crease",
                     "Right of the batter's crease", "Left of the batter's crease"],
         "world": [[0, 0], [3.05, 0], [3.05, 20.12], [0, 20.12]]},
    ],
    "Badminton / Tennis": [
        {"key": "badminton-doubles", "label": "Badminton court (13.4 × 6.1 m)",
         "corners": ["Near-left corner", "Near-right corner",
                     "Far-right corner", "Far-left corner"],
         "world": [[0, 0], [6.1, 0], [6.1, 13.4], [0, 13.4]]},
        {"key": "tennis-doubles", "label": "Tennis court (23.77 × 10.97 m)",
         "corners": ["Near-left corner", "Near-right corner",
                     "Far-right corner", "Far-left corner"],
         "world": [[0, 0], [10.97, 0], [10.97, 23.77], [0, 23.77]]},
    ],
    "Kho-Kho": [
        {"key": "field", "label": "Field (27 × 16 m)",
         "corners": ["Near-left corner", "Near-right corner",
                     "Far-right corner", "Far-left corner"],
         "world": [[0, 0], [27, 0], [27, 16], [0, 16]]},
    ],
}



@app.post("/api/matches", status_code=201)
def start_match(payload: MatchUploadIn, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    """Announce a full match or a snippet. Once uploaded, the worker detects and follows
    every player in it; the coach then says which track is which student."""
    clip = MatchClip(sport=coach.sport, coach_id=coach.id,
                     label=(payload.label or "").strip() or None,
                     attack_direction=payload.attack_direction,
                     **open_upload(payload, MAX_MATCH_BYTES))
    db.add(clip)
    db.commit()
    return {"id": clip.id, "chunkSize": storage.CHUNK}


@app.put("/api/matches/{clip_id}/upload")
async def upload_match_chunk(clip_id: int, request: Request,
                             x_chunk_range: str | None = Header(default=None),
                             db: Session = Depends(get_db),
                             coach: Coach = Depends(auth.current_coach)):
    return await take_chunk(coach_clip(clip_id, coach, db), request, x_chunk_range, db)


@app.get("/api/matches", response_model=list[MatchClipOut])
def list_matches(db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    return db.scalars(
        select(MatchClip).where(MatchClip.sport == coach.sport, MatchClip.status != "uploading")
        .order_by(MatchClip.created_at.desc())
    ).all()


@app.get("/api/matches/{clip_id}")
def get_match(clip_id: int, db: Session = Depends(get_db),
              coach: Coach = Depends(auth.current_coach)):
    return clip_detail(coach_clip(clip_id, coach, db))


@app.get("/api/matches/{clip_id}/keyframe")
def match_keyframe(clip_id: int, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    return stored_image(keyframe_of(coach_clip(clip_id, coach, db)), "No keyframe for this clip")


@app.get("/api/matches/{clip_id}/frames/{n}")
def match_frame(clip_id: int, n: int, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    """One of the stills a coach can scrub through to calibrate on."""
    items = frame_items(coach_clip(clip_id, coach, db))
    return stored_image(items[n]["key"] if 0 <= n < len(items) else None, "No such frame")


def assigned_students(clip: MatchClip):
    return [a.student for a in clip.assignments]


@app.post("/api/matches/{clip_id}/assign")
def assign_track(clip_id: int, payload: MatchAssignIn, db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    """'This tracked player is that student.' A track names one student and a student is
    one track per clip, so naming them again moves the link rather than adding a second."""
    clip = coach_clip(clip_id, coach, db)
    student = coach_student(payload.student_id, coach, db)

    track = next((t for t in (clip.tracks or []) if t["trackId"] == payload.track_id), None)
    if track is None:
        raise HTTPException(404, f"Track {payload.track_id} is not in this clip")

    touched = [student]
    for old in db.scalars(select(MatchAssignment).where(
            MatchAssignment.clip_id == clip.id,
            or_(MatchAssignment.track_id == payload.track_id,
                MatchAssignment.student_id == student.id))).all():
        touched.append(old.student)
        db.delete(old)
    db.flush()

    db.add(MatchAssignment(clip_id=clip.id, student_id=student.id, track_id=payload.track_id,
                           metrics=track["metrics"], context=track["context"]))
    db.commit()
    sync_sheet(db, touched)
    db.refresh(clip)
    return clip_detail(clip)


@app.delete("/api/matches/{clip_id}/assign/{track_id}")
def unassign_track(clip_id: int, track_id: int, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    clip = coach_clip(clip_id, coach, db)
    row = db.scalar(select(MatchAssignment).where(
        MatchAssignment.clip_id == clip.id, MatchAssignment.track_id == track_id))
    if row is None:
        raise HTTPException(404, "That track is not assigned")
    student = row.student
    db.delete(row)
    db.commit()
    sync_sheet(db, [student])
    db.refresh(clip)
    return clip_detail(clip)


def _refresh_assignments(clip: MatchClip, tracks: list):
    by_track = {t["trackId"]: t for t in tracks}
    for assignment in clip.assignments:
        fresh = by_track.get(assignment.track_id)
        if fresh:
            assignment.metrics = fresh["metrics"]
            assignment.context = fresh["context"]


@app.post("/api/matches/{clip_id}/calibrate")
def calibrate_match(clip_id: int, payload: CalibrationIn, db: Session = Depends(get_db),
                    coach: Coach = Depends(auth.current_coach)):
    """Mark out the pitch, and every track is re-derived in metres and km/h.

    No video is re-read: the per-frame samples captured during tracking are kept on the
    clip precisely so this is instant — and so it still works after the video itself
    has been deleted. Assignments already made are refreshed too, so a student
    identified before calibration picks up the real-world numbers.
    """
    clip = coach_clip(clip_id, coach, db)
    if not clip.tracks:
        raise HTTPException(400, "This clip has no tracked players to recalculate.")

    image_points = [[p.x, p.y] for p in payload.image_points]
    world_points = [[p.x, p.y] for p in payload.world_points]

    tracks, message = match_metrics.recompute(
        {"tracks": clip.tracks}, image_points, world_points,
        family=sc.SPORT_MATCH_FAMILY[clip.sport],
        attack_direction=clip.attack_direction,
    )
    if tracks is None:
        raise HTTPException(400, message)

    clip.tracks = tracks
    clip.calibration = {
        "imagePoints": image_points, "worldPoints": world_points,
        "preset": payload.preset, "label": payload.label,
    }
    _refresh_assignments(clip, tracks)
    db.commit()
    sync_sheet(db, assigned_students(clip))
    db.refresh(clip)
    return {**clip_detail(clip), "message": message}


@app.delete("/api/matches/{clip_id}/calibrate", status_code=200)
def clear_calibration(clip_id: int, db: Session = Depends(get_db),
                      coach: Coach = Depends(auth.current_coach)):
    """Back to scale-free units — useful when the four points were clicked badly."""
    clip = coach_clip(clip_id, coach, db)
    if not clip.tracks:
        raise HTTPException(400, "This clip has no tracked players.")

    rebuilt, _message = match_metrics.recompute(
        {"tracks": clip.tracks},
        family=sc.SPORT_MATCH_FAMILY[clip.sport],
        attack_direction=clip.attack_direction,
    )
    clip.tracks = rebuilt
    clip.calibration = None
    _refresh_assignments(clip, rebuilt)
    db.commit()
    sync_sheet(db, assigned_students(clip))
    db.refresh(clip)
    return {**clip_detail(clip), "message": "Calibration removed."}


@app.delete("/api/matches/{clip_id}", status_code=204)
def delete_match(clip_id: int, db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    clip = coach_clip(clip_id, coach, db)
    touched = assigned_students(clip)
    forget_files(clip.stored_name, keyframe_of(clip), *(f["key"] for f in frame_items(clip)))
    db.delete(clip)
    db.commit()
    sync_sheet(db, touched)


# ------------------------------ photos & documents -------------------------- #
#
# Small files come up as the raw request body (the browser shrinks photos first), which
# keeps them under the hosted API's 4.5 MB request cap. What a file is gets decided by
# its first bytes, never by the name or type the browser claims.

MAX_PHOTO_BYTES = 2 * 1024 * 1024
MAX_OPEN_ACHIEVEMENTS = 20     # a student's certificates not yet verified
UPLOADS_PER_HOUR = 30          # per student
MAX_DOC_BYTES = 4 * 1024 * 1024
EXTENSION = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp",
             "application/pdf": ".pdf"}


def sniff(data: bytes) -> str | None:
    if data[:3] == b"\xff\xd8\xff":
        return "image/jpeg"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    if data[:5] == b"%PDF-":
        return "application/pdf"
    return None


async def read_upload(request: Request, limit: int, allowed: set) -> tuple[bytes, str]:
    data = await request.body()
    if not data:
        raise HTTPException(400, "The file was empty.")
    if len(data) > limit:
        raise HTTPException(413, f"That file is over {limit // (1024 * 1024)} MB — take a "
                                 f"photo of it instead, or shrink it.")
    mime = sniff(data)
    if mime not in allowed:
        raise HTTPException(415, "Upload a photo (JPEG or PNG) or a PDF.")
    if os.environ.get("VERCEL") and storage.backend() == "local":
        raise HTTPException(503, "File storage isn't set up yet: add STORAGE=drive and the "
                                 "Google settings in Vercel, then redeploy.")
    return data, mime


async def set_photo(student: Student, request: Request, db: Session):
    data, mime = await read_upload(request, MAX_PHOTO_BYTES, {"image/jpeg"})
    try:
        key = await run_in_threadpool(storage.save_bytes, f"photo-{student.id}.jpg", data, mime)
    except storage.StorageError as exc:
        raise HTTPException(502, str(exc)) from exc
    old, student.photo_key = student.photo_key, key
    db.commit()
    forget_files(old)
    return {"photo_version": student.photo_version}


@app.put("/api/student/photo")
async def student_put_photo(request: Request, db: Session = Depends(get_db),
                            account: StudentAccount = Depends(auth.current_student)):
    return await set_photo(my_student(account), request, db)


@app.get("/api/student/photo")
def student_get_photo(account: StudentAccount = Depends(auth.current_student)):
    return stored_image(my_student(account).photo_key, "No photo yet")


@app.put("/api/students/{student_id}/photo")
async def admin_put_photo(student_id: int, request: Request, db: Session = Depends(get_db),
                          coach: Coach = Depends(auth.current_coach)):
    require_admin(coach)
    return await set_photo(coach_student(student_id, coach, db), request, db)


@app.get("/api/students/{student_id}/photo")
def student_photo(student_id: int, db: Session = Depends(get_db),
                  coach: Coach = Depends(auth.current_coach)):
    return stored_image(coach_student(student_id, coach, db).photo_key, "No photo yet")


# ------------------------------- achievements ------------------------------- #

def achievement_list(student: Student) -> list:
    return [AchievementOut.model_validate(a).model_dump()
            for a in sorted(student.achievements, key=lambda a: a.id, reverse=True)]


def prefill(achievement: Achievement, found: dict | None):
    """Copy what the AI read into the editable fields; the student corrects the rest."""
    achievement.ai_read = found
    if not found:
        return
    year = found.get("year")
    extra = [found.get("details"), found.get("issued_by") and f"Issued by {found['issued_by']}"]
    achievement.title = (found.get("title") or "")[:200] or None
    achievement.level = found.get("level") if found.get("level") in LEVELS else None
    achievement.year = year if isinstance(year, int) and 1990 <= year <= 2100 else None
    achievement.result = (found.get("result") or "")[:80] or None
    achievement.details = " ".join(x for x in extra if x)[:2000] or None


async def add_achievement(student: Student, request: Request, filename: str | None,
                          db: Session, status: str) -> Achievement:
    data, mime = await read_upload(request, MAX_DOC_BYTES, set(EXTENSION))
    try:
        key = await run_in_threadpool(storage.save_bytes, f"cert-{student.id}{EXTENSION[mime]}",
                                      data, mime)
    except storage.StorageError as exc:
        raise HTTPException(502, str(exc)) from exc
    name = Path(unquote(filename or "")).name[:255] or f"certificate{EXTENSION[mime]}"
    achievement = Achievement(student_id=student.id, cert_key=key, cert_name=name,
                              cert_mime=mime, status=status)
    prefill(achievement, await run_in_threadpool(docreader.read_certificate, data, mime))
    db.add(achievement)
    db.commit()
    db.refresh(achievement)
    return achievement


def my_achievement(achievement_id: int, account: StudentAccount, db: Session) -> Achievement:
    achievement = db.get(Achievement, achievement_id)
    if achievement is None or achievement.student_id != my_student(account).id:
        raise HTTPException(404, "Achievement not found")
    return achievement


def coach_achievement(achievement_id: int, coach: Coach, db: Session,
                      drafts: bool = False) -> Achievement:
    """One of the sport's achievements. Drafts — not yet sent — stay the student's own."""
    achievement = db.get(Achievement, achievement_id)
    if (achievement is None or achievement.student.sport != coach.sport
            or (achievement.status == "draft" and not drafts)):
        raise HTTPException(404, "Achievement not found")
    return achievement


def disposition(kind: str, name: str) -> str:
    """A filename header that survives any name: an ASCII stand-in for old browsers and
    the real name percent-encoded (headers can only carry latin-1)."""
    plain = re.sub(r"[^\w .-]+", "_", name, flags=re.ASCII).strip() or "file"
    return f"{kind}; filename=\"{plain}\"; filename*=UTF-8''{quote(name, safe='')}"


def certificate(achievement: Achievement) -> Response:
    response = stored_image(achievement.cert_key, "Certificate missing",
                            achievement.cert_mime or "image/jpeg")
    response.headers["Content-Disposition"] = disposition("inline", achievement.cert_name or "certificate")
    return response


def edit_achievement(achievement: Achievement, payload: AchievementIn, submit_as: str | None):
    """Apply edited fields; `submit_as` is the status sending it moves it to."""
    changes = payload.model_dump(exclude_unset=True, exclude={"submit"})
    for field, value in changes.items():
        setattr(achievement, field, value)
    if submit_as and changes and not payload.submit:
        # a student changing one that is with the coach (or was sent back) takes it back:
        # nobody should verify details they haven't seen
        achievement.status = "draft"
    if payload.submit and submit_as:
        if not (achievement.title and achievement.level):
            raise HTTPException(400, "Fill in at least the event and its level before sending it.")
        achievement.status = submit_as
        achievement.review_note = achievement.reviewed_by_id = achievement.reviewed_at = None


@app.get("/api/student/achievements")
def student_achievements(account: StudentAccount = Depends(auth.current_student)):
    return achievement_list(my_student(account))


@app.post("/api/student/achievements", status_code=201)
async def student_add_achievement(request: Request, x_filename: str | None = Header(default=None),
                                  db: Session = Depends(get_db),
                                  account: StudentAccount = Depends(auth.current_student)):
    """Upload a certificate. It comes back as a draft with whatever the AI could read off
    it, for the student to check and send."""
    student = my_student(account)
    if sum(a.status != "verified" for a in student.achievements) >= MAX_OPEN_ACHIEVEMENTS:
        raise HTTPException(409, f"You have {MAX_OPEN_ACHIEVEMENTS} certificates not verified yet "
                                 f"— send or delete some before adding more.")
    # each upload costs Drive space and an AI read, so an hour's worth is capped too
    key = f"uploads:{student.id}"
    hour = utcnow().strftime("%Y-%m-%dT%H")
    used = get_state(db, key)
    count = used.get("n", 0) if used.get("hour") == hour else 0
    if count >= UPLOADS_PER_HOUR:
        raise HTTPException(429, "That's a lot of uploads for one hour — try again later.")
    set_state(db, key, {"hour": hour, "n": count + 1})
    achievement = await add_achievement(student, request, x_filename, db, "draft")
    return AchievementOut.model_validate(achievement)


@app.patch("/api/student/achievements/{achievement_id}")
def student_edit_achievement(achievement_id: int, payload: AchievementIn,
                             db: Session = Depends(get_db),
                             account: StudentAccount = Depends(auth.current_student)):
    achievement = my_achievement(achievement_id, account, db)
    if achievement.status == "verified":
        raise HTTPException(409, "This one is already verified — ask your coach if it needs changing.")
    edit_achievement(achievement, payload, "pending")
    db.commit()
    sync_people(db, "achievements")
    db.refresh(achievement)
    return AchievementOut.model_validate(achievement)


@app.delete("/api/student/achievements/{achievement_id}", status_code=204)
def student_delete_achievement(achievement_id: int, db: Session = Depends(get_db),
                               account: StudentAccount = Depends(auth.current_student)):
    achievement = my_achievement(achievement_id, account, db)
    if achievement.status == "verified":
        raise HTTPException(409, "A verified achievement stays on your record.")
    forget_files(achievement.cert_key)
    db.delete(achievement)
    db.commit()
    sync_people(db, "achievements")


@app.get("/api/student/achievements/{achievement_id}/certificate")
def student_certificate(achievement_id: int, db: Session = Depends(get_db),
                        account: StudentAccount = Depends(auth.current_student)):
    return certificate(my_achievement(achievement_id, account, db))


@app.get("/api/achievements")
def squad_achievements(status: str | None = None, db: Session = Depends(get_db),
                       coach: Coach = Depends(auth.current_coach)):
    """The sport's achievements (drafts stay private to the student), newest first."""
    query = (select(Achievement).join(Student).where(Student.sport == coach.sport,
                                                     Achievement.status != "draft")
             .order_by(Achievement.id.desc()))
    if status:
        query = query.where(Achievement.status == status)
    return [{**AchievementOut.model_validate(a).model_dump(), "student_name": a.student.name,
             "ra_number": a.student.ra_number}
            for a in db.scalars(query)]


@app.get("/api/students/{student_id}/achievements")
def student_achievements_for_coach(student_id: int, db: Session = Depends(get_db),
                                   coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    return [a for a in achievement_list(student) if a["status"] != "draft"]


@app.post("/api/students/{student_id}/achievements", status_code=201)
async def admin_add_achievement(student_id: int, request: Request,
                                x_filename: str | None = Header(default=None),
                                db: Session = Depends(get_db),
                                coach: Coach = Depends(auth.current_coach)):
    """An admin adding one for a student (one added by hand has no portal). It lands as
    pending, to be checked and verified like any other."""
    require_admin(coach)
    student = coach_student(student_id, coach, db)
    achievement = await add_achievement(student, request, x_filename, db, "pending")
    sync_people(db, "achievements")
    return AchievementOut.model_validate(achievement)


@app.patch("/api/achievements/{achievement_id}")
def admin_edit_achievement(achievement_id: int, payload: AchievementIn,
                           db: Session = Depends(get_db),
                           coach: Coach = Depends(auth.current_coach)):
    require_admin(coach)
    achievement = coach_achievement(achievement_id, coach, db)
    edit_achievement(achievement, payload, None)
    db.commit()
    sync_people(db, "achievements", "profiles")
    db.refresh(achievement)
    return AchievementOut.model_validate(achievement)


@app.post("/api/achievements/{achievement_id}/review")
def review_achievement(achievement_id: int, payload: ReviewIn, db: Session = Depends(get_db),
                       coach: Coach = Depends(auth.current_coach)):
    """A coach or admin has looked at the certificate: verified, or rejected with a reason."""
    achievement = coach_achievement(achievement_id, coach, db, drafts=True)
    if achievement.status == "draft":
        raise HTTPException(409, "The student has taken this back to change it — it comes "
                                 "back to you when they send it again.")
    if payload.version and payload.version != achievement.version:
        raise HTTPException(409, "The student changed this after you opened it — have another look.")
    if payload.decision == "verified" and not (achievement.title and achievement.level):
        raise HTTPException(400, "It needs an event and a level before it can be verified.")
    achievement.status = payload.decision
    achievement.review_note = payload.note
    achievement.reviewed_by_id = coach.id
    achievement.reviewed_at = utcnow()
    db.commit()
    sync_people(db, "achievements", "profiles")
    db.refresh(achievement)
    return AchievementOut.model_validate(achievement)


@app.get("/api/achievements/{achievement_id}/certificate")
def coach_certificate(achievement_id: int, db: Session = Depends(get_db),
                      coach: Coach = Depends(auth.current_coach)):
    return certificate(coach_achievement(achievement_id, coach, db))


# ------------------------------ Excel downloads ----------------------------- #

def histories(db: Session, student_ids) -> dict:
    out: dict[int, list] = {}
    for r in db.scalars(select(TestResult).where(TestResult.student_id.in_(list(student_ids)))
                        .order_by(TestResult.recorded_at.asc(), TestResult.id.asc())):
        out.setdefault(r.student_id, []).append(
            {"metric_key": r.metric_key, "value": r.value, "recorded_at": r.recorded_at})
    return out


def xlsx(data: bytes, name: str) -> Response:
    return Response(data, media_type=export.XLSX,
                    headers={"Content-Disposition": disposition("attachment", name.replace(" ", "-"))})


@app.get("/api/export/squad")
def export_squad(scope: str = "sport", db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    """The whole squad as an Excel file; an admin can ask for every sport at once."""
    everyone = scope == "all"
    if everyone:
        require_admin(coach)
    query = select(Student).order_by(Student.sport, Student.name)
    students = db.scalars(query if everyone else query.where(Student.sport == coach.sport)).all()
    stale = [s for s in students if not s.sheet_row or len(s.sheet_row) != len(sheets.HEADER)]
    for s in stale:     # rows cached before a sheet column was added (the worker also does this)
        s.sheet_row = sheets.row_for(build_report(db, s), s)
    if stale:
        db.commit()
    coaches = db.scalars(select(Coach).order_by(Coach.sport, Coach.name)).all() if everyone else None
    data = export.squad(students, histories(db, [s.id for s in students]), coaches)
    what = "all-sports" if everyone else coach.sport
    return xlsx(data, f"Stridian-{what}-{utcnow():%Y-%m-%d}.xlsx")


@app.get("/api/students/{student_id}/export")
def export_student(student_id: int, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    data = export.student(student, build_report(db, student), history_rows(db, student.id))
    return xlsx(data, f"Stridian-{student.ra_number or student.id}-{student.name}.xlsx")


# ------------------------------- AI training ------------------------------- #

AGREES_COLUMN = sheets.HEADER.index("Coach agrees with system")


def version_out(v: ModelVersion) -> dict:
    return {"id": v.id, "kind": v.kind, "deployed": v.deployed, "labels": v.labels,
            "accuracy": v.accuracy, "liveAccuracy": v.live_accuracy, "note": v.note,
            "createdAt": v.created_at}


@app.get("/api/training")
def training_overview(db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    """Everything the AI Training page shows for the coach's sport, in one call."""
    sport = coach.sport
    students = sport_students(db, sport)
    verified = [s for s in students if s.status == "verified"]

    # how often the live model already agrees with the coaches, from the cached rows
    judged = [s.sheet_row[AGREES_COLUMN] for s in verified
              if s.sheet_row and len(s.sheet_row) == len(sheets.HEADER)
              and s.sheet_row[AGREES_COLUMN] in ("Yes", "No")]

    versions = db.scalars(select(ModelVersion).where(ModelVersion.sport == sport)
                          .order_by(ModelVersion.id.desc()).limit(25)).all()
    live = db.scalar(select(ModelVersion).where(ModelVersion.sport == sport,
                                                ModelVersion.deployed.is_(True))
                     .order_by(ModelVersion.id.desc()).limit(1))
    baseline = db.scalar(select(ModelVersion).where(ModelVersion.sport == sport,
                                                    ModelVersion.kind == "baseline",
                                                    ModelVersion.deployed.is_(True))
                         .order_by(ModelVersion.id.desc()).limit(1))
    learned = (trainer.biggest_changes(sport, baseline.weights, live.weights)
               if live and baseline and live.kind == "trained" else [])

    def queue_count(model, *where):
        return db.scalar(select(func.count()).select_from(model).where(*where)) or 0

    video_sport = VideoAnalysis.student_id.in_(select(Student.id).where(Student.sport == sport))
    sheet = get_state(db, "sheet")
    return {
        "sport": sport,
        "minLabels": trainer.MIN_LABELS,
        "labels": {
            "verified": len(verified),
            "pending": len(students) - len(verified),
            "byPosition": dict(Counter(s.verified_position for s in verified)),
            "positions": list(sc.get_sport(sport)["positions"]),
        },
        "agreement": {"agree": judged.count("Yes"), "judged": len(judged)},
        "live": version_out(live) if live else None,
        "learned": learned,
        "versions": [version_out(v) for v in versions],
        "queue": {
            "videos": queue_count(VideoAnalysis, VideoAnalysis.status.in_(("queued", "processing")),
                                  video_sport),
            "matches": queue_count(MatchClip, MatchClip.status.in_(("queued", "processing")),
                                   MatchClip.sport == sport),
        },
        "worker": worker_status(db),
        "storage": storage.backend(),
        # the Google Sheets belong to the admins; coaches download Excel files instead
        "sheet": {"configured": sheets.configured(),
                  "url": sheets.sheet_url() if coach.is_admin else None, **sheet},
        "peopleSheets": people_sheets(db) if coach.is_admin else None,
    }


@app.post("/api/training/versions/{version_id}/rollback")
def rollback_version(version_id: int, db: Session = Depends(get_db),
                     coach: Coach = Depends(auth.current_coach)):
    """Put an older version's weights back live. It becomes a baseline — weights a person
    chose — so training starts from it and won't re-deploy until the data changes."""
    version = db.get(ModelVersion, version_id)
    if version is None or version.sport != coach.sport:
        raise HTTPException(404, "Version not found")
    apply_weights(db, coach.sport, version.weights)
    db.add(ModelVersion(sport=coach.sport, kind="baseline", weights=version.weights,
                        deployed=True, labels=version.labels, accuracy=version.accuracy,
                        note=f"Rolled back to version #{version.id} by {coach.name}"))
    db.commit()
    sync_sheet(db, sport_students(db, coach.sport))
    return training_overview(db, coach)


# ------------------- serve the built frontend, if present ------------------ #
# (on Vercel the CDN serves it instead; this is for running everything locally)
_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if _dist.is_dir():
    app.mount("/", StaticFiles(directory=_dist, html=True), name="frontend")
