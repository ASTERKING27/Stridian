"""
Match-footage analysis: YOLO person detection + ByteTrack over every player.

This is the second analysis lane. The MediaPipe lane (video.py) looks at one athlete
doing a drill and judges *technique*. This lane takes a full match or a snippet, finds
and follows every player in it, and measures *what they did in the game*. The coach
then clicks the player they care about, so there is no ball detector: knowing who to
follow comes from the person who knows the squad.

Only the worker computer runs this file (it needs OpenCV and PyTorch). The maths that
turns tracked positions into metrics lives in match_metrics.py, which the web server
also uses to re-derive everything when a coach calibrates the pitch.

Ultralytics is an optional dependency (it pulls in PyTorch). Without it the worker
simply leaves match clips queued for a computer that has it installed.
"""

from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

# re-exported so existing callers (and tests) can keep using match_video.X
from match_metrics import (MIN_RATE_SECONDS, aggregate, build_track_metrics,  # noqa: F401
                           calibrated_metrics, foot_point, make_homography,
                           movement_metrics, recompute, to_pitch, track_metrics)

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
# The plain detector, not the pose model: only the boxes are used here, and the pose model
# misses players the size they are in a wide shot (0 of ~20 in broadcast frames, where
# this finds them all).
DETECT_MODEL = MODEL_DIR / "yolo11n.pt"
IMGSZ = 1280            # 640 shrinks a 1080p frame 3x, and distant players with it
RELEASE = "https://github.com/ultralytics/assets/releases/download/v8.3.0"

SAMPLE_FPS = 5          # ByteTrack copes fine at 5 fps and it keeps a long clip tractable
MAX_FRAMES = 900        # hard ceiling: 3 minutes of play at the sample rate
MAX_TRACKS_KEPT = 30    # a squad plus officials; the rest is detection noise
MIN_TRACK_SECONDS = 2.0
MIN_TRACK_SHARE = 0.06  # seen in at least 6% of sampled frames
FRAME_CHOICES = 16      # stills kept for calibration, spread through the clip


# --------------------------------------------------------------------------- #
# Model availability
# --------------------------------------------------------------------------- #

def _ensure(path):
    if path.exists() and path.stat().st_size > 1_000_000:
        return True
    MODEL_DIR.mkdir(exist_ok=True)
    try:
        import urllib.request

        urllib.request.urlretrieve(f"{RELEASE}/{path.name}", path)
        return path.exists()
    except Exception:
        path.unlink(missing_ok=True)
        return False


def backend_status():
    try:
        import ultralytics  # noqa: F401
    except Exception:
        return {
            "available": False,
            "detail": "ultralytics is not installed — run: pip install -r requirements-match.txt",
        }
    if not _ensure(DETECT_MODEL):
        return {
            "available": False,
            "detail": f"YOLO weights missing. Download {RELEASE}/{DETECT_MODEL.name} to {DETECT_MODEL}.",
        }
    return {"available": True, "detail": "YOLO11n + ByteTrack"}


# --------------------------------------------------------------------------- #
# The pipeline
# --------------------------------------------------------------------------- #

