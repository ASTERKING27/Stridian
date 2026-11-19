"""
Every sport's own scripts, and its video analyser on stick figures whose angles are known:
run with  python test_analysers.py  (numpy only — no video, no MediaPipe, no server).
"""

import math
import sys

import numpy as np

import pose_sports
import sports
import sports_config as sc
from sports.pose import (L_ANKLE, L_ELBOW, L_HIP, L_KNEE, L_SHOULDER, L_WRIST, NOSE, R_ANKLE,
                         R_ELBOW, R_HIP, R_KNEE, R_SHOULDER, R_WRIST, angle_at)

FPS = 30.0


def bend(top, bottom, angle, forward=1):
    """Where the middle joint goes so that top-middle-bottom makes `angle` degrees, both
    segments the same length, pushed out on the `forward` side (+1 is +x)."""
    (x0, y0), (x1, y1) = top, bottom
    d = math.hypot(x1 - x0, y1 - y0)
    if angle >= 179.9:
        return ((x0 + x1) / 2, (y0 + y1) / 2)
    half = d / 2
    length = half / math.sin(math.radians(angle) / 2)
    out = math.sqrt(max(0.0, length ** 2 - half ** 2))
    nx, ny = -(y1 - y0) / d, (x1 - x0) / d            # unit normal
    if nx * forward < 0:
        nx, ny = -nx, -ny
    return ((x0 + x1) / 2 + nx * out, (y0 + y1) / 2 + ny * out)


def figure(hip_x=0.5, hip_y=0.55, knees=(178, 178), feet=(-0.04, 0.04), feet_y=(0.9, 0.9),
           lean=0.0, arm=None, elbow=170):
    """One frame of a side-on body. `arm`: where the right wrist is (x, y), else hanging.
    `lean` tilts the shoulders forward by that many degrees from upright."""
    p = np.full((33, 2), np.nan)
    shoulder_y = hip_y - 0.25 * math.cos(math.radians(lean))
    shoulder_x = hip_x + 0.25 * math.sin(math.radians(lean))
    p[L_SHOULDER], p[R_SHOULDER] = (shoulder_x - 0.03, shoulder_y), (shoulder_x + 0.03, shoulder_y)
    p[NOSE] = (shoulder_x, shoulder_y - 0.1)
    p[L_HIP], p[R_HIP] = (hip_x - 0.03, hip_y), (hip_x + 0.03, hip_y)
    for (hip, knee, ankle), angle, dx, fy in zip(((L_HIP, L_KNEE, L_ANKLE), (R_HIP, R_KNEE, R_ANKLE)),
                                                knees, feet, feet_y):
        p[ankle] = (hip_x + dx, fy)
        p[knee] = bend(p[hip], p[ankle], angle, forward=1 if dx >= 0 else -1)
    for shoulder, elbow_j, wrist in ((L_SHOULDER, L_ELBOW, L_WRIST), (R_SHOULDER, R_ELBOW, R_WRIST)):
        hand = arm if (arm is not None and wrist == R_WRIST) else (p[shoulder][0], p[shoulder][1] + 0.22)
        p[wrist] = hand
        p[elbow_j] = bend(p[shoulder], hand, elbow if wrist == R_WRIST and arm is not None else 178)
    return p


def clip(frames):
    return np.stack(frames)


