"""
Tennis: the tests a coach records, and the positions they are read against.

Every test carries a poor -> elite pair, which turns a raw number into a 0-100 score
wherever the sport has no level ladder for it (levels.json holds those). The weights are
the starting ones: they are seeded into the database on first run and edited from the app
after that, so changing one here changes what "Reset to defaults" gives back.
"""

from sports.kit import HEIGHT, M

NOTE = "Starts with the same racket-sport battery as badminton: sprint, jump, grip, on-court agility and aerobic level."

METRICS = [
    M("sprint20m", "20m Sprint", "sec", "lower", 3.80, 2.90),
    M("verticalJump", "Vertical Jump", "cm", "higher", 30, 65),
    M("handGrip", "Hand-grip Strength", "kg", "higher", 25, 60),
    # Timed with the Spider run, which covers the whole baseline half of the court and takes
    # longer than badminton's court test.
    # ponytail: the protocol is our pick until the coaches confirm theirs; the key stays the
    # same as badminton's, so switching it back is this one entry.
    M("onCourtAgility", "Spider Run (on-court agility)", "sec", "lower", 20.0, 15.5,
      basis="published", authority="Tennis Spider run",
      note="Five sprints out from the centre of the baseline to the court's lines and back. "
      "College players run about 18 s; elite junior boys about 18 s, girls about 19 s."),
    M("yoyoLevel", "Yo-Yo / Aerobic Test Level", "level", "higher", 13.0, 20.0),
    HEIGHT(155, 195),
]

POSITIONS = {
    "Attacking / Power player": {
        "blurb": "Ends rallies early with smashes and flat drives. Jump height and grip strength lead.",
        "weights": {"verticalJump": 0.30, "handGrip": 0.30, "sprint20m": 0.20, "onCourtAgility": 0.15,
                    "yoyoLevel": 0.05},
    },
    "Defensive / Counter player": {
        "blurb": "Wins by retrieving everything. Court coverage and aerobic capacity are the weapons.",
        "weights": {"onCourtAgility": 0.35, "yoyoLevel": 0.30, "sprint20m": 0.20, "verticalJump": 0.10,
                    "handGrip": 0.05},
    },
    "All-court / Balanced": {
        "blurb": "Switches styles mid-match. Wants an even spread with no obvious hole.",
        "weights": {"onCourtAgility": 0.25, "sprint20m": 0.20, "yoyoLevel": 0.20, "verticalJump": 0.20,
                    "handGrip": 0.15},
    },
}

# What to do about a test the player scores badly on.
TIPS = {
    "sprint20m": "Short sprint repeats with full recovery and start-technique drills.",
    "verticalJump": "Plyometrics plus heavy lower-body strength work (squat, trap-bar deadlift).",
    "handGrip": "Grip work - farmer's carries, dead hangs, grip trainers.",
    "onCourtAgility": "Sport-specific shadow footwork and multi-directional movement patterns.",
    "yoyoLevel": "Interval running (4x4 min at high intensity) plus tempo runs to build the aerobic base.",
}

# Measured traits no training changes (a reach, a wingspan): this battery has none.
FIXED = set()
