"""
The worker: the computer that does the heavy lifting.

Run it on the laptop now, the lab iMac later:

    python worker.py          keep going until you press Ctrl+C (or shut the lid)
    python worker.py --once   one full pass, then exit

It shares nothing with the website except the database (DATABASE_URL) and the video
storage (Google Drive). Every time it runs it:

1. analyses every queued video — MediaPipe for drill clips, YOLO for match footage;
2. hands back any job it was halfway through when it was last switched off;
3. retrains each sport's position weights from the coaches' verifications, and puts
   the new model live only if it tests better than the current one;
4. deletes videos older than 30 days (their measurements stay), and
5. pushes the Google Sheet, in case a push from the website was missed.

Switching it off at any moment is safe. Nothing is lost; the next run carries on with
yesterday's data plus whatever arrived since.
"""

import argparse
import logging
import os
import platform
import sys
import tempfile
import time
from datetime import timedelta
from pathlib import Path

from sqlalchemy import select, update

import main
import sports_config as sc
import storage
import trainer
from db import SessionLocal
from models import MatchClip, ModelVersion, Student, VideoAnalysis
from models import _now as utcnow

LEASE = timedelta(minutes=30)          # a claim older than this was interrupted
MAX_ATTEMPTS = 3                       # then the job is marked failed, not retried forever
RETENTION = timedelta(days=int(os.environ.get("VIDEO_RETENTION_DAYS", "30")))
ABANDONED_UPLOAD = timedelta(days=1)   # a browser that never finished sending a video
POLL_SECONDS = 20
MAINTENANCE_EVERY = timedelta(minutes=15)

log = logging.getLogger("worker")


# --------------------------------------------------------------------------- #
# What this computer can do
# --------------------------------------------------------------------------- #

def capabilities():
    """Only claim jobs this machine can actually run; the rest stay queued for one that can."""
    caps = {"pose": False, "match": False, "poseDetail": "", "matchDetail": ""}
    try:
        import video
        status = video.backend_status()
        caps["pose"], caps["poseDetail"] = status["available"], status["detail"]
    except Exception as exc:  # noqa: BLE001 — mediapipe/opencv not installed
        caps["poseDetail"] = f"not installed ({exc.__class__.__name__})"
    try:
        import match_video
        status = match_video.backend_status()
        caps["match"], caps["matchDetail"] = status["available"], status["detail"]
    except Exception as exc:  # noqa: BLE001
        caps["matchDetail"] = f"not installed ({exc.__class__.__name__})"
    return caps


def heartbeat(db, caps, doing="idle"):
    main.set_state(db, "worker", {
        "host": platform.node(), "lastSeen": utcnow().isoformat(), "doing": doing,
        "pose": caps["pose"], "match": caps["match"], "storage": storage.backend(),
    })


# --------------------------------------------------------------------------- #
# The queue
# --------------------------------------------------------------------------- #

def claim(db, model, skip=()):
    """Take the oldest queued job not in `skip`. The conditional UPDATE is the lock: if
    two workers ever race for the same row, only one of them changes it."""
    while True:
        job_id = db.scalar(select(model.id).where(model.status == "queued", model.id.notin_(skip))
                           .order_by(model.id).limit(1))
        if job_id is None:
            return None
        won = db.execute(
            update(model).where(model.id == job_id, model.status == "queued")
            .values(status="processing", claimed_at=utcnow(), attempts=model.attempts + 1,
                    message="Being analysed now.")
        ).rowcount
        db.commit()
        if won:
            return db.get(model, job_id)


def fail_or_retry(db, job, exc):
    job.claimed_at = None
    if job.attempts >= MAX_ATTEMPTS:
        job.status = "failed"
        job.message = f"Gave up after {job.attempts} attempts: {exc}"
    else:
        job.status = "queued"
        job.message = f"Will retry — last attempt failed: {exc}"
    db.commit()


def run_video(db, job, tmp):
    import video

    src = tmp / ("clip" + Path(job.original_name).suffix.lower())
    stored, student = job.stored_name, job.student
    height, sport = student.height_cm, student.sport
    # Hand the database connection back before minutes of download and analysis. Held
    # open and idle that long, it gets cut (by Neon, WARP or the network), and saving the
    # result then fails; from the pool it is checked, and replaced if it died.
    db.commit()
    storage.download(stored, src)
    thumb = tmp / "thumb.jpg"
    result = video.analyse_video(src, height_cm=height, sport=sport, thumbnail_path=thumb)

    job.status = result.get("status", "failed")
    job.message = result.get("message")
    job.duration_sec = result.get("durationSec")
    job.fps = result.get("fps")
    job.frames_total = result.get("framesTotal")
    job.frames_detected = result.get("framesDetected")
    job.metrics = {
        "values": result.get("metrics", {}),
        "labels": result.get("readable", {}),
        "units": result.get("units", {}),
        "explain": result.get("explain", {}),
        "observations": result.get("observations", []),
        "drills": result.get("drills", []),
        "sportSpecific": result.get("sportSpecific", {}),
        "detectionRate": result.get("detectionRate"),
        "framesSampled": result.get("framesSampled"),
    }
    if thumb.exists():
        job.thumb_key = storage.save_bytes(f"video-{job.id}-thumb.jpg", thumb.read_bytes())
    job.claimed_at = None
    db.commit()
    main.sync_sheet(db, [student])


