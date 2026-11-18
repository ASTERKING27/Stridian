"""
Kho-Kho: the tests a coach records, and the positions they are read against.

Every test carries a poor -> elite pair, which turns a raw number into a 0-100 score
wherever the sport has no level ladder for it (levels.json holds those). The weights are
the starting ones: they are seeded into the database on first run and edited from the app
after that, so changing one here changes what "Reset to defaults" gives back.
"""

from sports.kit import HEIGHT, M

NOTE = "Based on published Indian academic and SAI testing studies."

METRICS = [
    M("sprint30m", "30m Dash", "sec", "lower", 5.40, 4.00),
    M("shuttleRun", "Shuttle Run (4x10m)", "sec", "lower", 12.0, 9.0),
    M("standingBroadJump", "Standing Broad Jump", "m", "higher", 1.70, 2.80),
    M("sitAndReach", "Sit and Reach", "cm", "higher", 10, 40),
    HEIGHT(150, 185),
]

POSITIONS = {
    "Chaser": {
        "blurb": "Pole dives, direction changes and the sitting-to-sprint transition. Flexibility matters here.",
        "weights": {"shuttleRun": 0.35, "sitAndReach": 0.25, "sprint30m": 0.25, "standingBroadJump": 0.15},
    },
    "Runner / Dodger": {
        "blurb": "Survives as long as possible in the square. Straight-line speed plus evasive footwork.",
        "weights": {"sprint30m": 0.35, "shuttleRun": 0.30, "standingBroadJump": 0.20, "sitAndReach": 0.15},
    },
}

# What to do about a test the player scores badly on.
TIPS = {
    "sprint30m": "Short sprint repeats (10-30m) with full recovery, plus acceleration-mechanics work.",
    "shuttleRun": "Repeat 5-10-5 shuttles, working on the turn rather than the run.",
    "standingBroadJump": "Horizontal plyometrics - broad jumps, bounds, single-leg hops.",
    "sitAndReach": "Daily hamstring and lower-back mobility routine, held 30-45 seconds per stretch.",
}

# Measured traits no training changes (a reach, a wingspan): this battery has none.
FIXED = set()
