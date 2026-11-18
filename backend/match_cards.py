"""
Match cards: the paper sheets a scorer fills in during a match, one design per sport.

Volleyball copies the Directorate of Sports' own hardcopy. Every other sport follows the
same five parts at the same depth, with that sport's own skills:

  Part A  live match sheet — one row per player, a + / 0 / − tally for every skill
  Part B  the scoring key — what counts as + / 0 / −, the formulas and their targets
  Part C  the coach's post-match review, and a team summary
  Part D  one player's progress across a tournament, with a trend arrow per match
  Player card  every attempt, success and error by zone of the court or field

What each sport's card holds is in its own folder, backend/sports/<sport>/card.py,
written with the building blocks in sports/kit.py. This file is the engine every card
shares: how its numbers are worked out, laid out and checked, and how they turn into the
0–100 scores the position engine uses. main.py stores the cards; this file never touches
the database.

The targets are Stridian's starting values, a University one and an Elite one per
category (men / women) and, for cricket, per format. Elite values come from published
competition statistics; University values sit a step below.
"""

from datetime import date

from sports import ALL
from sports.kit import MAX_COUNT, Tally
from sports.kit import clock as _clock

CATEGORIES = {"M": "Men", "W": "Women"}       # in this order wherever a choice is shown
# Part A's "Level" boxes, as printed on the hardcopy
LEVELS = ["University", "Inter-University", "National / Intercollegiate"]

# B3 — the same five steps for every sport, word for word from the hardcopy
RATING = [
    (5, "Excellent", "Decisive impact, very few errors, sets the standard"),
    (4, "Good", "Consistently positive; errors well controlled"),
    (3, "Average", "Meets role expectation; mixed impact"),
    (2, "Below expectation", "More errors than points; needs correction"),
    (1, "Poor", "Major errors, little positive impact; urgent work"),
]

# Part C and Part D columns every sport shares, with the hardcopy's own headings
BUILTIN = {
    "pos": "Pos.",
    "coord": "Coordination (1–5)",
    "overall": "Overall (1–5)",
    "strength": "Key strength this match",
    "improve": "Area to improve / action for next match",
    "match_no": "Match No.",
    "date": "Date",
    "opponent": "Opponent",
    "result": "Result (W/L)",
    "trend": "Trend ↑↔↓",
    "remarks": "Coach's remarks",
}


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #

# each sport's card, from its card.py (a copy: the engine adds what it works out below)
SPORTS = {sport.NAME: dict(sport.card.CARD) for sport in ALL}

# Part B joins some measures onto one line, as the hardcopy does
ROW_LABELS = {"serve": "Serve ace % / fault %", "sideout": "Side-out % / Break-point %",
              "smash": "Smash winner % / error %", "kho": "Kho quality % / kho foul %"}
RESULT_SHORT = {"Won": "W", "Lost": "L", "Drawn": "D", "Tied": "T", "No result": "NR"}
METRIC_UNIT = {"%": "%", "seconds": "s"}
TEXT_LIMITS = {"tournament": 120, "round": 60, "venue": 120, "opponent": 120, "recorded_by": 80,
               "coach": 80, "match_no": 20}

for _cfg in SPORTS.values():
    for _k, _v in (("formats", None), ("layout", "grid"), ("b1_head", "Main positions who record it"),
                   ("header_extra", []), ("b1_skip", []), ("sheet_note", ""), ("b2_note", ""),
                   ("team_note", ""), ("team_title", "Team match summary"), ("team_labels", {})):
        _cfg.setdefault(_k, _v)
    _cfg["skill_keys"] = [s["key"] for s in _cfg["skills"]]
    _cfg["measure"] = {m["key"]: m for m in _cfg["measures"]}
    _cfg["field"] = {f["key"]: f for f in _cfg["fields"]}
    _cfg["team_field"] = {f["key"]: f for f in _cfg["team_fields"]}
    # the measures the position engine scores, in a stable order
    _cfg["used"] = list(dict.fromkeys(k for w in _cfg["weights"].values() for k in w))