def analyse_match(path, attack_direction="right", keyframe_path=None, family="field",
                  frames_dir=None):
    """Track every player in the clip. Never raises — returns a status dict.

    With `frames_dir`, it also saves FRAME_CHOICES stills from across the clip (plus the
    keyframe) there, so the coach can calibrate on a moment where the marking they need
    is fully in view."""
    status = backend_status()
    if not status["available"]:
        return {"status": "unavailable", "message": status["detail"], "tracks": []}

    from ultralytics import YOLO

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        return {"status": "failed", "message": "Could not open the video file.", "tracks": []}

    try:
        src_fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
        if src_fps <= 0:
            src_fps = 25.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        step = max(1, round(src_fps / SAMPLE_FPS))

        model = YOLO(str(DETECT_MODEL))

        raw = defaultdict(list)     # track id -> [(t, cx, cy, box_h)]
        frame_boxes, frames_kept = {}, {}
        sampled_at = []             # frame index of every sampled frame
        index = sampled = 0

        while sampled < MAX_FRAMES:
            ok, frame = cap.read()
            if not ok:
                break
            if index % step:
                index += 1
                continue

            t = round(index / src_fps, 3)
            sampled_at.append(index)
            # conf 0.1 on purpose: ByteTrack uses the weak boxes to keep a partly hidden
            # player's track going, and only starts new tracks from confident ones
            result = model.track(frame, persist=True, classes=[0], conf=0.1,
                                 imgsz=IMGSZ, tracker="bytetrack.yaml", verbose=False)[0]

            boxes = getattr(result, "boxes", None)
            if boxes is not None and boxes.id is not None:
                ids = boxes.id.int().cpu().tolist()
                xywhn = boxes.xywhn.cpu().numpy()
                here = []
                for tid, (cx, cy, bw, bh) in zip(ids, xywhn):
                    raw[tid].append((t, float(cx), float(cy), float(bh)))
                    here.append((tid, float(cx), float(cy), float(bw), float(bh)))
                frame_boxes[index] = here
                frames_kept[index] = len(here)

            index += 1
            sampled += 1

        if sampled == 0:
            return {"status": "failed", "message": "The video had no readable frames.", "tracks": []}

        duration = (total / src_fps) if total else (index / src_fps)

        keep = {
            tid: s for tid, s in raw.items()
            if len(s) >= 3
            and (s[-1][0] - s[0][0]) >= MIN_TRACK_SECONDS
            and len(s) / sampled >= MIN_TRACK_SHARE
        }
        keep = dict(sorted(keep.items(), key=lambda kv: -len(kv[1]))[:MAX_TRACKS_KEPT])

        base = {
            "fps": round(src_fps, 2), "durationSec": round(duration, 2),
            "framesSampled": sampled, "attackDirection": attack_direction,
        }

        if not keep:
            return {
                **base, "status": "done",
                "message": f"Sampled {sampled} frames but followed no player for long enough. "
                           "A wider, steadier shot with players clearly visible works best.",
                "tracks": [], "keyframeBoxes": [],
            }

        team_mean_x = float(np.mean([x for s in keep.values() for _t, x, _y, _h in s]))

        tracks = []
        for tid, samples in keep.items():
            metrics, context = build_track_metrics(
                samples, team_mean_x, attack_direction, family=family)
            if not metrics:
                continue
            tracks.append({
                "trackId": int(tid),
                "metrics": metrics,
                "context": context,
                "firstSeen": round(samples[0][0], 1),
                "lastSeen": round(samples[-1][0], 1),
                # kept so calibration can re-derive everything without re-running the model
                "samples": [[round(t, 3), round(x, 4), round(y, 4), round(h, 4)]
                            for t, x, y, h in samples],
                "path": [[round(x, 3), round(y, 3)] for _t, x, y, _h in samples[::2]][:120],
            })
        tracks.sort(key=lambda t: -t["context"]["trackedSeconds"])

        keyframe_boxes = []
        if frames_kept:
            best_index = max(frames_kept, key=lambda i: frames_kept[i])
            kept_ids = set(keep)
            keyframe_boxes = [
                {"trackId": int(tid), "x": round(cx - bw / 2, 4), "y": round(cy - bh / 2, 4),
                 "w": round(bw, 4), "h": round(bh, 4)}
                for tid, cx, cy, bw, bh in frame_boxes[best_index] if tid in kept_ids
            ]
            if keyframe_path:
                _write_frames(path, {best_index: keyframe_path})

        frames, frames_start = [], None
        if frames_dir and frames_kept:
            n = len(sampled_at)
            count = min(FRAME_CHOICES, n)
            picks = sorted({sampled_at[round(i * (n - 1) / max(1, count - 1))]
                            for i in range(count)} | {best_index})
            targets = {i: Path(frames_dir) / f"frame-{k}.jpg" for k, i in enumerate(picks)}
            written = _write_frames(path, targets)
            kept_picks = [i for i in picks if i in written]
            frames = [{"t": round(i / src_fps, 2), "path": str(targets[i])} for i in kept_picks]
            if best_index in kept_picks:
                frames_start = kept_picks.index(best_index)

        return {
            **base, "status": "done",
            "message": f"Followed {len(tracks)} players across {sampled} sampled frames.",
            "teamMeanX": round(team_mean_x, 3),
            "tracks": tracks,
            "keyframeBoxes": keyframe_boxes,
            "frames": frames,
            "framesStart": frames_start,
        }
    finally:
        cap.release()


def _write_frames(video_path, targets):
    """Save {frame index: path} unannotated — the UI draws the clickable boxes and the
    calibration points over them. Returns the indices actually written."""
    cap = cv2.VideoCapture(str(video_path))
    written = set()
    try:
        for index in sorted(targets):
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                continue
            h, w = frame.shape[:2]
            if w > 1280:
                frame = cv2.resize(frame, (1280, int(h * 1280 / w)))
            if cv2.imwrite(str(targets[index]), frame, [cv2.IMWRITE_JPEG_QUALITY, 85]):
                written.add(index)
    finally:
        cap.release()
    return written
