"""
Football's video analyser.

Drill clips — one athlete, filmed side-on, read with MediaPipe pose. Strike mechanics at
the frame where a foot is fastest, plus running posture over the clip. video.py measures
what matters in every sport (symmetry, trunk stability, joint ranges) and calls
technique() here for what only matters in this one.

Match footage — YOLO and ByteTrack follow every player, and the coach says who is who.
The same tracker serves every sport; what differs is here: what counts as fast, what a
good number looks like, what each position looks like in a match, and the markings a coach
can calibrate on.
"""

import math

import numpy as np

from sports.pose import (L_SHOULDER, R_SHOULDER, L_HIP, R_HIP, L_KNEE, R_KNEE, L_ANKLE,
                         R_ANKLE, angle_at, body_span, drill, fastest_frame, mid, speed_series)

# --------------------------------------------------------------------------- #
# Match footage
# --------------------------------------------------------------------------- #

# Scale-free measures: a player's own height on screen is the ruler, so they compare
# across zoom levels and camera angles with no setting up. poor -> elite; starting points
# to retune from the Weights tab once there is footage from your own camera position.
FOOTAGE = {
    "matchDistance": (25, 75),
    "matchTopSpeed": (1.8, 4.5),
    "matchSprints": (0.2, 1.6),
    "matchWorkRate": (35, 80),
    "matchWidth": (8, 55),
    "matchAdvanced": (20, 80),
    # the mirror of work rate, carried only here: being deep *and* still is what
    # separates a goalkeeper from a centre-back, who is deep and covers ground
    "matchStationary": (20, 65),
}

# Once a coach has marked out the pitch, positions are metres and the numbers compare with
# a GPS vest's. The speeds (km/h) that count as high-speed running and as a sprint here,
# and how firm they are ("standard", "published" or "estimated"):
SPEEDS = {"hsr": 19.8, "sprint": 25.2, "basis": "standard"}

# ...and poor -> elite in those real units.
CALIBRATED = {
    "matchMetresPerMin": (70, 125),
    "matchTopSpeedKmh": (22, 33),
    "matchHsrPerMin": (1.0, 10.0),
    "matchSprintMetresPerMin": (0.2, 3.5),
    "matchAccelPerMin": (0.3, 1.5),
}

# What each position looks like in a match: one of sports_config.MATCH_ARCHETYPES.
ROLES = {
    "Goalkeeper": "goalkeeper",
    "Centre-back": "deep-anchor",
    "Full-back": "wide-support",
    "Central Midfielder": "central-engine",
    "Winger": "wide-attack",
    "Striker": "box-finisher",
}

# Known real-world dimensions a coach can mark out, so nobody has to remember them.
PITCH = [
    {"key": "penalty-area", "label": "Penalty area (40.32 × 16.5 m)",
     "corners": ["Left edge, goal line", "Right edge, goal line",
                 "Right edge, 18-yard line", "Left edge, 18-yard line"],
     "world": [[0, 0], [40.32, 0], [40.32, 16.5], [0, 16.5]]},
    {"key": "goal-area", "label": "Six-yard box (18.32 × 5.5 m)",
     "corners": ["Left edge, goal line", "Right edge, goal line",
                 "Right edge, 6-yard line", "Left edge, 6-yard line"],
     "world": [[0, 0], [18.32, 0], [18.32, 5.5], [0, 5.5]]},
    {"key": "full-pitch", "label": "Full pitch (105 × 68 m)",
     "corners": ["Near-left corner", "Near-right corner",
                 "Far-right corner", "Far-left corner"],
     "world": [[0, 0], [105, 0], [105, 68], [0, 68]]},
]


# --------------------------------------------------------------------------- #
# Drill clips
# --------------------------------------------------------------------------- #

# what each measurement is called on screen, and its unit
LABELS = {
    "strikeFoot": ("Striking foot", ""),
    "plantFootDistance": ("Plant-foot distance", "body-heights"),
    "strikeKneeAngleDeg": ("Knee angle at contact", "deg"),
    "strikeTrunkLeanDeg": ("Trunk lean at contact", "deg"),
    "runTrunkLeanDeg": ("Trunk lean while running", "deg"),
}


