"""
Basketball's video analyser.

Drill clips — one athlete, filmed side-on, read with MediaPipe pose. Shooting form at
the frame where a hand is highest: the set, the release elbow, release height and
whether the follow-through holds. video.py measures what matters in every sport
(symmetry, trunk stability, joint ranges) and calls technique() here for what only
matters in this one.

Match footage — YOLO and ByteTrack follow every player, and the coach says who is who.
The same tracker serves every sport; what differs is here: what counts as fast, what a
good number looks like, what each position looks like in a match, and the markings a coach
can calibrate on.
"""

import math

import numpy as np

from sports.pose import (NOSE, L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE, R_ANKLE, angle_at,
                         arm_for, body_span, drill, highest_wrist_frame)

# --------------------------------------------------------------------------- #
# Match footage
# --------------------------------------------------------------------------- #

# Scale-free measures: a player's own height on screen is the ruler, so they compare
# across zoom levels and camera angles with no setting up. poor -> elite; starting points
# to retune from the Weights tab once there is footage from your own camera position.
# No attacking / defensive positioning here: that is read against where the other players
# are, which only means something where play runs along one axis of the frame.
FOOTAGE = {
    "matchDistance": (20, 65),
    "matchTopSpeed": (1.5, 4.0),
    "matchSprints": (0.3, 2.0),
    "matchWorkRate": (40, 85),
    "matchWidth": (10, 60),
}

# Once a coach has marked out the pitch, positions are metres and the numbers compare with
# a GPS vest's. The speeds (km/h) that count as high-speed running and as a sprint here,
# and how firm they are ("standard", "published" or "estimated"):
SPEEDS = {"hsr": 14.4, "sprint": 18.0, "basis": "published"}

# ...and poor -> elite in those real units.
CALIBRATED = {
    "matchMetresPerMin": (40, 90),
    "matchTopSpeedKmh": (15, 26),
    "matchHsrPerMin": (0.5, 6.0),
    "matchSprintMetresPerMin": (0.1, 2.0),
    "matchAccelPerMin": (0.5, 2.5),
}

# What each position looks like in a match: one of sports_config.MATCH_ARCHETYPES.
ROLES = {
    "Point Guard": "high-motor",
    "Shooting Guard": "wide-attack",
    "Small Forward": "central-engine",
    "Power Forward": "box-finisher",
    "Centre": "deep-anchor",
}

# Known real-world dimensions a coach can mark out, so nobody has to remember them.
PITCH = [
    {"key": "full-court", "label": "FIBA court (28 × 15 m)",
     "corners": ["Near-left corner", "Near-right corner",
                 "Far-right corner", "Far-left corner"],
     "world": [[0, 0], [28, 0], [28, 15], [0, 15]]},
    {"key": "three-second", "label": "Restricted area (4.9 × 5.8 m)",
     "corners": ["Left edge, baseline", "Right edge, baseline",
                 "Right edge, free-throw line", "Left edge, free-throw line"],
     "world": [[0, 0], [4.9, 0], [4.9, 5.8], [0, 5.8]]},
]


# --------------------------------------------------------------------------- #
# Drill clips
# --------------------------------------------------------------------------- #

# what each measurement is called on screen, and its unit
LABELS = {
    "releaseElbowAngleDeg": ("Elbow angle at release", "deg"),
    "releaseAboveHead": ("Release above head", "body-heights"),
    "setKneeAngleDeg": ("Knee bend in the set", "deg"),
    "followThroughElbowDeg": ("Follow-through elbow", "deg"),
}


def technique(points, fps, height_cm=None):
    """Shooting form: set position, release elbow, release height, follow-through."""
    span = body_span(points)
    frame, wrist = highest_wrist_frame(points)
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    shoulder_j, elbow_j, wrist_j = arm_for(wrist)

    elbow = angle_at(points[frame, shoulder_j], points[frame, elbow_j], points[frame, wrist_j])
    if not math.isnan(elbow):
        metrics["releaseElbowAngleDeg"] = round(elbow, 1)

    head_y = points[frame, NOSE, 1]
    wrist_y = points[frame, wrist_j, 1]
    if not (np.isnan(head_y) or np.isnan(wrist_y)):
        metrics["releaseAboveHead"] = round(float((head_y - wrist_y) / span), 3)

    # the set position: deepest knee bend in the frames leading up to release
    window = slice(max(0, frame - int(fps)), frame + 1)
    knees = np.array([
        np.nanmean([
            angle_at(points[i, L_HIP], points[i, L_KNEE], points[i, L_ANKLE]),
            angle_at(points[i, R_HIP], points[i, R_KNEE], points[i, R_ANKLE]),
        ]) for i in range(*window.indices(len(points)))
    ])
    if knees.size and np.any(~np.isnan(knees)):
        metrics["setKneeAngleDeg"] = round(float(np.nanmin(knees)), 1)

    # follow-through: elbow angle a beat after release
    after = min(len(points) - 1, frame + max(1, int(fps * 0.2)))
    follow = angle_at(points[after, shoulder_j], points[after, elbow_j], points[after, wrist_j])
    if not math.isnan(follow):
        metrics["followThroughElbowDeg"] = round(follow, 1)

    release = metrics.get("releaseElbowAngleDeg")
    if release is not None and release < 140:
        drills.append(drill(
            "Short release — elbow still bent",
            "Releasing before the arm extends flattens the arc and makes the shot "
            "distance-dependent rather than repeatable.",
            "Form shooting from 1 m with a 'finish high, hold the follow-through' cue, "
            "50 makes before stepping back.",
            "releaseElbowAngleDeg", release))

    follow_angle = metrics.get("followThroughElbowDeg")
    if follow_angle is not None and release is not None and follow_angle < release - 10:
        drills.append(drill(
            "Follow-through collapsing",
            "Pulling the arm down straight after release adds side-spin and costs "
            "consistency far more than it looks like it should.",
            "Hold the follow-through until the ball lands, every rep, for two weeks.",
            "followThroughElbowDeg", follow_angle))

    set_knee = metrics.get("setKneeAngleDeg")
    if set_knee is not None and set_knee > 150:
        drills.append(drill(
            "Barely any leg drive in the shot",
            "Shooting with straight legs makes range come from the arm, which breaks "
            "down under fatigue and defensive pressure.",
            "Dip-and-rise shooting with a target knee bend around 120 degrees; start "
            "close and extend range only once the legs stay involved.",
            "setKneeAngleDeg", set_knee))
    return metrics, drills
