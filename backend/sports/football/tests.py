"""
Football: the tests a coach records, and the positions they are read against.

Every test carries a poor -> elite pair, which turns a raw number into a 0-100 score
wherever the sport has no level ladder for it (levels.json holds those). The weights are
the starting ones: they are seeded into the database on first run and edited from the app
after that, so changing one here changes what "Reset to defaults" gives back.
"""

from sports.kit import HEIGHT, M

NOTE = "Standard field-testing battery used by professional and national football setups."

METRICS = [
    M("sprint30m", "30m Sprint", "sec", "lower", 5.20, 3.90,
      basis="published", authority="Standard field protocol",
      note="Elite senior players are typically around 4.0 s; the elite anchor here reflects that."),
    M("cmj", "Countermovement Jump (CMJ)", "cm", "higher", 28, 55,
      basis="published", authority="Force-plate / jump-mat protocol",
      note="Professional outfield players commonly sit in the 38-45 cm band."),
    M("agilityTtest", "Agility (T-test)", "sec", "lower", 12.0, 9.0,
      basis="estimated", authority="Semenick T-test protocol",
      note="Protocol is standard; the range is a starting point - retune on your own timing gates."),
    M("yoyoLevel", "Yo-Yo IR1 Level", "level", "higher", 14.0, 21.0,
      basis="published", authority="Bangsbo Yo-Yo IR1",
      note="Professional outfield players usually reach level 20-21."),
    HEIGHT(160, 195),
]

POSITIONS = {
    "Goalkeeper": {
        "blurb": "Owns the box. Needs reach, a fast standing jump and sharp reactions more than running volume.",
        "weights": {"heightCm": 0.30, "cmj": 0.30, "agilityTtest": 0.25, "sprint30m": 0.10, "yoyoLevel": 0.05},
    },
    "Centre-back": {
        "blurb": "Wins the ball in the air and holds the line. Height and jump dominate, with enough pace to cover.",
        "weights": {"heightCm": 0.30, "cmj": 0.25, "sprint30m": 0.20, "yoyoLevel": 0.15, "agilityTtest": 0.10},
    },
    "Full-back": {
        "blurb": "Up and down the touchline for 90 minutes. Endurance plus repeatable sprint speed.",
        "weights": {"yoyoLevel": 0.30, "sprint30m": 0.30, "agilityTtest": 0.25, "cmj": 0.10, "heightCm": 0.05},
    },
    "Central Midfielder": {
        "blurb": "Covers the most ground on the pitch. Aerobic capacity first, everything else second.",
        "weights": {"yoyoLevel": 0.40, "agilityTtest": 0.25, "sprint30m": 0.20, "cmj": 0.10, "heightCm": 0.05},
    },
    "Winger": {
        "blurb": "Beats a defender one-on-one. Top-end speed and change of direction are the whole job.",
        "weights": {"sprint30m": 0.40, "agilityTtest": 0.30, "yoyoLevel": 0.15, "cmj": 0.10, "heightCm": 0.05},
    },
    "Striker": {
        "blurb": "Finishes chances. Explosive over 5-30m, strong in the air, doesn't need midfield lungs.",
        "weights": {"sprint30m": 0.30, "cmj": 0.25, "agilityTtest": 0.20, "heightCm": 0.15, "yoyoLevel": 0.10},
    },
}

# What to do about a test the player scores badly on.
TIPS = {
    "sprint30m": "Short sprint repeats (10-30m) with full recovery, plus acceleration-mechanics work.",
    "cmj": "Plyometrics - box jumps, depth jumps, squat jumps - twice a week on fresh legs.",
    "agilityTtest": "Cone and ladder drills with a focus on deceleration and plant-foot mechanics.",
    "yoyoLevel": "Interval running (4x4 min at high intensity) plus tempo runs to build the aerobic base.",
}

# Measured traits no training changes (a reach, a wingspan): this battery has none.
FIXED = set()
