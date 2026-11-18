"""
What a sport's scripts are written with.

Each sport lives in its own folder (football/, basketball/, ...). Its tests.py is written
with M() and HEIGHT(); its card.py with skill(), field(), measure() and the rest. Nothing
here knows about any one sport, and nothing here reads the database.
"""

# --------------------------------------------------------------------------- #
# tests.py — the test battery
# --------------------------------------------------------------------------- #

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

# Advice for the two things read off a student's profile rather than tested. A sport's
# own tests have theirs in its tests.py.
BODY_TIPS = {
    "heightCm": "Fixed trait - not trainable. Pick a role that suits the frame.",
    "weightKg": "Adjust through structured strength training and nutrition with qualified guidance.",
}

# Height is a trait no training changes: never a weekly focus or a level-up to chase. A
# sport adds its own (reach, wingspan) as FIXED in its tests.py.
BODY_FIXED = {"heightCm"}


# --------------------------------------------------------------------------- #
# card.py — the match card
# --------------------------------------------------------------------------- #

MAX_COUNT = 999          # no tally or count on a card is ever this big


def skill(key, label, legend, plus, zero, minus, who, sheet=None, marks="+0-", merged=False):
    """One Part A column group. `legend` is the three short words printed under its
    heading; `plus` / `zero` / `minus` are the B1 definitions. `marks` is "+-" for a
    skill with no neutral outcome (a free throw goes in or it doesn't). `merged` prints
    one wide cell for both marks, as the hardcopy's coordination column is."""
    return {"key": key, "label": label, "sheet": sheet or label.upper(), "legend": legend,
            "plus": plus, "zero": zero, "minus": minus, "who": who, "marks": marks, "merged": merged}


def field(key, label, short=None, sheet=True, kind="count", hi=MAX_COUNT):
    """A number per player that isn't a + / 0 / − tally: minutes, runs, time on the mat.
    `sheet` puts it on Part A; otherwise the coach adds it afterwards."""
    return {"key": key, "label": label, "short": short or label, "sheet": sheet,
            "kind": kind, "hi": hi}


def team_field(key, label, kind="count", hi=100000, elite=False):
    """A number for the whole team, typed in by the coach (it isn't on anyone's row)."""
    return {"key": key, "label": label, "kind": kind, "hi": hi, "elite": elite}


def measure(key, label, calc, formula="", example="", unit="%", better="higher", targets=None,
            text=None, count=None, min_n=0, row=None, extra=False, team=False, col=None,
            places=None, anchors=None, role=False, note=""):
    """One number worked out from the card.

    targets  (university, elite), or {"W": (...), "M": (...)}, optionally inside
             {format: ...} — numbers only; `text` replaces what Part B prints.
    count    how many attempts sit behind the value; below `min_n` it is too few to
             score (Part C and D still show it).
    row      measures sharing a row are printed on one Part B line, as the hardcopy does.
    extra    not printed in Part B — Stridian's own, for the position engine.
    team     only makes sense for the whole team (side-out %, points in the paint).
    role     describes what a player does rather than how well (the share of their
             actions that are sets). Scored against `anchors`, never called a weakness.
    """
    return {"key": key, "label": label, "calc": calc, "formula": formula, "example": example,
            "unit": unit, "better": better, "targets": targets, "text": text, "count": count,
            "min_n": min_n, "row": row, "extra": extra, "team": team, "col": col or label,
            "places": places, "anchors": anchors, "role": role, "note": note}


def zone(key, title, rowhead, rows, cols, total=True, print_only=False):
    """One table of the player card. On paper each cell lists jersey numbers; in the app
    it is a count per player."""
    return {"key": key, "title": title, "rowhead": rowhead, "rows": rows, "cols": cols,
            "total": total, "print_only": print_only}


def support(rows=("Cover teammate", "Communication / call", "Emergency support / save"), letter="G"):
    return zone("support", f"{letter}. SUPPORT / COORDINATION — simple post-set tick", "Action",
                list(rows), ["Successful / Good", "Error / Miss"], total=False)


def pct(a, b):
    return a / b * 100 if b else None


def div(a, b):
    return a / b if b else None


class Tally:
    """Sums over card lines: one player's match, one player's tournament, or a whole
    team's match. Every formula is written against this, so the same formula serves
    Part C, Part D's total row, the team summary and the position engine."""

    def __init__(self, lines, skills=(), team=None, fmt=None, score=None, matches=None):
        self.lines = list(lines)
        self.skills = [s for s in skills]
        self.values = team or {}
        self.format = fmt
        self.scores = score or []
        self.matches = len(self.lines) if matches is None else matches

    def _sum(self, i, keys):
        return sum(((line.get("tallies") or {}).get(k) or (0, 0, 0))[i]
                   for line in self.lines for k in keys)

    def p(self, *keys):
        return self._sum(0, keys or self.skills)

    def z(self, *keys):
        return self._sum(1, keys or self.skills)

    def m(self, *keys):
        return self._sum(2, keys or self.skills)

    def n(self, *keys):
        return self.p(*keys) + self.z(*keys) + self.m(*keys)

    def f(self, *keys):
        return sum((line.get("fields") or {}).get(k) or 0 for line in self.lines for k in keys)

    def has(self, key):
        return any((line.get("fields") or {}).get(key) is not None for line in self.lines)

    def team(self, key):
        return self.values.get(key)

    def score(self, i, side):
        """Header score part i, side 0 = us, 1 = them."""
        try:
            return self.scores[i][side]
        except (IndexError, TypeError):
            return None

    def eff(self, *keys):
        """(+ − −) ÷ attempts × 100 — the one-number quality of a skill."""
        return pct(self.p(*keys) - self.m(*keys), self.n(*keys))

    def share(self, keys, of=None):
        """The part of a player's actions that are `keys`."""
        return pct(self.n(*keys), self.n(*(of or self.skills)))


def mix(key, label, keys, elite, of=None, min_n=20):
    """A role metric: how much of what a player does is this kind of action."""
    return measure(key, label, lambda t: t.share(keys, of), unit="%", extra=True, role=True,
                   anchors=(0, elite), count=lambda t: t.n(*(of or t.skills)), min_n=min_n,
                   note="Share of this player's recorded actions.")


def efficiency(key, label, keys, targets, min_n=10):
    return measure(key, label, lambda t: t.eff(*keys), formula="(+ − −) ÷ attempts × 100",
                   targets=targets, count=lambda t: t.n(*keys), min_n=min_n, extra=True)


def clock(seconds):
    """A number of seconds as minutes and seconds: 95 is 1:35."""
    s = round(seconds)
    return f"{s // 60}:{s % 60:02d}"
