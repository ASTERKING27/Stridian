"""
Badminton's video analyser.

Drill clips — one athlete, filmed side-on, read with MediaPipe pose. An overhead stroke
where the hitting hand is highest — reach, arm and jump — and the deepest lunge in the
clip. video.py measures what matters in every sport (symmetry, trunk stability, joint
ranges) and calls technique() here for what only matters in this one.

Match footage — YOLO and ByteTrack follow every player, and the coach says who is who.
The same tracker serves every sport; what differs is here: what counts as fast, what a
good number looks like, what each position looks like in a match, and the markings a coach
can calibrate on.
"""

import math

import numpy as np

from sports.pose import (L_WRIST, L_ANKLE, R_ANKLE, angle_at, arm_for, body_span, drill,
                         highest_wrist_frame, hip_heights, hip_rise, knee_series,
                         overhead_reach, quiet, trunk_lean)

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
    {"key": "badminton-doubles", "label": "Badminton court (13.4 × 6.1 m)",
     "corners": ["Near-left corner", "Near-right corner",
                 "Far-right corner", "Far-left corner"],
     "world": [[0, 0], [6.1, 0], [6.1, 13.4], [0, 13.4]]},
]


# --------------------------------------------------------------------------- #
# Drill clips
# --------------------------------------------------------------------------- #

# what each measurement is called on screen, and its unit
LABELS = {
    "racketArm": ("Racket arm", ""),
    "contactAboveHead": ("Hand above head at contact", "body-heights"),
    "contactHeightCm": ("Estimated hand height at contact", "cm"),
    "contactElbowAngleDeg": ("Elbow angle at contact", "deg"),
    "jumpAtContactBodySpans": ("Jump at contact", "body-heights"),
    "jumpAtContactCm": ("Jump at contact", "cm"),
    "lungeKneeAngleDeg": ("Front knee in the deepest lunge", "deg"),
    "lungeStrideBodySpans": ("Lunge length", "body-heights"),
    "lungeTrunkLeanDeg": ("Trunk lean in the lunge", "deg"),
}

# An overhead stroke is one where the hitting hand goes at least this far above the nose
# (body-heights). A hand that stays lower is a drive, a net shot or a run, and says nothing
# about the overhead.
OVERHEAD = 0.05
ARM_STRAIGHT = 150.0      # an elbow angle below this at contact is a bent arm

# A lunge is feet split at least this far (body-heights), both on the floor, the hips
# dropped and the front knee bent — a running stride has one foot in the air and the hips up.
LUNGE_STRIDE = 0.35
LUNGE_LEVEL = 0.08        # how far apart in height the two feet may be
LUNGE_DROP = 0.06         # how far the hips sit below standing height
LUNGE_KNEE = 135.0        # the front knee is bent at least to this
LUNGE_UPRIGHT = 35.0      # more trunk lean than this is reaching with the back
LUNGE_COLLAPSED = 80.0    # a front knee folded past this has to climb out before it can push back


def _deepest_lunge(points, span):
    """(frame, front-knee angle, lunge length) of the deepest lunge in the clip, or None."""
    left, right = knee_series(points)
    feet = points[:, [L_ANKLE, R_ANKLE]]
    hips = hip_heights(points)
    if not np.any(~np.isnan(hips)):
        return None
    with quiet(), np.errstate(invalid="ignore"):
        front = np.fmin(left, right)                              # the more bent knee
        split = np.abs(feet[:, 0, 0] - feet[:, 1, 0]) / span
        lifted = np.abs(feet[:, 0, 1] - feet[:, 1, 1]) / span
        drop = (hips - float(np.nanpercentile(hips, 10))) / span   # below where the hips are when standing
        lunging = ((split >= LUNGE_STRIDE) & (lifted <= LUNGE_LEVEL) & (drop >= LUNGE_DROP)
                   & (front <= LUNGE_KNEE))
    if not lunging.any():
        return None
    frame = int(np.argmin(np.where(lunging, front, np.inf)))
    return frame, float(front[frame]), float(split[frame])


def technique(points, fps, height_cm=None):
    """An overhead stroke (smash, clear or drop) where the hitting hand is highest, and
    the deepest lunge in the clip."""
    span = body_span(points)
    metrics, drills = {}, []
    if span is None:
        return metrics, drills

    frame, wrist = highest_wrist_frame(points)
    above = overhead_reach(points, frame, wrist, span) if frame is not None else None
    if above is not None and above >= OVERHEAD:
        shoulder_j, elbow_j, wrist_j = arm_for(wrist)
        metrics["racketArm"] = "left" if wrist == L_WRIST else "right"
        metrics["contactAboveHead"] = round(above, 3)
        if height_cm:
            # the hand, not the racket head: the shuttle is met about a racket's length higher
            metrics["contactHeightCm"] = round(height_cm * (1 + above * 0.88), 1)

        elbow = angle_at(points[frame, shoulder_j], points[frame, elbow_j], points[frame, wrist_j])
        if not math.isnan(elbow):
            metrics["contactElbowAngleDeg"] = round(elbow, 1)

        rise = hip_rise(points, frame)
        if rise is not None:
            metrics["jumpAtContactBodySpans"] = round(rise / span, 3)
            if height_cm:
                metrics["jumpAtContactCm"] = round(rise / span * height_cm * 0.88, 1)

    lunge = _deepest_lunge(points, span)
    if lunge:
        at, knee, length = lunge
        metrics["lungeKneeAngleDeg"] = round(knee, 1)
        metrics["lungeStrideBodySpans"] = round(length, 3)
        lean = trunk_lean(points, at)
        if lean is not None:
            metrics["lungeTrunkLeanDeg"] = round(lean, 1)

    elbow_angle = metrics.get("contactElbowAngleDeg")
    if elbow_angle is not None and elbow_angle < ARM_STRAIGHT:
        drills.append(drill(
            "Arm bent at contact on the overhead",
            "Meeting the shuttle with a bent arm lowers the contact point, so the smash comes "
            "off flatter and the clear falls short.",
            "Shadow overheads to a shuttle hung at full reach, throwing action first; then high "
            "serves fed to the rear court, 3 sets of 15 with contact at full stretch.",
            "contactElbowAngleDeg", elbow_angle))

    lunge_lean = metrics.get("lungeTrunkLeanDeg")
    if lunge_lean is not None and lunge_lean > LUNGE_UPRIGHT:
        drills.append(drill(
            "Bending at the waist in the lunge",
            "Reaching with the back instead of the legs leaves the weight over the front foot: "
            "the push back to base is slow, and the lower back takes the load.",
            "Lunge-and-recover shadow footwork to the four corners with the chest up and the "
            "racket leg leading, 6 rounds of 30 seconds.",
            "lungeTrunkLeanDeg", lunge_lean))

    lunge_knee = metrics.get("lungeKneeAngleDeg")
    if lunge_knee is not None and lunge_knee < LUNGE_COLLAPSED:
        drills.append(drill(
            "Front knee collapsing in the lunge",
            "A knee folded well past a right angle has to climb out of the lunge before it can "
            "push back, so recovery is slower and the kneecap takes the strain.",
            "Split-step into a lunge that stops at a right angle, then reverse lunges and slow "
            "step-downs for control: 3 sets of 8 each leg.",
            "lungeKneeAngleDeg", lunge_knee))
    return metrics, drills
