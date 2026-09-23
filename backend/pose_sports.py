"""
Sport-specific technique metrics from the MediaPipe drill lane.

video.py measures things that matter in every sport — symmetry, trunk stability, joint
ranges. This module adds what only matters in one: how a footballer plants and strikes,
how a spiker reaches at contact, how a shooter's elbow sits at release, and whether a
bowler's arm straightens more than the Law allows.

Each sport works the same way: find the moment that matters (the frame where the ankle
is fastest, or the wrist is highest), measure a handful of angles and heights there, and
turn anything outside the expected band into a drill.

**Two honest limits, stated here and surfaced in the app:**

* These are 2D measurements from a single camera. A joint angle is only accurate when
  the movement happens roughly side-on to the lens; rotate the athlete 45 degrees and
  the same angle reads several degrees off. Film square to the action.
* The ICC's 15-degree elbow limit is adjudicated with 3D motion capture in an
  accredited lab. What this computes is an *indicator* to decide whether a proper test
  is worth arranging — it is not, and cannot be, a ruling.
"""

import math

import numpy as np

from video import (L_ANKLE, L_ELBOW, L_HIP, L_KNEE, L_SHOULDER, L_WRIST, NOSE,
                   R_ANKLE, R_ELBOW, R_HIP, R_KNEE, R_SHOULDER, R_WRIST, angle_at)

# The ICC's limit on elbow extension through the delivery swing.
ICC_ELBOW_LIMIT_DEG = 15.0


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _mid(points, frame, a, b):
    pair = points[frame, [a, b]]
    if np.isnan(pair).any():
        return None
    return tuple(np.nanmean(pair, axis=0))


def _body_span(points):
    """Nose-to-ankle in normalised units: the ruler for every height in this module."""
    import warnings

    with warnings.catch_warnings():
        # an undetected frame is expected here, and nanmean says so very loudly
        warnings.simplefilter("ignore", category=RuntimeWarning)
        ankles = np.nanmean(points[:, [L_ANKLE, R_ANKLE], 1], axis=1)
        span = np.nanmedian(ankles - points[:, NOSE, 1])
    return float(span) if span and not math.isnan(span) and span > 0.05 else None


def _speed_series(points, joint):
    """Per-frame speed of one landmark, in normalised units per frame."""
    xy = points[:, joint]
    deltas = np.linalg.norm(np.diff(xy, axis=0), axis=1)
    return np.concatenate([[np.nan], deltas])


def _fastest_frame(points, joints):
    """The frame where any of these landmarks is moving quickest — the moment of action."""
    best_frame, best_speed = None, -1.0
    for joint in joints:
        series = _speed_series(points, joint)
        if np.all(np.isnan(series)):
            continue
        frame = int(np.nanargmax(series))
        if series[frame] > best_speed:
            best_frame, best_speed = frame, float(series[frame])
    return best_frame


def _highest_wrist_frame(points):
    """The frame where a wrist is highest — contact in a spike, release in a shot."""
    wrists = np.nanmin(points[:, [L_WRIST, R_WRIST], 1], axis=1)
    if np.all(np.isnan(wrists)):
        return None, None
    frame = int(np.nanargmin(wrists))
    side = L_WRIST if (np.isnan(points[frame, R_WRIST, 1]) or
                       points[frame, L_WRIST, 1] <= points[frame, R_WRIST, 1]) else R_WRIST
    return frame, side


def _arm_for(wrist):
    return ((L_SHOULDER, L_ELBOW, L_WRIST) if wrist == L_WRIST
            else (R_SHOULDER, R_ELBOW, R_WRIST))


def _drill(finding, why, drill, metric=None, value=None):
    return {"finding": finding, "why": why, "drill": drill, "metric": metric, "value": value}


# --------------------------------------------------------------------------- #
# Football
# --------------------------------------------------------------------------- #

