"""
Sport definitions for Stridian.

Every sport declares:
  - `metrics`: the measurable inputs used to judge a player. Each metric carries a
    `poor`/`elite` reference pair, which is what turns a raw number (e.g. "4.4 sec")
    into a 0-100 score. `poor` may be numerically larger than `elite` (sprint times,
    agility times) - the scoring maths handles both directions from these two numbers
    alone, so `direction` is only used for labelling in the UI.
  - `positions`: each position has a weight profile over the metric keys. Weights are
    *defaults*; they are seeded into the database on first run and can be edited from
    the app afterwards (see models.PositionWeight).

`source` tells the backend where a metric's value comes from:
  - "test"    -> entered by the coach as a test result
  - "profile" -> read off the student's own profile (height, weight)
"""


def M(key, label, unit, direction, poor, elite, source="test",
      basis="estimated", authority="", note=""):
    """One measurable input.

    `basis` is deliberately explicit, because "is this an international standard?" is a
    fair question to ask of every number in this file and the answer differs per row:

      "standard"  - the number itself is an official threshold published by a governing
                    body (BCCI's Yo-Yo 17.1, the ICC's 15-degree elbow limit, the
                    19.8 / 25.2 km/h high-speed-running and sprint thresholds).
      "published" - drawn from widely reported norms for the level concerned. Good
                    enough to judge against, not an official pass mark.
      "estimated" - a sensible starting point set for this app. The test itself is
                    still the real protocol; only the poor -> elite range is ours, and
                    a coach should retune it from the Weights tab against their own
                    squad and camera setup.

    The app shows this next to every metric, so nobody mistakes a starting point for a
    selection standard.
    """
    return {
        "key": key,
        "label": label,
        "unit": unit,
        "direction": direction,  # "higher" or "lower" is better - display only
        "poor": poor,
        "elite": elite,
        "source": source,
        "basis": basis,
        "authority": authority,
        "note": note,
    }


HEIGHT = lambda poor, elite: M("heightCm", "Height", "cm", "higher", poor, elite, "profile")
WEIGHT = lambda poor, elite: M("weightKg", "Weight", "kg", "higher", poor, elite, "profile")


SPORTS = {
    "Football": {
        "note": "Standard field-testing battery used by professional and national football setups.",
        "metrics": [
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
        ],
        "positions": {
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
        },
    },

    "Basketball": {
        "note": "Based on the NBA Draft Combine testing protocol.",
        "metrics": [
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
        ],
        "positions": {
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
        },
    },

    "Volleyball": {
        "note": "Based on national-team combine testing (FIVB-aligned protocols).",
        "metrics": [
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
        ],
        "positions": {
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
        },
    },

    "Cricket": {
        "note": "Based on BCCI / National Cricket Academy fitness criteria for Indian selection.",
        "metrics": [
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
        ],
        "positions": {
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
        },
    },

    "Badminton / Tennis": {
        "note": "Based on BWF-aligned national junior and squad testing programmes.",
        "metrics": [
            M("sprint20m", "20m Sprint", "sec", "lower", 3.80, 2.90),
            M("verticalJump", "Vertical Jump", "cm", "higher", 30, 65),
            M("handGrip", "Hand-grip Strength", "kg", "higher", 25, 60),
            M("onCourtAgility", "On-court Agility Test", "sec", "lower", 18.0, 11.0),
            M("yoyoLevel", "Yo-Yo / Aerobic Test Level", "level", "higher", 13.0, 20.0),
            HEIGHT(155, 195),
        ],
        "positions": {
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
        },
    },

    "Kho-Kho": {
        "note": "Based on published Indian academic and SAI testing studies.",
        "metrics": [
            M("sprint30m", "30m Dash", "sec", "lower", 5.40, 4.00),
            M("shuttleRun", "Shuttle Run (4x10m)", "sec", "lower", 12.0, 9.0),
            M("standingBroadJump", "Standing Broad Jump", "m", "higher", 1.70, 2.80),
            M("sitAndReach", "Sit and Reach", "cm", "higher", 10, 40),
            HEIGHT(150, 185),
        ],
        "positions": {
            "Chaser": {
                "blurb": "Pole dives, direction changes and the sitting-to-sprint transition. Flexibility matters here.",
                "weights": {"shuttleRun": 0.35, "sitAndReach": 0.25, "sprint30m": 0.25, "standingBroadJump": 0.15},
            },
            "Runner / Dodger": {
                "blurb": "Survives as long as possible in the square. Straight-line speed plus evasive footwork.",
                "weights": {"sprint30m": 0.35, "shuttleRun": 0.30, "standingBroadJump": 0.20, "sitAndReach": 0.15},
            },
        },
    },
}


