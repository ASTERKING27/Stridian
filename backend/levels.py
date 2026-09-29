"""
Level targets: what a player typically posts at each level of the Indian university
pathway, University → Zonal (AIU zone) → State → National → International, for men and
women, per measure. A report reads each of a player's numbers against its ladder and says
the highest level it reaches and how far away the next one is.

This is a second, plainer reading of the same numbers. The 0-100 scores, the position
engine and the trainer never read it.

The starting numbers are in levels.json. They come from published norms where those exist,
and are interpolated or estimated where they don't; each measure says which, and where
from. Coaches retune them for their sport one measure at a time. Their edits live in
AppState["levels:<sport>"] as {metric key: targets}, and a reset deletes the edit.

`targets` has the same shape as a match card's: {"M": ladder, "W": ladder}, optionally
inside {format: ...} (cricket's T20 / 50-over). A ladder is five numbers in LEVELS order,
or None when the measure can't be compared across levels (T20 economy rises in stronger
leagues, for one).
"""

import json
from pathlib import Path

import match_cards
import sports_config as sc
from sports_config import TRAINING_TIPS
from models import LEVELS

DEFAULTS = json.loads((Path(__file__).parent / "levels.json").read_text(encoding="utf-8"))
LEVEL_WORDS = ("University", "Zonal", "State", "National", "International")
CATEGORIES = ("M", "W")
# how much each kind of evidence counts towards the overall level: the tests and the
# match cards lead, footage from one camera counts half
SOURCE_WEIGHT = {"test": 1.0, "profile": 1.0, "card": 1.0, "match": 0.5}
MIN_FOR_OVERALL = 3          # fewer judged measures than this is not enough to call a level


def group_of(source):
    return "test" if source == "profile" else source


def catalogue(sport):
    """{key: label, unit, better, source} for every measure of `sport` with a ladder."""
    metrics = sc.metric_map(sport)
    card = match_cards.SPORTS.get(sport) or {}
    out = {}
    for key in DEFAULTS.get(sport, {}):
        if key.startswith("card_"):
            m = card["measure"][key[5:]]
            out[key] = {"label": m["label"], "unit": match_cards.METRIC_UNIT.get(m["unit"], ""),
                        "better": m["better"], "source": "card"}
        else:
            m = metrics[key]
            out[key] = {"label": m["label"], "unit": m["unit"], "better": m["direction"],
                        "source": m["source"]}
    return out


def formats_of(sport, key):
    """The formats a measure's targets are split by, or None when one set serves all."""
    spec = DEFAULTS[sport][key]["targets"]
    return None if set(spec) <= set(CATEGORIES) else list(spec)


def targets(sport, key, overrides=None):
    return (overrides or {}).get(key) or DEFAULTS[sport][key]["targets"]


def ladder(spec, category, fmt=None):
    """The five numbers for one category (and format), or None."""
    if category not in CATEGORIES:
        return None
    return match_cards._pick(spec, category, fmt)


def reached(value, steps, better):
    """Index into LEVELS of the highest level `value` reaches, -1 below University. None
    when there is nothing to judge: no value, no ladder, or one that never moves."""
    if value is None or not steps or steps[0] == steps[-1]:
        return None
    sign = 1 if better == "higher" else -1
    return max((i for i, t in enumerate(steps) if (value - t) * sign >= -1e-9), default=-1)


def _weighted_median(pairs):
    """The level half the weight sits at or below — one strong test can't carry it."""
    pairs = sorted((level, w) for level, w in pairs if w > 0)
    total = sum(w for _, w in pairs)
    run = 0.0
    for level, w in pairs:
        run += w
        if run >= total / 2 - 1e-9:
            return level
    return None


def _counted(rows, weights, minimum=1):
    """(level, weight) for each judged row, weighted by how much it matters for the
    player's position. When fewer than `minimum` of them matter (the rest carry no
    weight), every judged row counts instead, by its source's weight. The overall level
    asks for MIN_FOR_OVERALL, so one weighted test can't outvote five clips that say
    otherwise."""
    judged = [r for r in rows if r["level"] is not None]
    pairs = [(r["level"], (weights or {}).get(r["key"], 0) * SOURCE_WEIGHT[r["source"]]) for r in judged]
    counted = [(level, w) for level, w in pairs if w > 0]
    if len(counted) < min(minimum, len(judged)):
        counted = [(r["level"], SOURCE_WEIGHT[r["source"]]) for r in judged]
    return counted