def football(points, fps, height_cm=None):
    """Strike mechanics at the fastest-foot frame, plus running posture over the clip."""
    span = _body_span(points)
    frame = _fastest_frame(points, [L_ANKLE, R_ANKLE])
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    left_speed = _speed_series(points, L_ANKLE)[frame]
    right_speed = _speed_series(points, R_ANKLE)[frame]
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

    shoulder = _mid(points, frame, L_SHOULDER, R_SHOULDER)
    hip = _mid(points, frame, L_HIP, R_HIP)
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
        drills.append(_drill(
            "Plant foot too close to the striking foot",
            "A narrow base leaves no room to swing through the ball and robs the strike of power.",
            "Wall-pass striking drill with a cone marking the plant foot a shoe's width "
            "outside the ball; 3 sets of 10 each foot.",
            "plantFootDistance", plant))
    if plant is not None and plant > 0.62:
        drills.append(_drill(
            "Plant foot very wide of the ball",
            "Overreaching tilts the body away and sends the contact point off-centre.",
            "Shorten the final approach step — practise striking from a two-step run-up "
            "before rebuilding the full run.",
            "plantFootDistance", plant))

    knee_angle = metrics.get("strikeKneeAngleDeg")
    if knee_angle is not None and knee_angle < 120:
        drills.append(_drill(
            "Striking leg still folded at contact",
            "Whipping through with a bent knee cuts the lever short — the ball leaves slower "
            "than the effort deserves.",
            "Slow-motion swing work focusing on snapping the lower leg through, then "
            "progress to a stationary ball.",
            "strikeKneeAngleDeg", knee_angle))

    run_lean = metrics.get("runTrunkLeanDeg")
    if run_lean is not None and run_lean > 18:
        drills.append(_drill(
            "Heavy trunk lean while running",
            "Leaning shifts load onto the lower back and shortens the stride.",
            "Hip-flexor and thoracic mobility, plus 'tall chest, eyes level' cues on "
            "every acceleration rep.",
            "runTrunkLeanDeg", run_lean))
    return metrics, drills


# --------------------------------------------------------------------------- #
# Volleyball
# --------------------------------------------------------------------------- #

def volleyball(points, fps, height_cm=None):
    """Spike and block: reach at contact, arm swing, and how much of it came from the jump."""
    span = _body_span(points)
    frame, wrist = _highest_wrist_frame(points)
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    shoulder_j, elbow_j, wrist_j = _arm_for(wrist)

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

    hip = _mid(points, frame, L_HIP, R_HIP)
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
        drills.append(_drill(
            "Arm not extended at contact",
            "Hitting with a bent elbow drops the contact point, which shrinks the angle "
            "available over the block.",
            "Standing reach-and-hit against a wall with a 'reach through the ball' cue, "
            "then add the approach once the arm stays long.",
            "contactElbowAngleDeg", elbow_angle))

    abduction = metrics.get("shoulderAbductionDeg")
    if abduction is not None and abduction < 140:
        drills.append(_drill(
            "Low arm position through the swing",
            "A low elbow loads the shoulder badly and costs height on the contact.",
            "Band external-rotation work plus overhead mobility; drill the high-elbow "
            "cocked position before adding speed.",
            "shoulderAbductionDeg", abduction))

    jump = metrics.get("approachJumpBodySpans")
    if jump is not None and jump < 0.12:
        drills.append(_drill(
            "Little height from the approach",
            "Most of the reach is coming from standing tall rather than from the jump.",
            "Approach-jump timing — three-step approach with a hard penultimate step, "
            "plus depth jumps twice a week on fresh legs.",
            "approachJumpBodySpans", jump))
    return metrics, drills


# --------------------------------------------------------------------------- #
# Basketball
# --------------------------------------------------------------------------- #

def basketball(points, fps, height_cm=None):
    """Shooting form: set position, release elbow, release height, follow-through."""
    span = _body_span(points)
    frame, wrist = _highest_wrist_frame(points)
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    shoulder_j, elbow_j, wrist_j = _arm_for(wrist)

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
        drills.append(_drill(
            "Short release — elbow still bent",
            "Releasing before the arm extends flattens the arc and makes the shot "
            "distance-dependent rather than repeatable.",
            "Form shooting from 1 m with a 'finish high, hold the follow-through' cue, "
            "50 makes before stepping back.",
            "releaseElbowAngleDeg", release))

    follow_angle = metrics.get("followThroughElbowDeg")
    if follow_angle is not None and release is not None and follow_angle < release - 10:
        drills.append(_drill(
            "Follow-through collapsing",
            "Pulling the arm down straight after release adds side-spin and costs "
            "consistency far more than it looks like it should.",
            "Hold the follow-through until the ball lands, every rep, for two weeks.",
            "followThroughElbowDeg", follow_angle))

    set_knee = metrics.get("setKneeAngleDeg")
    if set_knee is not None and set_knee > 150:
        drills.append(_drill(
            "Barely any leg drive in the shot",
            "Shooting with straight legs makes range come from the arm, which breaks "
            "down under fatigue and defensive pressure.",
            "Dip-and-rise shooting with a target knee bend around 120 degrees; start "
            "close and extend range only once the legs stay involved.",
            "setKneeAngleDeg", set_knee))
    return metrics, drills