# Training advice shown for a metric the player scores badly on.
TRAINING_TIPS = {
    "sprint30m": "Short sprint repeats (10-30m) with full recovery, plus acceleration-mechanics work.",
    "sprint20m": "Short sprint repeats with full recovery and start-technique drills.",
    "cmj": "Plyometrics - box jumps, depth jumps, squat jumps - twice a week on fresh legs.",
    "verticalJump": "Plyometrics plus heavy lower-body strength work (squat, trap-bar deadlift).",
    "standingVertical": "Standing-jump plyometrics and hip-extension strength work.",
    "maxVertical": "Approach-jump technique (penultimate step) plus plyometric leg power.",
    "standingBroadJump": "Horizontal plyometrics - broad jumps, bounds, single-leg hops.",
    "agilityTtest": "Cone and ladder drills with a focus on deceleration and plant-foot mechanics.",
    "laneAgility": "Lateral shuffle and drop-step drills, plus hip-mobility work.",
    "shuttleRun": "Repeat 5-10-5 shuttles, working on the turn rather than the run.",
    "onCourtAgility": "Sport-specific shadow footwork and multi-directional movement patterns.",
    "proAgility": "5-10-5 shuttle repeats and cutting-mechanics drills.",
    "yoyoLevel": "Interval running (4x4 min at high intensity) plus tempo runs to build the aerobic base.",
    "timeTrial2km": "Threshold and tempo running 2-3 times a week; build weekly volume gradually.",
    "handGrip": "Grip work - farmer's carries, dead hangs, grip trainers.",
    "sitAndReach": "Daily hamstring and lower-back mobility routine, held 30-45 seconds per stretch.",
    "bowlingSpeed": "Run-up rhythm and front-arm mechanics with a coach, plus medicine-ball rotational power.",
    "serveVelocity": "Shoulder external/internal rotation strength and arm-speed drills.",
    "attackVelocity": "Approach-jump timing plus arm-swing speed and core rotational power.",
    "blockTouch": "Net timing drills and standing-jump power.",
    "spikeTouch": "Approach-jump technique and reach mechanics at the top of the jump.",
    "standingReach": "Fixed anthropometric trait - not trainable, build technique around it.",
    "wingspan": "Fixed anthropometric trait - not trainable, build technique around it.",
    "heightCm": "Fixed trait - not trainable. Pick a role that suits the frame.",
    "weightKg": "Adjust through structured strength training and nutrition with qualified guidance.",
}


# Energy and macro targets per sport, in grams (or kcal) per kg of bodyweight per day.
# Ranges follow general sports-nutrition guidance for athletes in regular training:
# endurance-dominant sports sit higher on carbohydrate, power sports higher on protein.
# These are starting points for a coach to adjust, not prescriptions.
# Tuned so that carbohydrate lands around 50-55% of energy, protein 13-16% and fat
# 25-33% — the usual split for a training athlete. nutrition.py clamps fat into that
# band and trims carbohydrate if the numbers ever drift.
NUTRITION = {
    "Football":           {"kcal_per_kg": 46, "carb_g_per_kg": 6.5, "protein_g_per_kg": 1.6, "style": "endurance"},
    "Basketball":         {"kcal_per_kg": 45, "carb_g_per_kg": 6.0, "protein_g_per_kg": 1.7, "style": "mixed"},
    "Volleyball":         {"kcal_per_kg": 43, "carb_g_per_kg": 5.5, "protein_g_per_kg": 1.7, "style": "power"},
    "Cricket":            {"kcal_per_kg": 41, "carb_g_per_kg": 5.5, "protein_g_per_kg": 1.6, "style": "mixed"},
    "Badminton / Tennis": {"kcal_per_kg": 45, "carb_g_per_kg": 6.0, "protein_g_per_kg": 1.6, "style": "endurance"},
    "Kho-Kho":            {"kcal_per_kg": 45, "carb_g_per_kg": 6.0, "protein_g_per_kg": 1.6, "style": "endurance"},
}