def technique(points, fps, height_cm=None):
    """Strike mechanics at the fastest-foot frame, plus running posture over the clip."""
    span = body_span(points)
    frame = fastest_frame(points, [L_ANKLE, R_ANKLE])
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    left_speed = speed_series(points, L_ANKLE)[frame]
    right_speed = speed_series(points, R_ANKLE)[frame]
    striking_left = not np.isnan(left_speed) and (np.isnan(right_speed) or left_speed >= right_speed)
    strike_ankle, plant_ankle = ((L_ANKLE, R_ANKLE) if striking_left else (R_ANKLE, L_ANKLE))
    strike_hip, strike_knee = ((L_HIP, L_KNEE) if striking_left else (R_HIP, R_KNEE))

    metrics["strikeFoot"] = "left" if striking_left else "right"

    # how far the plant foot sits from the striking foot, in body-heights
    feet = points[frame, [strike_ankle, plant_ankle]]
    if not np.isnan(feet).any():
        metrics["plantFootDistance"] = round(
            float(np.linalg.norm(feet[0] - feet[1])) / span, 3)

    knee = angle_at(points[frame, strike_hip], points[frame, strike_knee], points[frame, strike_ankle])
    if not math.isnan(knee):
        metrics["strikeKneeAngleDeg"] = round(knee, 1)

    shoulder = mid(points, frame, L_SHOULDER, R_SHOULDER)
    hip = mid(points, frame, L_HIP, R_HIP)
    if shoulder and hip:
        lean = math.degrees(math.atan2(shoulder[0] - hip[0], abs(hip[1] - shoulder[1]) + 1e-9))
        metrics["strikeTrunkLeanDeg"] = round(abs(lean), 1)

    # running posture across the whole clip, not just the strike
    shoulders = np.nanmean(points[:, [L_SHOULDER, R_SHOULDER]], axis=1)
    hips = np.nanmean(points[:, [L_HIP, R_HIP]], axis=1)
    leans = np.degrees(np.arctan2(shoulders[:, 0] - hips[:, 0],
                                  np.abs(hips[:, 1] - shoulders[:, 1]) + 1e-9))
    if np.any(~np.isnan(leans)):
        metrics["runTrunkLeanDeg"] = round(float(np.nanmean(np.abs(leans))), 1)

    plant = metrics.get("plantFootDistance")
    if plant is not None and plant < 0.18:
        drills.append(drill(
            "Plant foot too close to the striking foot",
            "A narrow base leaves no room to swing through the ball and robs the strike of power.",
            "Wall-pass striking drill with a cone marking the plant foot a shoe's width "
            "outside the ball; 3 sets of 10 each foot.",
            "plantFootDistance", plant))
    if plant is not None and plant > 0.62:
        drills.append(drill(
            "Plant foot very wide of the ball",
            "Overreaching tilts the body away and sends the contact point off-centre.",
            "Shorten the final approach step — practise striking from a two-step run-up "
            "before rebuilding the full run.",
            "plantFootDistance", plant))

    knee_angle = metrics.get("strikeKneeAngleDeg")
    if knee_angle is not None and knee_angle < 120:
        drills.append(drill(
            "Striking leg still folded at contact",
            "Whipping through with a bent knee cuts the lever short — the ball leaves slower "
            "than the effort deserves.",
            "Slow-motion swing work focusing on snapping the lower leg through, then "
            "progress to a stationary ball.",
            "strikeKneeAngleDeg", knee_angle))

    run_lean = metrics.get("runTrunkLeanDeg")
    if run_lean is not None and run_lean > 18:
        drills.append(drill(
            "Heavy trunk lean while running",
            "Leaning shifts load onto the lower back and shortens the stride.",
            "Hip-flexor and thoracic mobility, plus 'tall chest, eyes level' cues on "
            "every acceleration rep.",
            "runTrunkLeanDeg", run_lean))
    return metrics, drills
