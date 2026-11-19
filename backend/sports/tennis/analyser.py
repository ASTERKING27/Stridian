"""
Tennis's video analyser.

Drill clips — one athlete, filmed side-on, read with MediaPipe pose. The serve at
contact — reach and arm — and the second before it: the knee bend and the leg drive.
video.py measures what matters in every sport (symmetry, trunk stability, joint ranges)
and calls technique() here for what only matters in this one.

Match footage — YOLO and ByteTrack follow every player, and the coach says who is who.
The same tracker serves every sport; what differs is here: what counts as fast, what a
good number looks like, what each position looks like in a match, and the markings a coach
can calibrate on.
"""

import math

import numpy as np

from sports.pose import (L_WRIST, angle_at, arm_for, body_span, drill, highest_wrist_frame,
                         hip_heights, knee_series, overhead_reach, quiet, trunk_lean)

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
    "Attacking / Power player": "power-specialist",
    "Defensive / Counter player": "high-motor",
    "All-court / Balanced": "central-engine",
}

# Known real-world dimensions a coach can mark out, so nobody has to remember them.
PITCH = [
    {"key": "tennis-doubles", "label": "Tennis court (23.77 × 10.97 m)",
     "corners": ["Near-left corner", "Near-right corner",
                 "Far-right corner", "Far-left corner"],
     "world": [[0, 0], [10.97, 0], [10.97, 23.77], [0, 23.77]]},
]


# --------------------------------------------------------------------------- #
# Drill clips
# --------------------------------------------------------------------------- #

# what each measurement is called on screen, and its unit
LABELS = {
    "hittingArm": ("Hitting arm", ""),
    "contactAboveHead": ("Hand above head at contact", "body-heights"),
    "contactHeightCm": ("Estimated hand height at contact", "cm"),
    "contactElbowAngleDeg": ("Elbow angle at contact", "deg"),
    "trophyKneeAngleDeg": ("Knee bend before the serve", "deg"),
    "legDriveBodySpans": ("Leg drive into contact", "body-heights"),
    "legDriveCm": ("Leg drive into contact", "cm"),
    "contactTrunkLeanDeg": ("Trunk lean at contact", "deg"),
}

# A serve (or a smash) is a stroke where the hitting hand goes at least this far above the
# nose (body-heights). A hand that stays lower is a groundstroke or a run, and says
# nothing about the serve.
OVERHEAD = 0.05
ARM_STRAIGHT = 150.0      # an elbow angle below this at contact is a bent arm
LEGS_STRAIGHT = 155.0     # knees straighter than this in the trophy position put nothing in


def technique(points, fps, height_cm=None):
    """The serve at contact — where the hitting hand is highest — and the second before
    it: reach, arm, and how much the legs put in."""
    span = body_span(points)
    frame, wrist = highest_wrist_frame(points)
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    above = overhead_reach(points, frame, wrist, span)
    if above is None or above < OVERHEAD:
        return metrics, drills

    shoulder_j, elbow_j, wrist_j = arm_for(wrist)
    metrics["hittingArm"] = "left" if wrist == L_WRIST else "right"
    metrics["contactAboveHead"] = round(above, 3)
    if height_cm:
        # the hand, not the strings: the ball is met about a racket's length higher
        metrics["contactHeightCm"] = round(height_cm * (1 + above * 0.88), 1)

    elbow = angle_at(points[frame, shoulder_j], points[frame, elbow_j], points[frame, wrist_j])
    if not math.isnan(elbow):
        metrics["contactElbowAngleDeg"] = round(elbow, 1)

    # the trophy position: the deepest knee bend in the second leading up to contact
    start = max(0, frame - max(1, int(fps)))
    left, right = knee_series(points[start:frame + 1])
    with quiet():
        knees = np.nanmean(np.vstack([left, right]), axis=0)
    if np.any(~np.isnan(knees)):
        metrics["trophyKneeAngleDeg"] = round(float(np.nanmin(knees)), 1)

    # ...and how far the hips rose from their lowest point there into contact
    hips = hip_heights(points)
    before = hips[start:frame + 1]
    if not np.isnan(hips[frame]) and np.any(~np.isnan(before)):
        drive = max(0.0, float(np.nanmax(before)) - float(hips[frame]))
        metrics["legDriveBodySpans"] = round(drive / span, 3)
        if height_cm:
            metrics["legDriveCm"] = round(drive / span * height_cm * 0.88, 1)

    lean = trunk_lean(points, frame)
    if lean is not None:
        metrics["contactTrunkLeanDeg"] = round(lean, 1)

    elbow_angle = metrics.get("contactElbowAngleDeg")
    if elbow_angle is not None and elbow_angle < ARM_STRAIGHT:
        drills.append(drill(
            "Arm bent at contact on the serve",
            "Contact below full stretch lowers the hitting point, which leaves less net to "
            "clear — the serve has to slow down to go in.",
            "Serves from the trophy position with a pause, reaching up to meet the ball at full "
            "stretch; then full serves with the toss a racket's length above the outstretched hand.",
            "contactElbowAngleDeg", elbow_angle))

    knee = metrics.get("trophyKneeAngleDeg")
    if knee is not None and knee > LEGS_STRAIGHT:
        drills.append(drill(
            "Barely any knee bend before the serve",
            "Without leg drive the pace has to come from the shoulder alone: the serve is "
            "slower, and the shoulder takes the load.",
            "Knee-bend-and-drive serves — hold the trophy position with the knees at about 120 "
            "degrees, then drive up into contact — plus overhead medicine-ball throws.",
            "trophyKneeAngleDeg", knee))
    return metrics, drills
