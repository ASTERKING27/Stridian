"""
Basketball: the tests a coach records, and the positions they are read against.

Every test carries a poor -> elite pair, which turns a raw number into a 0-100 score
wherever the sport has no level ladder for it (levels.json holds those). The weights are
the starting ones: they are seeded into the database on first run and edited from the app
after that, so changing one here changes what "Reset to defaults" gives back.
"""

from sports.kit import HEIGHT, M

NOTE = "Based on the NBA Draft Combine testing protocol."

METRICS = [
    M("wingspan", "Wingspan", "cm", "higher", 170, 220,
      basis="published", authority="NBA Draft Combine anthropometrics"),
    M("standingReach", "Standing Reach", "cm", "higher", 220, 280,
      basis="published", authority="NBA Draft Combine anthropometrics"),
    M("laneAgility", "Lane Agility", "sec", "lower", 12.5, 10.3,
      basis="published", authority="NBA Draft Combine",
      note="Combine participants cluster around 11.0-11.5 s."),
    M("shuttleRun", "Shuttle Run (3/4 court)", "sec", "lower", 3.40, 2.85,
      basis="published", authority="NBA Draft Combine",
      note="The Combine's three-quarter-court sprint."),
    M("standingVertical", "Standing Vertical Leap", "cm", "higher", 45, 90,
      basis="published", authority="NBA Draft Combine"),
    M("maxVertical", "Max Vertical Leap (run-up)", "cm", "higher", 55, 105,
      basis="published", authority="NBA Draft Combine"),
    HEIGHT(165, 215),
]

POSITIONS = {
    "Point Guard": {
        "blurb": "Brings the ball up and creates. Lateral quickness and first-step speed outweigh size.",
        "weights": {"laneAgility": 0.30, "shuttleRun": 0.30, "maxVertical": 0.15, "standingVertical": 0.10,
                    "heightCm": 0.05, "wingspan": 0.05, "standingReach": 0.05},
    },
    "Shooting Guard": {
        "blurb": "Scores off movement. Needs elevation to shoot over closeouts plus guard-level agility.",
        "weights": {"maxVertical": 0.25, "laneAgility": 0.20, "shuttleRun": 0.20, "standingVertical": 0.15,
                    "heightCm": 0.10, "wingspan": 0.10},
    },
    "Small Forward": {
        "blurb": "The all-rounder. Balanced size, reach and explosiveness - no single dominant trait.",
        "weights": {"heightCm": 0.20, "wingspan": 0.20, "maxVertical": 0.20, "laneAgility": 0.15,
                    "standingVertical": 0.15, "shuttleRun": 0.10},
    },
    "Power Forward": {
        "blurb": "Works in traffic. Standing jump and frame matter more than run-up leaping.",
        "weights": {"heightCm": 0.25, "wingspan": 0.20, "standingReach": 0.20, "standingVertical": 0.20,
                    "maxVertical": 0.10, "laneAgility": 0.05},
    },
    "Centre": {
        "blurb": "Protects the rim and rebounds. Standing reach is the single biggest predictor here.",
        "weights": {"standingReach": 0.30, "heightCm": 0.30, "wingspan": 0.25, "standingVertical": 0.10,
                    "maxVertical": 0.05},
    },
}

# What to do about a test the player scores badly on.
TIPS = {
    "wingspan": "Fixed anthropometric trait - not trainable, build technique around it.",
    "standingReach": "Fixed anthropometric trait - not trainable, build technique around it.",
    "laneAgility": "Lateral shuffle and drop-step drills, plus hip-mobility work.",
    "shuttleRun": "Repeat 5-10-5 shuttles, working on the turn rather than the run.",
    "standingVertical": "Standing-jump plyometrics and hip-extension strength work.",
    "maxVertical": "Approach-jump technique (penultimate step) plus plyometric leg power.",
}

# Measured traits no training changes: never a weekly focus or a level-up to chase.
FIXED = {"wingspan", "standingReach"}