def default_format(sport):
    formats = SPORTS[sport]["formats"]
    return next(iter(formats)) if formats else None


def pick_format(sport, fmt):
    formats = SPORTS[sport]["formats"]
    return fmt if formats and fmt in formats else default_format(sport)


def _pick(spec, category, fmt):
    """A target or text: plain, by category, by format, or by format then category."""
    if isinstance(spec, dict) and spec and not set(spec) <= set(CATEGORIES):
        spec = spec.get(fmt)
    if isinstance(spec, dict):
        spec = spec.get(category)
    return spec


def targets(m, category, fmt):
    return _pick(m["targets"], category, fmt)


def show(value, unit="count", places=None):
    """How a number is written on a card."""
    if value is None:
        return "—"
    if unit == "text":
        return str(value)
    if unit == "yesno":
        return "Yes" if value else "No"
    if unit == "seconds":
        return _clock(value)
    if unit == "overs":
        balls = int(round(value))
        return f"{balls // 6}.{balls % 6}"
    if places is None:
        places = {"%": 1, "ratio": 2, "rate": 1}.get(unit, 0)
    text = f"{value:.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text == "-0":
        text = "0"
    if unit == "%":
        text += "%"
    if unit == "signed" and value > 0 and text != "0":
        text = "+" + text
    return text


def _show(m, value):
    return show(value, m["unit"], m["places"])


def target_text(m, category, fmt):
    """(University, Elite) as Part B prints them."""
    text = _pick(m["text"], category, fmt)
    if text:
        return tuple(text)
    t = targets(m, category, fmt)
    if not t:
        return ("", "")
    return tuple(_show(m, v) + (" or less" if m["better"] == "lower" and v else "") for v in t)


def anchors(m, category, fmt):
    """(poor, elite) for the 0–100 scale. Meeting the University target scores 60 and each
    step towards Elite adds 40; when Elite is not the better side (economy in the IPL is
    worse than a good university spell), the step is 15% of the University value."""
    if m["anchors"]:
        return m["anchors"]
    t = targets(m, category, fmt)
    if not t:
        return None
    uni, elite = t
    sign = 1 if m["better"] == "higher" else -1
    step = (elite - uni) * sign
    if step <= 0:
        step = abs(uni) * 0.15 or 1.0
    return (round(uni - 1.5 * step * sign, 3), round(uni + step * sign, 3))


def _value(m, t):
    try:
        return m["calc"](t)
    except (ZeroDivisionError, TypeError, ValueError):
        return None


def _enough(m, t):
    return not m["count"] or (m["count"](t) or 0) >= m["min_n"]


def tally(sport, lines, card=None, matches=None):
    card = card or {}
    return Tally(lines, SPORTS[sport]["skill_keys"], team=card.get("team"), fmt=card.get("format"),
                 score=(card.get("header") or {}).get("score"), matches=matches)


def _label(cfg, key):
    if key in BUILTIN:
        return BUILTIN[key]
    if key in cfg["measure"]:
        return cfg["measure"][key]["col"]
    return cfg["field"][key]["short"]


def _player(line):
    jersey = line.get("jersey")
    return f"#{jersey} {line.get('name') or ''}".strip() if jersey is not None else (line.get("name") or "")


def _date_text(iso):
    try:
        return date.fromisoformat(iso).strftime("%d %b %Y")
    except (TypeError, ValueError):
        return ""


def _cell(cfg, key, t, line, card):
    header = (card or {}).get("header") or {}
    if key in cfg["measure"]:
        m = cfg["measure"][key]
        return _show(m, _value(m, t))
    if key in cfg["field"]:
        kind = cfg["field"][key]["kind"]
        value = t.f(key) if t.has(key) else None
        return show(value, "seconds" if kind == "seconds" else "count")
    value = {
        "pos": line.get("position"), "coord": line.get("coord"), "overall": line.get("overall"),
        "strength": line.get("strength"), "improve": line.get("improve"), "remarks": line.get("remarks"),
        "match_no": header.get("match_no"), "date": _date_text(header.get("date")),
        "opponent": header.get("opponent"), "result": RESULT_SHORT.get(header.get("result"), ""),
    }.get(key)
    return "" if value is None else str(value)


