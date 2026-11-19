"""
What a sport's analyser reads a drill clip with: the landmarks MediaPipe finds on a body,
and the handful of measurements every analyser needs.

A clip arrives as `points`, an (n_frames, 33, 2) array of x/y in 0-1 image coordinates
(y grows downwards); a frame with nobody in it is NaN. Each sport's analyser.py finds the
moment that matters in it — the frame where the ankle is fastest, or the wrist is highest —
measures a few angles and heights there, and turns anything outside the expected band
into a drill.

numpy only: this is imported by the website too, which has no OpenCV.

**Two honest limits, stated here and surfaced in the app:**

* These are 2D measurements from a single camera. A joint angle is only accurate when
  the movement happens roughly side-on to the lens; rotate the athlete 45 degrees and
  the same angle reads several degrees off. Film square to the action.
* The ICC's 15-degree elbow limit is adjudicated with 3D motion capture in an
  accredited lab. What the cricket analyser computes is an *indicator* to decide whether
  a proper test is worth arranging — it is not, and cannot be, a ruling.
"""

import contextlib
import math
import warnings

import numpy as np

# BlazePose 33-point topology (identical in both MediaPipe APIs)
NOSE = 0
L_SHOULDER, R_SHOULDER = 11, 12
L_ELBOW, R_ELBOW = 13, 14
L_WRIST, R_WRIST = 15, 16
L_HIP, R_HIP = 23, 24
L_KNEE, R_KNEE = 25, 26
L_ANKLE, R_ANKLE = 27, 28

CAMERA_NOTE = ("Angles are measured from a single camera in 2D — film square to the "
               "action, or they read several degrees off.")


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


@contextlib.contextmanager
def quiet():
    """An undetected frame is expected here, and numpy's nan-functions say so very loudly."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        yield


def mid(points, frame, a, b):
    """The point halfway between two landmarks in one frame, or None if either is missing."""
    pair = points[frame, [a, b]]
    if np.isnan(pair).any():
        return None
    return tuple(np.nanmean(pair, axis=0))


def body_span(points):
    """Nose-to-ankle in normalised units: the ruler for every height an analyser reports."""
    with quiet():
        ankles = np.nanmean(points[:, [L_ANKLE, R_ANKLE], 1], axis=1)
        span = np.nanmedian(ankles - points[:, NOSE, 1])
    return float(span) if span and not math.isnan(span) and span > 0.05 else None


def speed_series(points, joint):
    """Per-frame speed of one landmark, in normalised units per frame."""
    xy = points[:, joint]
    deltas = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    return np.concatenate([[np.nan], deltas])


def fastest_frame(points, joints):
    """The frame where any of these landmarks is moving quickest — the moment of action."""
    best_frame, best_speed = None, -1.0
    for joint in joints:
        series = speed_series(points, joint)
        if np.all(np.isnan(series)):
            continue
        frame = int(np.nanargmax(series))
        if series[frame] > best_speed:
            best_frame, best_speed = frame, float(series[frame])
    return best_frame


def highest_wrist_frame(points):
    """The frame where a wrist is highest — contact in a spike, release in a shot — and
    which wrist it is."""
    with quiet():
        wrists = np.nanmin(points[:, [L_WRIST, R_WRIST], 1], axis=1)
    if np.all(np.isnan(wrists)):
        return None, None
    frame = int(np.nanargmin(wrists))
    side = L_WRIST if (np.isnan(points[frame, R_WRIST, 1]) or
                       points[frame, L_WRIST, 1] <= points[frame, R_WRIST, 1]) else R_WRIST
    return frame, side


def arm_for(wrist):
    """(shoulder, elbow, wrist) of the arm a wrist belongs to."""
    return ((L_SHOULDER, L_ELBOW, L_WRIST) if wrist == L_WRIST
            else (R_SHOULDER, R_ELBOW, R_WRIST))


def drill(finding, why, what, metric=None, value=None):
    """One piece of advice from a clip: what was seen, why it matters, what to train."""
    return {"finding": finding, "why": why, "drill": what, "metric": metric, "value": value}


# --------------------------------------------------------------------------- #
# Measurements more than one sport's analyser takes
# --------------------------------------------------------------------------- #

def knee_series(points):
    """(left, right) knee angles for every frame, NaN where a leg wasn't found."""
    n = len(points)
    left = np.array([angle_at(points[i, L_HIP], points[i, L_KNEE], points[i, L_ANKLE]) for i in range(n)])
    right = np.array([angle_at(points[i, R_HIP], points[i, R_KNEE], points[i, R_ANKLE]) for i in range(n)])
    return left, right


def trunk_lean(points, frame):
    """How far the trunk leans from upright in one frame, in degrees; None if it isn't there."""
    shoulder = mid(points, frame, L_SHOULDER, R_SHOULDER)
    hip = mid(points, frame, L_HIP, R_HIP)
    if not (shoulder and hip):
        return None
    return abs(math.degrees(math.atan2(shoulder[0] - hip[0], abs(hip[1] - shoulder[1]) + 1e-9)))


def hip_heights(points):
    """Mid-hip y for every frame (larger is lower on screen), NaN where the hips weren't found."""
    with quiet():
        return np.nanmean(points[:, [L_HIP, R_HIP], 1], axis=1)


def hip_rise(points, frame):
    """How far the hips are above their grounded height in one frame, in normalised units
    (never negative); None when the hips weren't found there."""
    hips = hip_heights(points)
    if np.isnan(hips[frame]):
        return None
    grounded = float(np.nanpercentile(hips, 90))      # where the hips sit with the feet down
    return max(0.0, grounded - float(hips[frame]))


def overhead_reach(points, frame, wrist, span):
    """How far a wrist is above the nose in one frame, in body-heights; None if either is missing."""
    head_y, wrist_y = points[frame, NOSE, 1], points[frame, wrist, 1]
    if np.isnan(head_y) or np.isnan(wrist_y):
        return None
    return float((head_y - wrist_y) / span)