def run_match(db, job, tmp):
    import match_video

    src = tmp / ("match" + Path(job.original_name).suffix.lower())
    stored, direction, family = job.stored_name, job.attack_direction, sc.SPORT_MATCH_FAMILY[job.sport]
    db.commit()   # release the connection for the long part, as in run_video
    storage.download(stored, src)
    keyframe, frames_dir = tmp / "key.jpg", tmp / "frames"
    frames_dir.mkdir()
    result = match_video.analyse_match(src, attack_direction=direction, keyframe_path=keyframe,
                                       family=family, frames_dir=frames_dir)

    job.status = result.get("status", "failed")
    job.message = result.get("message")
    job.duration_sec = result.get("durationSec")
    job.fps = result.get("fps")
    job.frames_sampled = result.get("framesSampled")
    job.tracks = result.get("tracks", [])
    job.keyframe_boxes = result.get("keyframeBoxes", [])
    if keyframe.exists():
        job.keyframe_key = storage.save_bytes(f"match-{job.id}-keyframe.jpg", keyframe.read_bytes())
    items = [{"key": storage.save_bytes(f"match-{job.id}-frame-{k}.jpg", Path(f["path"]).read_bytes()),
              "t": f["t"]} for k, f in enumerate(result.get("frames", []))]
    job.calibration_frames = {"items": items, "start": result.get("framesStart")} if items else None
    job.claimed_at = None
    db.commit()


def work_queue(db, caps):
    """Run every queued job this machine can handle. Returns how many it finished."""
    runners = []
    if caps["pose"]:
        runners.append((VideoAnalysis, run_video, "drill video"))
    if caps["match"]:
        runners.append((MatchClip, run_match, "match clip"))

    done = 0
    for model, runner, what in runners:
        failed = set()   # a job that errored waits for the next pass, not an instant retry
        while (job := claim(db, model, failed)) is not None:
            heartbeat(db, caps, f"{what} #{job.id}")
            log.info("analysing %s #%s (%s)", what, job.id, job.original_name)
            started = time.monotonic()
            try:
                with tempfile.TemporaryDirectory() as tmp:
                    runner(db, job, Path(tmp))
                log.info("  %s in %.0fs — %s", job.status, time.monotonic() - started, job.message)
            except Exception as exc:  # noqa: BLE001 — one bad file must not stop the queue
                db.rollback()
                log.exception("  failed")
                failed.add(job.id)
                current = db.get(model, job.id)
                if current is not None:          # None: deleted by a coach mid-analysis
                    fail_or_retry(db, current, exc)
            done += 1
    heartbeat(db, caps)
    return done


def recover(db):
    """Hand back jobs a switched-off worker was holding, and drop dead uploads."""
    now = utcnow()
    for model in (VideoAnalysis, MatchClip):
        for job in db.scalars(select(model).where(model.status == "processing",
                                                  model.claimed_at < now - LEASE)).all():
            log.info("requeueing interrupted %s #%s", model.__tablename__, job.id)
            fail_or_retry(db, job, "the analysis computer was switched off mid-way")
        for job in db.scalars(select(model).where(model.status == "uploading",
                                                  model.created_at < now - ABANDONED_UPLOAD)).all():
            log.info("dropping unfinished upload %s #%s", model.__tablename__, job.id)
            main.forget_files(job.stored_name)
            db.delete(job)
    db.commit()


# --------------------------------------------------------------------------- #
# Housekeeping: retention, training, the sheet
# --------------------------------------------------------------------------- #

def expire_videos(db):
    """Delete video files past the retention window. Every measurement taken from them
    stays; the row just records that the file itself is gone."""
    cutoff = utcnow() - RETENTION
    removed = 0
    for model in (VideoAnalysis, MatchClip):
        old = db.scalars(select(model).where(
            model.status.in_(("done", "failed", "unavailable")),
            model.created_at < cutoff, model.video_deleted_at.is_(None))).all()
        for job in old:
            try:
                storage.delete(job.stored_name)
            except Exception:  # noqa: BLE001 — try again next pass
                log.warning("could not delete %s", job.stored_name, exc_info=True)
                continue
            job.video_deleted_at = utcnow()
            removed += 1
    db.commit()
    if removed:
        log.info("deleted %s video(s) older than %s days", removed, RETENTION.days)
    return removed


