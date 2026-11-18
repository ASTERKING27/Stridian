"""
Volleyball's video analyser.

Drill clips — one athlete, filmed side-on, read with MediaPipe pose. Spike and block at
the frame where a hand is highest: reach at contact, the arm swing, and how much of the
reach came from the jump. video.py measures what matters in every sport (symmetry, trunk
stability, joint ranges) and calls technique() here for what only matters in this one.

Match footage — YOLO and ByteTrack follow every player, and the coach says who is who.
The same tracker serves every sport; what differs is here: what counts as fast, what a
good number looks like, what each position looks like in a match, and the markings a coach
can calibrate on.
"""

import math

import numpy as np

from sports.pose import (NOSE, L_HIP, R_HIP, angle_at, arm_for, body_span, drill,
                         highest_wrist_frame, mid)

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
    "Setter": "high-motor",
    "Libero": "deep-anchor",
    "Outside Hitter": "wide-attack",
    "Middle Blocker": "box-finisher",
    "Opposite / Server": "power-specialist",
}

# Known real-world dimensions a coach can mark out, so nobody has to remember them.
PITCH = [
    {"key": "full-court", "label": "Court (18 × 9 m)",
     "corners": ["Near-left corner", "Near-right corner",
                 "Far-right corner", "Far-left corner"],
     "world": [[0, 0], [18, 0], [18, 9], [0, 9]]},
    {"key": "half-court", "label": "One side (9 × 9 m)",
     "corners": ["Left corner at the net", "Right corner at the net",
                 "Right back corner", "Left back corner"],
     "world": [[0, 0], [9, 0], [9, 9], [0, 9]]},
]


# --------------------------------------------------------------------------- #
# Drill clips
# --------------------------------------------------------------------------- #

# what each measurement is called on screen, and its unit
LABELS = {
    "contactAboveHead": ("Contact above head", "body-heights"),
    "contactHeightCm": ("Estimated contact height", "cm"),
    "contactElbowAngleDeg": ("Elbow angle at contact", "deg"),
    "shoulderAbductionDeg": ("Shoulder angle through the swing", "deg"),
    "approachJumpBodySpans": ("Approach jump", "body-heights"),
    "approachJumpCm": ("Approach jump", "cm"),
}


def technique(points, fps, height_cm=None):
    """Spike and block: reach at contact, arm swing, and how much of it came from the jump."""
    span = body_span(points)
    frame, wrist = highest_wrist_frame(points)
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    shoulder_j, elbow_j, wrist_j = arm_for(wrist)

    # contact height above the head, in body-heights, then converted if height is known
    head_y = points[frame, NOSE, 1]
    wrist_y = points[frame, wrist_j, 1]
    if not (np.isnan(head_y) or np.isnan(wrist_y)):
        above = (head_y - wrist_y) / span
        metrics["contactAboveHead"] = round(float(above), 3)
        if height_cm:
            metrics["contactHeightCm"] = round(height_cm * (1 + float(above) * 0.88), 1)

    elbow = angle_at(points[frame, shoulder_j], points[frame, elbow_j], points[frame, wrist_j])
    if not math.isnan(elbow):
        metrics["contactElbowAngleDeg"] = round(elbow, 1)

    hip = mid(points, frame, L_HIP, R_HIP)
    shoulder = points[frame, shoulder_j]
    elbow_pt = points[frame, elbow_j]
    if hip and not (np.isnan(shoulder).any() or np.isnan(elbow_pt).any()):
        abduction = angle_at(hip, shoulder, elbow_pt)
        if not math.isnan(abduction):
            metrics["shoulderAbductionDeg"] = round(abduction, 1)

    # how much of the reach came from the jump rather than standing tall
    hips_y = np.nanmean(points[:, [L_HIP, R_HIP], 1], axis=1)
    if np.any(~np.isnan(hips_y)):
        grounded = float(np.nanpercentile(hips_y, 90))
        rise = max(0.0, grounded - float(hips_y[frame]))
        metrics["approachJumpBodySpans"] = round(rise / span, 3)
        if height_cm:
            metrics["approachJumpCm"] = round(rise / span * height_cm * 0.88, 1)

    elbow_angle = metrics.get("contactElbowAngleDeg")
    if elbow_angle is not None and elbow_angle < 150:
        drills.append(drill(
            "Arm not extended at contact",
            "Hitting with a bent elbow drops the contact point, which shrinks the angle "
            "available over the block.",
            "Standing reach-and-hit against a wall with a 'reach through the ball' cue, "
            "then add the approach once the arm stays long.",
            "contactElbowAngleDeg", elbow_angle))

    abduction = metrics.get("shoulderAbductionDeg")
    if abduction is not None and abduction < 140:
        drills.append(drill(
            "Low arm position through the swing",
            "A low elbow loads the shoulder badly and costs height on the contact.",
            "Band external-rotation work plus overhead mobility; drill the high-elbow "
            "cocked position before adding speed.",
            "shoulderAbductionDeg", abduction))

    jump = metrics.get("approachJumpBodySpans")
    if jump is not None and jump < 0.12:
        drills.append(drill(
            "Little height from the approach",
            "Most of the reach is coming from standing tall rather than from the jump.",
            "Approach-jump timing — three-step approach with a hard penultimate step, "
            "plus depth jumps twice a week on fresh legs.",
            "approachJumpBodySpans", jump))
    return metrics, drills
