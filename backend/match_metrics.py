"""
Match-footage maths: everything that turns tracked positions into metrics.

Split out of match_video.py so the web server can use it without OpenCV, PyTorch or
a model file. The worker runs YOLO over the video and stores raw samples per track;
the server re-derives metrics from those samples whenever a coach calibrates the
pitch. Both sides go through the functions here, so the numbers always agree.

Two layers of measurement:

1. **Scale-free** — distance and speed divided by each player's own bounding-box
   height. Always available, comparable between players in the same clip and across
   zoom levels, but not comparable to any published benchmark.

2. **Calibrated** — once a coach has marked four known points on the pitch, a
   homography turns pixel positions into metres on the ground plane. Distance per
   minute, top speed in km/h, and distance above the high-speed-running and sprint
   thresholds then mean the same thing they mean on a GPS report.
"""

import math

import numpy as np

from sports_config import SPEED_THRESHOLDS

SPRINT_BH_PER_SEC = 2.8   # body-heights/sec that counts as a sprint (scale-free layer)
MOVING_BH_PER_SEC = 0.55  # above this the player is working rather than standing
ACCEL_THRESHOLD = 3.0     # m/s^2, the usual cut for a "high acceleration" effort

# Per-minute rates are only honest over a reasonable sample. A ten-second highlight of
# somebody sprinting extrapolates to several hundred metres per minute and would score
# a perfect 100 against an elite benchmark, so below this the rate metrics are simply
# not reported — the engine then treats them as unmeasured and lowers confidence, which
# is the correct answer rather than a flattering one. Peak speed is exempt: a peak is a
# peak however short the clip.
MIN_RATE_SECONDS = 45.0


# --------------------------------------------------------------------------- #
# Pitch calibration
# --------------------------------------------------------------------------- #

def _normaliser(points):
    """Hartley normalisation: centre the points and scale them to mean distance √2.

    Image points live in 0-1 and pitch points in tens of metres; solving with both raw
    would be badly conditioned. Returns None when every point is the same point.
    """
    centre = points.mean(axis=0)
    spread = np.sqrt(((points - centre) ** 2).sum(axis=1)).mean()
    if spread < 1e-12:
        return None
    s = math.sqrt(2) / spread
    return np.array([[s, 0, -s * centre[0]], [0, s, -s * centre[1]], [0, 0, 1.0]])


def make_homography(image_points, world_points):
    """Map normalised image coordinates onto real-world metres on the ground plane.

    `image_points` are four (x, y) pairs in 0-1 frame coordinates, in the same order as
    `world_points`, which are four (X, Y) pairs in metres. Returns None if the four
    points are degenerate (collinear, or two of them coincident), which is the usual
    result of a mis-click and must not be treated as a valid calibration.

    Plain direct linear transform with numpy — for exactly four points this is the
    same answer cv2.findHomography gives, without needing OpenCV on the server.
    """
    if not image_points or not world_points or len(image_points) != 4 or len(world_points) != 4:
        return None
    src = np.array(image_points, dtype=np.float64)
    dst = np.array(world_points, dtype=np.float64)
    if len({tuple(p) for p in src}) < 4 or len({tuple(p) for p in dst}) < 4:
        return None

    t_src, t_dst = _normaliser(src), _normaliser(dst)
    if t_src is None or t_dst is None:
        return None
    ones = np.ones((4, 1))
    a = (t_src @ np.hstack([src, ones]).T).T
    b = (t_dst @ np.hstack([dst, ones]).T).T

    rows = []
    for (x, y, _), (u, v, _) in zip(a, b):
        rows.append([-x, -y, -1, 0, 0, 0, u * x, u * y, u])
        rows.append([0, 0, 0, -x, -y, -1, v * x, v * y, v])
    _u, singular, vt = np.linalg.svd(np.array(rows))

    # three collinear points leave the system short of rank 8: no unique plane mapping
    if singular[-1] < 1e-9 * singular[0]:
        return None
    H = np.linalg.inv(t_dst) @ vt[-1].reshape(3, 3) @ t_src
    if abs(H[2, 2]) < 1e-12:
        return None
    H = H / H[2, 2]
    if not np.isfinite(H).all() or abs(np.linalg.det(H)) < 1e-12:
        return None
    return H


def to_pitch(H, x, y):
    """One image point (normalised) to metres. Returns None behind the horizon."""
    v = H @ np.array([x, y, 1.0])
    if abs(v[2]) < 1e-9:
        return None
    return float(v[0] / v[2]), float(v[1] / v[2])