def _team_item(cfg, sport, item, t, lines, card):
    if item.startswith("top:"):
        _, key, n = item.split(":")
        m = cfg["measure"][key]
        ranked = []
        for line in lines:
            v = _value(m, tally(sport, [line], card, matches=1))
            if v:
                ranked.append((v, line))
        ranked.sort(key=lambda pair: pair[0], reverse=m["better"] == "higher")
        label = cfg["team_labels"].get(item) or {
            "fibaEff": "Top 3 by efficiency", "runs": "Top run-scorer", "wicketsM": "Top wicket-taker",
            "outs": "Top chaser", "matTime": "Top defender (time on the mat)"}.get(key, m["label"])
        value = ", ".join(f"{_player(line)} ({_show(m, v)})" for v, line in ranked[:int(n)])
        return {"key": item, "label": label, "value": value or "—"}
    if item in cfg["measure"]:
        m = cfg["measure"][item]
        return {"key": item, "label": cfg["team_labels"].get(item) or m["col"], "value": _show(m, _value(m, t))}
    f = cfg["team_field"][item]
    value = ((card or {}).get("team") or {}).get(item)
    unit = {"percent": "%", "seconds": "seconds"}.get(f["kind"], "count")
    return {"key": item, "label": f["label"] + (" *" if f["elite"] else ""), "value": show(value, unit)}


def part_c(sport, card, lines):
    """The coach's post-match review: a row per player, then the team summary."""
    cfg = SPORTS[sport]
    keys = cfg["partC"]
    rows = [[_player(line)] + [_cell(cfg, k, tally(sport, [line], card, matches=1), line, card) for k in keys]
            for line in lines]
    team_t = tally(sport, lines, card, matches=1)
    return {
        "columns": ["Player Name"] + [_label(cfg, k) for k in keys], "keys": keys, "rows": rows,
        "teamTitle": cfg["team_title"], "teamNote": cfg["team_note"],
        "team": [_team_item(cfg, sport, item, team_t, lines, card) for item in cfg["team"]],
    }


def _when(entry):
    card = entry["card"]
    return ((card.get("header") or {}).get("date") or "", card.get("id") or 0)


def _trend(before, now):
    if before is None or now is None:
        return ""
    return "↑" if now > before else "↓" if now < before else "↔"


def part_d(sport, entries):
    """One player's matches, grouped by tournament, oldest first, with trend arrows and
    an average / total row. `entries` is [{"card": ..., "line": ...}]."""
    cfg = SPORTS[sport]
    keys = cfg["partD"]
    groups = {}
    for entry in sorted(entries, key=_when):
        name = ((entry["card"].get("header") or {}).get("tournament") or "").strip() or "Other matches"
        groups.setdefault(name.casefold(), (name, []))[1].append(entry)

    out = []
    for name, items in groups.values():
        rows, last_rating = [], None
        for entry in items:
            line, card = entry["line"], entry["card"]
            t = tally(sport, [line], card, matches=1)
            rows.append([_trend(last_rating, line.get("overall")) if k == "trend"
                         else _cell(cfg, k, t, line, card) for k in keys])
            if line.get("overall") is not None:
                last_rating = line["overall"]

        lines = [e["line"] for e in items]
        latest = items[-1]["card"]
        t = tally(sport, lines, {"format": latest.get("format")})
        total = []
        for k in keys:
            if k in ("coord", "overall"):
                rated = [line[k] for line in lines if line.get(k) is not None]
                total.append(show(sum(rated) / len(rated), "rate") if rated else "")
            elif k in cfg["measure"] or k in cfg["field"]:
                total.append(_cell(cfg, k, t, {}, None))
            else:
                total.append("")
        total[0] = "AVERAGE / TOTAL"

        category, fmt = latest.get("category"), latest.get("format")
        goals = {}
        for level, i in (("University", 0), ("Elite", 1)):
            goals[level] = [target_text(cfg["measure"][k], category, fmt)[i] if k in cfg["measure"] else ""
                            for k in keys]
        out.append({"tournament": name, "columns": [_label(cfg, k) for k in keys], "keys": keys,
                    "rows": rows, "total": total, "targets": goals, "category": category,
                    "position": next((e["line"].get("position") for e in reversed(items)
                                      if e["line"].get("position")), None),
                    "jersey": items[-1]["line"].get("jersey")})
    return out


