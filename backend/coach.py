"""
The second coach: plain rules that turn a report into a few things worth saying.

No AI and nothing to pay for — every sentence is a template filled in from the numbers
Stridian already has: the level each result reaches (levels.py), what changed since the
last test, what the coach still has to do. A student hears it the way a friend on the
team would say it; a coach gets it short and practical.

Which wording is used is picked from the student and the day, so a message reads the same
all day and changes tomorrow.

The game layer lives here too: rings to the next level, badges, level-up moments, and
a weekly focus with a streak (the sessions are stored in FocusWeek).
"""

import hashlib
from datetime import date, datetime, timedelta

from levels import LEVEL_WORDS
from scoring import normalize_ladder
from sports_config import TRAINING_TIPS

TARGET_SESSIONS = 3            # sessions a week that complete the weekly focus
CARDS_MAX = 5                  # things the dashboard says at once; the tabs have the rest
IST = timedelta(hours=5, minutes=30)


def today_ist(now: datetime) -> date:
    """The day in India, where every user is: a session ticked at 1 am is today's."""
    return (now + IST).date()


def week_of(day: date) -> str:
    year, week, _ = day.isocalendar()
    return f"{year}-W{week:02d}"


def _monday(week: str) -> date:
    year, w = week.split("-W")
    return date.fromisocalendar(int(year), int(w), 1)


def pick(options, *seed):
    """One of `options`, the same one for the same seed (student, day, message)."""
    h = int(hashlib.sha256("|".join(map(str, seed)).encode()).hexdigest(), 16)
    return options[h % len(options)]


def level_name(i):
    return "below University" if i is None or i < 0 else LEVEL_WORDS[i]


def _num(x):
    a = abs(x)
    text = f"{a:.{2 if a < 1 else 1 if a < 10 else 0}f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def amount(row, delta):
    """A difference in the measure's own unit: "0.08 sec", "4 cm", "2.5%"."""
    unit = row.get("unit") or ""
    if unit == "%":
        return f"{_num(delta)}%"
    return f"{_num(delta)} {unit}".strip()


def gap_words(row, target):
    """How far a value is from a target, said the natural way round."""
    if row.get("unit") == "level":                    # Yo-Yo levels don't subtract
        return f"level {target}"
    return amount(row, target - row["value"])


def ring(row):
    """How far through its current level a result is, 0 → 1, and what comes next."""
    level, steps = row["level"], row["ladder"]
    score = normalize_ladder(row["value"], steps, row["better"])
    progress = 1.0 if level >= len(steps) - 1 else max(0.0, min(1.0, (score - 20 * (level + 1)) / 20))
    nxt = row.get("next")
    return {"key": row["key"], "label": row["label"], "source": row["source"],
            "value": row["value"], "unit": row.get("unit") or "", "level": level,
            "levelName": level_name(level), "score": score, "progress": round(progress, 3),
            "next": LEVEL_WORDS[nxt["level"]] if nxt else None,
            "gap": gap_words(row, nxt["target"]) if nxt else None}


# ------------------------------------------------------------- what changed

