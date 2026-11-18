"""
Cricket's video analyser.

Drill clips — one athlete, filmed side-on, read with MediaPipe pose. The bowling action
at release, with an indicator against the ICC's 15-degree elbow limit. video.py measures
what matters in every sport (symmetry, trunk stability, joint ranges) and calls
technique() here for what only matters in this one.

Match footage — YOLO and ByteTrack follow every player, and the coach says who is who.
The same tracker serves every sport; what differs is here: what counts as fast, what a
good number looks like, what each position looks like in a match, and the markings a coach
can calibrate on.
"""

import math

import numpy as np

from sports.pose import (L_SHOULDER, R_SHOULDER, L_WRIST, L_HIP, R_HIP, L_KNEE, R_KNEE,
                         L_ANKLE, R_ANKLE, angle_at, arm_for, body_span, drill,
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
    "matchDistance": (8, 45),
    "matchTopSpeed": (1.5, 4.2),
    "matchSprints": (0.1, 1.0),
    "matchWorkRate": (15, 60),
    "matchWidth": (5, 50),
}

# Once a coach has marked out the pitch, positions are metres and the numbers compare with
# a GPS vest's. The speeds (km/h) that count as high-speed running and as a sprint here,
# and how firm they are ("standard", "published" or "estimated"):
SPEEDS = {"hsr": 15.0, "sprint": 20.0, "basis": "estimated"}

# ...and poor -> elite in those real units.
CALIBRATED = {
    "matchMetresPerMin": (15, 70),
    "matchTopSpeedKmh": (15, 30),
    "matchHsrPerMin": (0.2, 5.0),
    "matchSprintMetresPerMin": (0.1, 2.0),
    "matchAccelPerMin": (0.1, 1.0),
}

# What each position looks like in a match: one of sports_config.MATCH_ARCHETYPES.
ROLES = {
    "Opening Batsman": "wide-support",
    "Middle-order Batsman": "central-engine",
    "Fast Bowler": "power-specialist",
    "Spin Bowler": "high-motor",
    "Wicketkeeper": "deep-anchor",
    "All-rounder": "central-engine",
}

# Known real-world dimensions a coach can mark out, so nobody has to remember them.
PITCH = [
    {"key": "pitch", "label": "Pitch (20.12 × 3.05 m)",
     "corners": ["Left of the bowler's crease", "Right of the bowler's crease",
                 "Right of the batter's crease", "Left of the batter's crease"],
     "world": [[0, 0], [3.05, 0], [3.05, 20.12], [0, 20.12]]},
]


# --------------------------------------------------------------------------- #
# Drill clips
# --------------------------------------------------------------------------- #

# The ICC's limit on elbow extension through the delivery swing.
ICC_ELBOW_LIMIT_DEG = 15.0

# what each measurement is called on screen, and its unit
LABELS = {
    "bowlingArm": ("Bowling arm", ""),
    "elbowAtHorizontalDeg": ("Elbow when arm reaches horizontal", "deg"),
    "elbowAtReleaseDeg": ("Elbow at release", "deg"),
    "elbowExtensionDeg": ("Elbow extension through the swing", "deg"),
    "iccLimitDeg": ("ICC limit", "deg"),
    "withinIccIndicator": ("Within the ICC limit (indicator)", ""),
    "frontKneeAtReleaseDeg": ("Front knee at release", "deg"),
    "releaseTrunkLeanDeg": ("Trunk lean at release", "deg"),
}


def technique(points, fps, height_cm=None):
    """Bowling action, including an indicator against the ICC's 15-degree elbow limit."""
    span = body_span(points)
    frame, wrist = highest_wrist_frame(points)
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    shoulder_j, elbow_j, wrist_j = arm_for(wrist)
    metrics["bowlingArm"] = "left" if wrist == L_WRIST else "right"

    # The Law measures extension between the arm reaching horizontal and the ball
    # leaving the hand. Find the horizontal moment by looking back from release for the
    # frame where the upper arm is flattest.
    best_i, flattest = None, None
    for i in range(max(0, frame - int(fps * 1.2)), frame + 1):
        shoulder = points[i, shoulder_j]
        elbow_pt = points[i, elbow_j]
        if np.isnan(shoulder).any() or np.isnan(elbow_pt).any():
            continue
        rise = abs(elbow_pt[1] - shoulder[1])
        run = abs(elbow_pt[0] - shoulder[0]) + 1e-9
        flatness = rise / run
        if flattest is None or flatness < flattest:
            best_i, flattest = i, flatness

    if best_i is not None:
        at_horizontal = angle_at(points[best_i, shoulder_j], points[best_i, elbow_j],
                                 points[best_i, wrist_j])
        at_release = angle_at(points[frame, shoulder_j], points[frame, elbow_j],
                              points[frame, wrist_j])
        if not (math.isnan(at_horizontal) or math.isnan(at_release)):
            metrics["elbowAtHorizontalDeg"] = round(at_horizontal, 1)
            metrics["elbowAtReleaseDeg"] = round(at_release, 1)
            extension = at_release - at_horizontal
            metrics["elbowExtensionDeg"] = round(extension, 1)
            metrics["iccLimitDeg"] = ICC_ELBOW_LIMIT_DEG
            metrics["withinIccIndicator"] = bool(extension <= ICC_ELBOW_LIMIT_DEG)

    front_knee = min(
        (a for a in (angle_at(points[frame, L_HIP], points[frame, L_KNEE], points[frame, L_ANKLE]),
                     angle_at(points[frame, R_HIP], points[frame, R_KNEE], points[frame, R_ANKLE]))
         if not math.isnan(a)), default=None)
    if front_knee is not None:
        metrics["frontKneeAtReleaseDeg"] = round(front_knee, 1)

    shoulder_mid = mid(points, frame, L_SHOULDER, R_SHOULDER)
    hip_mid = mid(points, frame, L_HIP, R_HIP)
    if shoulder_mid and hip_mid:
        lean = math.degrees(math.atan2(shoulder_mid[0] - hip_mid[0],
                                       abs(hip_mid[1] - shoulder_mid[1]) + 1e-9))
        metrics["releaseTrunkLeanDeg"] = round(abs(lean), 1)

    extension = metrics.get("elbowExtensionDeg")
    if extension is not None and extension > ICC_ELBOW_LIMIT_DEG:
        drills.append(drill(
            f"Elbow extension indicator above the ICC limit ({extension:.0f}° vs {ICC_ELBOW_LIMIT_DEG:.0f}°)",
            "This is a single-camera 2D estimate, not a ruling — official testing uses 3D "
            "motion capture in an accredited lab. Treat it as a prompt to film the action "
            "properly side-on and, if it repeats, to arrange a formal assessment before a "
            "match official raises it.",
            "Re-film square to the bowler at 60 fps first, since an off-axis camera "
            "inflates this reading. If it holds up, work with a bowling coach on a "
            "braced-elbow action rather than trying to self-correct.",
            "elbowExtensionDeg", extension))

    knee = metrics.get("frontKneeAtReleaseDeg")
    if knee is not None and knee < 150:
        drills.append(drill(
            "Front leg collapsing at release",
            "A bent front knee absorbs the energy the run-up built instead of converting "
            "it into ball speed, and loads the back over time.",
            "Front-leg bracing drills — single-leg landings and Nordic curls — plus "
            "bowling off a shortened run until the leg holds.",
            "frontKneeAtReleaseDeg", knee))
    return metrics, drills