def train_sport(db, sport):
    """Retrain one sport if its verified data changed. Returns a line for the log."""
    positions = sc.get_sport(sport)["positions"]
    samples = []
    for student in db.scalars(select(Student).where(Student.sport == sport,
                                                    Student.status == "verified")).all():
        rows = main.metric_rows(db, student)
        if student.verified_position in positions and len(trainer.scores_of(rows)) >= 3:
            samples.append((rows, student.verified_position))

    ok, reason = trainer.ready(sport, samples)
    if not ok:
        return reason

    signature = trainer.signature(samples)
    last = db.scalar(select(ModelVersion).where(ModelVersion.sport == sport,
                                                ModelVersion.kind == "trained")
                     .order_by(ModelVersion.id.desc()).limit(1))
    if last and last.signature == signature:
        return "no new verified data since the last training run"

    live = main.load_weights(db, sport)
    baseline = db.scalar(select(ModelVersion).where(ModelVersion.sport == sport,
                                                    ModelVersion.kind == "baseline",
                                                    ModelVersion.deployed.is_(True))
                         .order_by(ModelVersion.id.desc()).limit(1))
    prior = baseline.weights if baseline else live
    result = trainer.train(sport, prior, live, samples)

    if result["deploy"]:
        if baseline is None:
            # keep the pre-training weights as a version, so there is something to roll back to
            db.add(ModelVersion(sport=sport, kind="baseline", weights=live, deployed=True,
                                note="Weights in use before the first trained model"))
            db.flush()
        main.apply_weights(db, sport, result["weights"])

    accuracy, live_accuracy = result["accuracy"], result["live_accuracy"]
    verdict = (f"held-out accuracy {accuracy:.0%} beat the live model's {live_accuracy:.0%}"
               if result["deploy"] else
               f"held-out accuracy {accuracy:.0%} did not beat the live model's {live_accuracy:.0%}")
    db.add(ModelVersion(sport=sport, kind="trained", weights=result["weights"],
                        deployed=result["deploy"], labels=len(samples), accuracy=accuracy,
                        live_accuracy=live_accuracy, signature=signature,
                        note=f"Trained on {len(samples)} verified students; {verdict}."))
    db.commit()

    if result["deploy"]:
        main.sync_sheet(db, main.sport_students(db, sport))   # recommendations may have moved
        return f"new model live — {verdict}"
    return f"kept the live model — {verdict}"


def maintenance(db):
    expire_videos(db)
    for sport in sc.sport_names():
        log.info("training %s: %s", sport, train_sport(db, sport))
    # rows that were never computed (sheet set up after students enrolled) get built here
    main.sync_sheet(db, db.scalars(select(Student).where(Student.sheet_row.is_(None))).all())
    # and the people sheets catch up on any push that failed. Not the coaches sheet: its
    # Admin column comes from ADMIN_EMAILS, which only the website needs to have set
    main.sync_people(db, "profiles", "achievements")


# --------------------------------------------------------------------------- #

def run(once=False):
    main.init_db()
    caps = capabilities()
    log.info("worker on %s — storage: %s", platform.node(), storage.backend())
    log.info("  drill videos (MediaPipe): %s", caps["poseDetail"] if caps["pose"] else f"OFF — {caps['poseDetail']}")
    log.info("  match footage (YOLO):     %s", caps["matchDetail"] if caps["match"] else f"OFF — {caps['matchDetail']}")

    last_maintenance = None
    while True:
        db = SessionLocal()
        try:
            heartbeat(db, caps)
            recover(db)
            work_queue(db, caps)
            if once or last_maintenance is None or utcnow() - last_maintenance >= MAINTENANCE_EVERY:
                heartbeat(db, caps, "training")
                maintenance(db)
                heartbeat(db, caps)
                last_maintenance = utcnow()
        except Exception:  # noqa: BLE001 — a network blip must not end a two-hour session
            log.exception("pass failed; trying again shortly")
        finally:
            db.close()
        if once:
            return
        time.sleep(POLL_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Analyse queued videos and train the model.")
    parser.add_argument("--once", action="store_true", help="one pass, then exit")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s  %(message)s", datefmt="%H:%M:%S",
                        stream=sys.stdout)
    try:
        run(once=args.once)
    except KeyboardInterrupt:
        print("\nStopped. Anything half-done will be picked up next time.")