def changes(history, rows_by_key):
    """The latest result against the one before, per measure with at least two.
    [(row, delta, previous date, better?, crossed a level?)] — newest sessions first."""
    by_key = {}
    for h in history:
        by_key.setdefault(h["metric_key"], []).append(h)
    out = []
    for key, entries in by_key.items():
        row = rows_by_key.get(key)
        if row is None or len(entries) < 2 or entries[-1]["value"] == entries[-2]["value"]:
            continue
        before, now = entries[-2], entries[-1]
        sign = 1 if row["better"] == "higher" else -1
        better = (now["value"] - before["value"]) * sign > 0
        crossed = None
        if row.get("ladder"):
            old = normalize_ladder(before["value"], row["ladder"], row["better"])
            new = normalize_ladder(now["value"], row["ladder"], row["better"])
            if int(new // 20) > int(old // 20) and new >= 20:
                crossed = min(4, int(new // 20) - 1)
        out.append({"row": row, "delta": abs(now["value"] - before["value"]), "since": before["recorded_at"],
                    "at": now["recorded_at"], "better": better, "crossed": crossed})
    out.sort(key=lambda c: c["at"], reverse=True)
    return out


def _date_words(when):
    when = when if isinstance(when, (date, datetime)) else datetime.fromisoformat(str(when))
    return f"{when.day} {when.strftime('%b')}"


# ------------------------------------------------------------- weekly focus

def focus_metric(report):
    """What to work on this week: the weakest measure that matters most for their
    position (the training plan's first item), else the lowest-level one with a next step.
    Height can't be trained, so it is never the focus."""
    rows = {r["key"]: r for r in (report.get("levels") or {}).get("rows", [])}
    for item in report.get("developmentPlan") or []:
        row = rows.get(item["key"])
        if row and row.get("next") and row["source"] != "profile":
            return item["key"]
    candidates = [r for r in rows.values()
                  if r.get("next") and r["level"] is not None and r["source"] != "profile"]
    candidates.sort(key=lambda r: (r["level"], r["source"] != "test"))
    return candidates[0]["key"] if candidates else None


def streak(weeks, today):
    """Weeks in a row with the focus done (TARGET_SESSIONS or more), counting this week
    only once it is done — so a new week never shows the streak as broken."""
    done = {w["week"] for w in weeks if len(w.get("sessions") or []) >= TARGET_SESSIONS}
    cursor = _monday(week_of(today))
    if week_of(cursor) not in done:
        cursor -= timedelta(days=7)
    count = 0
    while week_of(cursor) in done:
        count += 1
        cursor -= timedelta(days=7)
    return count


def focus_view(week, report, today, weeks):
    rows = {r["key"]: r for r in (report.get("levels") or {}).get("rows", [])} if report else {}
    row = rows.get(week["metric_key"])
    sessions = sorted(week.get("sessions") or [])
    return {
        "week": week["week"], "key": week["metric_key"],
        "label": row["label"] if row else week["metric_key"],
        "tip": TRAINING_TIPS.get(week["metric_key"], "Work on it with your coach using sport-specific drills."),
        "ring": ring(row) if row and row.get("ladder") and row["level"] is not None else None,
        "sessions": sessions, "target": TARGET_SESSIONS,
        "doneToday": today.isoformat() in sessions,
        "complete": len(sessions) >= TARGET_SESSIONS,
        "streak": streak(weeks, today),
    }


# ------------------------------------------------------------------- badges

# (id, icon, title, what earns it) — the icon is a name from the frontend's Icon.jsx
BADGES = [
    ("first_test", "clipboard", "First rep", "Your first test result is in."),
    ("verified", "shield", "Squad official", "Your coach confirmed your position."),
    ("profile", "student", "All set", "Every part of your profile filled in."),
    ("receipts", "card", "Receipts", "A certificate verified by your coach."),
    ("match_day", "whistle", "Match day", "Played on a finished match card."),
    ("state", "l1", "State-ready", "A result at State level or better."),
    ("national", "l2", "National contender", "A result at National level or better."),
    ("international", "l3", "World-class moment", "A result at International level."),
    ("on_the_up", "trend", "On the up", "Three measures better than the time before."),
    ("focus", "target", "Focus finished", "Did every session of a weekly focus."),
    ("streak_2", "flame", "Locked in", "Two weeks of focus in a row."),
    ("streak_4", "bolt", "Machine", "Four weeks of focus in a row."),
    ("streak_8", "medal", "Unstoppable", "Eight weeks of focus in a row."),
]


def earned_badges(student, report, history, achievements, weeks, today, profile_done):
    rows = (report.get("levels") or {}).get("rows", []) if report else []
    # height isn't an achievement: the level badges count what they did
    best = max((r["level"] for r in rows if r["level"] is not None and r["source"] != "profile"), default=-1)
    ups = sum(1 for c in changes(history, {r["key"]: r for r in rows}) if c["better"])
    best_streak = longest_streak(weeks)
    matches = ((report or {}).get("matchCards") or {}).get("context") or {}
    got = {
        "first_test": bool(history),
        "verified": student.get("status") == "verified",
        "profile": profile_done,
        "receipts": any(a.get("status") == "verified" for a in achievements),
        "match_day": bool(matches.get("matches")),
        "state": best >= 2,
        "national": best >= 3,
        "international": best >= 4,
        "on_the_up": ups >= 3,
        "focus": any(len(w.get("sessions") or []) >= TARGET_SESSIONS for w in weeks),
        "streak_2": best_streak >= 2,
        "streak_4": best_streak >= 4,
        "streak_8": best_streak >= 8,
    }
    return [{"id": i, "icon": icon, "title": t, "desc": d, "earned": got[i]} for i, icon, t, d in BADGES]


def longest_streak(weeks):
    done = sorted(_monday(w["week"]) for w in weeks if len(w.get("sessions") or []) >= TARGET_SESSIONS)
    best = run = 0
    for i, monday in enumerate(done):
        run = run + 1 if i and monday - done[i - 1] == timedelta(days=7) else 1
        best = max(best, run)
    return best


# ------------------------------------------------------------ the student

HEADLINES = {
    "top": ["International level. You're literally the benchmark now. Keep it there.",
            "International level — the top of the ladder. Stay hungry, it's yours to defend."],
    "below": ["Every pro started here. Get more of your numbers to University level and it's yours.",
              "Not on the ladder yet — and that's the fun part. University level is the first unlock."],
    "none": ["Not enough results for a level yet. Once your coach logs a few more tests, you'll see exactly where you stand.",
             "A few more test results and your level shows up here. Ask your coach when the next testing day is."],
    "level": ["You're playing at {L} level. {met} of {of} of your key numbers already hit {N} — keep cooking.",
              "{L} level, locked in. {met}/{of} of what matters is already at {N}. Next stop: {N}.",
              "Certified {L}-level athlete. {N} is calling — {met} of {of} there already."],
    "level_zero": ["You're playing at {L} level. {N} is the next unlock — one measure there and you're on your way.",
                   "{L} level, locked in. Next stop: {N}. Pick one number and chase it."],
}

NEAR = [("{gap} off {N}", "{label}: you're at {L}. One locked-in session could flip it to {N}."),
        ("So close: {N} in {label}", "Just {gap} to go. That's one good day, fr."),
        ("{label} is knocking on {N}", "{gap} away from {N}. Stay consistent and it's yours.")]
WEAK = [("Your weak spot: {label}", "It's at {L}, and it matters for {pos}. {tip}"),
        ("{label} needs some love", "Currently {L}. {tip} Hit it 2–3 times a week and watch it move.")]
# no weak spot as such (nothing below 40/100): the lowest level is simply the next job
STEP = [("Next project: {label}", "It's your lowest level right now, at {L}. {tip}"),
        ("{label} is your next level-up", "Currently {L}, the lowest of your numbers. {tip}")]
WIN = [("{label} up {d}", "Better than {since}. That's real progress — no cap."),
       ("Look at you — {label} improved", "{d} better than {since}. Keep stacking sessions.")]
LEVEL_WIN = [("New level unlocked: {N} in {label}", "You crossed into {N} since {since}. Earned it."),
             ("{label} just hit {N} level", "Up from {since}. That's how it's done.")]
DROP = [("{label} dipped {d}", "vs {since}. Happens to everyone — sleep, fuel, then run it back."),
        ("Small setback in {label}", "Down {d} since {since}. Not a vibe, but fixable: recovery first, then go again.")]
STRONG = [("{label} is your superpower", "{L} level. Build your game around it."),
          ("{label}: {L} level", "That's your weapon. Keep it sharp.")]
MISSING = [("No {label} result yet", "Ask your coach to test it so your report sees the full picture.")]


def _card(kind, title, body, tab=None, key=None, ring_=None):
    return {"kind": kind, "title": title, "body": body, "tab": tab, "key": key, "ring": ring_}


def profile_todos(student, achievements):
    """What the student still has to do themselves — before the numbers mean anything."""
    todos = []
    if not student.get("category"):
        todos.append(_card("todo", "Pick your team",
                           "Men's or women's — without it we can't compare your tests with any level.", "Profile"))
    if not student.get("photo_version"):
        todos.append(_card("todo", "Add a profile pic", "Coaches put names to faces. Takes ten seconds.", "Profile"))
    if not (student.get("height_cm") and student.get("weight_kg")):
        todos.append(_card("todo", "Add your height and weight",
                           "They feed your position match and your diet plan.", "Profile"))
    rejected = sum(1 for a in achievements if a.get("status") == "rejected")
    drafts = sum(1 for a in achievements if a.get("status") == "draft")
    if rejected:
        todos.append(_card("todo", f"{rejected} certificate{'s' if rejected > 1 else ''} to fix",
                           "Your coach left a note on it — check Achievements.", "Achievements"))
    if drafts:
        todos.append(_card("todo", f"{drafts} certificate{'s' if drafts > 1 else ''} not sent yet",
                           "Send it to your coach so it counts.", "Achievements"))
    return todos


def student_coach(student, report, history, achievements, weeks, seen, today, profile_done):
    """Everything the student dashboard says. `report` is None until the coach has
    verified them, and then only the to-dos and badges show."""
    sid = student["id"]
    day = today.isoformat()
    say = lambda options, key: pick(options, sid, day, key)   # noqa: E731
    lv = (report or {}).get("levels") or {}
    rows = [r for r in lv.get("rows", []) if r["level"] is not None and r.get("ladder")]
    rows_by_key = {r["key"]: r for r in lv.get("rows", [])}
    position = (student.get("verified_position") if student.get("status") == "verified"
                else ((report or {}).get("recommended") or {}).get("position")) or "your position"

    headline, cards = None, []
    if report is None:
        headline = say(["Your coach hasn't verified you yet. Once they log your tests, your full breakdown unlocks right here.",
                        "Almost there — your coach just needs to test and verify you. Then this page comes alive."], "wait")
    else:
        overall = lv.get("overall") or {}
        level = overall.get("level")
        if level is None:
            headline = say(HEADLINES["none"], "head")
        elif level >= 4:
            headline = say(HEADLINES["top"], "head")
        elif level < 0:
            headline = say(HEADLINES["below"], "head")
        else:
            nxt = (lv.get("standing") or [])[level + 1]
            template = "level" if nxt["met"] else "level_zero"
            headline = say(HEADLINES[template], "head").format(
                L=LEVEL_WORDS[level], N=LEVEL_WORDS[level + 1], met=nxt["met"], of=nxt["of"])

        # 1. anything that just happened — a level crossed, a jump, a dip
        recent = changes(history, rows_by_key)
        for c in recent[:3]:
            row, d, since = c["row"], amount(c["row"], c["delta"]), _date_words(c["since"])
            if c["crossed"] is not None:
                t, b = say(LEVEL_WIN, f"lw{row['key']}")
                cards.append(_card("levelup", t.format(label=row["label"], N=LEVEL_WORDS[c["crossed"]]),
                                   b.format(N=LEVEL_WORDS[c["crossed"]], since=since), "My report", row["key"]))
            elif c["better"]:
                t, b = say(WIN, f"w{row['key']}")
                cards.append(_card("win", t.format(label=row["label"], d=d), b.format(d=d, since=since),
                                   "My report", row["key"]))
            else:
                t, b = say(DROP, f"d{row['key']}")
                cards.append(_card("drop", t.format(label=row["label"], d=d), b.format(d=d, since=since),
                                   "My report", row["key"]))

        # 2. the closest level-up
        rings = sorted((ring(r) for r in rows if r.get("next")), key=lambda x: -x["progress"])
        for x in rings[:1]:
            if x["progress"] >= 0.4:
                t, b = say(NEAR, f"n{x['key']}")
                cards.append(_card("near", t.format(gap=x["gap"], N=x["next"], label=x["label"]),
                                   b.format(label=x["label"], L=x["levelName"], N=x["next"], gap=x["gap"]),
                                   "My report", x["key"], x))

        # 3. the weak spot that matters most
        focus_key = focus_metric(report)
        if focus_key and focus_key in rows_by_key:
            row = rows_by_key[focus_key]
            weak = any(p["key"] == focus_key for p in report.get("developmentPlan") or [])
            t, b = say(WEAK if weak else STEP, "weak")
            cards.append(_card("focus" if weak else "step", t.format(label=row["label"]),
                               b.format(L=level_name(row["level"]), pos=position,
                                        tip=TRAINING_TIPS.get(focus_key, "Work on it with your coach.")),
                               "My report", focus_key))

        # 4. their best weapon
        best = max(rows, key=lambda r: (r["level"], r["source"] != "profile"), default=None)
        if best and best["level"] >= 2 and best["source"] != "profile":
            t, b = say(STRONG, "strong")
            cards.append(_card("strength", t.format(label=best["label"], L=LEVEL_WORDS[best["level"]]),
                               b.format(L=LEVEL_WORDS[best["level"]]), "My report", best["key"]))

        # 5. a test that hasn't been done
        missing = [m for m in report.get("missingMetrics") or []
                   if not m["key"].startswith(("match", "card_"))]
        if missing:
            t, b = say(MISSING, "miss")
            cards.append(_card("missing", t.format(label=missing[0]["label"]), b, "My report", missing[0]["key"]))

    todos = profile_todos(student, achievements)
    cards = (cards + todos)[:CARDS_MAX] if report else todos

    badges = earned_badges(student, report, history, achievements, weeks, today, profile_done)
    earned = [b["id"] for b in badges if b["earned"]]
    levels_now = {r["key"]: r["level"] for r in rows}
    overall = (lv.get("overall") or {}).get("level") if report else None
    celebrate = {"level": None, "levelUps": [], "badges": []}
    if seen is not None:
        before = seen.get("levels") or {}
        celebrate["levelUps"] = [{"key": k, "label": rows_by_key[k]["label"], "level": LEVEL_WORDS[v]}
                                 for k, v in levels_now.items() if k in before and v > before[k] and v >= 0]
    # the level they play at is the big one: its first reading, and every step up, is put
    # on record for them (a step down just becomes the new baseline, quietly)
    had_level = (seen or {}).get("overall")
    if overall is not None and overall >= 0 and (had_level is None or overall > had_level):
        standing = lv.get("standing") or []
        nxt = standing[overall + 1] if overall + 1 < len(standing) else None
        celebrate["level"] = {
            "level": overall, "word": LEVEL_WORDS[overall], "first": had_level is None,
            "met": standing[overall]["met"], "of": standing[overall]["of"], "position": position,
            "next": LEVEL_WORDS[overall + 1] if nxt else None,
            # measures still to bring up, counting each the same (the real rule weighs them)
            "need": max(1, nxt["of"] // 2 + 1 - nxt["met"]) if nxt else None,
        }
    had = set((seen or {}).get("badges") or [])
    celebrate["badges"] = [b for b in badges if b["earned"] and b["id"] not in had]
    for b in badges:
        b["new"] = b["id"] in {x["id"] for x in celebrate["badges"]}

    this_week = next((w for w in weeks if w["week"] == week_of(today)), None)
    return {
        "verified": report is not None,
        "headline": headline,
        "level": (lv.get("overall") or {}).get("level") if report else None,
        "standing": lv.get("standing") or [],
        "levels": list(LEVEL_WORDS),
        "cards": cards,
        "rings": sorted((ring(r) for r in rows), key=lambda x: (x["source"] == "match", -x["score"])),
        "badges": badges,
        "focus": focus_view(this_week, report, today, weeks) if this_week and report else None,
        "celebrate": celebrate,
        "snapshot": {"levels": levels_now, "badges": earned, "overall": overall},
    }


# ------------------------------------------------------------------ the coach

def coach_feed(players, pending_certs, today):
    """What a coach should know about their squad today, most useful first.

    `players` is one dict per student: id, name, status, category, has_results, last_test
    (date or None), rows (levels rows from their tests and height), history, streak."""
    feed = []

    def item(kind, title, body, people=None, tab=None):
        # only a name, an id to open and a line — never the rows and history a player carries
        people = [{"id": p["id"], "name": p["name"], "text": p.get("text")} for p in people or []]
        feed.append({"kind": kind, "title": title, "body": body, "people": people, "tab": tab})

    def names(ps, n=3):
        shown = ", ".join(p["name"] for p in ps[:n])
        return shown + (f" and {len(ps) - n} more" if len(ps) > n else "")

    waiting = [p for p in players if p["status"] != "verified" and p["has_results"]]
    if waiting:
        item("verify", f"{len(waiting)} player{'s' if len(waiting) > 1 else ''} waiting to be verified",
             f"They have results — confirm their positions: {names(waiting)}.", waiting, "dashboard")
    if pending_certs:
        item("certs", f"{pending_certs} certificate{'s' if pending_certs > 1 else ''} to check",
             "Open each one before you verify it.", None, "dashboard")
    no_team = [p for p in players if not p["category"]]
    if no_team:
        item("team", f"{len(no_team)} player{'s' if len(no_team) > 1 else ''} without a team",
             f"Levels can't be read until you set Men's or Women's on their Profile tab: {names(no_team)}.",
             no_team, "dashboard")

    near = []
    for p in players:
        for r in p["rows"]:
            if r["level"] is None or not r.get("next") or not r.get("ladder") or r["source"] == "profile":
                continue
            x = ring(r)
            if x["progress"] >= 0.6:
                near.append((x["progress"], p, x))
    near.sort(key=lambda t: -t[0])
    if near:
        seen_people, lines = set(), []
        for _, p, x in near:
            if p["id"] in seen_people:
                continue
            seen_people.add(p["id"])
            lines.append({"id": p["id"], "name": p["name"],
                          "text": f"{x['gap']} off {x['next']} in {x['label']}"})
            if len(lines) == 4:
                break
        item("near", "Close to a level-up", "A focused block could tip these over.", lines)

    movers, drops = [], []
    for p in players:
        rows_by_key = {r["key"]: r for r in p["rows"]}
        said = set()                      # one line per player in each list: their latest change
        for c in changes(p["history"], rows_by_key):
            if (today - _as_date(c["at"])).days > 45 or c["better"] in said:
                continue
            said.add(c["better"])
            line = {"id": p["id"], "name": p["name"],
                    "text": f"{c['row']['label']} {'up' if c['better'] else 'down'} {amount(c['row'], c['delta'])} "
                            f"since {_date_words(c['since'])}"}
            (movers if c["better"] else drops).append(line)
    if movers:
        item("movers", "Improving", "Worth a word of praise.", movers[:4])
    if drops:
        item("drops", "Worth a check-in", "Results down since their last test — recovery, illness or form?", drops[:4])

    stale = [p for p in players if p["last_test"] and (today - p["last_test"]).days > 30]
    never = [p for p in players if not p["has_results"]]
    if never:
        item("untested", f"{len(never)} player{'s' if len(never) > 1 else ''} never tested",
             f"No results yet: {names(never)}.", never, "coach")
    if stale:
        item("stale", f"{len(stale)} player{'s' if len(stale) > 1 else ''} not tested in 30+ days",
             f"Time for a retest: {names(stale)}.", stale, "coach")

    rolling = sorted((p for p in players if p["streak"] >= 2), key=lambda p: -p["streak"])
    if rolling:
        item("streaks", "On a roll", "Doing their weekly focus week after week.",
             [{"id": p["id"], "name": p["name"], "text": f"{p['streak']}-week streak"} for p in rolling[:4]])

    if not feed:
        item("clear", "All caught up", "Nothing needs you right now. Nice work, coach.")
    return feed


def merge_seen(old, shown):
    """What has been shown so far, after `shown` has been: the best level of each measure
    and overall, and every milestone ever announced. Nothing goes down, so a dip and a
    recovery (or being un-verified and verified again) is never announced twice — only a
    new best is."""
    old = old or {}
    levels = dict(old.get("levels") or {})
    for key, level in (shown.get("levels") or {}).items():
        levels[key] = max(level, levels.get(key, level))
    overall = [x for x in (old.get("overall"), shown.get("overall")) if x is not None]
    return {"levels": levels, "badges": sorted(set(old.get("badges") or []) | set(shown.get("badges") or [])),
            "overall": max(overall) if overall else None}


def _as_date(when):
    return when.date() if isinstance(when, datetime) else when


if __name__ == "__main__":
    d = date(2026, 9, 30)
    assert week_of(d) == "2026-W40" and _monday("2026-W40") == date(2026, 9, 28)
    weeks = [{"week": "2026-W38", "sessions": ["a", "b", "c"]}, {"week": "2026-W39", "sessions": ["a", "b", "c"]},
             {"week": "2026-W40", "sessions": ["a"]}]
    assert streak(weeks, d) == 2 and longest_streak(weeks) == 2       # this week not done yet: still 2
    weeks[2]["sessions"] = ["a", "b", "c"]
    assert streak(weeks, d) == 3
    assert streak([{"week": "2026-W37", "sessions": ["a", "b", "c"]}], d) == 0    # a gap breaks it
    assert pick(["x", "y", "z"], 1, "2026-09-30", "head") == pick(["x", "y", "z"], 1, "2026-09-30", "head")
    row = {"key": "sprint30m", "label": "30m Sprint", "unit": "sec", "better": "lower", "source": "test",
           "value": 4.30, "level": 2, "ladder": [4.55, 4.44, 4.33, 4.22, 4.1],
           "next": {"level": 3, "target": 4.22, "gap": -0.08}}
    x = ring(row)
    assert x["gap"] == "0.08 sec" and x["next"] == "National" and 0 < x["progress"] < 1, x
    hist = [{"metric_key": "sprint30m", "value": 4.45, "recorded_at": datetime(2026, 8, 1)},
            {"metric_key": "sprint30m", "value": 4.30, "recorded_at": datetime(2026, 9, 20)}]
    c = changes(hist, {"sprint30m": row})[0]
    assert c["better"] and c["crossed"] == 2 and amount(row, c["delta"]) == "0.15 sec", c
    seen = merge_seen({"levels": {"a": 3, "b": 1}, "badges": ["x"], "overall": 2},
                      {"levels": {"a": 2, "c": 0}, "badges": ["y"], "overall": None})
    assert seen == {"levels": {"a": 3, "b": 1, "c": 0}, "badges": ["x", "y"], "overall": 2}, seen
    print("coach: ok")
