"""
Stridian — API.

Run from this folder:  uvicorn main:app --reload
Interactive docs:      http://127.0.0.1:8000/docs

Access model: students enter their own details without an account. Everything else
is coach-only, and a coach is locked to one sport — a football coach never sees
basketball students, their weights, or their videos.

This process never runs a vision model. Uploaded videos are queued, and the worker
(worker.py, on the laptop or the lab iMac) analyses them whenever it is switched on.
That is what lets this API run on a free serverless host.
"""

import hmac
import logging
import os
import re
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select
from sqlalchemy.orm import Session

import auth
import match_metrics
import migrate
import nutrition
import scoring
import sheets
import sports_config as sc
import storage
import trainer
from db import Base, SessionLocal, engine, get_db
from models import (AppState, Coach, MatchAssignment, MatchClip, ModelVersion, PositionWeight,
                    Student, TestResult, VideoAnalysis)
from models import _now as utcnow
from schemas import (CalibrationIn, CoachLogin, CoachOut, CoachSignup, MatchAssignIn,
                     MatchClipOut, MatchUploadIn, ResultsIn, StudentCreate, StudentListItem,
                     StudentOut, StudentUpdate, TokenOut, UploadIn, VerifyIn, VideoOut,
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
    """Fetch a student, 404ing for anyone outside the coach's own sport."""
    student = db.get(Student, student_id)
    if student is None or student.sport != coach.sport:
        raise HTTPException(404, "Student not found")
    return student


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
        for student in students:
            student.sheet_row = sheets.row_for(build_report(db, student), student)
        db.commit()
        if sheets.configured():
            status = sheets.push(db.scalars(select(Student)).all())
            set_state(db, "sheet", {**status, "at": utcnow().isoformat()})
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("sheet sync failed")


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
    coach = Coach(name=payload.name.strip(), email=email, sport=sport,
                  password_hash=auth.hash_password(payload.password))
    db.add(coach)
    db.commit()
    db.refresh(coach)
    return TokenOut(token=auth.issue_token(db, coach), coach=CoachOut.model_validate(coach))


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


@app.post("/api/auth/logout", status_code=204)
def logout(authorization: str = Header(), db: Session = Depends(get_db),
           coach: Coach = Depends(auth.current_coach)):
    """Revoke just the token that made this call, leaving other devices signed in."""
    auth.revoke_token(db, authorization.split(" ", 1)[1].strip())


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
def create_student(payload: StudentCreate, db: Session = Depends(get_db)):
    """Public — students register themselves; the sport decides which coach sees them."""
    data = payload.model_dump()
    data["sport"] = require_sport(payload.sport)
    student = Student(**data)
    db.add(student)
    db.commit()
    db.refresh(student)
    sync_sheet(db, [student])
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
                        video_count=sum(v.status == "done" for v in s.videos))
        for s in students
    ]


@app.get("/api/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    return coach_student(student_id, coach, db)


@app.patch("/api/students/{student_id}", response_model=StudentOut)
def update_student(student_id: int, payload: StudentUpdate, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(student, field, value)
    db.commit()
    db.refresh(student)
    sync_sheet(db, [student])
    return student


@app.delete("/api/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    for v in student.videos:
        forget_files(v.stored_name, thumb_of(v))
    db.delete(student)
    db.commit()
    sync_sheet(db)


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
    """Every recorded measurement, for progress-over-time charts."""
    student = coach_student(student_id, coach, db)
    rows = db.scalars(
        select(TestResult).where(TestResult.student_id == student.id)
        .order_by(TestResult.recorded_at.asc(), TestResult.id.asc())
    ).all()
    return [{"metric_key": r.metric_key, "value": r.value, "recorded_at": r.recorded_at} for r in rows]


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


def stored_image(key: str | None, missing: str) -> Response:
    if not key:
        raise HTTPException(404, missing)
    try:
        return Response(storage.read_bytes(key), media_type="image/jpeg",
                        headers={"Cache-Control": "private, max-age=86400"})
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


def assigned_students(clip: MatchClip):
    return [a.student for a in clip.assignments]


@app.post("/api/matches/{clip_id}/assign")
def assign_track(clip_id: int, payload: MatchAssignIn, db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    """'This tracked player is that student.' Re-assigning a track replaces the old link."""
    clip = coach_clip(clip_id, coach, db)
    student = coach_student(payload.student_id, coach, db)

    track = next((t for t in (clip.tracks or []) if t["trackId"] == payload.track_id), None)
    if track is None:
        raise HTTPException(404, f"Track {payload.track_id} is not in this clip")

    touched = [student]
    existing = db.scalar(select(MatchAssignment).where(
        MatchAssignment.clip_id == clip.id, MatchAssignment.track_id == payload.track_id))
    if existing:
        touched.append(existing.student)
        db.delete(existing)
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
    forget_files(clip.stored_name, keyframe_of(clip))
    db.delete(clip)
    db.commit()
    sync_sheet(db, touched)


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
              if s.sheet_row and s.sheet_row[AGREES_COLUMN] in ("Yes", "No")]

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
        "sheet": {"configured": sheets.configured(), "url": sheets.sheet_url(), **sheet},
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
