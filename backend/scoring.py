"""
Rule-based position-fit engine.

The whole thing rests on one idea: every raw measurement is converted to a 0-100
score against a `poor` -> `elite` reference range, and every position is a weighted
average of those scores. That keeps the output fully explainable - for any ranking
we can point at exactly which metrics pushed it up or dragged it down, which is the
"and WHY" part of the brief.

Nothing here reads the database; main.py passes the weights in, so the coach's edited
weights and the built-in defaults go through identical code.
"""

from sports_config import TRAINING_TIPS, get_sport, metric_map

# A metric is only called a strength / weakness past these score lines. On the level
# scale (below) that is State level or better, and short of Zonal level.
STRENGTH_LINE = 60.0
WEAKNESS_LINE = 40.0

# Where a metric has level targets for the player's team, its score is read off them:
# University 20, Zonal 40, State 60, National 80, International 100.
LEVEL_WORDS = ("University", "Zonal", "State", "National", "International")


def normalize(value, poor, elite):
    """Map a raw measurement onto 0-100.

    Works for both directions without a branch: for a timed test `poor` is the larger
    number, so the denominator is negative and a faster time scores higher.
    """
    if value is None:
        return None
    if elite == poor:
        return 50.0
    score = (value - poor) / (elite - poor) * 100.0
    return round(max(0.0, min(100.0, score)), 1)


def ladder_floor(steps):
    """Where the level scale starts (0): one average step short of University."""
    return steps[0] - (steps[-1] - steps[0]) / 4


def normalize_ladder(value, steps, better):
    """Map a raw measurement onto 0-100 by the five level targets in `steps`
    (University ... International): 20 per level, a straight line between two targets,
    so 64 reads as "just past State". A value at or past International is 100."""
    if value is None:
        return None
    sign = 1 if better == "higher" else -1
    points = [ladder_floor(steps), *steps]           # scores 0, 20, 40, 60, 80, 100
    reached = [i for i, p in enumerate(points) if (value - p) * sign >= -1e-9]
    if not reached:
        return 0.0
    k = reached[-1]
    if k == len(points) - 1:
        return 100.0
    a, b = points[k], points[k + 1]      # a <= value < b (in the better direction), so a != b
    # capped short of the next target, so rounding never lifts a score into a level it hasn't reached
    return round(20.0 * k + min(19.9, 20.0 * (value - a) / (b - a)), 1)