def zone_totals(sport, lines):
    """The player card summed over matches: one table per zone section that has data."""
    out = []
    for z in SPORTS[sport]["zones"]:
        shape = (len(z["rows"]), len(z["cols"]))
        grids = [(line.get("zones") or {}).get(z["key"]) for line in lines]
        grids = [g for g in grids if g and (len(g), len(g[0])) == shape]
        if z["print_only"] or not grids:
            continue
        cells = [[sum(g[r][c] for g in grids) for c in range(len(z["cols"]))] for r in range(len(z["rows"]))]
        out.append({"key": z["key"], "title": z["title"], "rowhead": z["rowhead"], "rows": z["rows"],
                    "cols": z["cols"], "total": z["total"], "cells": cells})
    return out


def player_values(sport, entries):
    """What the position engine sees from a player's cards: ({metric: value},
    {metric: (poor, elite)}, context). Only cards in the category and format of their
    latest card count, so a 50-over strike rate never mixes with a T20 one."""
    cfg = SPORTS.get(sport)
    if not cfg or not entries:
        return {}, {}, None
    values, context = measure_values(sport, entries, cfg["used"])
    category, fmt = context["category"], context["format"]
    ranges = {f"card_{key}": anchors(cfg["measure"][key], category, fmt) for key in cfg["used"]}
    return values, ranges, context


def measure_values(sport, entries, keys):
    """({"card_<key>": value}, context) for these measures, over the cards in the category
    and format of the player's latest one."""
    cfg = SPORTS[sport]
    latest = max(entries, key=_when)["card"]
    category, fmt = latest.get("category"), latest.get("format")
    lines = [e["line"] for e in entries
             if e["card"].get("category") == category and e["card"].get("format") == fmt]
    t = tally(sport, lines, {"format": fmt})
    values = {}
    for key in keys:
        m = cfg["measure"][key]
        v = _value(m, t) if _enough(m, t) else None
        values[f"card_{key}"] = None if v is None else round(v, 1 if m["unit"] == "%" else 2)
    return values, {"category": category, "format": fmt, "matches": len(lines)}


def install(sports):
    """Fold card metrics and their position weights into sports_config.SPORTS, once, at
    import. Each position's card weights add up to 1, like its tests and its footage.
    The ranges here are the women's (and default format's); a player's report re-anchors
    them to the category and format they actually played."""
    for name, cfg in SPORTS.items():
        sport = sports.get(name)
        if sport is None:
            continue
        for key in cfg["used"]:
            m = cfg["measure"][key]
            poor, elite = anchors(m, "W", default_format(name))
            sport["metrics"].append({
                "key": f"card_{key}", "label": m["label"], "unit": METRIC_UNIT.get(m["unit"], ""),
                "direction": m["better"], "poor": poor, "elite": elite, "source": "card",
                "basis": "estimated" if m["extra"] or m["role"] else "published",
                "authority": "Match cards", "note": m["note"] or m["formula"], "role": m["role"],
            })
        for position, pos_cfg in sport["positions"].items():
            weights = cfg["weights"][position]
            total = sum(weights.values())
            pos_cfg["weights"].update({f"card_{k}": round(w / total, 4) for k, w in weights.items()})


