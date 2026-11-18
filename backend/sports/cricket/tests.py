"""
Cricket: the tests a coach records, and the positions they are read against.

Every test carries a poor -> elite pair, which turns a raw number into a 0-100 score
wherever the sport has no level ladder for it (levels.json holds those). The weights are
the starting ones: they are seeded into the database on first run and edited from the app
after that, so changing one here changes what "Reset to defaults" gives back.
"""

from sports.kit import HEIGHT, M

NOTE = "Based on BCCI / National Cricket Academy fitness criteria for Indian selection."

METRICS = [
    M("yoyoLevel", "Yo-Yo Test Level", "level", "higher", 13.0, 19.5,
      basis="standard", authority="BCCI / NCA",
      note="India's senior selection bar has been reported at level 17.1 — "
           "that is the number that matters, not the range ends."),
    M("timeTrial2km", "2km Time Trial", "sec", "lower", 600, 450,
      basis="standard", authority="BCCI / NCA",
      note="Reported BCCI targets: about 8:30 for batters and keepers, 8:15 for fast bowlers."),
    M("sprint20m", "20m Sprint", "sec", "lower", 3.60, 2.80,
      basis="estimated", authority="Standard field protocol",
      note="Running between the wickets; retune against your own timing gates."),
    M("bowlingSpeed", "Bowling Speed", "km/h", "higher", 90, 150,
      basis="published", authority="Match speed-gun norms",
      note="International fast bowlers operate around 135-145 km/h."),
    HEIGHT(160, 195),
]

POSITIONS = {
    "Opening Batsman": {
        "blurb": "Faces the new ball and turns ones into twos. Short-sprint speed above all.",
        "weights": {"sprint20m": 0.40, "yoyoLevel": 0.25, "timeTrial2km": 0.20, "heightCm": 0.15},
    },
    "Middle-order Batsman": {
        "blurb": "Bats long and runs hard in the middle overs. Endurance-weighted profile.",
        "weights": {"yoyoLevel": 0.35, "sprint20m": 0.30, "timeTrial2km": 0.30, "heightCm": 0.05},
    },
    "Fast Bowler": {
        "blurb": "Bowls long spells at pace. Speed plus the aerobic base to repeat it.",
        "weights": {"bowlingSpeed": 0.40, "heightCm": 0.20, "timeTrial2km": 0.20, "yoyoLevel": 0.15,
                    "sprint20m": 0.05},
    },
    "Spin Bowler": {
        "blurb": "Bowls into the wind all day. Stamina and fielding mobility, not raw pace.",
        "weights": {"yoyoLevel": 0.35, "timeTrial2km": 0.30, "sprint20m": 0.20, "heightCm": 0.10,
                    "bowlingSpeed": 0.05},
    },
    "Wicketkeeper": {
        "blurb": "Up and down behind the stumps for the full innings. Quick feet, high work rate.",
        "weights": {"sprint20m": 0.35, "yoyoLevel": 0.30, "timeTrial2km": 0.20, "heightCm": 0.15},
    },
    "All-rounder": {
        "blurb": "Does two jobs in one match. Needs a flat, high profile with no weak link.",
        "weights": {"yoyoLevel": 0.30, "bowlingSpeed": 0.25, "sprint20m": 0.20, "timeTrial2km": 0.20,
                    "heightCm": 0.05},
    },
}

# What to do about a test the player scores badly on.
TIPS = {
    "yoyoLevel": "Interval running (4x4 min at high intensity) plus tempo runs to build the aerobic base.",
    "timeTrial2km": "Threshold and tempo running 2-3 times a week; build weekly volume gradually.",
    "sprint20m": "Short sprint repeats with full recovery and start-technique drills.",
    "bowlingSpeed": "Run-up rhythm and front-arm mechanics with a coach, plus medicine-ball rotational power.",
}

# Measured traits no training changes (a reach, a wingspan): this battery has none.
FIXED = set()
