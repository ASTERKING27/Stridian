"""
Volleyball: the tests a coach records, and the positions they are read against.

Every test carries a poor -> elite pair, which turns a raw number into a 0-100 score
wherever the sport has no level ladder for it (levels.json holds those). The weights are
the starting ones: they are seeded into the database on first run and edited from the app
after that, so changing one here changes what "Reset to defaults" gives back.
"""

from sports.kit import HEIGHT, M

NOTE = "Based on national-team combine testing (FIVB-aligned protocols)."

METRICS = [
    M("standingReach", "Standing Reach (one-hand)", "cm", "higher", 210, 260,
      basis="published", authority="FIVB-aligned combine testing"),
    M("blockTouch", "Block Touch Height", "cm", "higher", 260, 350,
      basis="published", authority="FIVB-aligned combine testing",
      note="Men's net is 2.43 m, women's 2.24 m — block touch is judged against the net height in play."),
    M("spikeTouch", "Spike Touch Height (with approach)", "cm", "higher", 275, 370,
      basis="published", authority="FIVB-aligned combine testing"),
    M("proAgility", "Pro Agility (5-10-5)", "sec", "lower", 5.50, 4.20,
      basis="estimated", authority="5-10-5 shuttle protocol"),
    M("serveVelocity", "Serve Velocity", "km/h", "higher", 60, 120,
      basis="published", authority="Match radar norms"),
    M("attackVelocity", "Attack / Spike Velocity", "km/h", "higher", 70, 130,
      basis="published", authority="Match radar norms"),
    HEIGHT(160, 210),
]

POSITIONS = {
    "Setter": {
        "blurb": "Touches the second ball every rally. Footwork and court coverage come before power.",
        "weights": {"proAgility": 0.35, "standingReach": 0.20, "blockTouch": 0.15, "heightCm": 0.15,
                    "spikeTouch": 0.10, "serveVelocity": 0.05},
    },
    "Libero": {
        "blurb": "Back-court defence specialist. Pure reaction and agility - height is close to irrelevant.",
        "weights": {"proAgility": 0.60, "serveVelocity": 0.15, "standingReach": 0.10, "heightCm": 0.10,
                    "spikeTouch": 0.05},
    },
    "Outside Hitter": {
        "blurb": "Main attacking option. Spike reach and arm speed carry the position.",
        "weights": {"attackVelocity": 0.30, "spikeTouch": 0.30, "heightCm": 0.15, "proAgility": 0.10,
                    "blockTouch": 0.10, "serveVelocity": 0.05},
    },
    "Middle Blocker": {
        "blurb": "Lives at the net. Block touch and standing reach decide how much of the net gets covered.",
        "weights": {"blockTouch": 0.35, "heightCm": 0.25, "standingReach": 0.20, "spikeTouch": 0.10,
                    "attackVelocity": 0.05, "proAgility": 0.05},
    },
    "Opposite / Server": {
        "blurb": "Points from the service line and the right side. Raw arm velocity is the differentiator.",
        "weights": {"serveVelocity": 0.40, "attackVelocity": 0.25, "spikeTouch": 0.15, "heightCm": 0.10,
                    "proAgility": 0.10},
    },
}

# What to do about a test the player scores badly on.
TIPS = {
    "standingReach": "Fixed anthropometric trait - not trainable, build technique around it.",
    "blockTouch": "Net timing drills and standing-jump power.",
    "spikeTouch": "Approach-jump technique and reach mechanics at the top of the jump.",
    "proAgility": "5-10-5 shuttle repeats and cutting-mechanics drills.",
    "serveVelocity": "Shoulder external/internal rotation strength and arm-speed drills.",
    "attackVelocity": "Approach-jump timing plus arm-swing speed and core rotational power.",
}

# Measured traits no training changes: never a weekly focus or a level-up to chase.
FIXED = {"standingReach"}