def run():
    # ---- every sport is a complete folder, and the shared tables are built from them
    assert [s.NAME for s in sports.ALL] == sc.sport_names()
    for sport in sports.ALL:
        for part in ("tests", "analyser", "nutrition", "card"):
            assert hasattr(sport, part), (sport.NAME, part)
        assert sport.LEVELS, sport.NAME
        assert set(sport.analyser.ROLES) == set(sport.tests.POSITIONS), sport.NAME
        assert set(sport.card.CARD["weights"]) == set(sport.tests.POSITIONS), sport.NAME
        assert sport.analyser.PITCH and sport.analyser.FOOTAGE and sport.analyser.SPEEDS, sport.NAME
        assert sc.NUTRITION[sport.NAME] == sport.nutrition.PROFILE
        for metric in sport.tests.METRICS:
            if metric["source"] == "test":
                assert metric["key"] in sport.tests.TIPS, (sport.NAME, metric["key"])
        assert sport.NAME in pose_sports.ANALYSERS, sport.NAME
    # a tip is the sport's own
    assert sc.tip("Football", "yoyoLevel") == sports.football.tests.TIPS["yoyoLevel"]
    assert sc.tip("Football", "heightCm").startswith("Fixed trait")
    assert sc.tip(None, "nope", "default") == "default"

    # ---- nobody in the clip: every analyser says nothing rather than failing
    empty = np.full((40, 33, 2), np.nan)
    for name in pose_sports.ANALYSERS:
        assert pose_sports.analyse(name, empty, FPS, 175) == {}, name

    # ---- tennis: a serve with a known knee bend, leg drive and arm at contact
    serve = [figure() for _ in range(6)]
    serve += [figure(hip_y=0.55 + 0.01 * i, knees=(178 - 12 * i, 178 - 12 * i)) for i in range(1, 6)]   # down to 118°
    serve += [figure(hip_y=0.60 - 0.01 * i, knees=(118 + 12 * i, 118 + 12 * i)) for i in range(1, 6)]   # drive up
    serve += [figure(arm=(0.53, 0.12), elbow=176)]                                                    # contact
    serve += [figure() for _ in range(5)]
    got = pose_sports.analyse("Tennis", clip(serve), FPS, 180)
    m = got["metrics"]
    assert m["hittingArm"] == "right" and m["contactElbowAngleDeg"] > 170, m
    assert abs(m["trophyKneeAngleDeg"] - 118) < 1.5, m
    assert abs(m["legDriveBodySpans"] - 0.05 / 0.7) < 0.01 and m["legDriveCm"] > 0, m
    assert not got["drills"], got["drills"]
    assert got["labels"]["trophyKneeAngleDeg"] == "Knee bend before the serve"
    # the same serve with stiff legs and a bent arm gets both drills
    stiff = [figure() for _ in range(15)] + [figure(arm=(0.60, 0.14), elbow=120)] + [figure() for _ in range(5)]
    found = {d["metric"] for d in pose_sports.analyse("Tennis", clip(stiff), FPS, 180)["drills"]}
    assert found == {"contactElbowAngleDeg", "trophyKneeAngleDeg"}, found
    # hands never above the head: a rally, not a serve — nothing to say
    assert pose_sports.analyse("Tennis", clip([figure() for _ in range(30)]), FPS, 180) == {}

    # ---- badminton: an overhead, then a lunge with the trunk folded and the knee collapsed
    rally = [figure() for _ in range(5)] + [figure(hip_y=0.50, arm=(0.53, 0.10), elbow=135)]
    rally += [figure() for _ in range(5)]
    lunge = dict(hip_y=0.66, feet=(-0.18, 0.18), knees=(178, 75), lean=45)
    rally += [figure(**lunge) for _ in range(3)] + [figure() for _ in range(5)]
    got = pose_sports.analyse("Badminton", clip(rally), FPS, 170)
    m = got["metrics"]
    assert m["racketArm"] == "right" and abs(m["contactElbowAngleDeg"] - 135) < 1, m
    assert m["jumpAtContactBodySpans"] > 0.05 and m["jumpAtContactCm"] > 0, m
    assert abs(m["lungeKneeAngleDeg"] - 75) < 1 and abs(m["lungeTrunkLeanDeg"] - 45) < 1, m
    assert abs(m["lungeStrideBodySpans"] - 0.36 / 0.7) < 0.02, m
    found = {d["metric"] for d in got["drills"]}
    assert found == {"contactElbowAngleDeg", "lungeTrunkLeanDeg", "lungeKneeAngleDeg"}, found
    # a running stride (back foot in the air) is not a lunge
    stride = [figure() for _ in range(5)] + [figure(hip_y=0.6, feet=(-0.18, 0.18), feet_y=(0.82, 0.9),
                                                    knees=(150, 100)) for _ in range(3)]
    assert "lungeKneeAngleDeg" not in (pose_sports.analyse("Badminton", clip(stride), FPS, 170).get("metrics") or {})

    # ---- kho-kho: out, back and out again — two turns, low ones, at a known speed
    path = [0.2 + 0.02 * i for i in range(20)] + [0.6 - 0.02 * i for i in range(1, 20)] + \
           [0.22 + 0.02 * i for i in range(1, 20)]
    turns = {19, 38}
    chase = [figure(hip_x=x, knees=(100, 100) if i in turns else (170, 170)) for i, x in enumerate(path)]
    m = pose_sports.analyse("Kho-Kho", clip(chase), FPS, 165)["metrics"]
    assert m["directionChanges"] == 2, m
    assert abs(m["turnKneeAngleDeg"] - 100) < 1 and abs(m["crouchKneeAngleDeg"] - 100) < 1, m
    assert abs(m["topSpeedBodySpansPerSec"] - 0.02 * FPS / 0.7) < 0.05, m
    # the same chase turning tall gets the drill
    tall = [figure(hip_x=x, knees=(172, 172)) for x in path]
    got = pose_sports.analyse("Kho-Kho", clip(tall), FPS, 165)
    assert [d["metric"] for d in got["drills"]] == ["turnKneeAngleDeg"], got["drills"]
    # a wobble on the spot is no change of direction
    wobble = [figure(hip_x=0.5 + 0.01 * (-1) ** i) for i in range(40)]
    assert pose_sports.analyse("Kho-Kho", clip(wobble), FPS, 165)["metrics"]["directionChanges"] == 0

    # ---- the four analysers from before still read their moment the same way
    kick = [figure() for _ in range(5)]
    kick += [figure(feet=(-0.04, 0.04 + 0.08 * i)) for i in range(1, 4)] + [figure() for _ in range(5)]
    m = pose_sports.analyse("Football", clip(kick), FPS, 175)["metrics"]
    assert m["strikeFoot"] == "right", m
    shot = [figure() for _ in range(5)] + [figure(arm=(0.53, 0.12), elbow=125)] + [figure(arm=(0.53, 0.3))] * 8
    m = pose_sports.analyse("Basketball", clip(shot), FPS, 190)["metrics"]
    assert abs(m["releaseElbowAngleDeg"] - 125) < 1, m
    assert abs(angle_at((0, 0), (1, 0), (1, 1)) - 90) < 1e-9
    print("analysers: ok")


if __name__ == "__main__":
    sys.exit(run())
