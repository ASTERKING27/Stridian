"""
Sport definitions for Stridian, assembled from backend/sports/ — one folder per sport.

Every sport declares (in its tests.py):
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
  - "match"   -> match footage (added below, from the sport's analyser.py)
  - "card"    -> match cards (added by match_cards.install, from the sport's card.py)

This file holds what every sport shares — how footage is labelled, what each kind of
role looks like in a match — and builds the tables the rest of the backend reads.
"""

from sports import ALL, BY_NAME
from sports.kit import BODY_FIXED, BODY_TIPS, M

# Copies, so that folding in the footage and card measures below never changes a sport's
# own scripts.
SPORTS = {
    sport.NAME: {
        "note": sport.tests.NOTE,
        "metrics": [dict(m) for m in sport.tests.METRICS],
        "positions": {p: {**c, "weights": dict(c["weights"])} for p, c in sport.tests.POSITIONS.items()},
    }
    for sport in ALL
}


# Training advice shown for a metric the player scores badly on: each sport's own, plus
# the two things on everyone's profile. tip() is what to ask; TRAINING_TIPS is every
# sport's together, for a caller that doesn't know the sport.
TIPS = {sport.NAME: {**sport.tests.TIPS, **BODY_TIPS} for sport in ALL}
TRAINING_TIPS = {}
for _tips in TIPS.values():
    for _key, _tip in _tips.items():
        TRAINING_TIPS.setdefault(_key, _tip)


def tip(sport_name, key, default=None):
    """What to do about `key` in this sport — its own advice, else any sport's."""
    return (TIPS.get(sport_name) or {}).get(key) or TRAINING_TIPS.get(key, default)


# Measured traits no training changes (their tips say so): never a weekly focus or a level-up to chase.
UNTRAINABLE = set(BODY_FIXED).union(*(sport.tests.FIXED for sport in ALL))


# Energy and macro targets per sport (its nutrition.py), in grams (or kcal) per kg of
# bodyweight per day. nutrition.py clamps fat into a 22-30% band and trims carbohydrate
# if the numbers ever drift.
NUTRITION = {sport.NAME: dict(sport.nutrition.PROFILE) for sport in ALL}


# ===========================================================================
# Match-footage layer
#
# These metrics come from the YOLO lane (match_video.py) rather than a testing
# session, so they carry source="match" and the engine can score them on their own,
# separately from the test battery. Each sport's analyser.py says what a good number
# is in that sport (FOOTAGE, and CALIBRATED once a coach has marked out the pitch),
# what counts as high-speed running and a sprint (SPEEDS), and which kind of role each
# position plays (ROLES); what follows is shared.
#
# Scale-free units are body-heights rather than metres: a player's own bounding-box
# height is the ruler, which keeps the numbers comparable across zoom levels and
# camera angles without any calibration. The positional pair (matchAdvanced /
# matchDeepness, measured against where the other players on screen are) is only
# carried by sports whose play really does run along one axis in normal footage.
# ===========================================================================

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

# The speeds that count as high-speed running and as a sprint in each sport (km/h), and
# the markings a coach can calibrate on — from each sport's analyser.py.
SPEED_THRESHOLDS = {sport.NAME: dict(sport.analyser.SPEEDS) for sport in ALL}
CALIBRATION_PRESETS = {sport.NAME: sport.analyser.PITCH for sport in ALL}
POSITION_ARCHETYPES = {sport.NAME: dict(sport.analyser.ROLES) for sport in ALL}


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
        footage = BY_NAME[sport_name].analyser

        ranges = dict(footage.FOOTAGE)
        if "matchAdvanced" in ranges:
            ranges["matchDeepness"] = ranges["matchAdvanced"]

        for key, (poor, elite) in ranges.items():
            label, unit, direction, basis, note = MATCH_LABELS[key]
            sport["metrics"].append(M(key, label, unit, direction, poor, elite,
                                      source="match", basis=basis,
                                      authority="Derived from tracking", note=note))

        thresholds = footage.SPEEDS
        for key, (poor, elite) in footage.CALIBRATED.items():
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
            archetype = footage.ROLES[position]
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

# the match-card layer (match_cards.py) adds its metrics and weights the same way
import match_cards  # noqa: E402 — it extends SPORTS, so it has to come after it

match_cards.install(SPORTS)


def slug_for(name):
    """URL-safe id for a sport name ("Kho-Kho" -> "kho-kho")."""
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