def public(sport, category="M", fmt=None):
    """Everything the app needs to show, print and edit this sport's card — no formulas'
    code, just their words — with Part B's targets for this category and format."""
    cfg = SPORTS[sport]
    category = category if category in CATEGORIES else "M"
    fmt = pick_format(sport, fmt)
    skills = [{k: s[k] for k in ("key", "label", "sheet", "legend", "plus", "zero", "minus", "who", "marks",
                                 "merged")} for s in cfg["skills"]]
    b2 = []
    for m in cfg["measures"]:
        if m["extra"]:
            continue
        uni, elite = target_text(m, category, fmt)
        if m["row"] and b2 and b2[-1]["row"] == m["row"]:
            last = b2[-1]
            for key, value, joiner in (("formula", m["formula"], " | "), ("example", m["example"], " | "),
                                       ("uni", uni, " | "), ("elite", elite, " | ")):
                if value:
                    last[key] = f"{last[key]}{joiner}{value}" if last[key] else value
            continue
        b2.append({"row": m["row"], "label": ROW_LABELS.get(m["row"], m["label"]), "formula": m["formula"],
                   "example": m["example"], "uni": uni, "elite": elite})
    return {
        "sport": sport, "category": category, "format": fmt,
        "categories": [{"key": k, "label": v} for k, v in CATEGORIES.items()],
        "formats": [{"key": k, "label": v} for k, v in (cfg["formats"] or {}).items()],
        "levels": LEVELS, "results": cfg["results"], "score": cfg["score"],
        "headerExtra": [{"key": k, "label": label, "choices": choices}
                        for k, label, choices in cfg["header_extra"]],
        "layout": cfg["layout"], "skills": skills,
        "b1": [s for s in skills if s["key"] not in cfg["b1_skip"]], "b1Head": cfg["b1_head"],
        "b2": [{k: v for k, v in row.items() if k != "row"} for row in b2], "b2Note": cfg["b2_note"],
        "rating": [{"value": v, "word": w, "text": t} for v, w, t in RATING],
        "coordination": cfg["coordination"], "b4": cfg["b4"],
        "fields": [{k: f[k] for k in ("key", "label", "short", "sheet", "kind", "hi")} for f in cfg["fields"]],
        "teamFields": [dict(f) for f in cfg["team_fields"]],
        "zones": [dict(z) for z in cfg["zones"]],
        "sheetNote": cfg["sheet_note"],
        "partC": {"keys": cfg["partC"], "columns": [_label(cfg, k) for k in cfg["partC"]]},
        "partD": {"keys": cfg["partD"], "columns": [_label(cfg, k) for k in cfg["partD"]]},
        "team": [_team_item(cfg, sport, item, tally(sport, []), [], None)["label"] for item in cfg["team"]],
        "teamTitle": cfg["team_title"], "teamNote": cfg["team_note"],
        "positions": list(cfg["weights"]),
    }


# --------------------------------------------------------------------------- #
# Checking what comes in — from a coach's screen or from the AI
# --------------------------------------------------------------------------- #

class CardError(ValueError):
    """Something on a card that can't be right; the message says what, for the coach."""


def _text(value, cap):
    if value is None:
        return None
    text = "".join(ch for ch in str(value) if ch == " " or ch.isprintable()).strip()
    return text[:cap] or None


def _num(value, lo, hi, what, strict, integer=True):
    if value is None or value == "":
        return None
    try:
        x = float(value)
    except (TypeError, ValueError):
        x = None
    if x is None or x != x or not lo <= x <= hi or (integer and x != int(x)):
        if strict:
            raise CardError(f"{what} must be a {'whole ' if integer else ''}number from {lo} to {hi}.")
        return None
    return int(x) if integer or x == int(x) else round(x, 2)


