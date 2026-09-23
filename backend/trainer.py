"""
Learning position weights from the coaches' verdicts.

Every verified student is one labelled example: their 0-100 metric scores, and the
position a coach confirmed they actually play. From those the trainer asks, for each
position, "which measurements set the players a coach put here apart from the rest of
the squad?" and moves that position's weights towards them.

It stays the same explainable engine — a weighted average of scores — so every
recommendation can still say exactly WHY. Only the weights change.

Three guards keep it honest with a small squad:

- **Shrinkage.** The starting weights (the defaults, or whatever a coach last set by
  hand) count as PRIOR_STRENGTH verified students. A position with two labels barely
  moves; one with forty is mostly learned from data.
- **Held-out testing.** A candidate is scored leave-one-out: every student is predicted
  by a model trained without them. That is the accuracy that gets compared.
- **Deploy only if better.** The candidate goes live only if its held-out accuracy
  beats the live model's accuracy on the same students. Otherwise it is recorded and
  the live model stays.

Pure functions only: no database, so it is testable on made-up squads.
"""

import hashlib
import json

import scoring
import sports_config as sc

PRIOR_STRENGTH = 8     # the starting weights count as this many verified students
MIN_LABELS = 6         # below this there is nothing trustworthy to learn from
MIN_PER_METRIC = 2     # a position needs this many measured players before a metric can move


def _group(source):
    """Tests and physique form one evidence pool, match footage the other. Each keeps
    its own share of a position's weight, so learning never tips the tests-vs-footage
    balance a coach set."""
    return "match" if source == "match" else "test"


def scores_of(rows):
    return {r["key"]: r["score"] for r in rows if r["score"] is not None}


def signature(samples):
    """A fingerprint of the training data, so the worker only retrains when it changed."""
    payload = sorted((label, sorted(scores_of(rows).items())) for rows, label in samples)
    return hashlib.sha1(json.dumps(payload).encode()).hexdigest()[:16]


def ready(sport_name, samples):
    """(ok, reason). Training needs enough labels spread over more than one position."""
    positions = {label for _rows, label in samples}
    if len(samples) < MIN_LABELS:
        return False, (f"Needs at least {MIN_LABELS} verified students with results; "
                       f"{len(samples)} so far.")
    if len(positions) < 2:
        return False, "Every verified student plays the same position — nothing to tell apart yet."
    return True, ""


# --------------------------------------------------------------------------- #
# Fitting
# --------------------------------------------------------------------------- #

def _stats(samples):
    """Running sums, so leave-one-out can subtract one student instead of refitting."""
    overall, by_position = {}, {}
    for rows, label in samples:
        for key, score in scores_of(rows).items():
            s, n = overall.get(key, (0.0, 0))
            overall[key] = (s + score, n + 1)
            s, n = by_position.setdefault(label, {}).get(key, (0.0, 0))
            by_position[label][key] = (s + score, n + 1)
    counts = {}
    for _rows, label in samples:
        counts[label] = counts.get(label, 0) + 1
    return overall, by_position, counts


def _without(stats, sample):
    overall, by_position, counts = stats
    rows, label = sample
    overall = dict(overall)
    mine = dict(by_position.get(label, {}))
    for key, score in scores_of(rows).items():
        s, n = overall[key]
        overall[key] = (s - score, n - 1)
        s, n = mine[key]
        mine[key] = (s - score, n - 1)
    counts = {**counts, label: counts[label] - 1}
    return overall, {**by_position, label: mine}, counts


def _fit(sport_name, prior, stats):
    overall, by_position, counts = stats
    sources = {key: meta["source"] for key, meta in sc.metric_map(sport_name).items()}

    learned = {}
    for position, prior_weights in prior.items():
        mine = by_position.get(position, {})
        n = counts.get(position, 0)
        keep = PRIOR_STRENGTH / (PRIOR_STRENGTH + n)   # share that stays with the prior

        weights = {}
        for group in ("test", "match"):
            keys = [k for k, src in sources.items() if _group(src) == group]
            budget = sum(max(0.0, prior_weights.get(k, 0.0)) for k in keys)
            if budget <= 0:
                # a pool the coach switched off for this position stays off
                weights.update({k: 0.0 for k in keys})
                continue

            # how far above the squad average this position's players score, per metric
            lift = {}
            for key in keys:
                s_pos, n_pos = mine.get(key, (0.0, 0))
                s_all, n_all = overall.get(key, (0.0, 0))
                if n_pos >= MIN_PER_METRIC and n_all > 0:
                    lift[key] = max(0.0, s_pos / n_pos - s_all / n_all)
            lift_total = sum(lift.values())

            for key in keys:
                p = max(0.0, prior_weights.get(key, 0.0)) / budget
                d = lift.get(key, 0.0) / lift_total if lift_total > 0 else p
                weights[key] = round(budget * (keep * p + (1 - keep) * d), 4)
        learned[position] = weights
    return learned


def fit(sport_name, prior, samples):
    """New weights for every position, blended from `prior` and what the labels show."""
    return _fit(sport_name, prior, _stats(samples))


# --------------------------------------------------------------------------- #
# Testing
# --------------------------------------------------------------------------- #

def predict(sport_name, weights, rows):
    """The position the live engine would recommend — same code path as the report."""
    ranked = scoring.rank_positions(sport_name, rows, weights)
    return ranked[0]["position"] if ranked and ranked[0]["fit"] is not None else None


def accuracy(sport_name, weights, samples):
    if not samples:
        return None
    hits = sum(predict(sport_name, weights, rows) == label for rows, label in samples)
    return round(hits / len(samples), 4)


def held_out_accuracy(sport_name, prior, samples):
    """Leave-one-out: each student is predicted by a model that never saw them."""
    if not samples:
        return None
    stats = _stats(samples)
    hits = 0
    for sample in samples:
        weights = _fit(sport_name, prior, _without(stats, sample))
        hits += predict(sport_name, weights, sample[0]) == sample[1]
    return round(hits / len(samples), 4)


def train(sport_name, prior, live, samples):
    """Fit a candidate and decide whether it should replace the live weights."""
    candidate = fit(sport_name, prior, samples)
    candidate_acc = held_out_accuracy(sport_name, prior, samples)
    # ponytail: the live model is scored in-sample, which flatters it if it was trained
    # on these same students. That only makes the gate stricter, never looser.
    live_acc = accuracy(sport_name, live, samples)
    return {
        "weights": candidate,
        "accuracy": candidate_acc,
        "live_accuracy": live_acc,
        "deploy": candidate_acc is not None and live_acc is not None and candidate_acc > live_acc,
    }


def biggest_changes(sport_name, before, after, per_position=3):
    """What the model learned, in words a coach can check: the largest weight moves."""
    labels = {key: meta["label"] for key, meta in sc.metric_map(sport_name).items()}
    out = []
    for position, weights in after.items():
        old = before.get(position, {})
        moves = sorted(
            ((key, old.get(key, 0.0), w) for key, w in weights.items()
             if abs(w - old.get(key, 0.0)) >= 0.005),
            key=lambda m: -abs(m[2] - m[1]),
        )[:per_position]
        if moves:
            out.append({"position": position, "changes": [
                {"key": k, "label": labels.get(k, k), "from": round(a, 3), "to": round(b, 3)}
                for k, a, b in moves
            ]})
    return out