def foot_point(sample):
    """Players stand on the ground plane, so the bottom of the box is what maps."""
    _t, cx, cy, bh = sample
    return cx, cy + bh / 2


def _smooth(values, window=3):
    """Median filter. Tracking jitter otherwise shows up as a fake top speed."""
    if len(values) < window:
        return list(values)
    out = []
    half = window // 2
    for i in range(len(values)):
        lo, hi = max(0, i - half), min(len(values), i + half + 1)
        out.append(float(np.median(values[lo:hi])))
    return out


# --------------------------------------------------------------------------- #
# Metric maths — pure functions, testable without a model or a video
# --------------------------------------------------------------------------- #

def _speeds(samples):
    """Body-heights per second between consecutive samples of one track."""
    out = []
    for (t0, x0, y0, h0), (t1, x1, y1, h1) in zip(samples, samples[1:]):
        dt = t1 - t0
        scale = (h0 + h1) / 2
        if dt <= 0 or scale <= 1e-6:
            continue
        step = math.hypot(x1 - x0, y1 - y0) / scale
        out.append((step / dt, step, dt))
    return out


def _count_bursts(flags):
    """One unbroken run above a threshold counts once, however many samples long."""
    count, inside = 0, False
    for flag in flags:
        if flag and not inside:
            count += 1
            inside = True
        elif not flag:
            inside = False
    return count


def movement_metrics(samples, team_mean_x, attack_direction="right"):
    """The scale-free layer: everything divided by the player's own body height."""
    if len(samples) < 3:
        return {}
    duration = samples[-1][0] - samples[0][0]
    if duration <= 0:
        return {}

    speeds = _speeds(samples)
    if not speeds:
        return {}

    values = [s for s, _, _ in speeds]
    travelled = sum(step for _, step, _ in speeds)
    moving_time = sum(dt for s, _, dt in speeds if s >= MOVING_BH_PER_SEC)
    total_time = sum(dt for _, _, dt in speeds)

    xs = [x for _t, x, _y, _h in samples]
    minutes = duration / 60
    sign = 1 if attack_direction == "right" else -1
    advanced = 50 + (float(np.mean(xs)) - team_mean_x) * 100 * sign

    long_enough = duration >= MIN_RATE_SECONDS
    metrics = {
        "matchDistance": round(travelled / minutes, 1) if long_enough else None,
        "matchTopSpeed": round(float(np.percentile(values, 95)), 2),
        "matchSprints": round(_count_bursts([s >= SPRINT_BH_PER_SEC for s, _, _ in speeds]) / minutes, 2)
                        if long_enough else None,
        "matchWorkRate": round(100 * moving_time / total_time, 1) if total_time > 0 else None,
        "matchWidth": round((max(xs) - min(xs)) * 100, 1),
        "matchAdvanced": round(max(0.0, min(100.0, advanced)), 1),
    }
    metrics["matchDeepness"] = round(100 - metrics["matchAdvanced"], 1)
    if metrics["matchWorkRate"] is not None:
        metrics["matchStationary"] = round(100 - metrics["matchWorkRate"], 1)
    return {k: v for k, v in metrics.items() if v is not None}


# The scale-free layer on its own, which is what most callers and tests want.
track_metrics = movement_metrics


def calibrated_metrics(samples, H, family="field"):
    """The metres-and-km/h layer. Only produced once the pitch has been marked out."""
    if H is None or len(samples) < 3:
        return {}

    pitch = []
    for s in samples:
        mapped = to_pitch(H, *foot_point(s))
        if mapped is not None:
            pitch.append((s[0], mapped[0], mapped[1]))
    if len(pitch) < 3:
        return {}

    duration = pitch[-1][0] - pitch[0][0]
    if duration <= 0:
        return {}

    steps, dts = [], []
    for (t0, x0, y0), (t1, x1, y1) in zip(pitch, pitch[1:]):
        dt = t1 - t0
        if dt <= 0:
            continue
        steps.append(math.hypot(x1 - x0, y1 - y0))
        dts.append(dt)
    if not steps:
        return {}

    raw_speeds = [d / dt for d, dt in zip(steps, dts)]          # m/s
    speeds = _smooth(raw_speeds)
    kmh = [v * 3.6 for v in speeds]

    thresholds = SPEED_THRESHOLDS[family]
    hsr_m = sum(d for d, v in zip(steps, kmh) if v >= thresholds["hsr"])
    sprint_m = sum(d for d, v in zip(steps, kmh) if v >= thresholds["sprint"])

    accels = [abs(speeds[i + 1] - speeds[i]) / dts[i + 1]
              for i in range(len(speeds) - 1) if dts[i + 1] > 0]

    minutes = duration / 60
    if minutes <= 0:
        return {}

    out = {
        # a peak is meaningful however short the clip
        "matchTopSpeedKmh": round(float(np.percentile(kmh, 95)), 1),
        "_calibrated": {
            "totalMetres": round(sum(steps), 1),
            "hsrMetres": round(hsr_m, 1),
            "sprintMetres": round(sprint_m, 1),
            "hsrThresholdKmh": thresholds["hsr"],
            "sprintThresholdKmh": thresholds["sprint"],
            "ratesReported": duration >= MIN_RATE_SECONDS,
            "minSecondsForRates": MIN_RATE_SECONDS,
        },
    }
    if duration >= MIN_RATE_SECONDS:
        out.update({
            "matchMetresPerMin": round(sum(steps) / minutes, 1),
            "matchHsrPerMin": round(hsr_m / minutes, 2),
            "matchSprintMetresPerMin": round(sprint_m / minutes, 2),
            "matchAccelPerMin": round(
                _count_bursts([a >= ACCEL_THRESHOLD for a in accels]) / minutes, 2),
        })
    return out