def _summary(rows, weights, minimum=1):
    counted = _counted(rows, weights, minimum)
    return {"level": _weighted_median(counted) if counted else None, "measures": len(counted)}


def standing(counted):
    """For each level, how many of the counted measures meet it and what share of their
    weight that is. The level a player plays at is the highest one met by more than half."""
    total = sum(w for _, w in counted)
    if not total:
        return []
    # `meets` is decided on the unrounded weights, with the same tolerance as the median,
    # so the highest level it marks is always the level they play at
    return [{"met": sum(1 for level, _ in counted if level >= i), "of": len(counted),
             "share": round(sum(w for level, w in counted if level >= i) / total, 3),
             "meets": sum(w for level, w in counted if level < i) < total / 2 - 1e-9}
            for i in range(len(LEVELS))]


def scales(sport, category, card_category=None, card_format=None, overrides=None):
    """{metric key: five level targets} for every measure of `sport` with a usable
    ladder for this player: tests and footage for their team, card measures for the team
    and format of their cards. Scores are read off these instead of poor → elite."""
    out = {}
    for key, meta in catalogue(sport).items():
        card = meta["source"] == "card"
        steps = ladder(targets(sport, key, overrides), card_category if card else category,
                       card_format if card else None)
        if steps and steps[0] != steps[-1]:
            out[key] = list(steps)
    return out


def read_out(sport, values, category, card_category=None, card_format=None, weights=None,
             overrides=None, category_from=None):
    """Every measured value against its ladder, plus a level for each kind of evidence
    and overall.

    `values` is {metric key: value} — tests, height, footage and card measures together.
    `category` ("M"/"W") picks the ladders for tests and footage; card measures use the
    category and format of the cards they came from. `weights` is the student's position's
    weights ({metric key: weight}); None counts every measure the same.
    """
    rows = []
    for key, meta in catalogue(sport).items():
        value = values.get(key)
        if value is None:
            continue
        card = meta["source"] == "card"
        steps = ladder(targets(sport, key, overrides), card_category if card else category,
                       card_format if card else None)
        level = reached(value, steps, meta["better"])
        nxt = None
        if level is not None and level < len(LEVELS) - 1:
            target = steps[level + 1]
            nxt = {"level": level + 1, "target": target, "gap": round(target - value, 3)}
        entry = DEFAULTS[sport][key]
        rows.append({"key": key, **meta, "value": value, "ladder": steps, "level": level, "next": nxt,
                     "custom": key in (overrides or {}), "basis": entry["basis"],
                     "tip": TRAINING_TIPS.get(key)})

    groups = {g: _summary([r for r in rows if group_of(r["source"]) == g], weights)
              for g in ("test", "card", "match")}
    counted = _counted(rows, weights, MIN_FOR_OVERALL)
    overall = {"level": _weighted_median(counted) if len(counted) >= MIN_FOR_OVERALL else None,
               "measures": len(counted)}
    return {"levels": LEVEL_WORDS, "category": category, "categoryFrom": category_from,
            "cardCategory": card_category, "cardFormat": card_format,
            "overall": overall, "groups": groups, "rows": rows,
            "standing": standing(counted) if overall["level"] is not None else []}


def check(sport, key, spec):
    """The cleaned targets a coach sent for one measure, or ValueError. Same shape as the
    built-in ones; each ladder five numbers that never get worse from University up, or
    None for "don't compare this across levels"."""
    meta = catalogue(sport).get(key)
    if meta is None:
        raise ValueError(f"'{key}' has no level targets in {sport}")
    sign = 1 if meta["better"] == "higher" else -1

    def one(steps):
        if steps is None:
            return None
        # abs() < 1e12 also turns away NaN, infinity and integers too big for a float
        if (not isinstance(steps, list) or len(steps) != len(LEVELS)
                or not all(isinstance(x, (int, float)) and not isinstance(x, bool) and abs(x) < 1e12
                           for x in steps)):
            raise ValueError("Each level needs a number — five in all — or leave all five empty.")
        if any((b - a) * sign < 0 for a, b in zip(steps, steps[1:])):
            raise ValueError(f"{meta['label']}: each level's target must be at least as good as the "
                             f"one below ({'higher' if sign > 0 else 'lower'} is better).")
        return list(steps)

    def pair(d):
        if not isinstance(d, dict) or set(d) != set(CATEGORIES):
            raise ValueError("Targets need a men's and a women's ladder.")
        return {c: one(d[c]) for c in CATEGORIES}

    formats = formats_of(sport, key)
    if formats is None:
        return pair(spec)
    if not isinstance(spec, dict) or set(spec) != set(formats):
        raise ValueError(f"Targets need one set per format: {', '.join(formats)}.")
    return {f: None if spec[f] is None else pair(spec[f]) for f in formats}


