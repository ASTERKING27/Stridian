"""
Pose-based video analysis.

Pipeline: decode the clip with OpenCV -> run MediaPipe pose on sampled frames ->
turn the landmark time-series into coachable numbers (jump height, joint angles,
left/right symmetry, trunk stability, movement speed, stride cadence).

Two MediaPipe APIs exist in the wild and this module supports both:
  * `mediapipe.solutions.pose` - the classic one. The model ships inside the wheel,
    so it works with no internet. Available up to mediapipe 0.10.14 (what
    requirements.txt pins).
  * `mediapipe.tasks.vision.PoseLandmarker` - the current one. Needs a .task model
    file, downloaded once to backend/models/ on first use.

If neither is importable the rest of the app still runs; the upload endpoint just
reports status "unavailable" with an explanation instead of crashing.
"""

import contextlib
import math
import warnings
from pathlib import Path

import cv2
import numpy as np


@contextlib.contextmanager
def _quiet_nan():
    """np.nanmean over an all-NaN row warns loudly; an undetected frame is expected here."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        with np.errstate(invalid="ignore", divide="ignore"):
            yield

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "pose_landmarker_lite.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/pose_landmarker/"
    "pose_landmarker_lite/float16/1/pose_landmarker_lite.task"
)

MAX_FRAMES = 300  # sampled evenly across the clip - keeps a 2-minute video under ~20s

# BlazePose 33-point topology (identical in both MediaPipe APIs)
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

SKELETON = [
    (L_SHOULDER, R_SHOULDER), (L_SHOULDER, L_ELBOW), (L_ELBOW, L_WRIST),
    (R_SHOULDER, R_ELBOW), (R_ELBOW, R_WRIST), (L_SHOULDER, L_HIP),
    (R_SHOULDER, R_HIP), (L_HIP, R_HIP), (L_HIP, L_KNEE), (L_KNEE, L_ANKLE),
    (R_HIP, R_KNEE), (R_KNEE, R_ANKLE),
]


# --------------------------------------------------------------------------- #
# MediaPipe backend selection
# --------------------------------------------------------------------------- #

def _legacy_backend():
    import mediapipe as mp

    if not hasattr(mp, "solutions"):
        return None
    pose = mp.solutions.pose.Pose(
        static_image_mode=False, model_complexity=1,
        min_detection_confidence=0.5, min_tracking_confidence=0.5,
    )

    def run(rgb, _timestamp_ms):
        res = pose.process(rgb)
        if not res.pose_landmarks:
            return None
        return [(p.x, p.y, p.visibility) for p in res.pose_landmarks.landmark]

    return run, pose.close, "mediapipe.solutions.pose"


def _ensure_task_model():
    if MODEL_PATH.exists():
        return True
    MODEL_DIR.mkdir(exist_ok=True)
    try:
        import urllib.request

        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        return MODEL_PATH.exists()
    except Exception:
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        return False


def _tasks_backend():
    import mediapipe as mp
    from mediapipe.tasks import python as mp_python
    from mediapipe.tasks.python import vision

    if not _ensure_task_model():
        raise RuntimeError(
            "MediaPipe's pose model file is missing and could not be downloaded. "
            f"Download {MODEL_URL} manually and save it as {MODEL_PATH}."
        )

    landmarker = vision.PoseLandmarker.create_from_options(
        vision.PoseLandmarkerOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(MODEL_PATH)),
            running_mode=vision.RunningMode.VIDEO,
            num_poses=1,
        )
    )

    def run(rgb, timestamp_ms):
        image = mp.Image(image_format=mp.ImageFormat.SRGB, data=np.ascontiguousarray(rgb))
        res = landmarker.detect_for_video(image, int(timestamp_ms))
        if not res.pose_landmarks:
            return None
        return [(p.x, p.y, getattr(p, "visibility", 1.0)) for p in res.pose_landmarks[0]]

    return run, landmarker.close, "mediapipe.tasks.PoseLandmarker"


def get_backend():
    """(run_fn, close_fn, name) or (None, None, reason-string)."""
    try:
        import mediapipe  # noqa: F401
    except Exception as exc:
        return None, None, f"mediapipe is not installed ({exc})"

    legacy = _legacy_backend()
    if legacy:
        return legacy
    try:
        return _tasks_backend()
    except Exception as exc:
        return None, None, str(exc)


def backend_status():
    run, close, name = get_backend()
    if run is None:
        return {"available": False, "detail": name}
    if close:
        close()
    return {"available": True, "detail": name}


# --------------------------------------------------------------------------- #
# Geometry helpers - pure functions, unit-testable without any video
# --------------------------------------------------------------------------- #

def angle_at(a, b, c):
    """Interior angle in degrees at point b, formed by a-b-c. NaN if any point is missing."""
    a, b, c = np.asarray(a, float), np.asarray(b, float), np.asarray(c, float)
    if np.isnan(a).any() or np.isnan(b).any() or np.isnan(c).any():
        return math.nan
    ba, bc = a - b, c - b
    na, nc = np.linalg.norm(ba), np.linalg.norm(bc)
    if na == 0 or nc == 0:
        return math.nan
    cosine = float(np.clip(np.dot(ba, bc) / (na * nc), -1.0, 1.0))
    return math.degrees(math.acos(cosine))


def _nanmin(arr):
    arr = np.asarray(arr, float)
    return float(np.nanmin(arr)) if np.any(~np.isnan(arr)) else None


def _nanmax(arr):
    arr = np.asarray(arr, float)
    return float(np.nanmax(arr)) if np.any(~np.isnan(arr)) else None


def _count_peaks(signal, min_prominence):
    """Simple local-maximum counter - enough for stride cadence, no SciPy needed."""
    sig = np.asarray(signal, float)
    valid = sig[~np.isnan(sig)]
    if valid.size < 5:
        return 0
    peaks = 0
    for i in range(1, len(sig) - 1):
        a, b, c = sig[i - 1], sig[i], sig[i + 1]
        if np.isnan(a) or np.isnan(b) or np.isnan(c):
            continue
        if b > a and b >= c and (b - min(a, c)) >= min_prominence:
            peaks += 1
    return peaks


def compute_metrics(points, fps, height_cm=None):
    """Turn a landmark time-series into metrics.

    `points` is an (n_frames, 33, 2) float array of normalised x/y coordinates
    (y grows downwards, as in image space). Missing frames are NaN.
    """
    with _quiet_nan():
        return _compute_metrics(points, fps, height_cm)


def _compute_metrics(points, fps, height_cm=None):
    n = len(points)
    if n == 0 or fps <= 0:
        return {}

    xs, ys = points[:, :, 0], points[:, :, 1]

    mid_hip_y = np.nanmean(ys[:, [L_HIP, R_HIP]], axis=1)
    mid_hip_x = np.nanmean(xs[:, [L_HIP, R_HIP]], axis=1)
    mid_ankle_y = np.nanmean(ys[:, [L_ANKLE, R_ANKLE]], axis=1)
    mid_shoulder_y = np.nanmean(ys[:, [L_SHOULDER, R_SHOULDER]], axis=1)
    mid_shoulder_x = np.nanmean(xs[:, [L_SHOULDER, R_SHOULDER]], axis=1)

    # Body span in normalised units: nose to mid-ankle. Used to convert to real units.
    body_span = np.nanmedian(mid_ankle_y - ys[:, NOSE])
    cm_per_unit = None
    if height_cm and body_span and not math.isnan(body_span) and body_span > 0.05:
        # nose-to-ankle is roughly 88% of standing height
        cm_per_unit = (height_cm * 0.88) / body_span

    metrics = {}

    # ---- vertical displacement / jump -------------------------------------
    if np.any(~np.isnan(mid_hip_y)):
        grounded = float(np.nanpercentile(mid_hip_y, 90))   # lowest body position
        highest = float(np.nanmin(mid_hip_y))               # highest body position
        rise_units = max(0.0, grounded - highest)
        metrics["verticalRiseBodySpans"] = round(rise_units / body_span, 3) if body_span and body_span > 0 else None
        if cm_per_unit:
            metrics["jumpHeightCm"] = round(rise_units * cm_per_unit, 1)

        # airborne = hip is in the top 40% of the observed rise
        if rise_units > 0.01:
            threshold = grounded - 0.6 * rise_units
            airborne = int(np.sum(mid_hip_y < threshold))
            metrics["airtimeSec"] = round(airborne / fps, 2)

    # ---- joint angles -----------------------------------------------------
    knee_l = np.array([angle_at(points[i, L_HIP], points[i, L_KNEE], points[i, L_ANKLE]) for i in range(n)])
    knee_r = np.array([angle_at(points[i, R_HIP], points[i, R_KNEE], points[i, R_ANKLE]) for i in range(n)])
    elbow_l = np.array([angle_at(points[i, L_SHOULDER], points[i, L_ELBOW], points[i, L_WRIST]) for i in range(n)])
    elbow_r = np.array([angle_at(points[i, R_SHOULDER], points[i, R_ELBOW], points[i, R_WRIST]) for i in range(n)])

    knee_mean = np.nanmean(np.vstack([knee_l, knee_r]), axis=0)
    metrics["kneeFlexionMinDeg"] = round(_nanmin(knee_mean), 1) if _nanmin(knee_mean) is not None else None
    metrics["kneeExtensionMaxDeg"] = round(_nanmax(knee_mean), 1) if _nanmax(knee_mean) is not None else None
    elbow_mean = np.nanmean(np.vstack([elbow_l, elbow_r]), axis=0)
    metrics["elbowFlexionMinDeg"] = round(_nanmin(elbow_mean), 1) if _nanmin(elbow_mean) is not None else None
    metrics["elbowExtensionMaxDeg"] = round(_nanmax(elbow_mean), 1) if _nanmax(elbow_mean) is not None else None

    # ---- left / right symmetry -------------------------------------------
    def _range(arr):
        lo, hi = _nanmin(arr), _nanmax(arr)
        return None if lo is None or hi is None else hi - lo

    rl, rr = _range(knee_l), _range(knee_r)
    if rl is not None and rr is not None and max(rl, rr) > 1e-6:
        metrics["kneeSymmetryPct"] = round(100.0 * (1 - abs(rl - rr) / max(rl, rr)), 1)
    el, er = _range(elbow_l), _range(elbow_r)
    if el is not None and er is not None and max(el, er) > 1e-6:
        metrics["armSymmetryPct"] = round(100.0 * (1 - abs(el - er) / max(el, er)), 1)

    # ---- trunk lean & stability ------------------------------------------
    lean = np.degrees(np.arctan2(mid_shoulder_x - mid_hip_x, np.abs(mid_hip_y - mid_shoulder_y) + 1e-9))
    if np.any(~np.isnan(lean)):
        metrics["trunkLeanAvgDeg"] = round(float(np.nanmean(np.abs(lean))), 1)
        spread = float(np.nanstd(lean))
        metrics["trunkStabilityPct"] = round(max(0.0, 100.0 - spread * 4.0), 1)

    # ---- horizontal movement ---------------------------------------------
    dx = np.abs(np.diff(mid_hip_x))
    travelled = float(np.nansum(dx))
    duration = n / fps
    if duration > 0 and body_span and body_span > 0:
        metrics["movementBodySpansPerSec"] = round((travelled / body_span) / duration, 2)
        if cm_per_unit:
            metrics["movementSpeedMps"] = round((travelled * cm_per_unit / 100.0) / duration, 2)

    # ---- stride cadence ---------------------------------------------------
    ankle_gap = np.abs(xs[:, L_ANKLE] - xs[:, R_ANKLE])
    steps = _count_peaks(ankle_gap, min_prominence=0.02)
    if duration > 0 and steps:
        metrics["strideCadencePerSec"] = round(steps / duration, 2)
        metrics["stepsDetected"] = steps

    return {k: v for k, v in metrics.items() if v is not None}


# --------------------------------------------------------------------------- #
# Interpretation
# --------------------------------------------------------------------------- #

READABLE = {
    "jumpHeightCm": ("Jump height", "cm", "Peak rise of the hips above their grounded position."),
    "verticalRiseBodySpans": ("Vertical rise", "body-spans", "Hip rise measured in body lengths - works even without a height on file."),
    "airtimeSec": ("Airtime", "sec", "Time spent near the top of the jump."),
    "kneeFlexionMinDeg": ("Deepest knee bend", "deg", "Smaller means a deeper loading position."),
    "kneeExtensionMaxDeg": ("Knee extension", "deg", "How fully the leg straightens at take-off."),
    "elbowFlexionMinDeg": ("Deepest elbow bend", "deg", "Relevant for throwing, spiking and bowling actions."),
    "elbowExtensionMaxDeg": ("Elbow extension", "deg", "How fully the arm extends through the action."),
    "kneeSymmetryPct": ("Leg symmetry", "%", "How evenly both legs worked. Under 80% often flags a dominant side."),
    "armSymmetryPct": ("Arm symmetry", "%", "How evenly both arms worked."),
    "trunkLeanAvgDeg": ("Average trunk lean", "deg", "Forward/sideways lean of the torso."),
    "trunkStabilityPct": ("Trunk stability", "%", "How steady the torso stayed. Higher is better."),
    "movementBodySpansPerSec": ("Movement rate", "body-spans/sec", "Horizontal travel speed, scale-free."),
    "movementSpeedMps": ("Movement speed", "m/s", "Estimated horizontal speed using the student's height."),
    "strideCadencePerSec": ("Stride cadence", "steps/sec", "Steps per second across the clip."),
    "stepsDetected": ("Steps detected", "steps", "Number of steps counted."),
}


def interpret(metrics, detection_rate):
    """Plain-language observations the coach can act on."""
    notes = []
    if detection_rate < 0.5:
        notes.append("The player was only detected in part of the clip - film from the side, "
                     "full body in frame, good lighting, and keep the camera still for better results.")

    sym = metrics.get("kneeSymmetryPct")
    if sym is not None:
        if sym < 80:
            notes.append(f"Legs worked unevenly ({sym}% symmetry) - worth checking for a dominant side or an old injury.")
        else:
            notes.append(f"Left and right legs worked evenly ({sym}% symmetry).")

    stab = metrics.get("trunkStabilityPct")
    if stab is not None and stab < 75:
        notes.append(f"Trunk was unsteady ({stab}%) - core stability work would show up directly in the results.")

    knee = metrics.get("kneeFlexionMinDeg")
    if knee is not None:
        if knee > 120:
            notes.append(f"Shallow knee bend ({knee} deg at the deepest point) - limits how much force can be put into the ground.")
        elif knee < 70:
            notes.append(f"Very deep knee bend ({knee} deg) - good loading depth, watch that it doesn't slow the movement down.")

    jump = metrics.get("jumpHeightCm")
    if jump is not None and jump > 5:
        notes.append(f"Estimated jump height {jump} cm from the hip trajectory (rough - a proper Vertec or force plate is more accurate).")

    cad = metrics.get("strideCadencePerSec")
    if cad is not None:
        notes.append(f"Stride cadence around {cad} steps/sec across the clip.")

    if not notes:
        notes.append("Clip processed, but nothing stood out. Longer clips showing a full movement give richer results.")
    return notes


# Each rule: (metric, test, finding, why it matters, what to train).
DRILL_RULES = [
    ("kneeSymmetryPct", lambda v: v < 85,
     "Legs are not sharing the load evenly",
     "A dominant side raises injury risk and caps how much force the weaker leg can put down.",
     "Single-leg work 2x/week — Bulgarian split squats, single-leg RDLs, single-leg box jumps. "
     "Start every set with the weaker side and match the reps on the strong side."),
    ("armSymmetryPct", lambda v: v < 85,
     "Arms are working unevenly",
     "Asymmetric arm action leaks energy and, in overhead sports, loads one shoulder harder.",
     "Unilateral pulls and presses, plus mirror drills filmed from the front so the athlete sees the difference."),
    ("trunkStabilityPct", lambda v: v < 75,
     "Trunk is unsteady through the movement",
     "Force made by the legs is lost if the torso gives way before it reaches the ground or the ball.",
     "Anti-rotation and anti-extension core work — Pallof press, dead bug, suitcase carry, plank variations. "
     "Three sets, quality over duration."),
    ("kneeFlexionMinDeg", lambda v: v > 120,
     "Shallow loading position",
     "Not enough knee bend means a short runway to build force, so jumps and first steps come out flat.",
     "Tempo goblet squats (3s down), ankle dorsiflexion mobility, and countermovement depth cues on jumps."),
    ("kneeExtensionMaxDeg", lambda v: v < 155,
     "Incomplete extension at take-off",
     "Leaving the last few degrees unused wastes the most powerful part of the range.",
     "Triple-extension work — trap-bar jumps, hip thrusts, pogo hops with a 'finish tall' cue."),
    ("trunkLeanAvgDeg", lambda v: v > 22,
     "Heavy trunk lean",
     "Excess lean shifts load onto the lower back and shortens the stride.",
     "Hip-flexor and thoracic mobility, plus posture cues on the run — 'tall chest, eyes level'."),
    ("strideCadencePerSec", lambda v: v < 2.4,
     "Low stride cadence",
     "A slow turnover usually means overstriding, which brakes on every step.",
     "Metronome runs at 2.8-3.0 steps/sec over 20-30m, plus A-skips and quick-feet ladder work."),
    ("jumpHeightCm", lambda v: v < 28,
     "Limited jump height in this clip",
     "Jump height tracks lower-body power, which shows up in sprinting and change of direction too.",
     "Plyometrics on fresh legs twice a week — box jumps, depth jumps, broad jumps — paired with heavy squats."),
]


def training_from_video(metrics, detection_rate=1.0):
    """Turn pose findings into corrective drills, matching the dashboard's plan format."""
    if detection_rate < 0.35:
        return [{
            "finding": "Not enough of the clip was usable",
            "why": f"A pose was detected in only {round(detection_rate * 100)}% of the sampled frames, "
                   "so the measurements are unreliable.",
            "drill": "Re-film side-on, whole body in frame, steady camera, good light, one person visible.",
            "metric": None, "value": None,
        }]

    out = []
    for key, failing, finding, why, drill in DRILL_RULES:
        value = metrics.get(key)
        if value is not None and failing(value):
            out.append({"finding": finding, "why": why, "drill": drill, "metric": key, "value": value})
    return out


