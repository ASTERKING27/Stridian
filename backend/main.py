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
from collections import Counter, defaultdict
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import quote, unquote

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, or_, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import auth
import coach as second_coach
import docreader
import export
import levels
import mailer
import match_cards
import match_metrics
import migrate
import nutrition
import push
import scoring
import sheets
import sports_config as sc
import storage
import trainer
from db import Base, SessionLocal, engine, get_db
from models import (LEVELS, Achievement, AppState, Coach, CoachSession, FocusWeek, MatchAssignment,
                    MatchCard, MatchCardLine, MatchClip, ModelVersion, PositionWeight, PushToken, Student,
                    StudentAccount, StudentSession, TestResult, VideoAnalysis)
from models import _now as utcnow
from models import admin_emails
from schemas import (ADMIN_ONLY, STUDENT_ONCE, AchievementIn, AchievementOut, CalibrationIn, CardIn,
                     CardNew, CoachDetails, CoachLogin, CoachOut, CoachSignup, EmailCodeIn, EmailIn, FocusLogIn,
                     LevelTargetsIn, MatchAssignIn, MatchClipOut, MatchUploadIn, PasswordIn, PushTokenIn, ResultsIn,
                     ReviewIn, SeenIn, SportIn,
                     StudentCreate, StudentEnrol, StudentListItem, StudentLogin, StudentOut,
                     StudentSelfUpdate, StudentUpdate, TokenOut, UploadIn, VerifyIn, VideoOut,
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


def card_dict(card: MatchCard) -> dict:
    return {"id": card.id, "category": card.category, "format": card.format,
            "header": card.header or {}, "team": card.team or {}}


def line_dict(line: MatchCardLine) -> dict:
    data = line.data or {}
    return {"id": line.id, "student_id": line.student_id, "jersey": line.jersey,
            "name": line.student.name if line.student else line.name, "position": line.position,
            "tallies": data.get("tallies") or {}, "fields": data.get("fields") or {},
            "zones": data.get("zones") or {}, "coord": line.coord, "overall": line.overall,
            "strength": line.strength, "improve": line.improve, "remarks": line.remarks}


def card_entries(student: Student) -> list:
    """The student's rows on final cards of the sport they play now — what Part D, the
    report and the position engine read."""
    return [{"card": card_dict(line.card), "line": line_dict(line)}
            for line in student.card_lines
            if line.card.status == "final" and line.card.sport == student.sport]


def score_inputs(db: Session, student: Student, entries: list):
    """(card values, ranges, card context) for a student's scores. The ranges are the
    level targets wherever there are any for their team (University 20 ... International
    100 — levels.py), and otherwise the match cards' own anchors or the sport's poor →
    elite. Tests and footage use the team on their profile, or else their latest card's."""
    card_values, ranges, context = match_cards.player_values(student.sport, entries)
    card_category, card_format = (context["category"], context["format"]) if context else (None, None)
    ranges.update(levels.scales(student.sport, student.category or card_category, card_category,
                                card_format, get_state(db, f"levels:{student.sport}")))
    return card_values, ranges, context


def metric_rows(db: Session, student: Student) -> list:
    """A student's 0-100 score on every metric — what the trainer learns from."""
    match_values = match_metrics.aggregate(
        [a.metrics for a in student.match_assignments if a.metrics])
    card_values, ranges, _ = score_inputs(db, student, card_entries(student))
    values = scoring.build_metric_values(
        student.sport, {"height_cm": student.height_cm, "weight_kg": student.weight_kg},
        latest_results(db, student.id), match_values, card_values)
    return scoring.score_metrics(student.sport, values, ranges=ranges)


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


SOURCE_WORDS = {"test": "the tests", "match": "the match footage", "card": "the match cards"}
ONLY = {
    "test": ("tests-only", "Based on testing data alone. Assign this student in a match clip, or record "
                           "them on a match card, to check whether {pos} holds up in a real game."),
    "match": ("match-only", "Based on match footage alone. Record the test battery to confirm the "
                            "physical profile behind {pos}."),
    "card": ("cards-only", "Based on match cards alone. Record the test battery to confirm the physical "
                           "profile behind {pos}."),
}


def _join(words):
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def reconcile(reports: dict) -> dict:
    """Say plainly whether the tests, the match footage and the match cards tell the
    same story. `reports` is {source: that source's own analysis}."""
    picks = {src: r["recommended"]["position"] for src, r in reports.items() if r.get("recommended")}
    out = {f"{src}Position": pos for src, pos in picks.items()}
    if not picks:
        return {"agreement": "none",
                "text": "No test results, match footage or match cards yet — nothing to compare."}
    if len(picks) == 1:
        (src, pos), = picks.items()
        agreement, text = ONLY[src]
        return {**out, "agreement": agreement, "text": text.format(pos=pos)}

    words = [SOURCE_WORDS[src] for src in picks]
    if len(set(picks.values())) == 1:
        pos = next(iter(picks.values()))
        said = _join(words)
        return {**out, "agreement": "agree",
                "text": f"{said[0].upper()}{said[1:]} {'both' if len(words) == 2 else 'all'} agree on "
                        f"{pos} — separate kinds of evidence pointing the same way is the "
                        f"strongest signal this report can give."}

    def rank(src, pos):
        return next((i for i, p in enumerate(reports[src]["positions"]) if p["position"] == pos), 99)

    views = "; ".join(f"{SOURCE_WORDS[src]} favour {pos}" for src, pos in picks.items())
    if all(rank(a, picks[b]) <= 2 for a in picks for b in picks):
        return {**out, "agreement": "near",
                "text": f"Close but not identical: {views}. Each ranks the others' picks in its "
                        f"own top three, so either role suits them; the choice is tactical, not physical."}
    return {**out, "agreement": "disagree",
            "text": f"They disagree: {views}. That usually means they are being deployed out of "
                    f"position, or one source caught an unusual game — worth another match before "
                    f"acting on it."}


def build_report(db: Session, student: Student) -> dict:
    profile = {"height_cm": student.height_cm, "weight_kg": student.weight_kg}
    tests = latest_results(db, student.id)
    weights = load_weights(db, student.sport)
    match_values = match_metrics.aggregate(
        [a.metrics for a in student.match_assignments if a.metrics]
    )
    entries = card_entries(student)
    card_values, ranges, card_context = score_inputs(db, student, entries)

    def run(sources):
        return scoring.analyse(student.sport, profile, tests, weights, match_values=match_values,
                               sources=sources, card_values=card_values, ranges=ranges)

    report = run(None)                          # the headline, all evidence together
    by_source = {"test": run({"test", "profile"}),   # the battery, plus height/weight
                 "match": run({"match"}),            # what the footage alone says
                 "card": run({"card"})}              # what the match cards alone say

    report["bySource"] = {src: summarise(r) for src, r in by_source.items()}
    report["reconciliation"] = reconcile(by_source)
    report["matchCards"] = {
        "partD": match_cards.part_d(student.sport, entries),
        "zones": match_cards.zone_totals(student.sport, [e["line"] for e in entries]),
        "context": card_context,
    }
    report["matchValues"] = match_values
    position = (student.verified_position if student.status == "verified"
                else (report.get("recommended") or {}).get("position"))
    report["levels"] = level_read_out(db, student, tests, match_values, entries,
                                      weights.get(position) if position else None)
    report["levels"]["position"] = position      # whose weights the overall level used
    if student.status == "verified" and position:
        # once the coach has confirmed a position, what to train is ranked for that one
        report["developmentPlan"] = scoring.development_plan(report["metrics"], weights.get(position, {}))
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
         "has_thumbnail": v.has_thumbnail, "has_pose": v.has_pose, "label": v.label,
         "uploaded_by": v.uploaded_by,
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


def level_read_out(db: Session, student: Student, tests: dict, match_values: dict, entries: list,
                   weights: dict | None) -> dict:
    """The student's numbers against the level targets (see levels.py). Tests and footage
    use the team on their profile, or else the one on their latest match card."""
    sport = student.sport
    keys = [k[5:] for k in levels.DEFAULTS.get(sport, {}) if k.startswith("card_")]
    card_values, context = (match_cards.measure_values(sport, entries, keys) if entries and keys
                            else ({}, None))
    category, source = student.category, "profile" if student.category else None
    if category is None and context:
        category, source = context["category"], "card"
    return levels.read_out(sport, {**tests, "heightCm": student.height_cm, **match_values, **card_values},
                           category, context and context["category"], context and context["format"],
                           weights, get_state(db, f"levels:{sport}"), source)


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


def publish(db: Session, registry: str, key: str, title: str, tabs: list, old_tabs: list, data):
    """Rewrite one of the admin's spreadsheets with `data()` ({tab: rows}), making it the
    first time and adding or dropping tabs when the layout has changed. Records how it
    went under AppState[registry][key]. Never raises: a Google hiccup must not turn a
    saved enrolment into an error page, and the worker repeats every push anyway."""
    entry = dict(get_state(db, registry).get(key) or {})
    try:
        if not entry.get("id"):
            # ponytail: two first-ever pushes at the same moment could each make one;
            # the spare is simply never written to again
            entry.update(id=sheets.create(title, tabs), tabs=tabs)
            set_state(db, registry, {**get_state(db, registry), key: entry})
        elif entry.get("tabs") != tabs:
            sheets.retab(entry["id"], tabs, entry.get("tabs") or old_tabs)
            entry["tabs"] = tabs
        sheets.write(entry["id"], data())
        entry.update(ok=True, error=None)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        log.exception("sheet %s/%s failed", registry, key)
        entry.update(ok=False, error=str(exc)[:300])
    entry["at"] = utcnow().isoformat()
    set_state(db, registry, {**get_state(db, registry), key: entry})


def sync_sheet(db: Session, students=(), sports=()):
    """Recompute these students' sheet rows, then rewrite their sports' squad files (and
    any in `sports`, e.g. one a student just left). One file per sport, so no sport's
    sheet shows another sport's students.

    Called after every change a coach or student makes. Never raises, and the worker
    pushes every sport again on its next pass, so a missed push repairs itself.
    """
    try:
        # a row cached before a sheet column was added would land in the wrong columns;
        # rebuild those instead of pushing them
        width = len(sheets.HEADER)
        stale = [s for s in db.scalars(select(Student)) if s.sheet_row and len(s.sheet_row) != width]
        touched = {*students, *stale}
        for student in touched:
            student.sheet_row = sheets.row_for(build_report(db, student), student)
        db.commit()
        pushes = sorted({s.sport for s in touched} | set(sports))
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("sheet rows failed")
        return
    if not sheets.configured():
        return
    for sport in pushes:
        publish(db, "squad_sheets", sport, f"Stridian — {sport} squad", list(sheets.TABS),
                list(sheets.TABS), lambda sport=sport: sheets.squad(sport_students(db, sport)))


def squad_sports(db: Session) -> list:
    """Every sport with students or a squad file already — what the worker repushes."""
    return sorted(set(db.scalars(select(Student.sport).distinct())) | set(get_state(db, "squad_sheets")))


def sync_people(db: Session, *keys):
    """Rewrite the admin's people spreadsheets (all of them, or just `keys`): Student
    profiles and Achievements with a tab per sport, Coaches as one list."""
    if not sheets.configured():
        return

    def by_sport(pairs):
        out = {sheets.tab_name(sport): [] for sport in sc.sport_names()}
        for sport, row in pairs:
            out.setdefault(sheets.tab_name(sport), []).append(row)
        return out

    rows = {
        "profiles": lambda: by_sport((s.sport, sheets.profile_row(s)) for s in
                                     db.scalars(select(Student).order_by(Student.name))),
        "achievements": lambda: by_sport((a.student.sport, sheets.achievement_row(a)) for a in
                                         db.scalars(select(Achievement).where(Achievement.status != "draft")
                                                    .order_by(Achievement.id.desc()))),
        "coaches": lambda: {"Coaches": [sheets.coach_row(c) for c in
                                        db.scalars(select(Coach).order_by(Coach.id))]},
    }
    for key in keys or sheets.PEOPLE:
        title, header, tab = sheets.PEOPLE[key]
        tabs = [tab] if tab else [sheets.tab_name(sport) for sport in sc.sport_names()]
        publish(db, "people_sheets", key, title, tabs, sheets.OLD_TABS[key],
                lambda key=key, header=header: {t: [header] + r for t, r in rows[key]().items()})


def admin_sheets(db: Session) -> list:
    """Every spreadsheet the app keeps for the admin, with a link and how its last push went."""
    squads, people = get_state(db, "squad_sheets"), get_state(db, "people_sheets")
    cards = get_state(db, "card_sheets")
    listed = [(f"{sport} squad", squads[sport]) for sport in sc.sport_names() if sport in squads]
    listed += [(f"{sport} match cards", cards[sport]) for sport in sc.sport_names() if sport in cards]
    listed += [(title.replace("Stridian — ", ""), people.get(key) or {})
               for key, (title, _header, _tab) in sheets.PEOPLE.items()]
    return [{"title": title, "url": sheets.url(e.get("id")), "ok": e.get("ok"),
             "error": e.get("error"), "at": e.get("at")} for title, e in listed]


def sport_students(db: Session, sport_name: str):
    return db.scalars(select(Student).where(Student.sport == sport_name)).all()


# --------------------------------------------------------------------------- #
# App
# --------------------------------------------------------------------------- #

OLD_RACKET = "Badminton / Tennis"


def split_racket_sports():
    """Badminton and tennis were one sport until each got its own match card. Everything
    filed under the old name becomes Badminton; an admin moves any tennis players across
    (Edit details on their Profile tab). Does nothing once there is nothing to move."""
    with engine.begin() as conn:
        def run(sql, **params):
            return conn.execute(text(sql), {"old": OLD_RACKET, "new": "Badminton", **params})

        # a student's cached sheet row names their sport, so it is rebuilt (the worker
        # builds every row that is missing)
        run("UPDATE students SET sport = :new, sheet_row = NULL WHERE sport = :old")
        for table in ("coaches", "match_clips", "model_versions"):
            run(f"UPDATE {table} SET sport = :new WHERE sport = :old")
        # (sport, position, metric) is unique: keep Badminton's rows if it already has some
        if run("SELECT COUNT(*) FROM position_weights WHERE sport = :new").scalar():
            run("DELETE FROM position_weights WHERE sport = :old")
        else:
            run("UPDATE position_weights SET sport = :new WHERE sport = :old")
    db = SessionLocal()
    try:
        old_code = get_state(db, f"enrol:{OLD_RACKET}")
        if old_code and not get_state(db, "enrol:Badminton"):
            set_state(db, "enrol:Badminton", old_code)
        for registry in ("squad_sheets", "card_sheets"):
            entries = get_state(db, registry)
            if OLD_RACKET in entries:
                # its Drive file stays where it is; a fresh "Badminton squad" replaces it
                set_state(db, registry, {k: v for k, v in entries.items() if k != OLD_RACKET})
    finally:
        db.close()


# what a cached squad-sheet row holds; a new value drops every cached row once, and the
# worker (or the next export) builds them again
SHEET_ROWS = "level-scale"


def rebuild_sheet_rows_once():
    """Scores moved to the level scale, so rows cached before it are rebuilt, once."""
    db = SessionLocal()
    try:
        if get_state(db, "sheet_rows").get("version") == SHEET_ROWS:
            return
        db.execute(text("UPDATE students SET sheet_row = NULL"))
        set_state(db, "sheet_rows", {"version": SHEET_ROWS})       # commits both
    finally:
        db.close()


def init_db():
    """Tables, missing columns, default weights. Safe to run on every start."""
    Base.metadata.create_all(bind=engine)
    # create_all won't touch a table that already exists, so a database made before a
    # column was added keeps working until something writes that field. Close the gap
    # here rather than making anyone delete their data to pick up a new feature.
    migrate.run(engine, Base.metadata)
    try:
        split_racket_sports()
    except Exception:  # noqa: BLE001 — never block start-up; it is retried on the next one
        log.warning("could not move Badminton / Tennis data across", exc_info=True)
    try:
        rebuild_sheet_rows_once()
    except Exception:  # noqa: BLE001 — retried on the next start
        log.warning("could not reset the cached sheet rows", exc_info=True)
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


def _code_state(db: Session, purpose: str, email: str):
    """The emailed code for (purpose, email), row-locked until the caller commits, so
    guesses sent in parallel still count one at a time. Each purpose keeps its own code:
    one emailed for a sign-up never resets a password."""
    key = f"{purpose}code:" + hashlib.sha256(email.encode()).hexdigest()[:24]
    row = db.scalar(select(AppState).where(AppState.key == key).with_for_update())
    state = dict(row.value or {}) if row else {}
    sent = datetime.fromisoformat(state["sentAt"]) if state.get("sentAt") else None
    return key, state, (utcnow() - sent).total_seconds() if sent else None


def send_email_code(db: Session, purpose: str, email: str) -> None:
    """Email a fresh 6-digit code, unless one went out less than a minute ago (that one
    still stands). Any earlier code stops working."""
    key, _state, age = _code_state(db, purpose, email)
    if age is not None and age < auth.CODE_RESEND_SECONDS:
        db.rollback()                     # release the lock
        return
    code = f"{secrets.randbelow(1_000_000):06d}"
    try:
        mailer.send_code(email, code)
    except mailer.MailError as exc:
        db.rollback()
        raise HTTPException(503, str(exc)) from exc
    set_state(db, key, {"hash": auth.code_hash(email, code), "sentAt": utcnow().isoformat(),
                        "tries": 0})


def email_code_ok(db: Session, purpose: str, email: str, typed: str) -> bool:
    """Check a typed code. A right one is used up; wrong guesses count towards
    CODE_TRIES, after which even the right code is refused."""
    key, state, age = _code_state(db, purpose, email)
    if not state.get("hash"):
        db.rollback()                     # nothing was sent (or it was used): nothing to count
        return False
    tries = state.get("tries", 0)
    if (age is not None and age <= auth.CODE_MINUTES * 60 and tries < auth.CODE_TRIES
            and hmac.compare_digest(state["hash"], auth.code_hash(email, typed.strip()))):
        set_state(db, key, {})            # used up
        return True
    set_state(db, key, {**state, "tries": tries + 1})
    return False


def prove_admin_email(db: Session, email: str, typed: str | None) -> None:
    """An ADMIN_EMAILS address gets an account only once its owner has typed a code
    emailed to it — otherwise whoever typed a listed address first would be an admin.
    Without a code this sends one and answers 428; with one it checks it."""
    if typed and typed.strip():
        if email_code_ok(db, "admin", email, typed):
            return
        raise HTTPException(400, "That code is wrong or has expired — clear it and create the "
                                 "account again for a new one.")
    send_email_code(db, "admin", email)
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


# A forgotten coach password: a code emailed to the account's address, then the code with
# the new password. Whoever can read that inbox sets the password, as with students.

@app.post("/api/auth/reset-code", status_code=202)
def coach_reset_code(payload: EmailIn, db: Session = Depends(get_db)):
    """Email a 6-digit code to a coach account's address. The answer is the same whether
    or not an account uses it; only a real account's inbox gets anything."""
    email = payload.email.strip().lower()
    if db.scalar(select(Coach.id).where(func.lower(Coach.email) == email)):
        send_email_code(db, "reset", email)
    return {"email": email}


@app.post("/api/auth/reset", response_model=TokenOut)
def coach_reset(payload: EmailCodeIn, db: Session = Depends(get_db)):
    """The emailed code and a new password: sets it, signs every other device out, and
    signs this one in."""
    email = payload.email.strip().lower()
    coach = db.scalar(select(Coach).where(func.lower(Coach.email) == email))
    if coach is None or not email_code_ok(db, "reset", email, payload.code):
        raise HTTPException(400, "That code is wrong or has expired — ask for a new one.")
    coach.password_hash = auth.hash_password(payload.password)
    db.query(CoachSession).filter(CoachSession.coach_id == coach.id).delete()
    db.commit()
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


@app.delete("/api/auth/me", status_code=204)
def coach_delete_account(payload: PasswordIn, db: Session = Depends(get_db),
                         coach: Coach = Depends(auth.current_coach)):
    """A coach deletes their own account. Their squad stays: students, results and
    finished cards belong to the sport, not to whoever recorded them."""
    if not auth.verify_password(payload.password, coach.password_hash):
        raise HTTPException(403, "That password isn't right.")
    db.execute(PushToken.__table__.delete().where(PushToken.role == "coach", PushToken.owner_id == coach.id))
    db.delete(coach)
    db.commit()
    sync_people(db, "coaches")


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
def student_code(payload: EmailIn, db: Session = Depends(get_db)):
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
def student_verify(payload: EmailCodeIn, db: Session = Depends(get_db)):
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


@app.delete("/api/student/me", status_code=204)
def student_delete_account(payload: PasswordIn, db: Session = Depends(get_db),
                           account: StudentAccount = Depends(auth.current_student)):
    """The student deletes their account from the app: their login, and their record in
    their sport with everything in it (results, certificates, videos, photo)."""
    if not (account.password_hash and auth.verify_password(payload.password, account.password_hash)):
        raise HTTPException(403, "That password isn't right.")
    student = account.student
    db.execute(PushToken.__table__.delete().where(PushToken.role == "student", PushToken.owner_id == account.id))
    db.delete(account)
    db.commit()
    if student is not None:
        remove_student(db, student)


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
    push.notify(db, "coach", "New in the squad", f"{student.name} enrolled in {sport}.",
                coaches=push.sport_coach_ids(db, sport), data={"student": student.id})
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
            raise HTTPException(403, "Your team can only be changed by your coach." if field == "category"
                                else "Your RA number and date of birth can only be changed by an "
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


# ---------------------------- phone notifications --------------------------- #

def push_owner(authorization: str | None, db: Session):
    """Whoever is signed in — a student account or a coach — as (role, id)."""
    for role, dep in (("student", auth.current_student), ("coach", auth.current_coach)):
        try:
            return role, dep(authorization=authorization, db=db).id
        except HTTPException:
            continue
    raise HTTPException(401, "Sign in again.")


@app.post("/api/push/token", status_code=204)
def push_register(payload: PushTokenIn, authorization: str | None = Header(default=None),
                  db: Session = Depends(get_db)):
    """The app's Expo push token, and which kinds of notification are switched on. A token
    moves with whoever signs in on that phone last."""
    role, owner = push_owner(authorization, db)
    row = db.scalar(select(PushToken).where(PushToken.token == payload.token))
    if row is None:
        row = PushToken(token=payload.token)
        db.add(row)
    row.role, row.owner_id, row.prefs = role, owner, payload.prefs
    db.commit()


@app.delete("/api/push/token", status_code=204)
def push_unregister(payload: PushTokenIn, db: Session = Depends(get_db)):
    """Signing out: this phone stops getting that account's notifications. Knowing the
    token is enough — it only ever stops messages to that phone."""
    db.execute(PushToken.__table__.delete().where(PushToken.token == payload.token))
    db.commit()


@app.get("/api/cron/weekly-nudge")
def weekly_nudge(authorization: str | None = Header(default=None), db: Session = Depends(get_db)):
    """Saturday evening (vercel.json "crons"): students whose weekly focus isn't done yet
    get one reminder. Vercel calls it with the CRON_SECRET; nobody else can."""
    secret = os.environ.get("CRON_SECRET", "")
    if not secret or not hmac.compare_digest(authorization or "", f"Bearer {secret}"):
        raise HTTPException(401, "Not allowed.")
    week = second_coach.week_of(second_coach.today_ist(utcnow()))
    behind = [(w.student, len(w.sessions or [])) for w in db.scalars(select(FocusWeek).where(FocusWeek.week == week))
              if len(w.sessions or []) < second_coach.TARGET_SESSIONS]
    for student, done in behind:
        left = second_coach.TARGET_SESSIONS - done
        push.notify(db, "focus", "Your week ends tomorrow",
                    f"{left} focus session{'s' if left > 1 else ''} to go — log {'them' if left > 1 else 'it'} to keep your streak.",
                    students=push.student_account_ids(db, student), data={"tab": "dash"})
    return {"nudged": len(behind)}


# ------------------------------ the second coach ---------------------------- #
#
# What the dashboards say (coach.py): plain rules over the numbers, no AI. Students get
# it once their coach has verified them; before that, only their to-dos and badges.

def profile_done(student: Student) -> bool:
    """Everything the student dashboard's checklist asks for is filled in."""
    return all([student.photo_key, student.ra_number, student.dob, student.phone,
                student.father_phone or student.mother_phone, student.aadhaar, student.blood_group,
                student.category, student.height_cm, student.weight_kg,
                not student.highest_level or any(a.status != "draft" for a in student.achievements)])


def focus_weeks(db: Session, student: Student, report: dict | None, today) -> list:
    """The student's focus weeks, oldest first. This week's is made on its first visit,
    with the measure it asks them to work on, so it stays put all week."""
    def load():
        return db.scalars(select(FocusWeek).where(FocusWeek.student_id == student.id)
                          .order_by(FocusWeek.week)).all()
    week = second_coach.week_of(today)
    rows = load()
    if report is not None and not any(w.week == week for w in rows):
        key = second_coach.focus_metric(report)
        if key:
            db.add(FocusWeek(student_id=student.id, week=week, metric_key=key, sessions=[]))
            try:
                db.commit()
            except IntegrityError:        # another tab made it a moment ago
                db.rollback()
            rows = load()
    return [{"week": w.week, "metric_key": w.metric_key, "sessions": list(w.sessions or []),
             "restored_by": w.restored_by, "restored_at": w.restored_at, "restored_day": w.restored_day}
            for w in rows]


def coach_payload(db: Session, student: Student) -> dict:
    report = build_report(db, student) if student.status == "verified" else None
    history = history_rows(db, student.id) if report else []
    today = second_coach.today_ist(utcnow())
    weeks = focus_weeks(db, student, report, today)
    achievements = [{"status": a.status, "level": a.level, "title": a.title} for a in student.achievements]
    return second_coach.student_coach(StudentOut.model_validate(student).model_dump(), report, history,
                                      achievements, weeks, student.coach_seen, today, profile_done(student))


@app.get("/api/student/coach")
def get_student_coach(db: Session = Depends(get_db),
                      account: StudentAccount = Depends(auth.current_student)):
    """The student's dashboard: what to know, what to do next, rings, badges, the week's focus."""
    student = my_student(account)
    payload = coach_payload(db, student)
    # nothing to celebrate: what is on screen now joins the baseline the next level-up is
    # measured from (with something to celebrate, /seen does that once it has been shown)
    party = payload["celebrate"]
    if not party["level"] and not party["levelUps"] and not party["badges"]:
        seen = second_coach.merge_seen(student.coach_seen, payload["snapshot"])
        if seen != student.coach_seen:
            student.coach_seen = seen
            db.commit()
    return payload


@app.post("/api/student/coach/seen", status_code=204)
def student_coach_seen(body: SeenIn | None = None, db: Session = Depends(get_db),
                       account: StudentAccount = Depends(auth.current_student)):
    """The level reached and the milestones on screen have been seen. The body is the
    snapshot the dashboard was given, so a level reached while the record was open is
    still announced next time; it is capped at what is true now, so it can only ever
    mark as seen what the student has. No body: everything as it is now."""
    student = my_student(account)
    now = coach_payload(db, student)["snapshot"]
    shown = now if body is None else {
        "levels": {k: min(v, now["levels"][k]) for k, v in body.levels.items() if k in now["levels"]},
        "badges": [b for b in body.badges if b in now["badges"]],
        "overall": None if body.overall is None or now["overall"] is None else min(body.overall, now["overall"]),
    }
    student.coach_seen = second_coach.merge_seen(student.coach_seen, shown)
    db.commit()


@app.post("/api/student/focus/tick")
def focus_tick(db: Session = Depends(get_db), account: StudentAccount = Depends(auth.current_student)):
    """Today's session of this week's focus is done — once a day counts."""
    student = my_student(account)
    if student.status != "verified":
        raise HTTPException(403, "Your weekly focus starts once your coach has verified you.")
    today = second_coach.today_ist(utcnow())
    this_week = select(FocusWeek).where(FocusWeek.student_id == student.id,
                                        FocusWeek.week == second_coach.week_of(today))
    if db.scalar(this_week) is None:
        # a new week began while the dashboard was open (Monday, just past midnight)
        focus_weeks(db, student, build_report(db, student), today)
    week = db.scalar(this_week.with_for_update())
    if week is None:
        raise HTTPException(409, "There's nothing to focus on yet — your coach hasn't recorded a test with a level.")
    if today.isoformat() not in (week.sessions or []):
        week.sessions = [*(week.sessions or []), today.isoformat()]
    db.commit()
    return coach_payload(db, student)


@app.post("/api/students/{student_id}/focus/log")
def coach_log_focus(student_id: int, payload: FocusLogIn, db: Session = Depends(get_db),
                    coach: Coach = Depends(auth.current_coach)):
    """A session the student trained but forgot to tick, logged by their coach — this
    week or last, never ahead. If it completes a week, the student's dashboard says the
    streak was restored."""
    student = coach_student(student_id, coach, db)
    today = second_coach.today_ist(utcnow())
    if payload.day > today or (today - payload.day).days > 13:
        raise HTTPException(400, "Log a session from this week or last week.")
    week = db.scalar(select(FocusWeek).where(FocusWeek.student_id == student.id,
                                             FocusWeek.week == second_coach.week_of(payload.day))
                     .with_for_update())
    if week is None:
        raise HTTPException(409, f"{student.name} had no weekly focus that week, so there is nothing to log it against.")
    day = payload.day.isoformat()
    if day not in (week.sessions or []):
        week.sessions = sorted([*(week.sessions or []), day])
        week.restored_by, week.restored_at, week.restored_day = coach.name, utcnow(), day
    db.commit()
    if len(week.sessions) == second_coach.TARGET_SESSIONS:
        push.notify(db, "coach", "Streak restored", f"{coach.name} logged {payload.day.strftime('%A')}'s session — that week counts.",
                    students=push.student_account_ids(db, student), data={"tab": "dash"})
    return {"week": week.week, "sessions": list(week.sessions)}


@app.get("/api/coach/feed")
def coach_feed(db: Session = Depends(get_db), who: Coach = Depends(auth.current_coach)):
    """What the coach should know about their squad today (coach.coach_feed)."""
    sport = who.sport
    students = sport_students(db, sport)
    ids = [s.id for s in students]
    history, weeks = defaultdict(list), defaultdict(list)
    if ids:
        for r in db.scalars(select(TestResult).where(TestResult.student_id.in_(ids))
                            .order_by(TestResult.recorded_at.asc(), TestResult.id.asc())):
            history[r.student_id].append({"metric_key": r.metric_key, "value": r.value,
                                          "recorded_at": r.recorded_at})
        for w in db.scalars(select(FocusWeek).where(FocusWeek.student_id.in_(ids))):
            weeks[w.student_id].append({"week": w.week, "sessions": list(w.sessions or [])})
    pending = db.scalar(select(func.count()).select_from(Achievement).where(
        Achievement.status == "pending", Achievement.student_id.in_(ids))) if ids else 0
    today = second_coach.today_ist(utcnow())
    overrides = get_state(db, f"levels:{sport}")
    players = []
    for s in students:
        h = history[s.id]
        latest = {r["metric_key"]: r["value"] for r in h}
        rows = levels.read_out(sport, {**latest, "heightCm": s.height_cm}, s.category,
                               overrides=overrides)["rows"]
        players.append({"id": s.id, "name": s.name, "status": s.status, "category": s.category,
                        "has_results": bool(h), "last_test": h[-1]["recorded_at"].date() if h else None,
                        "rows": rows, "history": h, "streak": second_coach.streak(weeks[s.id], today)})
    return {"feed": second_coach.coach_feed(players, pending or 0, today)}


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


# ------------------------------- level targets ----------------------------- #
#
# What a player typically posts at University, Zonal, State, National and International
# level (levels.py). Coaches retune them for their own sport, one measure at a time.

def level_metric(sport: str, key: str, overrides: dict) -> dict:
    entry = levels.DEFAULTS[sport][key]
    return {"key": key, **levels.catalogue(sport)[key], "formats": levels.formats_of(sport, key),
            "targets": levels.targets(sport, key, overrides), "defaults": entry["targets"],
            "custom": key in overrides, "basis": entry["basis"], "sources": entry["sources"],
            "note": entry["note"]}


def level_sport(sport: str, coach: Coach) -> str:
    name = require_sport(sport)
    auth.require_own_sport(coach, name)
    return name


@app.get("/api/sports/{sport}/levels")
def get_levels(sport: str, db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    name = level_sport(sport, coach)
    overrides = get_state(db, f"levels:{name}")
    formats = (match_cards.SPORTS.get(name) or {}).get("formats") or {}
    return {"sport": name, "levels": levels.LEVEL_WORDS,
            "formats": [{"key": k, "label": v} for k, v in formats.items()],
            "metrics": [level_metric(name, key, overrides) for key in levels.catalogue(name)]}


def edit_levels(db: Session, sport: str, key: str, change) -> dict:
    """Apply `change(overrides)` to the sport's edits with the row locked, so two coaches
    saving different measures at once both keep theirs."""
    state_key = f"levels:{sport}"
    if db.get(AppState, state_key) is None:
        # a lock needs a row: make it first, so a sport's first two edits can't collide
        try:
            db.add(AppState(key=state_key, value={}))
            db.commit()
        except IntegrityError:
            db.rollback()                 # the other request made it a moment ago
    # ponytail: SQLite ignores FOR UPDATE; Postgres (production) holds the lock
    db.scalar(select(AppState).where(AppState.key == state_key).with_for_update())
    overrides = get_state(db, state_key)
    change(overrides)
    set_state(db, state_key, overrides)
    return level_metric(sport, key, overrides)


@app.put("/api/sports/{sport}/levels/{key}")
def put_level(sport: str, key: str, payload: LevelTargetsIn, db: Session = Depends(get_db),
              coach: Coach = Depends(auth.current_coach)):
    name = level_sport(sport, coach)
    try:
        clean = levels.check(name, key, payload.targets)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    def change(overrides):
        if clean == levels.DEFAULTS[name][key]["targets"]:
            overrides.pop(key, None)      # the built-in numbers again: nothing to keep
        else:
            overrides[key] = clean
    out = edit_levels(db, name, key, change)
    sync_sheet(db, sport_students(db, name))      # scores are read off the ladder
    return out


@app.delete("/api/sports/{sport}/levels/{key}")
def reset_level(sport: str, key: str, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    name = level_sport(sport, coach)
    if key not in levels.catalogue(name):
        raise HTTPException(404, f"'{key}' has no level targets in {name}")
    out = edit_levels(db, name, key, lambda overrides: overrides.pop(key, None))
    sync_sheet(db, sport_students(db, name))
    return out


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
    left = student.sport
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
    sync_sheet(db, [student], sports=[left])      # the sport they left, if they moved
    sync_people(db, "profiles")
    return student


@app.delete("/api/students/{student_id}", status_code=204)
def delete_student(student_id: int, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    student = coach_student(student_id, coach, db)
    remove_student(db, student)


def remove_student(db: Session, student: Student) -> None:
    """A student and everything of theirs, files included — a coach deleting them, or
    the student deleting their own account from the app."""
    for v in student.videos:
        forget_files(v.stored_name, thumb_of(v), v.pose_key)
    forget_files(student.photo_key, *(a.cert_key for a in student.achievements))
    sport = student.sport
    carded = {line.card.sport for line in student.card_lines if line.card.status == "final"}
    db.delete(student)
    db.commit()
    sync_sheet(db, sports=[sport])
    sync_people(db, "profiles", "achievements")
    for card_sport in carded:       # their rows leave the match-card file too
        sync_cards(db, card_sport)


@app.post("/api/students/{student_id}/verify", response_model=StudentOut)
def verify_student(student_id: int, payload: VerifyIn, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    """The coach confirms where this student plays. It is also a training label."""
    student = coach_student(student_id, coach, db)
    if payload.position not in sc.get_sport(student.sport)["positions"]:
        raise HTTPException(400, f"'{payload.position}' is not a position in {student.sport}")
    first = student.status != "verified"
    student.status = "verified"
    student.verified_position = payload.position
    student.verified_by_id = coach.id
    student.verified_at = utcnow()
    db.commit()
    db.refresh(student)
    sync_sheet(db, [student])
    push.notify(db, "coach", "You're verified" if first else "Your position changed",
                f"{coach.name} confirmed you as {payload.position}. Your report is ready.",
                students=push.student_account_ids(db, student), data={"tab": "report"})
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
    record = VideoAnalysis(student_id=student.id, label=payload.label, **open_upload(payload, MAX_VIDEO_BYTES))
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
    forget_files(record.stored_name, thumb_of(record), record.pose_key)
    db.delete(record)
    db.commit()
    sync_sheet(db, [student])


def pose_file(key: str | None) -> Response:
    """The skeleton track for the app's pose overlay (worker.run_video saves it)."""
    if not key:
        raise HTTPException(404, "No pose data for this clip — it was analysed before the app could draw it.")
    try:
        return Response(storage.read_bytes(key), media_type="application/json",
                        headers={"Cache-Control": "private, max-age=86400"})
    except FileNotFoundError as exc:
        raise HTTPException(404, "No pose data for this clip") from exc
    except storage.StorageError as exc:
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/videos/{video_id}/pose")
def video_pose(video_id: int, db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    return pose_file(_coach_video(video_id, coach, db).pose_key)


# A student filming their own drills from the app: the same pieces and queue as a
# coach's upload, but only ever into their own record, and only once they are enrolled.

def _my_video(video_id: int, account: StudentAccount, db: Session) -> VideoAnalysis:
    record = db.get(VideoAnalysis, video_id)
    if record is None or account.student is None or record.student_id != account.student.id:
        raise HTTPException(404, "Video not found")
    return record


@app.post("/api/student/videos", status_code=201)
def student_start_video(payload: UploadIn, db: Session = Depends(get_db),
                        account: StudentAccount = Depends(auth.current_student)):
    student = my_student(account)
    record = VideoAnalysis(student_id=student.id, uploaded_by="student", label=payload.label,
                           **open_upload(payload, MAX_VIDEO_BYTES))
    db.add(record)
    db.commit()
    return {"id": record.id, "chunkSize": storage.CHUNK}


@app.put("/api/student/videos/{video_id}/upload")
async def student_video_chunk(video_id: int, request: Request,
                              x_chunk_range: str | None = Header(default=None),
                              db: Session = Depends(get_db),
                              account: StudentAccount = Depends(auth.current_student)):
    record = _my_video(video_id, account, db)
    out = await take_chunk(record, request, x_chunk_range, db)
    if out["done"] and out["status"] == "queued":
        student = record.student
        push.notify(db, "coach", "New drill clip", f"{student.name} sent a drill clip for analysis.",
                    coaches=push.sport_coach_ids(db, student.sport), data={"student": student.id})
    return out


@app.get("/api/student/videos", response_model=list[VideoOut])
def student_videos(account: StudentAccount = Depends(auth.current_student)):
    student = my_student(account)
    return sorted((v for v in student.videos if v.status != "uploading" or v.uploaded_by == "student"),
                  key=lambda v: v.created_at, reverse=True)


@app.get("/api/student/videos/{video_id}/thumbnail")
def student_video_thumbnail(video_id: int, db: Session = Depends(get_db),
                            account: StudentAccount = Depends(auth.current_student)):
    return stored_image(thumb_of(_my_video(video_id, account, db)), "No thumbnail for this clip")


@app.get("/api/student/videos/{video_id}/pose")
def student_video_pose(video_id: int, db: Session = Depends(get_db),
                       account: StudentAccount = Depends(auth.current_student)):
    return pose_file(_my_video(video_id, account, db).pose_key)


@app.delete("/api/student/videos/{video_id}", status_code=204)
def student_delete_video(video_id: int, db: Session = Depends(get_db),
                         account: StudentAccount = Depends(auth.current_student)):
    """A student can take back a clip they sent, while it is still waiting or unfinished;
    once analysed it is part of their report and their coach decides."""
    record = _my_video(video_id, account, db)
    if record.uploaded_by != "student" or record.status in ("processing", "done"):
        raise HTTPException(403, "Your coach looks after analysed clips — ask them to remove it.")
    forget_files(record.stored_name, thumb_of(record), record.pose_key)
    db.delete(record)
    db.commit()


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
    "Badminton": [
        {"key": "badminton-doubles", "label": "Badminton court (13.4 × 6.1 m)",
         "corners": ["Near-left corner", "Near-right corner",
                     "Far-right corner", "Far-left corner"],
         "world": [[0, 0], [6.1, 0], [6.1, 13.4], [0, 13.4]]},
    ],
    "Tennis": [
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
    was = achievement.status
    edit_achievement(achievement, payload, "pending")
    db.commit()
    sync_people(db, "achievements")
    db.refresh(achievement)
    if achievement.status == "pending" and was != "pending":
        st = achievement.student
        push.notify(db, "coach", "Certificate to check", f"{st.name} sent {achievement.title or 'a certificate'}.",
                    coaches=push.sport_coach_ids(db, st.sport), data={"student": st.id})
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
    what = achievement.title or "Your certificate"
    push.notify(db, "coach", "Certificate verified" if payload.decision == "verified" else "Certificate needs fixing",
                f"{what} — checked by {coach.name}." if payload.decision == "verified" else f"{what}: {payload.note}",
                students=push.student_account_ids(db, achievement.student), data={"tab": "ach"})
    return AchievementOut.model_validate(achievement)


@app.get("/api/achievements/{achievement_id}/certificate")
def coach_certificate(achievement_id: int, db: Session = Depends(get_db),
                      coach: Coach = Depends(auth.current_coach)):
    return certificate(coach_achievement(achievement_id, coach, db))


# -------------------------------- match cards ------------------------------- #

MAX_CARD_PHOTOS = 4
CARD_READS_PER_HOUR = 30      # per coach — every read is one call to the document AI


def coach_card(card_id: int, coach: Coach, db: Session) -> MatchCard:
    card = db.get(MatchCard, card_id)
    if card is None or card.sport != coach.sport:
        raise HTTPException(404, "Card not found")
    return card


def photo_version(photo: dict) -> str:
    """Stable per photo, so a URL never shows a different photo from the browser's cache."""
    return hashlib.sha256(photo["key"].encode()).hexdigest()[:12]


def card_out(card: MatchCard) -> dict:
    lines = [line_dict(line) for line in card.lines]
    return {**card_dict(card), "sport": card.sport, "status": card.status,
            "photos": [{"n": i, "v": photo_version(p), "mime": p.get("mime"),
                        "read": p["key"] in (card.ai_read or {})} for i, p in enumerate(card.photos or [])],
            # players on the card who have since moved to another sport
            "formerPlayers": [{"id": line.student.id, "name": line.student.name,
                               "jersey": line.student.jersey_number}
                              for line in card.lines if line.student and line.student.sport != card.sport],
            "lines": lines, "partC": match_cards.part_c(card.sport, card_dict(card), lines),
            "createdAt": card.created_at, "updatedAt": card.updated_at}


def card_summary(card: MatchCard) -> dict:
    h = card.header or {}
    return {"id": card.id, "status": card.status, "category": card.category, "format": card.format,
            "tournament": h.get("tournament"), "round": h.get("round"), "date": h.get("date"),
            "opponent": h.get("opponent"), "result": h.get("result"), "match_no": h.get("match_no"),
            "players": len(card.lines), "photos": len(card.photos or []), "updatedAt": card.updated_at}


def squad_list(db: Session, sport: str) -> list:
    """Who can go on a card: every student in the sport, jersey numbers first."""
    students = sport_students(db, sport)
    return [{"id": s.id, "name": s.name, "jersey": s.jersey_number,
             "position": s.verified_position or s.declared_position}
            for s in sorted(students, key=lambda s: (s.jersey_number is None, s.jersey_number or 0, s.name))]


def final_cards(db: Session, sport: str) -> list:
    """[(card, lines)] for the sport's finished cards, each line with the student's RA number."""
    cards = db.scalars(select(MatchCard).where(MatchCard.sport == sport, MatchCard.status == "final")).all()
    return [(card_dict(c), [{**line_dict(line), "ra": line.student.ra_number if line.student else None}
                            for line in c.lines]) for c in cards]


def card_sports(db: Session) -> list:
    """Every sport with a finished card or a card file already — what the worker repushes."""
    have = db.scalars(select(MatchCard.sport).where(MatchCard.status == "final").distinct())
    return sorted(set(have) | set(get_state(db, "card_sheets")))


def sync_cards(db: Session, sport: str):
    """Rewrite the sport's "match cards" spreadsheet: Matches and Tournaments. Never raises."""
    if not sheets.configured():
        return
    try:
        cards = final_cards(db, sport)
    except Exception:  # noqa: BLE001
        db.rollback()
        log.exception("card rows failed")
        return
    publish(db, "card_sheets", sport, f"Stridian — {sport} match cards", list(sheets.CARD_TABS),
            list(sheets.CARD_TABS), lambda: sheets.card_tabs(sport, cards))


def cards_changed(db: Session, sport: str, students):
    """A final card was saved, changed or deleted: its players' reports move, and so does
    the sport's card file."""
    sync_sheet(db, [s for s in students if s is not None and s.sport == sport])
    sync_cards(db, sport)


@app.get("/api/cards/config")
def cards_config(category: str = "M", format: str | None = None, db: Session = Depends(get_db),
                 coach: Coach = Depends(auth.current_coach)):
    """The coach's sport's card — for printing it blank, filling it in and reading it —
    with the squad whose names and jersey numbers go on it."""
    return {**match_cards.public(coach.sport, category, format), "squad": squad_list(db, coach.sport),
            "aiOn": docreader.configured()}


@app.get("/api/cards")
def list_cards(db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    cards = db.scalars(select(MatchCard).where(MatchCard.sport == coach.sport)).all()
    cards.sort(key=lambda c: ((c.header or {}).get("date") or "", c.id), reverse=True)
    return [card_summary(c) for c in cards]


@app.post("/api/cards", status_code=201)
def create_card(payload: CardNew, db: Session = Depends(get_db),
                coach: Coach = Depends(auth.current_coach)):
    try:
        header = match_cards.clean_header(coach.sport, payload.header)
    except match_cards.CardError as exc:
        raise HTTPException(422, str(exc)) from exc
    card = MatchCard(sport=coach.sport, category=payload.category,
                     format=match_cards.pick_format(coach.sport, payload.format),
                     header=header, team={}, photos=[], coach_id=coach.id)
    db.add(card)
    db.commit()
    db.refresh(card)
    return card_out(card)


@app.get("/api/cards/{card_id}")
def get_card(card_id: int, db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    return card_out(coach_card(card_id, coach, db))


@app.put("/api/cards/{card_id}")
def save_card(card_id: int, payload: CardIn, db: Session = Depends(get_db),
              coach: Coach = Depends(auth.current_coach)):
    """Save the whole card. `final` makes it count: reports, the sheets, the downloads.
    A final card can still be corrected, and saving it as a draft takes it back out."""
    card = coach_card(card_id, coach, db)
    sport = card.sport
    try:
        header = match_cards.clean_header(sport, payload.header)
        team = match_cards.clean_team(sport, payload.team)
        rows = [(line, match_cards.clean_line(sport, line.model_dump())) for line in payload.lines]
    except match_cards.CardError as exc:
        raise HTTPException(422, str(exc)) from exc

    ids = [line.student_id for line, _ in rows if line.student_id is not None]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "A player is on this card twice.")
    # someone already on the card may have moved sport since; they stay on it
    already = {line.student_id for line in card.lines}
    players = {s.id: s for s in db.scalars(select(Student).where(Student.id.in_(ids)))} if ids else {}
    if any(i not in players or (players[i].sport != sport and i not in already) for i in ids):
        raise HTTPException(422, "One of those players isn't in this sport's squad.")
    positions = sc.get_sport(sport)["positions"]
    for line, _ in rows:
        if line.position and line.position not in positions:
            raise HTTPException(422, f"'{line.position}' isn't a {sport} position.")
    if payload.final:
        if not rows:
            raise HTTPException(422, "Add the players before finishing the card.")
        unmatched = [str(line.jersey if line.jersey is not None else line.name or "?")
                     for line, _ in rows if line.student_id is None]
        if unmatched:
            raise HTTPException(422, f"Say which student is on the row for {', '.join(unmatched)} "
                                     f"before finishing the card.")

    counted = card.status == "final"
    touched = {line.student for line in card.lines} | set(players.values())
    card.category = payload.category
    card.format = match_cards.pick_format(sport, payload.format)
    card.header, card.team = header, team
    card.lines = [MatchCardLine(student_id=line.student_id, jersey=line.jersey, name=line.name,
                                position=line.position, data=data, coord=line.coord,
                                overall=line.overall, strength=line.strength, improve=line.improve,
                                remarks=line.remarks) for line, data in rows]
    card.status = "final" if payload.final else "draft"
    db.commit()
    db.refresh(card)
    if counted or payload.final:
        cards_changed(db, sport, touched)
    return card_out(card)


@app.delete("/api/cards/{card_id}", status_code=204)
def delete_card(card_id: int, db: Session = Depends(get_db), coach: Coach = Depends(auth.current_coach)):
    card = coach_card(card_id, coach, db)
    counted, sport = card.status == "final", card.sport
    students = [line.student for line in card.lines]
    keys = [p["key"] for p in card.photos or []]
    db.delete(card)
    db.commit()
    forget_files(*keys)
    if counted:
        cards_changed(db, sport, students)


def card_photo(card: MatchCard, n: int, v: str | None = None) -> dict:
    """Photo n — and, when the page says which photo it means, that one or a 409, so a
    photo deleted in another tab never makes the next one get read or deleted instead."""
    photos = card.photos or []
    if not 0 <= n < len(photos):
        raise HTTPException(404, "Photo not found")
    if v and v != photo_version(photos[n]):
        raise HTTPException(409, "The card's photos have changed — reopen the card.")
    return photos[n]


@app.post("/api/cards/{card_id}/photos", status_code=201)
async def add_card_photo(card_id: int, request: Request, db: Session = Depends(get_db),
                         coach: Coach = Depends(auth.current_coach)):
    """A photo (or PDF scan) of the paper card, kept with it until the card is deleted."""
    card = coach_card(card_id, coach, db)
    if len(card.photos or []) >= MAX_CARD_PHOTOS:
        raise HTTPException(409, f"A card holds up to {MAX_CARD_PHOTOS} photos — delete one first.")
    data, mime = await read_upload(request, MAX_DOC_BYTES, set(EXTENSION))
    try:
        key = await run_in_threadpool(storage.save_bytes, f"card-{card.id}{EXTENSION[mime]}", data, mime)
    except storage.StorageError as exc:
        raise HTTPException(502, str(exc)) from exc
    card.photos = [*(card.photos or []), {"key": key, "mime": mime}]
    db.commit()
    return card_out(card)


@app.get("/api/cards/{card_id}/photos/{n}")
def get_card_photo(card_id: int, n: int, v: str | None = None, db: Session = Depends(get_db),
                   coach: Coach = Depends(auth.current_coach)):
    photo = card_photo(coach_card(card_id, coach, db), n, v)
    return stored_image(photo["key"], "Photo missing", photo.get("mime") or "image/jpeg")


@app.delete("/api/cards/{card_id}/photos/{n}")
def delete_card_photo(card_id: int, n: int, v: str | None = None, db: Session = Depends(get_db),
                      coach: Coach = Depends(auth.current_coach)):
    card = coach_card(card_id, coach, db)
    photo = card_photo(card, n, v)
    card.photos = [p for i, p in enumerate(card.photos) if i != n]
    card.ai_read = {k: v for k, v in (card.ai_read or {}).items() if k != photo["key"]}
    db.commit()
    forget_files(photo["key"])
    return card_out(card)


def suggest(sport: str, squad: list, reading: dict) -> dict:
    """The AI's reading with each row matched to a student where that's certain: a jersey
    number only one squad member wears, or else exactly one name that matches."""
    by_jersey = {}
    for s in squad:
        if s["jersey"] is not None:
            by_jersey.setdefault(s["jersey"], []).append(s["id"])
    by_name = {}
    for s in squad:
        by_name.setdefault(" ".join(s["name"].split()).casefold(), []).append(s["id"])
    players = []
    for p in reading["players"]:
        found = by_jersey.get(p["jersey"], [])
        if len(found) != 1 and p["name"]:
            found = by_name.get(" ".join(p["name"].split()).casefold(), [])
        players.append({**p, "student_id": found[0] if len(found) == 1 else None})
    return {**reading, "players": players}


@app.post("/api/cards/{card_id}/photos/{n}/read")
async def read_card_photo(card_id: int, n: int, v: str | None = None, db: Session = Depends(get_db),
                          coach: Coach = Depends(auth.current_coach)):
    """Have the document AI read Part A off one photo. Nothing is saved on the card: the
    coach checks what it read in the editor, then saves."""
    card = coach_card(card_id, coach, db)
    photo = card_photo(card, n, v)
    if not docreader.configured():
        raise HTTPException(503, "Reading photos isn't switched on (GEMINI_API_KEY) — type the card in instead.")
    key = f"cardai:{coach.id}"
    hour = utcnow().strftime("%Y-%m-%dT%H")
    used = get_state(db, key)
    count = used.get("n", 0) if used.get("hour") == hour else 0
    if count >= CARD_READS_PER_HOUR:
        raise HTTPException(429, "That's a lot of photos read for one hour — try again later.")
    set_state(db, key, {"hour": hour, "n": count + 1})
    try:
        data = await run_in_threadpool(storage.read_bytes, photo["key"])
    except (FileNotFoundError, storage.StorageError) as exc:
        raise HTTPException(502, "Couldn't open that photo from storage.") from exc
    # two tries of 20 s each, plus the Drive read, stay inside the host's 60-second limit
    found = await run_in_threadpool(docreader.read, data, photo.get("mime") or "image/jpeg",
                                    match_cards.ai_prompt(card.sport), match_cards.ai_schema(card.sport), 20)
    if not found:
        raise HTTPException(502, "The photo couldn't be read. Try a sharper, straighter photo in good "
                                 "light, or type the card in.")
    reading = match_cards.from_ai(card.sport, found)
    card.ai_read = {**(card.ai_read or {}), photo["key"]: reading}
    db.commit()
    return suggest(card.sport, squad_list(db, card.sport), reading)


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
    sports = sc.sport_names() if everyone else [coach.sport]
    data = export.squad(students, histories(db, [s.id for s in students]), coaches,
                        {sport: final_cards(db, sport) for sport in sports})
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
        "sheetsConfigured": sheets.configured(),
        "sheets": admin_sheets(db) if coach.is_admin else None,
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