# ===========================================================================
# Match-footage layer
#
# The metrics below come from the YOLO lane (match_video.py) rather than a
# testing session, so they carry source="match" and the engine can score them on
# their own, separately from the test battery.
#
# Units are body-heights rather than metres: a player's own bounding-box height is
# the ruler, which keeps the numbers comparable across zoom levels and camera
# angles without any calibration. The ranges are starting points for a coach to
# tune from the Weights tab once they have footage from their own setup — framing
# and camera distance shift them more than anything about the players.
#
# The positional pair (matchAdvanced / matchDeepness, measured against where the
# other players on screen are) is only included for sports whose play really does
# run along one axis in normal footage. For court sports where teams swap ends
# every few seconds it would be noise dressed up as a number, so it is left out.
# ===========================================================================

MATCH_RANGES = {
    "field": {  # Football
        "matchDistance": (25, 75), "matchTopSpeed": (1.8, 4.5), "matchSprints": (0.2, 1.6),
        "matchWorkRate": (35, 80), "matchWidth": (8, 55), "matchAdvanced": (20, 80),
        # the mirror of work rate, carried only here: being deep *and* still is what
        # separates a goalkeeper from a centre-back, who is deep and covers ground
        "matchStationary": (20, 65),
    },
    "court": {  # Basketball, Volleyball, Badminton / Tennis
        "matchDistance": (20, 65), "matchTopSpeed": (1.5, 4.0), "matchSprints": (0.3, 2.0),
        "matchWorkRate": (40, 85), "matchWidth": (10, 60),
    },
    "cricket": {
        "matchDistance": (8, 45), "matchTopSpeed": (1.5, 4.2), "matchSprints": (0.1, 1.0),
        "matchWorkRate": (15, 60), "matchWidth": (5, 50),
    },
    "khokho": {
        "matchDistance": (30, 90), "matchTopSpeed": (2.0, 5.0), "matchSprints": (0.5, 2.5),
        "matchWorkRate": (45, 90), "matchWidth": (10, 55), "matchAdvanced": (20, 80),
    },
}

# --------------------------------------------------------------------------- #
# Calibrated (real-world) match metrics
#
# These only exist once a coach has marked out the pitch on the keyframe. With a
# homography in place the tracker's pixel positions become metres, and the numbers
# below are then directly comparable to the ones a GPS vest would produce — which is
# what makes them usable against international benchmarks rather than only against
# team-mates in the same clip.
#
# The high-speed-running and sprint thresholds are the standard ones for football
# (19.8 and 25.2 km/h). Court sports run on lower thresholds because the distances and
# top speeds are smaller; those are widely used rather than officially fixed.
# --------------------------------------------------------------------------- #

SPEED_THRESHOLDS = {
    #                     high-speed running, sprint   (km/h)
    "field":   {"hsr": 19.8, "sprint": 25.2, "basis": "standard"},
    "court":   {"hsr": 14.4, "sprint": 18.0, "basis": "published"},
    "cricket": {"hsr": 15.0, "sprint": 20.0, "basis": "estimated"},
    "khokho":  {"hsr": 15.0, "sprint": 20.0, "basis": "estimated"},
}

CALIBRATED_RANGES = {
    "field": {
        "matchMetresPerMin": (70, 125),
        "matchTopSpeedKmh": (22, 33),
        "matchHsrPerMin": (1.0, 10.0),
        "matchSprintMetresPerMin": (0.2, 3.5),
        "matchAccelPerMin": (0.3, 1.5),
    },
    "court": {
        "matchMetresPerMin": (40, 90),
        "matchTopSpeedKmh": (15, 26),
        "matchHsrPerMin": (0.5, 6.0),
        "matchSprintMetresPerMin": (0.1, 2.0),
        "matchAccelPerMin": (0.5, 2.5),
    },
    "cricket": {
        "matchMetresPerMin": (15, 70),
        "matchTopSpeedKmh": (15, 30),
        "matchHsrPerMin": (0.2, 5.0),
        "matchSprintMetresPerMin": (0.1, 2.0),
        "matchAccelPerMin": (0.1, 1.0),
    },
    "khokho": {
        "matchMetresPerMin": (60, 140),
        "matchTopSpeedKmh": (18, 30),
        "matchHsrPerMin": (1.0, 12.0),
        "matchSprintMetresPerMin": (0.5, 5.0),
        "matchAccelPerMin": (1.0, 4.0),
    },
}