# --------------------------------------------------------------------------- #
# Main entry point
# --------------------------------------------------------------------------- #

def analyse_video(path, height_cm=None, thumbnail_path=None, sport=None):
    """Run the full pipeline over one video file. Never raises - returns a status dict."""
    run, close, name = get_backend()
    if run is None:
        return {"status": "unavailable", "message": f"Pose analysis is not available: {name}", "metrics": {}}

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        if close:
            close()
        return {"status": "failed", "message": "Could not open the video file.", "metrics": {}}

    try:
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0:
            fps = 25.0
        step = max(1, total // MAX_FRAMES) if total > 0 else 1

        frames, detected = [], 0
        best_frame, best_y, index = None, None, 0

        while True:
            ok, frame = cap.read()
            if not ok:
                break
            if index % step != 0:
                index += 1
                continue

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            lms = run(rgb, (index / fps) * 1000.0)

            if lms:
                detected += 1
                arr = np.array([[p[0], p[1]] for p in lms], dtype=float)
                hip_y = float(np.nanmean([arr[L_HIP, 1], arr[R_HIP, 1]]))
                if best_y is None or hip_y < best_y:      # highest position in the clip
                    best_y, best_frame = hip_y, (frame.copy(), arr)
            else:
                arr = np.full((33, 2), np.nan)
            frames.append(arr)
            index += 1

        sampled = len(frames)
        if sampled == 0:
            return {"status": "failed", "message": "The video had no readable frames.", "metrics": {}}

        points = np.stack(frames)
        effective_fps = fps / step
        detection_rate = detected / sampled

        metrics = compute_metrics(points, effective_fps, height_cm) if detected else {}

        # sport-specific technique on top of the general movement measures
        sport_block = {}
        if detected and sport:
            import pose_sports

            sport_block = pose_sports.analyse(sport, points, effective_fps, height_cm)

        if thumbnail_path and best_frame is not None:
            _write_thumbnail(best_frame[0], best_frame[1], thumbnail_path)

        return {
            "status": "done",
            "message": f"Analysed {sampled} sampled frames with {name}.",
            "fps": round(fps, 2),
            "durationSec": round(total / fps, 2) if total else round(sampled * step / fps, 2),
            "framesTotal": total or sampled * step,
            "framesSampled": sampled,
            "framesDetected": detected,
            "detectionRate": round(detection_rate, 3),
            "metrics": metrics,
            "readable": {k: READABLE.get(k, (k, "", ""))[0] for k in metrics},
            "units": {k: READABLE.get(k, (k, "", ""))[1] for k in metrics},
            "explain": {k: READABLE.get(k, (k, "", ""))[2] for k in metrics},
            "observations": interpret(metrics, detection_rate),
            "drills": training_from_video(metrics, detection_rate)
                      + (sport_block.get("drills", []) if detection_rate >= 0.35 else []),
            "sportSpecific": sport_block,
        }
    finally:
        cap.release()
        if close:
            try:
                close()
            except Exception:
                pass


def _write_thumbnail(frame, landmarks, out_path):
    """Save the peak frame with the detected skeleton drawn over it."""
    try:
        h, w = frame.shape[:2]
        pts = [(int(x * w), int(y * h)) for x, y in landmarks]
        for a, b in SKELETON:
            if not (np.isnan(landmarks[a]).any() or np.isnan(landmarks[b]).any()):
                cv2.line(frame, pts[a], pts[b], (60, 220, 130), 2, cv2.LINE_AA)
        for i, p in enumerate(pts):
            if not np.isnan(landmarks[i]).any():
                cv2.circle(frame, p, 3, (237, 111, 47), -1, cv2.LINE_AA)
        scale = 640 / max(w, 1)
        if scale < 1:
            frame = cv2.resize(frame, (640, int(h * scale)))
        cv2.imwrite(str(out_path), frame)
    except Exception:
        pass