def clean_header(sport, raw, strict=True):
    cfg = SPORTS[sport]
    raw = raw if isinstance(raw, dict) else {}
    out = {key: _text(raw.get(key), cap) for key, cap in TEXT_LIMITS.items()}

    def choice(key, options, what):
        value = raw.get(key)
        if value in (None, ""):
            return None
        if value in options:
            return value
        if strict:
            raise CardError(f"{what} must be one of: {', '.join(options)}.")
        return None

    out["level"] = choice("level", LEVELS, "Level")
    out["result"] = choice("result", cfg["results"], "Result")
    day = raw.get("date")
    try:
        out["date"] = date.fromisoformat(day).isoformat() if day else None
    except (TypeError, ValueError):
        if strict:
            raise CardError("The date must look like 2026-09-27.") from None
        out["date"] = None
    parts = cfg["score"]["parts"]
    score = raw.get("score") if isinstance(raw.get("score"), list) else []
    if len(score) > len(parts):
        if strict:
            raise CardError(f"The score has {len(parts)} boxes.")
        score = score[:len(parts)]
    out["score"] = []
    for i, pair in enumerate(score):
        pair = pair if isinstance(pair, (list, tuple)) and len(pair) == 2 else (None, None)
        out["score"].append([_num(v, 0, 999, f"{parts[i]} score", strict, integer=False) for v in pair])
    for key, label, choices in cfg["header_extra"]:
        out[key] = choice(key, choices, label) if choices else _num(raw.get(key), 0, 600, label, strict)
    return out


def clean_team(sport, raw, strict=True):
    cfg = SPORTS[sport]
    raw = raw if isinstance(raw, dict) else {}
    out = {}
    for key, f in cfg["team_field"].items():
        value = _num(raw.get(key), 0, f["hi"], f["label"], strict, integer=f["kind"] != "percent")
        if value is not None:
            out[key] = value
    return out


def clean_line(sport, raw, strict=True):
    """A player's row: {"tallies": {skill: [+, 0, −]}, "fields": {...}, "zones": {...}}."""
    cfg = SPORTS[sport]
    raw = raw if isinstance(raw, dict) else {}
    tallies = {}
    for s in cfg["skills"]:
        cells = (raw.get("tallies") or {}).get(s["key"])
        if cells is None:
            continue
        if not isinstance(cells, (list, tuple)) or len(cells) != 3:
            if strict:
                raise CardError(f"{s['label']} needs three numbers: +, 0 and −.")
            continue
        counts = [_num(c, 0, MAX_COUNT, s["label"], strict) or 0 for c in cells]
        if "0" not in s["marks"]:
            counts[1] = 0
        if any(counts):
            tallies[s["key"]] = counts
    fields = {}
    for f in cfg["fields"]:
        lo = 1 if f["key"] == "batPos" else 0
        value = _num((raw.get("fields") or {}).get(f["key"]), lo, f["hi"], f["label"], strict)
        if value is not None:
            fields[f["key"]] = value
    zones = {}
    for z in cfg["zones"]:
        grid = (raw.get("zones") or {}).get(z["key"])
        if z["print_only"] or grid is None:
            continue
        ok = isinstance(grid, list) and len(grid) == len(z["rows"]) and all(
            isinstance(row, list) and len(row) == len(z["cols"]) for row in grid)
        if not ok:
            if strict:
                raise CardError(f"{z['title']} doesn't match the card's rows and columns.")
            continue
        grid = [[_num(v, 0, MAX_COUNT, z["title"], strict) or 0 for v in row] for row in grid]
        if any(any(row) for row in grid):
            zones[z["key"]] = grid
    return {"tallies": tallies, "fields": fields, "zones": zones}


# --------------------------------------------------------------------------- #
# Reading a photo of Part A with the document AI (docreader.py)
# --------------------------------------------------------------------------- #

MARK_WORDS = {"+": "plus", "0": "zero", "-": "minus"}