CALIBRATED_LABELS = {
    "matchMetresPerMin": ("Distance covered", "m/min", "higher", "published",
                          "Elite senior footballers average roughly 105-120 m/min in match play."),
    "matchTopSpeedKmh": ("Top speed", "km/h", "higher", "published",
                         "Elite senior footballers peak around 33-36 km/h."),
    "matchHsrPerMin": ("High-speed running", "m/min", "higher", "standard",
                       "Distance above the high-speed threshold for this sport."),
    "matchSprintMetresPerMin": ("Sprint distance", "m/min", "higher", "standard",
                                "Distance above the sprint threshold for this sport."),
    "matchAccelPerMin": ("Accelerations", "per min", "higher", "estimated",
                         "Bursts above 3 m/s squared — a proxy for repeated-effort load."),
}

UNCAL = "Scale-free fallback used when the clip has no pitch calibration."

MATCH_LABELS = {
    "matchDistance": ("Distance covered (uncalibrated)", "body-heights/min", "higher", "estimated", UNCAL),
    "matchTopSpeed": ("Top speed (uncalibrated)", "body-heights/sec", "higher", "estimated", UNCAL),
    "matchSprints": ("Sprints (uncalibrated)", "per minute", "higher", "estimated", UNCAL),
    "matchWorkRate": ("Active time", "%", "higher", "estimated",
                      "Share of the clip spent moving rather than standing."),
    "matchWidth": ("Width of area used", "%", "higher", "estimated",
                   "Lateral span as a share of the frame."),
    "matchAdvanced": ("Attacking positioning", "%", "higher", "estimated",
                      "Measured against where the other players on screen are, not against the pitch."),
    "matchDeepness": ("Defensive positioning", "%", "higher", "estimated",
                      "The mirror of attacking positioning, so deep roles score positively."),
    "matchStationary": ("Time held in position", "%", "higher", "estimated",
                        "The mirror of active time. Deep and still is what marks out a keeper."),
}

# A calibrated metric supersedes its scale-free twin: same quality, real units.
CALIBRATED_TWIN = {
    "matchDistance": "matchMetresPerMin",
    "matchTopSpeed": "matchTopSpeedKmh",
    "matchSprints": "matchSprintMetresPerMin",
}

# How each kind of role is expected to look in match footage. Positions point at one
# of these instead of repeating thirty weight tables; the seeder drops any weight
# whose metric that sport doesn't carry, and the engine renormalises on what it used.
MATCH_ARCHETYPES = {
    "wide-attack": {"matchTopSpeed": 0.25, "matchWidth": 0.25, "matchAdvanced": 0.20,
                    "matchSprints": 0.20, "matchDistance": 0.10},
    "central-engine": {"matchDistance": 0.35, "matchWorkRate": 0.25, "matchSprints": 0.15,
                       "matchWidth": 0.15, "matchAdvanced": 0.10},
    "deep-anchor": {"matchDeepness": 0.35, "matchWorkRate": 0.30, "matchDistance": 0.20,
                    "matchSprints": 0.15},
    "wide-support": {"matchWidth": 0.30, "matchTopSpeed": 0.25, "matchDistance": 0.25,
                     "matchSprints": 0.20},
    "box-finisher": {"matchAdvanced": 0.35, "matchTopSpeed": 0.30, "matchSprints": 0.25,
                     "matchDistance": 0.10},
    "goalkeeper": {"matchDeepness": 0.55, "matchStationary": 0.45},
    "high-motor": {"matchDistance": 0.30, "matchWorkRate": 0.30, "matchSprints": 0.25,
                   "matchTopSpeed": 0.15},
    "power-specialist": {"matchTopSpeed": 0.35, "matchSprints": 0.30, "matchWorkRate": 0.20,
                         "matchDistance": 0.15},
}

SPORT_MATCH_FAMILY = {
    "Football": "field",
    "Basketball": "court",
    "Volleyball": "court",
    "Badminton / Tennis": "court",
    "Cricket": "cricket",
    "Kho-Kho": "khokho",
}