# --------------------------------------------------------------------------- #
# Cricket
# --------------------------------------------------------------------------- #

def cricket(points, fps, height_cm=None):
    """Bowling action, including an indicator against the ICC's 15-degree elbow limit."""
    span = _body_span(points)
    frame, wrist = _highest_wrist_frame(points)
    metrics, drills = {}, []
    if frame is None or span is None:
        return metrics, drills

    shoulder_j, elbow_j, wrist_j = _arm_for(wrist)
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

    shoulder_mid = _mid(points, frame, L_SHOULDER, R_SHOULDER)
    hip_mid = _mid(points, frame, L_HIP, R_HIP)
    if shoulder_mid and hip_mid:
        lean = math.degrees(math.atan2(shoulder_mid[0] - hip_mid[0],
                                       abs(hip_mid[1] - shoulder_mid[1]) + 1e-9))
        metrics["releaseTrunkLeanDeg"] = round(abs(lean), 1)

    extension = metrics.get("elbowExtensionDeg")
    if extension is not None and extension > ICC_ELBOW_LIMIT_DEG:
        drills.append(_drill(
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
        drills.append(_drill(
            "Front leg collapsing at release",
            "A bent front knee absorbs the energy the run-up built instead of converting "
            "it into ball speed, and loads the back over time.",
            "Front-leg bracing drills — single-leg landings and Nordic curls — plus "
            "bowling off a shortened run until the leg holds.",
            "frontKneeAtReleaseDeg", knee))
    return metrics, drills


# --------------------------------------------------------------------------- #
# Dispatch
# --------------------------------------------------------------------------- #

ANALYSERS = {
    "Football": football,
    "Volleyball": volleyball,
    "Basketball": basketball,
    "Cricket": cricket,
}

LABELS = {
    "strikeFoot": ("Striking foot", ""),
    "plantFootDistance": ("Plant-foot distance", "body-heights"),
    "strikeKneeAngleDeg": ("Knee angle at contact", "deg"),
    "strikeTrunkLeanDeg": ("Trunk lean at contact", "deg"),
    "runTrunkLeanDeg": ("Trunk lean while running", "deg"),
    "contactAboveHead": ("Contact above head", "body-heights"),
    "contactHeightCm": ("Estimated contact height", "cm"),
    "contactElbowAngleDeg": ("Elbow angle at contact", "deg"),
    "shoulderAbductionDeg": ("Shoulder angle through the swing", "deg"),
    "approachJumpBodySpans": ("Approach jump", "body-heights"),
    "approachJumpCm": ("Approach jump", "cm"),
    "releaseElbowAngleDeg": ("Elbow angle at release", "deg"),
    "releaseAboveHead": ("Release above head", "body-heights"),
    "setKneeAngleDeg": ("Knee bend in the set", "deg"),
    "followThroughElbowDeg": ("Follow-through elbow", "deg"),
    "bowlingArm": ("Bowling arm", ""),
    "elbowAtHorizontalDeg": ("Elbow when arm reaches horizontal", "deg"),
    "elbowAtReleaseDeg": ("Elbow at release", "deg"),
    "elbowExtensionDeg": ("Elbow extension through the swing", "deg"),
    "iccLimitDeg": ("ICC limit", "deg"),
    "withinIccIndicator": ("Within the ICC limit (indicator)", ""),
    "frontKneeAtReleaseDeg": ("Front knee at release", "deg"),
    "releaseTrunkLeanDeg": ("Trunk lean at release", "deg"),
}

CAMERA_NOTE = ("Angles are measured from a single camera in 2D — film square to the "
               "action, or they read several degrees off.")


def analyse(sport, points, fps, height_cm=None):
    """{metrics, labels, drills, note} for the sport, or empty when there's no analyser."""
    analyser = ANALYSERS.get(sport)
    if analyser is None:
        return {}
    try:
        metrics, drills = analyser(points, fps, height_cm)
    except Exception:
        return {}
    if not metrics:
        return {}
    return {
        "sport": sport,
        "metrics": metrics,
        "labels": {k: LABELS.get(k, (k, ""))[0] for k in metrics},
        "units": {k: LABELS.get(k, (k, ""))[1] for k in metrics},
        "drills": drills,
        "note": CAMERA_NOTE,
    }