def build_track_metrics(samples, team_mean_x, attack_direction="right", height_cm=None,
                        H=None, family="field"):
    """Everything measurable about one track, in one dict."""
    metrics = movement_metrics(samples, team_mean_x, attack_direction)
    if not metrics:
        return {}, {}

    calibrated = calibrated_metrics(samples, H, family)
    calibration_context = calibrated.pop("_calibrated", None)
    metrics.update(calibrated)

    duration = samples[-1][0] - samples[0][0]
    xs = [x for _t, x, _y, _h in samples]
    ys = [y for _t, _x, y, _h in samples]
    body_height = float(np.median([h for *_r, h in samples]))

    context = {
        "trackedSeconds": round(duration, 1),
        "samples": len(samples),
        "avgX": round(float(np.mean(xs)), 3),
        "avgY": round(float(np.mean(ys)), 3),
        "verticalSpread": round((max(ys) - min(ys)) * 100, 1),
        "bodyHeightFrac": round(body_height, 3),
        "calibrated": calibration_context is not None,
    }
    if calibration_context:
        context.update(calibration_context)
    elif height_cm:
        # no pitch marked out: fall back to the player's own height for a rough metre figure
        speeds = _speeds(samples)
        travelled = sum(step for _, step, _ in speeds)
        context["approxMetres"] = round(travelled * (height_cm / 100))
        context["approxTopSpeedMps"] = round(
            float(np.percentile([s for s, _, _ in speeds], 95)) * (height_cm / 100), 1)
    return metrics, context


def aggregate(per_clip):
    """Average a student's metrics across clips, weighted by how long they were tracked."""
    if not per_clip:
        return {}
    keys = {k for m in per_clip for k in m if not k.startswith("_")}
    out = {}
    for key in keys:
        pairs = [
            (m[key], max(m.get("_context", {}).get("trackedSeconds", 1), 1))
            for m in per_clip if m.get(key) is not None
        ]
        if not pairs:
            continue
        total = sum(w for _v, w in pairs)
        out[key] = round(sum(v * w for v, w in pairs) / total, 2)
    return out


def recompute(clip_payload, image_points=None, world_points=None, family="field",
              attack_direction="right"):
    """Re-derive every track's metrics from the stored samples.

    With four points it applies a homography and produces real-world units; with none it
    rebuilds the scale-free metrics, which is how calibration gets undone. Either way no
    video is re-read and no model runs — the samples captured during tracking are all it
    needs, which makes marking out the pitch instant rather than a second upload.
    """
    H = None
    if image_points and world_points:
        H = make_homography(image_points, world_points)
        if H is None:
            return None, ("Those four points don't describe a plane — pick corners that "
                          "form a quadrilateral, not a line.")

    tracks = clip_payload.get("tracks") or []
    if not tracks:
        return [], "Nothing to recompute."

    all_samples = [tuple(s) for t in tracks for s in t["samples"]]
    team_mean_x = float(np.mean([s[1] for s in all_samples])) if all_samples else 0.5

    out = []
    for track in tracks:
        samples = [tuple(s) for s in track["samples"]]
        metrics, context = build_track_metrics(
            samples, team_mean_x, attack_direction, H=H, family=family)
        out.append({**track, "metrics": metrics, "context": context})

    units = "real-world units" if H is not None else "scale-free units"
    return out, f"Recalculated {len(out)} players in {units}."