def level_of(score):
    """The level a score on the level scale stands for; None below University."""
    if score is None or score < 20:
        return None
    return LEVEL_WORDS[min(4, int(score // 20) - 1)]


def confidence_label(coverage):
    if coverage >= 0.8:
        return "high"
    if coverage >= 0.5:
        return "medium"
    return "low"


def build_metric_values(sport_name, student_profile, test_values, match_values=None, card_values=None):
    """Collect every metric's raw value for one student.

    `student_profile` is a dict with height_cm / weight_kg.
    `test_values` is {metric_key: value} from the coach-entered results.
    `match_values` is {metric_key: value} aggregated from assigned match tracks.
    `card_values` is {metric_key: value} from their match cards (match_cards.player_values).
    Metrics marked source="profile" are read off the profile instead.
    """
    match_values = match_values or {}
    card_values = card_values or {}
    values = {}
    for key, meta in metric_map(sport_name).items():
        if meta["source"] == "profile":
            if key == "heightCm":
                values[key] = student_profile.get("height_cm")
            elif key == "weightKg":
                values[key] = student_profile.get("weight_kg")
            else:
                values[key] = None
        elif meta["source"] == "match":
            values[key] = match_values.get(key)
        elif meta["source"] == "card":
            values[key] = card_values.get(key)
        else:
            values[key] = test_values.get(key)
    return values


def score_metrics(sport_name, values, sources=None, ranges=None):
    """One row per metric: raw value, 0-100 score, and the reference range used.

    `sources` limits which kinds of evidence count. Anything outside it keeps its raw
    value for display but scores None, so it drops out of the ranking maths — that is
    what lets the same engine produce a tests-only verdict and a match-only verdict.
    `ranges` replaces a metric's (poor, elite) for this student — a match card's targets
    depend on whether they played in the women's or men's team — and None there means
    the metric has no target to be scored against. Five numbers instead of two are the
    level targets for their team (levels.py), and the score is read off those.
    """
    rows = []
    for meta in get_sport(sport_name)["metrics"]:
        raw = values.get(meta["key"])
        if sources is not None and meta["source"] not in sources:
            raw = None
        steps = None
        if ranges and meta["key"] in ranges:
            span = ranges[meta["key"]]
            if span and len(span) == 5:
                steps = list(span)
                span = (ladder_floor(steps), steps[-1])
            meta = {**meta, "poor": span[0] if span else None, "elite": span[1] if span else None}
            if not span:
                raw = None
        rows.append({
            "key": meta["key"],
            "label": meta["label"],
            "unit": meta["unit"],
            "direction": meta["direction"],
            "source": meta["source"],
            "poor": meta["poor"],
            "elite": meta["elite"],
            "value": raw,
            "score": (normalize_ladder(raw, steps, meta["direction"]) if steps
                      else normalize(raw, meta["poor"], meta["elite"])),
            "ladder": steps,
            # describes what a player does rather than how well, so it is never a
            # strength, a weakness or something to train
            "role": meta.get("role", False),
        })
    return rows


def _phrase(label, score, ladder=False):
    if ladder:
        level = level_of(score)
        return (f"{label} is at {level} level ({score:.0f}/100)" if level
                else f"{label} is short of University level ({score:.0f}/100)")
    if score >= 85:
        return f"{label} is elite-level ({score:.0f}/100)"
    if score >= STRENGTH_LINE:
        return f"{label} is a clear strength ({score:.0f}/100)"
    if score <= 15:
        return f"{label} is well below the level this role needs ({score:.0f}/100)"
    if score < WEAKNESS_LINE:
        return f"{label} is the weak link for this role ({score:.0f}/100)"
    return f"{label} is around average ({score:.0f}/100)"


def rank_positions(sport_name, metric_rows, weights_by_position, in_scope=None):
    """Score every position and sort best-fit first, with the reasoning attached.

    `in_scope` is the set of metric keys this pass is allowed to use. Weights on
    anything outside it are ignored entirely rather than counted as missing data —
    otherwise a tests-only verdict would report itself as half-covered just because
    the position also has match weights.
    """
    by_key = {r["key"]: r for r in metric_rows}
    ranked = []

    for position, weights in weights_by_position.items():
        if in_scope is not None:
            weights = {k: w for k, w in weights.items() if k in in_scope}
        total_weight = sum(w for w in weights.values() if w > 0)
        if total_weight <= 0:
            continue

        used_weight = 0.0
        weighted_sum = 0.0
        contributions = []

        for key, weight in weights.items():
            if weight <= 0:
                continue
            row = by_key.get(key)
            if row is None or row["score"] is None:
                continue
            used_weight += weight
            weighted_sum += weight * row["score"]
            contributions.append({
                "key": key,
                "label": row["label"],
                "score": row["score"],
                "weight": round(weight, 4),
                # how far this metric pulled the fit away from a flat 50
                "impact": round(weight * (row["score"] - 50.0), 2),
                "text": _phrase(row["label"], row["score"], bool(row.get("ladder"))),
            })

        coverage = used_weight / total_weight
        fit = round(weighted_sum / used_weight, 1) if used_weight > 0 else None

        contributions.sort(key=lambda c: c["impact"], reverse=True)
        drivers = [c for c in contributions if c["impact"] > 0][:3]
        drags = [c for c in reversed(contributions) if c["impact"] < 0][:3]

        missing = [
            {"key": k, "label": by_key[k]["label"] if k in by_key else k, "weight": round(w, 4)}
            for k, w in sorted(weights.items(), key=lambda kv: -kv[1])
            if w > 0 and (k not in by_key or by_key[k]["score"] is None)
        ]

        blurb = get_sport(sport_name)["positions"].get(position, {}).get("blurb", "")

        ranked.append({
            "position": position,
            "fit": fit,
            "coverage": round(coverage, 2),
            "confidence": confidence_label(coverage),
            "blurb": blurb,
            "drivers": drivers,
            "drags": drags,
            "missing": missing,
            "why": _build_why(position, fit, drivers, drags, blurb),
        })

    ranked.sort(key=lambda p: (p["fit"] is not None, p["fit"] or 0), reverse=True)
    return ranked


def _build_why(position, fit, drivers, drags, blurb):
    if fit is None:
        return f"Not enough data yet to judge {position}."
    parts = []
    if drivers:
        parts.append("Fits because " + "; ".join(d["text"] for d in drivers) + ".")
    if drags:
        parts.append("Held back by " + "; ".join(d["text"] for d in drags) + ".")
    if not parts:
        parts.append("Every measured attribute sits close to average for this role.")
    if blurb:
        parts.append(f"What the role asks for: {blurb}")
    return " ".join(parts)


def development_plan(metric_rows, top_position_weights):
    """What to train, weakest-and-most-relevant first."""
    plan = []
    for row in metric_rows:
        if row["score"] is None or row["score"] >= WEAKNESS_LINE or row["role"]:
            continue
        weight = top_position_weights.get(row["key"], 0.0)
        plan.append({
            "key": row["key"],
            "label": row["label"],
            "score": row["score"],
            "value": row["value"],
            "unit": row["unit"],
            "relevance": round(weight, 4),
            "tip": TRAINING_TIPS.get(row["key"], "Work on this with your coach using sport-specific drills."),
        })
    plan.sort(key=lambda p: (-p["relevance"], p["score"]))
    return plan


def analyse(sport_name, student_profile, test_values, weights_by_position,
            match_values=None, sources=None, card_values=None, ranges=None):
    """Full report for one student.

    `sources` is a set of {"test", "profile", "match", "card"}; None means all of them.
    Running it once per source and once with everything is how the report shows a
    test verdict, a footage verdict, a match-card verdict and a combined one.
    """
    sport = get_sport(sport_name)
    if sport is None:
        raise ValueError(f"Unknown sport: {sport_name}")

    values = build_metric_values(sport_name, student_profile, test_values, match_values, card_values)
    metric_rows = score_metrics(sport_name, values, sources, ranges)

    in_scope = None if sources is None else {
        m["key"] for m in sport["metrics"] if m["source"] in sources
    }

    scored = [r["score"] for r in metric_rows if r["score"] is not None and not r["role"]]
    overall = round(sum(scored) / len(scored), 1) if scored else None

    ranked = rank_positions(sport_name, metric_rows, weights_by_position, in_scope)
    recommended = ranked[0] if ranked and ranked[0]["fit"] is not None else None

    top_weights = weights_by_position.get(recommended["position"], {}) if recommended else {}
    plan = development_plan(metric_rows, top_weights)

    margin = None
    if recommended and len(ranked) > 1 and ranked[1]["fit"] is not None:
        margin = round(recommended["fit"] - ranked[1]["fit"], 1)

    return {
        "sport": sport_name,
        "note": sport["note"],
        "overallScore": overall,
        "metrics": metric_rows,
        "positions": ranked,
        "recommended": recommended,
        "margin": margin,
        "strengths": [
            {"key": r["key"], "label": r["label"], "score": r["score"], "source": r["source"]}
            for r in metric_rows if r["score"] is not None and r["score"] >= STRENGTH_LINE and not r["role"]
        ],
        "weaknesses": [
            {"key": r["key"], "label": r["label"], "score": r["score"], "source": r["source"]}
            for r in metric_rows if r["score"] is not None and r["score"] < WEAKNESS_LINE and not r["role"]
        ],
        "developmentPlan": plan,
        "missingMetrics": [
            {"key": r["key"], "label": r["label"]} for r in metric_rows
            if r["score"] is None and (in_scope is None or r["key"] in in_scope)
        ],
    }