if __name__ == "__main__":
    from scoring import level_of, normalize_ladder

    # every built-in ladder passes the same check a coach's edit must
    for sport_name, measures in DEFAULTS.items():
        for metric_key in measures:
            assert check(sport_name, metric_key, targets(sport_name, metric_key)) is not None
    assert reached(4.3, [4.55, 4.44, 4.33, 4.22, 4.1], "lower") == 2
    assert reached(4.6, [4.55, 4.44, 4.33, 4.22, 4.1], "lower") == -1
    assert reached(50, [45, 47, 50, 53, 56], "higher") == 2
    assert reached(50, [25, 25, 25, 25, 25], "lower") is None
    assert _weighted_median([(0, 1), (2, 1), (4, 1)]) == 2
    assert _weighted_median([(0, 0.2), (3, 0.9)]) == 3
    demo = read_out("Football", {"sprint30m": 4.30, "cmj": 38, "yoyoLevel": 17.4, "heightCm": 174},
                    "M")
    assert demo["overall"]["level"] is not None and demo["groups"]["test"]["measures"] == 4, demo
    for bad in ([4.1, 4.2, 4.3, 4.4, 4.5], [10 ** 400] * 5, [float("nan")] * 5, [True] * 5):
        try:
            check("Football", "sprint30m", {"M": bad, "W": None})
            raise AssertionError(f"{bad} was accepted")
        except ValueError:
            pass
    # one weighted test can't outvote five clips no position weighs (a goalkeeper's footage)
    keeper = sc.default_weights("Football")["Goalkeeper"]
    slow = {"matchMetresPerMin": 60, "matchTopSpeedKmh": 20, "matchHsrPerMin": 1,
            "matchSprintMetresPerMin": 0.1, "matchAccelPerMin": 0.1}
    alone = read_out("Football", {"sprint30m": 4.05, **slow}, "M", weights=keeper)
    assert alone["overall"]["level"] == -1, alone["overall"]
    # the level they play at is the highest one the standing marks as met — for any weights
    import random
    rng = random.Random(7)
    for _ in range(5000):
        pairs = [(rng.randint(-1, 4), rng.choice([0.5, 1.0, rng.random()]) * rng.random())
                 for _ in range(rng.randint(1, 12))]
        pairs = [(lv_, w) for lv_, w in pairs if w > 0] or [(0, 1.0)]
        met = [i for i, x in enumerate(standing(pairs)) if x["meets"]]
        assert (met[-1] if met else -1) == _weighted_median(pairs), (pairs, standing(pairs))
    # and a score never names a level its value hasn't reached, however it rounds
    for sport_name in DEFAULTS:
        for metric_key, meta in catalogue(sport_name).items():
            for cat in CATEGORIES:
                steps = ladder(targets(sport_name, metric_key), cat, (formats_of(sport_name, metric_key) or [None])[0])
                if not steps or steps[0] == steps[-1]:
                    continue
                lo, hi = sorted((steps[0] - (steps[-1] - steps[0]), steps[-1] + (steps[-1] - steps[0])))
                for n in range(401):
                    v = round(lo + (hi - lo) * n / 400, 3)
                    got = level_of(normalize_ladder(v, steps, meta["better"]))
                    want = reached(v, steps, meta["better"])
                    assert (LEVEL_WORDS.index(got) if got else -1) == want, (sport_name, metric_key, v, got, want)
    assert "card_bowlAvg" not in scales("Cricket", "M", "M", "t20")      # a flat ladder: no scale
    assert scales("Football", "W")["sprint30m"] == targets("Football", "sprint30m")["W"]
    print("levels: ok")