POSITION_ARCHETYPES = {
    "Football": {
        "Goalkeeper": "goalkeeper", "Centre-back": "deep-anchor", "Full-back": "wide-support",
        "Central Midfielder": "central-engine", "Winger": "wide-attack", "Striker": "box-finisher",
    },
    "Basketball": {
        "Point Guard": "high-motor", "Shooting Guard": "wide-attack",
        "Small Forward": "central-engine", "Power Forward": "box-finisher", "Centre": "deep-anchor",
    },
    "Volleyball": {
        "Setter": "high-motor", "Libero": "deep-anchor", "Outside Hitter": "wide-attack",
        "Middle Blocker": "box-finisher", "Opposite / Server": "power-specialist",
    },
    "Cricket": {
        "Opening Batsman": "wide-support", "Middle-order Batsman": "central-engine",
        "Fast Bowler": "power-specialist", "Spin Bowler": "high-motor",
        "Wicketkeeper": "deep-anchor", "All-rounder": "central-engine",
    },
    "Badminton / Tennis": {
        "Attacking / Power player": "power-specialist",
        "Defensive / Counter player": "high-motor",
        "All-court / Balanced": "central-engine",
    },
    "Kho-Kho": {"Chaser": "high-motor", "Runner / Dodger": "wide-attack"},
}


def _install_match_layer():
    """Fold the match metrics and their weights into SPORTS, once, at import.

    Two families of metric land here: the scale-free ones that always work, and the
    calibrated ones that only carry values once a coach has marked out the pitch. The
    coach says which player to follow, so there is no ball tracking to feed a third.
    A position's weights come from its archetype; anything the sport doesn't
    carry is dropped and the rest renormalised, so every sport ends up with match
    evidence weighted the same total as its test battery.
    """
    for sport_name, sport in SPORTS.items():
        family = SPORT_MATCH_FAMILY[sport_name]

        ranges = dict(MATCH_RANGES[family])
        if "matchAdvanced" in ranges:
            ranges["matchDeepness"] = ranges["matchAdvanced"]

        for key, (poor, elite) in ranges.items():
            label, unit, direction, basis, note = MATCH_LABELS[key]
            sport["metrics"].append(M(key, label, unit, direction, poor, elite,
                                      source="match", basis=basis,
                                      authority="Derived from tracking", note=note))

        thresholds = SPEED_THRESHOLDS[family]
        for key, (poor, elite) in CALIBRATED_RANGES[family].items():
            label, unit, direction, basis, note = CALIBRATED_LABELS[key]
            if key == "matchHsrPerMin":
                note = f"Distance above {thresholds['hsr']} km/h. {note}"
                basis = thresholds["basis"]
            elif key == "matchSprintMetresPerMin":
                note = f"Distance above {thresholds['sprint']} km/h. {note}"
                basis = thresholds["basis"]
            sport["metrics"].append(M(key, label, unit, direction, poor, elite,
                                      source="match", basis=basis,
                                      authority="GPS-equivalent, needs pitch calibration",
                                      note=note))

        keys = {m["key"] for m in sport["metrics"] if m["source"] == "match"}
        for position, config in sport["positions"].items():
            archetype = POSITION_ARCHETYPES[sport_name][position]
            config["archetype"] = archetype

            picked = dict(MATCH_ARCHETYPES[archetype])
            # a calibrated metric measures the same quality as its scale-free twin,
            # so it simply inherits that weight rather than needing its own table
            for scale_free, calibrated in CALIBRATED_TWIN.items():
                if scale_free in picked:
                    picked[calibrated] = picked[scale_free]
            if "matchSprints" in picked:
                picked["matchHsrPerMin"] = picked["matchSprints"]

            picked = {k: w for k, w in picked.items() if k in keys}
            total = sum(picked.values())
            config["weights"].update(
                {k: round(w / total, 4) for k, w in picked.items()} if total else {}
            )


_install_match_layer()


def slug_for(name):
    """URL-safe id for a sport name ("Badminton / Tennis" -> "badminton-tennis")."""
    out = []
    for ch in name.lower():
        out.append(ch if ch.isalnum() else "-")
    slug = "".join(out)
    while "--" in slug:
        slug = slug.replace("--", "-")
    return slug.strip("-")


SLUG_TO_NAME = {slug_for(name): name for name in SPORTS}


def name_for_slug(slug):
    return SLUG_TO_NAME.get((slug or "").lower())


def sport_names():
    return list(SPORTS.keys())


def get_sport(name):
    return SPORTS.get(name)


def metric_map(sport_name):
    """{metric_key: metric_dict} for one sport."""
    sport = SPORTS.get(sport_name)
    if not sport:
        return {}
    return {m["key"]: m for m in sport["metrics"]}


def default_weights(sport_name):
    """{position: {metric_key: weight}} straight from this file, ignoring the DB."""
    sport = SPORTS.get(sport_name)
    if not sport:
        return {}
    return {pos: dict(cfg["weights"]) for pos, cfg in sport["positions"].items()}