def ai_schema(sport):
    cfg = SPORTS[sport]

    def text(description=None):
        return {"type": "STRING", "nullable": True, **({"description": description} if description else {})}

    def number(description=None):
        return {"type": "NUMBER", "nullable": True, **({"description": description} if description else {})}

    def one_of(options):
        return {"type": "STRING", "nullable": True, "enum": list(options)}

    player = {"jersey": {"type": "INTEGER", "nullable": True}, "name": text()}
    for s in cfg["skills"]:
        for mark in s["marks"]:
            player[f"{s['key']}_{MARK_WORDS[mark]}"] = {
                "type": "INTEGER", "nullable": True,
                "description": f"{s['sheet']} column, {mark} cell: how many marks"}
    for f in cfg["fields"]:
        if f["sheet"]:
            player[f["key"]] = number(f["label"] + (", in seconds" if f["kind"] == "seconds" else ""))
    header = {key: text() for key in TEXT_LIMITS}
    header.update({
        "level": one_of(LEVELS), "result": one_of(cfg["results"]), "category": one_of(CATEGORIES.values()),
        "date": text("the match date as YYYY-MM-DD"),
        "score": {"type": "ARRAY", "description": f"{cfg['score']['label']}: " + ", ".join(cfg["score"]["parts"]),
                  "items": {"type": "OBJECT", "properties": {"us": number(), "them": number()}}},
    })
    for key, label, choices in cfg["header_extra"]:
        header[key] = one_of(choices) if choices else number(label)
    return {"type": "OBJECT", "required": ["header", "players"], "properties": {
        "header": {"type": "OBJECT", "properties": header},
        "players": {"type": "ARRAY", "items": {"type": "OBJECT", "properties": player}},
    }}


MARK_SHOW = {"+": "+", "0": "0", "-": "−"}


def _cells(s):
    if s["merged"]:
        return "one cell holding both + and − marks: count each kind"
    return " / ".join(MARK_SHOW[m] for m in s["marks"]) + " cells"


def ai_prompt(sport):
    cfg = SPORTS[sport]
    skills = "; ".join(f"{s['sheet']} ({_cells(s)})" for s in cfg["skills"])
    extra = ", ".join(f["label"] for f in cfg["fields"] if f["sheet"])
    if cfg["layout"] == "player":
        layout = f"""The sheet is for one player, named (often with a jersey number such as #7) in the Player box
under the header; return that player as the only entry in players. The skills are rows. Skills, top
to bottom: {skills}.
{('A table of totals beside it holds: ' + extra + '.') if extra else ''}"""
    else:
        layout = f"""Each row is one player. The Player Name column may hold a jersey number (often written as #7)
and a name. Skill columns, left to right: {skills}.
{('Other columns: ' + extra + '.') if extra else ''}"""
    return f"""This is a photo of Part A of a {sport} match card: the live recording sheet a scorer fills in
during a match at an Indian university. Read it into the fields.

{layout}
The scorer writes tally marks (strokes, with a line across four strokes to make a group of five) or
writes a number. Give the count for each cell. A blank cell in a row that has other marks is 0; use
null for a cell you cannot read.

Read the header too: tournament, round / stage, level, date, venue, opponent, result, the
{cfg['score']['label'].lower()} ({', '.join(cfg['score']['parts'])}), recorded by, coach, match number,
and whether it is the men's or women's team if the card says.

Use null for anything not written on the sheet. Never guess a jersey number, a name or a count."""


