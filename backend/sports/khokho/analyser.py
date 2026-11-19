"""
Kho-Kho's video analyser.

Drill clips — one athlete, filmed side-on, read with MediaPipe pose. A chase or a dodge
over the whole clip: speed, how often and how low the turns are, the crouch, and how
flat and how far a dive reaches. video.py measures what matters in every sport
(symmetry, trunk stability, joint ranges) and calls technique() here for what only
matters in this one.

Match footage — YOLO and ByteTrack follow every player, and the coach says who is who.
The same tracker serves every sport; what differs is here: what counts as fast, what a
good number looks like, what each position looks like in a match, and the markings a coach
can calibrate on.
"""

import numpy as np

from sports.pose import (L_SHOULDER, R_SHOULDER, L_WRIST, R_WRIST, L_HIP, R_HIP, body_span,
                         drill, knee_series, quiet)

# --------------------------------------------------------------------------- #
# Match footage
# --------------------------------------------------------------------------- #

# Scale-free measures: a player's own height on screen is the ruler, so they compare
# across zoom levels and camera angles with no setting up. poor -> elite; starting points
# to retune from the Weights tab once there is footage from your own camera position.
FOOTAGE = {
    "matchDistance": (30, 90),
    "matchTopSpeed": (2.0, 5.0),
    "matchSprints": (0.5, 2.5),
    "matchWorkRate": (45, 90),
    "matchWidth": (10, 55),
    "matchAdvanced": (20, 80),
}

# Once a coach has marked out the pitch, positions are metres and the numbers compare with
# a GPS vest's. The speeds (km/h) that count as high-speed running and as a sprint here,
# and how firm they are ("standard", "published" or "estimated"):
SPEEDS = {"hsr": 15.0, "sprint": 20.0, "basis": "estimated"}

# ...and poor -> elite in those real units.
CALIBRATED = {
    "matchMetresPerMin": (60, 140),
    "matchTopSpeedKmh": (18, 30),
    "matchHsrPerMin": (1.0, 12.0),
    "matchSprintMetresPerMin": (0.5, 5.0),
    "matchAccelPerMin": (1.0, 4.0),
}

# What each position looks like in a match: one of sports_config.MATCH_ARCHETYPES.
ROLES = {
    "Chaser": "high-motor",
    "Runner / Dodger": "wide-attack",
}

# Known real-world dimensions a coach can mark out, so nobody has to remember them.
PITCH = [
    {"key": "field", "label": "Field (27 × 16 m)",
     "corners": ["Near-left corner", "Near-right corner",
                 "Far-right corner", "Far-left corner"],
     "world": [[0, 0], [27, 0], [27, 16], [0, 16]]},
]


# --------------------------------------------------------------------------- #
# Drill clips
# --------------------------------------------------------------------------- #

# what each measurement is called on screen, and its unit
LABELS = {
    "topSpeedBodySpansPerSec": ("Top speed in the clip", "body-heights/sec"),
    "directionChanges": ("Changes of direction", ""),
    "turnKneeAngleDeg": ("Knee bend at the turns", "deg"),
    "crouchKneeAngleDeg": ("Deepest crouch", "deg"),
    "flattestBodyAngleDeg": ("Flattest body angle", "deg from upright"),
    "reachBodySpans": ("Longest reach from the hips", "body-heights"),
}

TURN_BACK = 0.15          # body-heights travelled back the other way before a turn counts
STANDING_TURN = 150.0     # legs straighter than this at the turn is turning tall


def _turns(xs, span):
    """The frames where the player's travel across the frame reverses — each one a change
    of direction — ignoring any wobble shorter than TURN_BACK."""
    turns, heading = [], 0
    far_frame = far_x = None
    for frame, x in enumerate(xs):
        if np.isnan(x):
            continue
        if far_x is None:
            far_frame, far_x = frame, x
        elif heading == 0:
            if abs(x - far_x) >= TURN_BACK * span:        # under way: now there is a direction
                heading = 1 if x > far_x else -1
                far_frame, far_x = frame, x
        elif (x - far_x) * heading > 0:                   # still going: a new furthest point
            far_frame, far_x = frame, x
        elif (far_x - x) * heading >= TURN_BACK * span:   # come back far enough: that was a turn
            turns.append(far_frame)
            heading = -heading
            far_frame, far_x = frame, x
    return turns


def technique(points, fps, height_cm=None):
    """A chase or a dodge over the whole clip: how fast, how often and how low the turns
    are, the crouch it starts from, and how flat and how far the dive reaches."""
    span = body_span(points)
    metrics, drills = {}, []
    if span is None or fps <= 0:
        return metrics, drills

    with quiet():
        hips = np.nanmean(points[:, [L_HIP, R_HIP]], axis=1)
        shoulders = np.nanmean(points[:, [L_SHOULDER, R_SHOULDER]], axis=1)

    speeds = np.linalg.norm(np.diff(hips, axis=0), axis=1) * fps / span
    speeds = speeds[~np.isnan(speeds)]
    if speeds.size >= 3:
        # the 95th percentile, not the maximum: one mis-tracked frame is not a sprint
        metrics["topSpeedBodySpansPerSec"] = round(float(np.percentile(speeds, 95)), 2)

    left, right = knee_series(points)
    with quiet():
        both = np.nanmean(np.vstack([left, right]), axis=0)
        bent = np.fmin(left, right)

    turns = _turns(hips[:, 0], span)
    if np.any(~np.isnan(hips[:, 0])):
        metrics["directionChanges"] = len(turns)
    at_turns = []
    for frame in turns:
        around = bent[max(0, frame - 1):frame + 2]
        if np.any(~np.isnan(around)):
            at_turns.append(float(np.nanmin(around)))
    if at_turns:
        metrics["turnKneeAngleDeg"] = round(sum(at_turns) / len(at_turns), 1)

    if np.any(~np.isnan(both)):
        metrics["crouchKneeAngleDeg"] = round(float(np.nanmin(both)), 1)

    leans = np.abs(np.degrees(np.arctan2(shoulders[:, 0] - hips[:, 0],
                                         np.abs(hips[:, 1] - shoulders[:, 1]) + 1e-9)))
    if np.any(~np.isnan(leans)):
        metrics["flattestBodyAngleDeg"] = round(float(np.nanmax(leans)), 1)

    reach = np.abs(points[:, [L_WRIST, R_WRIST], 0] - hips[:, [0]])
    if np.any(~np.isnan(reach)):
        metrics["reachBodySpans"] = round(float(np.nanmax(reach)) / span, 3)

    turn_knee = metrics.get("turnKneeAngleDeg")
    if turn_knee is not None and turn_knee > STANDING_TURN:
        drills.append(drill(
            "Turning with straight legs",
            "Staying tall through a change of direction means braking and setting off again "
            "with the weight high: the turn takes longer, and the knee takes the twist.",
            "Low 5-10-5 shuttles touching the line with a hand at every turn, and "
            "sitting-to-sprint starts: 6 each side, hips below the shoulders through the turn.",
            "turnKneeAngleDeg", turn_knee))
    return metrics, drills