def from_ai(sport, found):
    """The AI's reading, checked like anything else typed in, but never refused: a value
    that can't be right — or that the AI couldn't read — comes back as None, so the coach
    can tell it apart from a real 0 and fill it in."""
    cfg = SPORTS[sport]
    found = found if isinstance(found, dict) else {}
    head = found.get("header") if isinstance(found.get("header"), dict) else {}
    score = [[p.get("us"), p.get("them")] for p in head.get("score") or [] if isinstance(p, dict)]
    header = clean_header(sport, {**head, "score": score[:len(cfg["score"]["parts"])]}, strict=False)
    category = next((k for k, v in CATEGORIES.items() if v == head.get("category")), None)
    players = []
    for p in found.get("players") or []:
        if not isinstance(p, dict):
            continue
        tallies = {}
        for s in cfg["skills"]:
            cells = [_num(p.get(f"{s['key']}_{MARK_WORDS[mark]}"), 0, MAX_COUNT, s["label"], False)
                     if mark in s["marks"] else 0 for mark in "+0-"]
            if any(cells):
                tallies[s["key"]] = cells
        fields = {f["key"]: p.get(f["key"]) for f in cfg["fields"] if f["sheet"]}
        line = {**clean_line(sport, {"fields": fields}, strict=False), "tallies": tallies}
        jersey = _num(p.get("jersey"), 0, 999, "Jersey", False)
        name = _text(p.get("name"), 120)
        if jersey is None and not name and not line["tallies"]:
            continue
        players.append({"jersey": jersey, "name": name, "tallies": line["tallies"], "fields": line["fields"]})
    return {"header": header, "category": category, "players": players}


if __name__ == "__main__":
    # Self-check: every sport's card hangs together, and the hardcopy's worked examples
    # come out as printed.
    import random

    for name, cfg in SPORTS.items():
        for key in cfg["partC"] + cfg["partD"]:
            assert key in BUILTIN or key in cfg["measure"] or key in cfg["field"], (name, key)
        for item in cfg["team"]:
            key = item.split(":")[1] if item.startswith("top:") else item
            assert key in cfg["measure"] or key in cfg["team_field"], (name, item)
        for position, weights in cfg["weights"].items():
            assert abs(sum(weights.values()) - 1) < 1e-9, (name, position)
            for key in weights:
                assert anchors(cfg["measure"][key], "W", default_format(name)), (name, key)
        for fmt in cfg["formats"] or [None]:
            for cat in CATEGORIES:
                public(name, cat, fmt)
        random.seed(1)
        lines = [{"jersey": j, "name": f"P{j}", "position": None, "overall": random.randint(1, 5),
                  "tallies": {s: [random.randint(0, 9) for _ in range(3)] for s in cfg["skill_keys"]},
                  "fields": {f["key"]: random.randint(1 if f["key"] == "batPos" else 0, min(f["hi"], 30))
                             for f in cfg["fields"]}} for j in range(1, 8)]
        card = {"id": 1, "category": "M", "format": default_format(name),
                "header": {"date": "2026-09-27", "tournament": "Cup", "score": [[3, 1], [2, 2]]},
                "team": {f: 1 for f in cfg["team_field"]}}
        part_c(name, card, lines)
        part_c(name, card, [])
        part_d(name, [{"card": card, "line": line} for line in lines])
        player_values(name, [{"card": card, "line": line} for line in lines])
        assert ai_schema(name) and ai_prompt(name)

    vb = [{"tallies": {"attack": [9, 12, 4], "reception": [12, 10, 8], "serve": [3, 15, 2],
                       "block": [2, 0, 0]}}]
    t = tally("Volleyball", vb)
    got = {k: _value(SPORTS["Volleyball"]["measure"][k], t) for k in ("attackEff", "receptionPos", "serveAce",
                                                            "serveFault", "points")}
    assert got == {"attackEff": 20, "receptionPos": 40, "serveAce": 15, "serveFault": 10, "points": 14}, got
    assert show(20.0, "%") == "20%" and show(38.888, "%") == "38.9%" and show(3, "signed") == "+3"
    assert anchors(SPORTS["Volleyball"]["measure"]["attackEff"], "W", None) == (5, 30)
    assert target_text(SPORTS["Cricket"]["measure"]["economy"], "W", "t20") == ("7.5 or less", "8.5 or less (IPL)")
    assert target_text(SPORTS["Tennis"]["measure"]["firstWonPct"], "M", None) == ("62%", "72%")
    print("match cards: ok")
