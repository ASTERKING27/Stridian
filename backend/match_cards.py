"""
Match cards: the paper sheets a scorer fills in during a match, one design per sport.

Volleyball copies the Directorate of Sports' own hardcopy. Every other sport follows the
same five parts at the same depth, with that sport's own skills:

  Part A  live match sheet — one row per player, a + / 0 / − tally for every skill
  Part B  the scoring key — what counts as + / 0 / −, the formulas and their targets
  Part C  the coach's post-match review, and a team summary
  Part D  one player's progress across a tournament, with a trend arrow per match
  Player card  every attempt, success and error by zone of the court or field

Everything here is data plus a few pure functions: what each sport's card holds, how its
numbers are worked out, and how they turn into the 0–100 scores the position engine
uses. main.py stores the cards; this file never touches the database.

The targets are Stridian's starting values, a University one and an Elite one per
category (men / women) and, for cricket, per format. Elite values come from published
competition statistics; University values sit a step below.
"""

from datetime import date

CATEGORIES = {"M": "Men", "W": "Women"}       # in this order wherever a choice is shown
# Part A's "Level" boxes, as printed on the hardcopy
LEVELS = ["University", "Inter-University", "National / Intercollegiate"]
MAX_COUNT = 999          # no tally or count on a card is ever this big

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
# Building blocks
# --------------------------------------------------------------------------- #

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


# --------------------------------------------------------------------------- #
# Volleyball — the Directorate of Sports hardcopy, word for word
# --------------------------------------------------------------------------- #

VB_SKILLS = ["serve", "attack", "reception", "set", "dig", "block"]

VOLLEYBALL = {
    "skills": [
        skill("serve", "Serve", ("Clear/Ace", "In play", "Fault"),
              "Ace, or a serve that forces a poor / one-option reception",
              "Serve in play; opponent receives well",
              "Fault – net, out, foot fault, wrong server / rotation",
              "All servers (Libero only if allowed by competition rules)"),
        skill("attack", "Attack (Spike / Tip)", ("Kill", "In play", "Error"),
              "Kill – point won", "Ball kept in play (dug / rally continues)",
              "Error – out, net, antenna; or blocked for a point",
              "Outside Hitter, Opposite, Middle Blocker; Setter on attack / dump",
              sheet="ATTACK (SPIKE)"),
        skill("reception", "Reception (1st pass)", ("Perfect", "OK", "Error"),
              "Perfect – setter can use all attack options", "Playable – setter has limited options",
              "Error – ace against, or unplayable ball", "Libero, Outside Hitter, Defensive Specialist",
              sheet="RECEPTION (1st PASS)"),
        skill("set", "Set", ("Good", "OK", "Fault"),
              "Accurate set – hitter attacks freely (assist if it ends in a kill)",
              "Playable – hitter had to adjust", "Set error – double / lift, net, or unhittable ball",
              "Setter (others on free-ball / emergency sets)"),
        skill("dig", "Defense (Dig)", ("Good", "OK", "Drop"),
              "Good dig to target – rally continues with attack option",
              "Kept in play with limited options", "Missed dig / ball drops within reach",
              "Libero, Defensive Specialist, all back-row players", sheet="DEFENSE (DIG)"),
        skill("block", "Block", ("Point", "Touch", "Error"),
              "Block point (stuff)", "Touch that slows the ball or helps the dig",
              "Net touch, centre-line, block-out or misread", "Middle Blocker, Opposite, Outside Hitter, Setter"),
        # not a B1 row: the hardcopy's last Part A column, "+ Point  − Error"
        skill("coordTally", "Coordination", ("Point", None, "Error"), "", "", "", "", marks="+-", merged=True),
    ],
    "b1_skip": ["coordTally"],
    "fields": [field("sets", "Sets played", sheet=False, hi=5)],
    "measures": [
        measure("attackEff", "Attack efficiency %", lambda t: pct(t.p("attack") - t.m("attack"), t.n("attack")),
                "(Kills – Attack errors) ÷ Total attacks × 100", "(9 – 4) ÷ 25 × 100 = 20 %",
                targets={"W": (20, 30), "M": (25, 35)}, count=lambda t: t.n("attack"), min_n=20,
                col="Attack eff. %"),
        measure("receptionPos", "Reception positive %", lambda t: pct(t.p("reception"), t.n("reception")),
                "Perfect (+) receptions ÷ Total receptions × 100", "12 ÷ 30 × 100 = 40 %",
                targets=(30, 40), count=lambda t: t.n("reception"), min_n=20, col="Reception + %"),
        measure("serveAce", "Serve ace %", lambda t: pct(t.p("serve"), t.n("serve")),
                "Aces ÷ Total serves × 100", "3 ÷ 20 = 15 %", targets=(5, 6),
                count=lambda t: t.n("serve"), min_n=20, row="serve"),
        measure("serveFault", "Serve fault %", lambda t: pct(t.m("serve"), t.n("serve")),
                "Faults ÷ Total serves × 100", "2 ÷ 20 = 10 %", better="lower",
                targets={"W": (15, 10), "M": (15, 20)}, count=lambda t: t.n("serve"), min_n=20, row="serve"),
        measure("points", "Points scored", lambda t: t.p("serve") + t.p("attack") + t.p("block"),
                "Aces + Kills + Block points", "3 + 9 + 2 = 14", unit="count"),
        measure("net", "Net (points – errors)",
                lambda t: t.p("serve") + t.p("attack") + t.p("block") - t.m(),
                "Points scored – all errors (every – mark)", "14 – 11 = +3", unit="signed",
                col="Net (pts – err.)"),
        measure("sideOut", "Side-out %", lambda t: t.team("sideOut"),
                "Points won when receiving ÷ receiving rallies",
                "Team-level; recommended for Elite level", team=True, row="sideout",
                targets={"W": (58, 65), "M": (62, 70)}, col="Side-out % *"),
        measure("breakPoint", "Break-point %", lambda t: t.team("breakPoint"),
                "Points won when serving ÷ serving rallies", team=True, row="sideout",
                targets={"W": (45, 40), "M": (40, 35)}, col="Break-point % *"),
        # Part C, Part D and the team summary need these; Part B doesn't list them
        measure("errors", "Errors (all –)", lambda t: t.m(), unit="count", extra=True, col="Errors (all –)"),
        measure("blockPoints", "Block points", lambda t: t.p("block"), unit="count", extra=True),
        measure("aces", "Serve aces", lambda t: t.p("serve"), unit="count", extra=True),
        measure("serveFaults", "Serve faults", lambda t: t.m("serve"), unit="count", extra=True),
        # for the position engine: quality of the skills B2 has no formula for...
        efficiency("setEff", "Set efficiency %", ["set"], (30, 45), min_n=20),
        efficiency("digEff", "Dig efficiency %", ["dig"], (5, 20)),
        measure("blockPerSet", "Block points per set", lambda t: div(t.p("block"), t.f("sets")),
                "Block points ÷ sets played", unit="rate", places=2, targets=(0.3, 0.6),
                count=lambda t: t.f("sets"), min_n=4, extra=True),
        # ...and what each player actually does, which is what separates the roles
        mix("mixAttack", "Share of actions: attacks", ["attack"], 40, of=VB_SKILLS),
        mix("mixReception", "Share of actions: receptions", ["reception"], 35, of=VB_SKILLS),
        mix("mixSet", "Share of actions: sets", ["set"], 55, of=VB_SKILLS),
        mix("mixDig", "Share of actions: digs", ["dig"], 35, of=VB_SKILLS),
        mix("mixBlock", "Share of actions: blocks", ["block"], 30, of=VB_SKILLS),
    ],
    "partC": ["pos", "points", "errors", "net", "attackEff", "receptionPos", "coord", "overall",
              "strength", "improve"],
    "partD": ["match_no", "date", "opponent", "result", "sets", "points", "errors", "attackEff",
              "receptionPos", "blockPoints", "coord", "overall", "trend", "remarks"],
    "team": ["attackEff", "receptionPos", "aces", "serveFaults", "blockPoints", "opponentErrors",
             "errors", "sideOut", "breakPoint"],
    "team_fields": [
        team_field("opponentErrors", "Opponent errors"),
        team_field("sideOut", "Side-out %", kind="percent", hi=100, elite=True),
        team_field("breakPoint", "Break-point %", kind="percent", hi=100, elite=True),
    ],
    "team_labels": {"attackEff": "Team attack eff. %", "errors": "Own errors"},
    "team_note": "* Elite level (optional for University level).",
    "score": {"label": "Set scores", "parts": ["S1", "S2", "S3", "S4", "S5"]},
    "results": ["Won", "Lost"],
    "coordination": "Coordination = calling the ball / communication, court coverage, teamwork "
                    "with setter and blockers, and speed in transition. It is a coach's rating, "
                    "not a tally.",
    "b4": [
        "Reception on a 0–3 scale (3 perfect, 2 good, 1 poor / one option, 0 error) instead of + / 0 / –.",
        "Serve target zone (1–6) and serve type (float / jump float / jump serve).",
        "Attack by set type and zone (high outside, quick middle, back-row) and against single / double block.",
        "Transition points: side-out % (when receiving) and break-point % (when serving).",
        "Playing time, rotation and substitution impact per set.",
    ],
    "zones": [
        zone("attack", "A. ATTACK", "Zone", ["Z4", "Z3", "Z2", "Back row Z5/Z6/Z1"],
             ["Attempts", "Success / Kill", "Errors"]),
        zone("serve", "B. SERVE", "Target / Zone", ["Z1", "Z2", "Z5", "Other"],
             ["Attempts", "Aces / Points", "Errors"]),
        zone("reception", "C. RECEPTION / FIRST PASS", "Zone", ["Z5", "Z6", "Z1", "Other"],
             ["Attempts", "Successful / Good", "Errors"]),
        zone("dig", "D. DEFENSE / DIG", "Area", ["Z5", "Z6", "Z1", "Front / Cover"],
             ["Attempts", "Successful / Save", "Errors / Drop"]),
        zone("set", "E. SETTING", "Target", ["Z4 / OH", "Z3 / MB", "Z2 / OPH", "Back row",
                                              "Emergency / Free ball"],
             ["Attempts", "Successful / Good", "Errors / Miss"]),
        zone("block", "F. BLOCK", "Block Zone", ["Z4", "Z3", "Z2"],
             ["Attempts", "Block Point", "Touch", "Errors"]),
        support(),
    ],
    "weights": {
        "Setter": {"mixSet": 0.45, "setEff": 0.30, "digEff": 0.15, "serveAce": 0.10},
        "Libero": {"mixReception": 0.20, "mixDig": 0.25, "receptionPos": 0.30, "digEff": 0.25},
        "Outside Hitter": {"mixAttack": 0.20, "mixReception": 0.10, "attackEff": 0.35,
                           "receptionPos": 0.25, "serveAce": 0.10},
        "Middle Blocker": {"mixBlock": 0.30, "blockPerSet": 0.25, "attackEff": 0.30, "mixAttack": 0.15},
        "Opposite / Server": {"mixAttack": 0.20, "attackEff": 0.30, "serveAce": 0.30, "blockPerSet": 0.20},
    },
}


# --------------------------------------------------------------------------- #
# Football — Opta event definitions; Elite = Premier League 2024–25 averages
# --------------------------------------------------------------------------- #

FB_OUTFIELD = ["chance", "crossing", "touch", "dribble", "shooting", "tackle", "aerial", "interception"]
FB_GK = ["gkShot", "gkHigh", "gkDist"]
FB_ROLE = FB_OUTFIELD + FB_GK      # passing is left out: it is only marked for focus players

FOOTBALL = {
    "skills": [
        skill("passing", "Passing (open play)", ("Forward", "Safe", "Lost"),
              "Completed pass that goes forward past a line of opponents, into the next third, or into space",
              "Completed safe, sideways or backward pass", "Misplaced, intercepted or out of play",
              "All; most for Centre-back, Central Midfielder, Full-back", sheet="PASSING*"),
        skill("chance", "Chance creation", ("Key pass", "Off target", "Wasted"),
              "Key pass to a shot on target, or an assist (circle it)",
              "Key pass to an off-target or blocked shot",
              "Final ball into the box that reaches no teammate",
              "Central Midfielder, Winger, Full-back, Striker"),
        skill("crossing", "Crossing", ("Found", "Blocked", "Lost"),
              "Reaches a teammate", "Blocked or cleared for a corner or throw",
              "Cleared, caught by the keeper, out, or nobody there", "Full-back, Winger"),
        skill("touch", "First touch", ("Clean", "Routine", "Lost"),
              "Clean control under pressure, or a touch that turns the marker",
              "Routine control (optional)", "Miscontrol that loses the ball",
              "Central Midfielder, Winger, Striker"),
        skill("dribble", "Dribble / take-on", ("Beat", "Foul won", "Lost"),
              "Beats the opponent and keeps the ball", "Wins a foul, or the ball goes out off the defender",
              "Tackled or dispossessed", "Winger, Striker, Full-back"),
        skill("shooting", "Shooting", ("Goal", "Saved", "Off / blocked"),
              "Goal", "On target and saved, or cleared off the line",
              "Off target, hits the woodwork, or blocked by an outfield player",
              "Striker, Winger, Central Midfielder"),
        skill("tackle", "Tackle / ground duel", ("Won", "Back to opp.", "Beaten / foul"),
              "Ball won by the tackler or a teammate, or put safely out",
              "Tackle made but the ball goes back to the opponent", "Dribbled past, or foul conceded",
              "Centre-back, Full-back, Central Midfielder"),
        skill("aerial", "Aerial duel", ("Won", "Loose", "Lost"),
              "Header won to a teammate or clear of danger", "First contact won but the ball is loose",
              "Aerial duel lost", "Centre-back, Striker, Full-back"),
        skill("interception", "Interception / clearance / block", ("Kept", "Cleared", "To opp."),
              "Interception that keeps the ball, or a blocked shot or cross", "Clearance with no target",
              "Clearance straight to an opponent near goal, or an error leading to a shot",
              "Centre-back, Full-back, Central Midfielder", sheet="INTERCEPTION"),
        skill("gkShot", "GK: shot-stopping", ("Save", "Rebound", "Goal"),
              "Save held or pushed to safety", "Save, but the rebound falls to an opponent",
              "Goal conceded from a shot on target", "Goalkeeper", sheet="GK SHOT-STOPPING"),
        skill("gkHigh", "GK: high balls", ("Claim", "Punch", "Drop / flap"),
              "Catch or claim", "Punch clear", "Dropped ball, missed claim or flap", "Goalkeeper",
              sheet="GK HIGH BALLS"),
        skill("gkDist", "GK: distribution", ("Long", "Short", "Lost"),
              "Reaches a teammate beyond halfway, or starts a counter", "Short completed pass or throw",
              "To an opponent or out of play", "Goalkeeper", sheet="GK DISTRIBUTION"),
    ],
    "fields": [field("minutes", "Minutes played", "Min", hi=130),
               field("assists", "Assists (circled)", "Ast", hi=20)],
    "measures": [
        measure("passPct", "Pass completion %", lambda t: pct(t.p("passing") + t.z("passing"), t.n("passing")),
                "(Passing + and 0) ÷ all passes × 100", "40 ÷ 50 = 80%", targets=(75, 84),
                count=lambda t: t.n("passing"), min_n=20, col="Pass %"),
        measure("shotAcc", "Shot accuracy %", lambda t: pct(t.p("shooting") + t.z("shooting"), t.n("shooting")),
                "(Shooting + and 0) ÷ all shots × 100", "5 ÷ 10 = 50%", targets=(30, 35),
                count=lambda t: t.n("shooting"), min_n=5, col="Shot acc. %"),
        measure("conversion", "Conversion %", lambda t: pct(t.p("shooting"), t.n("shooting")),
                "Goals ÷ all shots × 100", "2 ÷ 10 = 20%", targets=(10, 11),
                count=lambda t: t.n("shooting"), min_n=5),
        measure("crossAcc", "Cross accuracy %", lambda t: pct(t.p("crossing"), t.n("crossing")),
                "Crossing + ÷ all crosses × 100", "3 ÷ 12 = 25%", targets=(15, 20),
                count=lambda t: t.n("crossing"), min_n=5),
        measure("dribblePct", "Dribble success %", lambda t: pct(t.p("dribble"), t.p("dribble") + t.m("dribble")),
                "Dribble + ÷ (+ and −) × 100", "4 ÷ 7 = 57%", targets=(45, 52),
                count=lambda t: t.p("dribble") + t.m("dribble"), min_n=5),
        measure("tacklePct", "Tackle success %", lambda t: pct(t.p("tackle"), t.p("tackle") + t.z("tackle")),
                "Tackle + ÷ (+ and 0) × 100", "6 ÷ 8 = 75%", targets=(50, 60),
                count=lambda t: t.p("tackle") + t.z("tackle"), min_n=5, col="Tackle %"),
        measure("aerialPct", "Aerial win % (Centre-back, Striker)",
                lambda t: pct(t.p("aerial") + t.z("aerial"), t.n("aerial")),
                "(Aerial + and 0) ÷ all aerial duels × 100", "7 ÷ 10 = 70%", targets=(50, 60),
                count=lambda t: t.n("aerial"), min_n=5, col="Aerial %"),
        measure("savePct", "Save %", lambda t: pct(t.p("gkShot") + t.z("gkShot"), t.n("gkShot")),
                "(GK shot-stopping + and 0) ÷ shots on target faced × 100", "5 ÷ 7 = 71%",
                targets=(62, 68), count=lambda t: t.n("gkShot"), min_n=5),
        measure("involvements90", "Goal involvements per 90",
                lambda t: div((t.p("shooting") + t.f("assists")) * 90, t.f("minutes")),
                "(Goals + assists) × 90 ÷ minutes played", "2 × 90 ÷ 75 = 2.4", unit="rate", places=2,
                text=("Set from the squad", "Set from the squad")),
        measure("net90", "Net per 90", lambda t: div((t.p() - t.m()) * 90, t.f("minutes")),
                "(All + − all −) × 90 ÷ minutes played", "(45 − 26) × 90 ÷ 90 = +19", unit="signed",
                text=("Rank within position", "Rank within position")),
        measure("goals", "Goals", lambda t: t.p("shooting"), unit="count", extra=True),
        measure("errors", "Errors (all −)", lambda t: t.m(), unit="count", extra=True),
        measure("net", "Net (+ − −)", lambda t: t.p() - t.m(), unit="signed", extra=True),
        # team summary
        measure("shots", "Shots", lambda t: t.n("shooting"), unit="count", extra=True, team=True),
        measure("shotsOn", "Shots on target", lambda t: t.p("shooting") + t.z("shooting"), unit="count",
                extra=True, team=True),
        measure("groundDuels", "Ground duels won %",
                lambda t: pct(t.p("tackle", "dribble"), t.n("tackle", "dribble")), extra=True, team=True),
        measure("possLost", "Possession lost", lambda t: t.m("passing", "touch", "dribble"), unit="count",
                extra=True, team=True),
        measure("possWon", "Possession regained", lambda t: t.p("tackle", "interception"), unit="count",
                extra=True, team=True),
        measure("goalsConceded", "Goals conceded", lambda t: t.score(1, 1), unit="count", extra=True, team=True),
        measure("cleanSheet", "Clean sheet", lambda t: None if t.score(1, 1) is None else t.score(1, 1) == 0,
                unit="yesno", extra=True, team=True),
        # for the position engine
        efficiency("interceptEff", "Interception efficiency %", ["interception"], (40, 60)),
        efficiency("chanceEff", "Chance creation efficiency %", ["chance"], (-10, 10), min_n=5),
        efficiency("touchEff", "First-touch efficiency %", ["touch"], (10, 30)),
        efficiency("gkHighEff", "High-ball efficiency %", ["gkHigh"], (50, 70), min_n=5),
        mix("mixGk", "Share of actions: goalkeeping", FB_GK, 70, of=FB_ROLE),
        mix("mixDef", "Share of actions: tackles, aerials, interceptions",
            ["tackle", "aerial", "interception"], 60, of=FB_ROLE),
        mix("mixAtt", "Share of actions: shots, dribbles, chances", ["shooting", "dribble", "chance"], 50,
            of=FB_ROLE),
        mix("mixCross", "Share of actions: crosses", ["crossing"], 25, of=FB_ROLE),
    ],
    "partC": ["pos", "minutes", "goals", "assists", "errors", "net", "passPct", "shotAcc", "tacklePct",
              "savePct", "coord", "overall", "strength", "improve"],
    "partD": ["match_no", "date", "opponent", "result", "minutes", "goals", "assists", "net", "passPct",
              "shotAcc", "tacklePct", "aerialPct", "savePct", "coord", "overall", "trend", "remarks"],
    "team": ["shots", "shotsOn", "shotsAgainst", "shotsOnAgainst", "passPct", "shotAcc", "conversion",
             "groundDuels", "aerialPct", "possLost", "possWon", "corners", "freeKicks", "setPieceGoals",
             "savePct", "goalsConceded", "cleanSheet", "fouls", "yellowCards", "redCards"],
    "team_fields": [
        team_field("shotsAgainst", "Shots against"),
        team_field("shotsOnAgainst", "Shots on target against"),
        team_field("corners", "Corners"),
        team_field("freeKicks", "Free kicks in the final third"),
        team_field("setPieceGoals", "Set-piece goals"),
        team_field("fouls", "Fouls committed"),
        team_field("yellowCards", "Yellow cards"),
        team_field("redCards", "Red cards"),
    ],
    "team_labels": {"passPct": "Team pass completion %", "shotAcc": "Shot accuracy %",
                    "aerialPct": "Aerial duels won %"},
    "score": {"label": "Score", "parts": ["Half-time", "Full-time"]},
    "results": ["Won", "Drawn", "Lost"],
    "sheet_note": "* Passing: mark it only for this match's 3–5 focus players. Goalkeeping columns are "
                  "for the goalkeeper only.",
    "b2_note": "A goalkeeper faces only 4–5 shots on target a match, so percentages count towards "
               "the report only after 5 attempts.",
    "coordination": "Coordination = communication, covering for teammates, keeping shape and pressing "
                    "as a unit, and speed in transition. It is a coach's rating, not a tally.",
    "b4": ["Big chances created and missed.",
           "A simple expected-goals value per shot zone.",
           "High turnovers (ball won within 40 m of the opponent's goal).",
           "Counter-press regains within 5 seconds.",
           "Errors leading to a shot or goal.",
           "Goalkeeper sweeping actions."],
    "zones": [
        zone("shots", "A. SHOOTING (shot map)", "Zone",
             ["6-yard box", "Central penalty area", "Wide penalty area", "Outside the box"],
             ["Attempts", "On target", "Goals", "Headers (H)"]),
        zone("keeper", "B. GOALKEEPER — SHOTS FACED", "Zone",
             ["6-yard box", "Central penalty area", "Wide penalty area", "Outside the box"],
             ["Shots faced", "Saves", "Goals conceded"]),
        zone("pitch", "C. BALL WON / LOST BY PITCH ZONE", "Pitch zone",
             [f"{third} third – {side}" for third in ("Defensive", "Middle", "Attacking")
              for side in ("left", "centre", "right")],
             ["Dribbles", "Tackles", "Aerials", "Interceptions", "Possession lost", "Crosses"]),
        support(letter="D"),
    ],
    "weights": {
        "Goalkeeper": {"mixGk": 0.45, "savePct": 0.35, "gkHighEff": 0.20},
        "Centre-back": {"mixDef": 0.30, "aerialPct": 0.30, "tacklePct": 0.20, "interceptEff": 0.20},
        "Full-back": {"mixCross": 0.15, "mixDef": 0.20, "crossAcc": 0.20, "tacklePct": 0.25,
                      "dribblePct": 0.20},
        "Central Midfielder": {"passPct": 0.30, "chanceEff": 0.20, "tacklePct": 0.20, "touchEff": 0.15,
                               "mixDef": 0.15},
        "Winger": {"mixAtt": 0.20, "mixCross": 0.15, "dribblePct": 0.30, "crossAcc": 0.15, "chanceEff": 0.20},
        "Striker": {"mixAtt": 0.25, "conversion": 0.30, "shotAcc": 0.25, "aerialPct": 0.20},
    },
}


# --------------------------------------------------------------------------- #
# Basketball — FIBA Statisticians' Manual; University = NCAA D-I median, Elite = NBA
# --------------------------------------------------------------------------- #

def _fga(t):
    return t.p("two", "three") + t.m("two", "three")      # a fouled miss (0) is not an attempt


def _bb_points(t):
    return 2 * t.p("two") + 3 * t.p("three") + t.p("ft")


def _turnovers(t):
    return t.m("passing", "handling")


BB_PLAY = ["two", "three", "passing", "handling", "rebound", "defence"]

BASKETBALL = {
    "skills": [
        skill("two", "2-pt shot (also dot it on the shot chart)", ("Made", "Fouled", "Miss / B"),
              "Made, including an and-one", "Missed but fouled while shooting — not counted as an attempt",
              "Missed, or blocked (write B)", "Centre, Power Forward, Small Forward; guards on drives",
              sheet="2-PT SHOT"),
        skill("three", "3-pt shot", ("Made", "Fouled", "Miss / B"),
              "Made", "Missed but fouled — not an attempt", "Missed or blocked (B)",
              "Shooting Guard, Small Forward, Point Guard"),
        skill("ft", "Free throw", ("Made", None, "Missed"), "Made", "—", "Missed", "All", marks="+-"),
        skill("passing", "Passing / assist", ("Assist", "Open miss", "TO"),
              "Assist: the last pass before a made basket",
              "Pass to an open shot that missed, or to a shooting foul", "Bad-pass turnover or interception",
              "Point Guard, Shooting Guard, Small Forward"),
        skill("handling", "Ball handling / drive", ("Beat", "Stopped", "TO"),
              "Beats the defender for a shot at the rim, a foul drawn or an open kick-out",
              "Drive stopped, ball kept",
              "Any other turnover: lost dribble, travel, double dribble, offensive foul, time violation",
              "Point Guard, Shooting Guard, Small Forward"),
        skill("rebound", "Rebounding (write O or D)", ("Got it", "Box-out", "Lost"),
              "Rebound secured, including a controlled tip to a teammate", "Boxed out and a teammate got it",
              "Lost the box-out or fumbled to the opponent", "Centre, Power Forward, Small Forward",
              sheet="REBOUNDING"),
        skill("defence", "Defence (write S, B or C)", ("S / B / C", "Contest", "Beaten"),
              "Steal, block, or charge drawn", "Contested shot that missed",
              "Beaten or left a shooter open, and the opponent scored or was fouled",
              "Guards on the ball; Centre, Power Forward at the rim", sheet="DEFENCE"),
        skill("fouls", "Fouls", ("Drawn", None, "Committed"), "Foul drawn", "—", "Personal foul committed",
              "All", marks="+-"),
    ],
    "fields": [field("minutes", "Minutes played", "Min", hi=60),
               field("offReb", "Offensive rebounds (O)", "O reb", hi=40),
               field("steals", "Steals (S)", "Stl", hi=30),
               field("blocks", "Blocks (B)", "Blk", hi=30),
               field("charges", "Charges drawn (C)", "Chg", hi=20)],
    "measures": [
        measure("points", "Points", _bb_points, "2 × 2-pt made + 3 × 3-pt made + free throws made",
                "10 + 6 + 4 = 20", unit="count", text=("—", "—")),
        measure("fgPct", "Field goal %", lambda t: pct(t.p("two", "three"), _fga(t)),
                "Baskets made ÷ attempted", "7 ÷ 18 = 38.9%", targets=(45, 47), count=_fga, min_n=10,
                col="FG %"),
        measure("threePct", "3-pt %", lambda t: pct(t.p("three"), t.p("three") + t.m("three")),
                "3-pt made ÷ attempted", "2 ÷ 7 = 28.6%", targets=(34, 36),
                count=lambda t: t.p("three") + t.m("three"), min_n=10),
        measure("ftPct", "Free throw %", lambda t: pct(t.p("ft"), t.n("ft")),
                "Made ÷ attempted", "4 ÷ 6 = 66.7%", targets=(73, 78), count=lambda t: t.n("ft"),
                min_n=10, col="FT %"),
        measure("efgPct", "Effective FG %", lambda t: pct(t.p("two", "three") + 0.5 * t.p("three"), _fga(t)),
                "(Baskets made + 0.5 × 3-pt made) ÷ attempted", "8 ÷ 18 = 44.4%", targets=(51, 55),
                count=_fga, min_n=10, col="eFG %"),
        measure("tsPct", "True shooting %", lambda t: pct(_bb_points(t), 2 * (_fga(t) + 0.44 * t.n("ft"))),
                "Points ÷ (2 × (attempts + 0.44 × free-throw attempts))", "20 ÷ 41.3 = 48.4%",
                targets=(55, 58), count=_fga, min_n=10, col="TS %"),
        # ponytail: no turnovers reads as one, so a clean game still gets a number
        measure("astTo", "Assist-to-turnover", lambda t: t.p("passing") / max(_turnovers(t), 1),
                "Assists ÷ turnovers", "4 ÷ 3 = 1.33", unit="ratio", targets=(1.2, 1.8),
                count=lambda t: t.p("passing") + _turnovers(t), min_n=10, col="AST/TO"),
        measure("fibaEff", "FIBA efficiency",
                lambda t: (_bb_points(t) + t.p("rebound") + t.p("passing") + t.f("steals", "blocks")
                           - (_fga(t) - t.p("two", "three")) - t.m("ft") - _turnovers(t)),
                "Points + rebounds + assists + steals + blocks − missed shots − missed free throws − turnovers",
                "20 + 7 + 4 + 2 + 1 − 11 − 2 − 3 = 18", unit="signed",
                text=("Set from the squad", "Set from the squad"), col="Eff."),
        measure("net", "Net", lambda t: t.p() - t.m(), "All + − all −, per skill and in total",
                "Passing: 4 − 2 = +2", unit="signed", text=("0 or better per skill", "—")),
        measure("rebounds", "Rebounds", lambda t: t.p("rebound"), unit="count", extra=True, col="Reb"),
        measure("assists", "Assists", lambda t: t.p("passing"), unit="count", extra=True, col="Ast"),
        measure("turnovers", "Turnovers", _turnovers, unit="count", extra=True, col="TO"),
        measure("offRebT", "Offensive rebounds", lambda t: t.f("offReb"), unit="count", extra=True, team=True),
        measure("defRebT", "Defensive rebounds", lambda t: max(t.p("rebound") - t.f("offReb"), 0),
                unit="count", extra=True, team=True),
        measure("stealsT", "Steals", lambda t: t.f("steals"), unit="count", extra=True, team=True),
        measure("blocksT", "Blocks", lambda t: t.f("blocks"), unit="count", extra=True, team=True),
        measure("chargesT", "Charges drawn", lambda t: t.f("charges"), unit="count", extra=True, team=True),
        measure("foulsCommitted", "Fouls committed", lambda t: t.m("fouls"), unit="count", extra=True, team=True),
        measure("foulsDrawn", "Fouls drawn", lambda t: t.p("fouls"), unit="count", extra=True, team=True),
        measure("shotMix", "Shot mix: rim & paint / mid-range / 3-pt", lambda t: _shot_mix(t), unit="text",
                extra=True, team=True),
        measure("threeRate", "3-pt attempt rate", lambda t: pct(t.p("three") + t.m("three"), _fga(t)),
                extra=True, role=True, anchors=(0, 50), count=_fga, min_n=10,
                note="Share of this player's shots taken from three."),
        measure("blk36", "Blocks per 36 minutes", lambda t: div(t.f("blocks") * 36, t.f("minutes")),
                unit="rate", places=1, extra=True, role=True, anchors=(0, 2.5),
                count=lambda t: t.f("minutes"), min_n=60),
        mix("mixPass", "Share of actions: passing", ["passing"], 30, of=BB_PLAY),
        mix("mixHandle", "Share of actions: drives and ball handling", ["handling"], 25, of=BB_PLAY),
        mix("mixReb", "Share of actions: rebounding", ["rebound"], 35, of=BB_PLAY),
        mix("mixDef", "Share of actions: defence", ["defence"], 25, of=BB_PLAY),
    ],
    "partC": ["pos", "minutes", "points", "fgPct", "threePct", "ftPct", "rebounds", "assists", "turnovers",
              "fibaEff", "coord", "overall", "strength", "improve"],
    "partD": ["match_no", "date", "opponent", "result", "minutes", "points", "fgPct", "threePct", "ftPct",
              "rebounds", "assists", "turnovers", "fibaEff", "coord", "overall", "trend", "remarks"],
    "team": ["fgPct", "threePct", "ftPct", "efgPct", "tsPct", "offRebT", "defRebT", "assists", "turnovers",
             "astTo", "stealsT", "blocksT", "chargesT", "foulsCommitted", "foulsDrawn", "foulsQ1", "foulsQ2",
             "foulsQ3", "foulsQ4", "paintPoints", "shotMix", "top:fibaEff:3"],
    "team_fields": [team_field(f"foulsQ{q}", f"Team fouls, Q{q}", hi=30) for q in range(1, 5)]
    + [team_field("paintPoints", "Points in the paint", hi=300)],
    "score": {"label": "Score by quarter", "parts": ["Q1", "Q2", "Q3", "Q4", "OT"]},
    "results": ["Won", "Lost"],
    "b2_note": "These are team averages. A Centre's field goal % should be higher, and 3-pt % often "
               "doesn't apply to them. Percentages count towards the report only after 10 attempts.",
    "coordination": "Coordination = communication, help defence and rotations, spacing and ball "
                    "movement, and speed in transition. It is a coach's rating, not a tally.",
    "b4": ["The Four Factors (turnover %, offensive rebound %, free-throw rate).",
           "A substitution log for minutes, per-40 rates and plus/minus.",
           "Fast-break, second-chance and points off turnovers.",
           "Assisted vs unassisted baskets.",
           "Points per shot by zone."],
    "zones": [
        zone("shots", "A. SHOT CHART (FIBA court markings)", "Zone",
             ["Rim (inside the no-charge arc)", "Paint", "Mid-range – left", "Mid-range – centre",
              "Mid-range – right", "Corner 3 – left", "Corner 3 – right", "Above-the-break 3",
              "Free throws"],
             ["Attempts", "Made", "Missed"]),
        support(letter="B"),
    ],
    "weights": {
        "Point Guard": {"astTo": 0.30, "mixPass": 0.25, "mixHandle": 0.20, "threePct": 0.10, "ftPct": 0.15},
        "Shooting Guard": {"threePct": 0.30, "threeRate": 0.25, "efgPct": 0.25, "ftPct": 0.20},
        "Small Forward": {"tsPct": 0.30, "efgPct": 0.20, "mixReb": 0.15, "mixDef": 0.15, "threePct": 0.20},
        "Power Forward": {"fgPct": 0.30, "mixReb": 0.30, "mixDef": 0.20, "ftPct": 0.10, "blk36": 0.10},
        "Centre": {"fgPct": 0.25, "mixReb": 0.35, "blk36": 0.30, "ftPct": 0.10},
    },
}


def _shot_mix(t):
    """Rim & paint / mid-range / threes, from the shot chart's attempts column."""
    counts = [0, 0, 0]
    seen = False
    for line in t.lines:
        rows = (line.get("zones") or {}).get("shots")
        if not rows:
            continue
        seen = True
        for i, row in enumerate(rows[:8]):
            counts[0 if i < 2 else 1 if i < 5 else 2] += (row or [0])[0] or 0
    return " / ".join(str(c) for c in counts) if seen else None


# --------------------------------------------------------------------------- #
# Cricket — ball by ball; T20 by default, 50-over chosen per match
# --------------------------------------------------------------------------- #

def _balls(t):
    return t.n("batting")                               # wides are not balls faced


def _legal(t):
    # ponytail: a card with more wides than tallied deliveries is a typing slip; it reads
    # as no overs rather than negative ones
    return max(t.n("bowling") - t.f("wides", "noBalls"), 0)


def _overs(t):
    return div(_legal(t), 6)


def _innings_share(t, low, high):
    batted = [(line.get("fields") or {}).get("batPos") for line in t.lines]
    batted = [b for b in batted if b]
    return pct(sum(low <= b <= high for b in batted), len(batted))


def _innings(t):
    return sum(1 for line in t.lines if (line.get("fields") or {}).get("batPos"))


def _overs_to_balls(overs):
    """18.4 overs is 18 overs and 4 balls."""
    if overs is None:
        return None
    whole = int(overs)
    return whole * 6 + round((overs - whole) * 10)


def _run_rate(t, side):
    balls = _overs_to_balls(t.score(2, side))
    runs = t.score(0, side)
    return div(runs * 6, balls) if runs is not None and balls else None


PHASE_OVERS = {"t20": (6, 9, 5), "odi": (10, 30, 10)}


def _phase(prefix, i):
    return [
        measure(f"{prefix}RR", f"{('Powerplay', 'Middle overs', 'Death overs')[i]} run rate",
                lambda t: div(t.team(f"{prefix}Runs"), PHASE_OVERS.get(t.format, PHASE_OVERS["t20"])[i]),
                unit="rate", places=2, extra=True, team=True),
        measure(f"{prefix}DotPct", f"{('Powerplay', 'Middle overs', 'Death overs')[i]} dot %",
                lambda t: pct(t.team(f"{prefix}Dots"), PHASE_OVERS.get(t.format, PHASE_OVERS["t20"])[i] * 6),
                extra=True, team=True),
    ]


CR_ROLE = ["batting", "bowling", "keeping"]

CRICKET = {
    "formats": {"t20": "T20", "odi": "50-over"},
    "skills": [
        skill("batting", "Batting — each ball faced (wides aren't balls faced)",
              ("In control", "Dot", "False shot"),
              "Scoring shot played in control; circle 4s and 6s",
              "Controlled dot: defended, left, or hit cleanly to a fielder",
              "False shot (edged or missed), with or without runs; or dismissed",
              "Opening Batsman, Middle-order Batsman, Wicketkeeper, All-rounder", sheet="BATTING (each ball)"),
        skill("running", "Running between wickets", ("Quick run", "Routine", "Risk / miss"),
              "Quick single stolen, 1 turned into 2, fielder put under pressure", "Routine run completed",
              "Run out through own call, clear run missed, near run-out", "All batters", sheet="RUNNING"),
        skill("bowling", "Bowling — each delivery", ("Wkt / dot / FS", "1–3 runs", "4 / 6, wd, nb"),
              "Wicket, dot ball, or false shot induced (even if runs came)", "1–3 runs off a controlled shot",
              "Boundary off a controlled shot; wide; no-ball", "Fast Bowler, Spin Bowler, All-rounder",
              sheet="BOWLING (each ball)"),
        skill("catching", "Catching (the fielder reached it in time)", ("Held", "Half-chance", "Dropped"),
              "Catch held (d for a difficult one)", "Half-chance, not reasonably catchable", "Dropped catch",
              "All fielders", sheet="CATCHING"),
        skill("fielding", "Ground fielding & throwing", ("Save / RO", "Clean", "Misfield"),
              "Run-out or direct hit, a save of 1+ run, a return that stops an extra run",
              "Routine clean stop and return", "Misfield, overthrow, fumble, missed run-out", "All fielders",
              sheet="FIELDING"),
        skill("keeping", "Wicketkeeping", ("Dismissal", "Clean take", "Byes / miss"),
              "Catch, stumping, run-out take, or a hard take that saves byes", "Routine clean take",
              "Byes from a fumble, dropped catch, missed stumping", "Wicketkeeper", sheet="KEEPING"),
    ],
    "fields": [
        field("batPos", "Batting position", "Bat no.", hi=11),
        field("runs", "Runs scored", "Runs", hi=400),
        field("dots", "Dot balls faced", "Dots", hi=300),
        field("fours", "Fours", "4s", hi=60),
        field("sixes", "Sixes", "6s", hi=40),
        field("out", "Dismissed (1 = out)", "Out", hi=1),
        field("bowlRuns", "Runs conceded", "Runs conc.", hi=200),
        field("wickets", "Wickets", "Wkts", hi=10),
        field("wides", "Wides bowled", "Wd", hi=60),
        field("noBalls", "No-balls bowled", "Nb", hi=60),
        field("bowlDots", "Dot balls bowled", "Dots bowled", hi=60),
        field("boundariesConc", "4s and 6s conceded", "4s+6s conc.", hi=60),
        field("maidens", "Maidens", "Mdn", sheet=False, hi=10),
    ],
    "measures": [
        measure("battingSR", "Batting strike rate", lambda t: pct(t.f("runs"), _balls(t)),
                "Runs ÷ balls faced × 100", "38 off 27 = 140.7", unit="rate", places=1,
                targets={"t20": (125, 150), "odi": (75, 90)},
                text={"t20": ("125 (finishers 140)", "150"), "odi": ("75", "90")},
                count=_balls, min_n=100, col="SR"),
        measure("battingAvg", "Batting average", lambda t: div(t.f("runs"), t.f("out")),
                "Runs ÷ dismissals", "186 ÷ 6 = 31.0", unit="rate", places=1,
                targets={"t20": (25, 30), "odi": (30, 40)}, count=_balls, min_n=100, col="Avg"),
        measure("batDotPct", "Batting dot-ball %", lambda t: pct(t.f("dots"), _balls(t)),
                "Dots faced ÷ balls faced × 100", "10 ÷ 27 = 37%", better="lower",
                targets={"t20": (40, 30)}, count=_balls, min_n=100),
        measure("boundaryPct", "Boundary %", lambda t: pct(t.f("fours", "sixes"), _balls(t)),
                "(4s + 6s) ÷ balls faced × 100", "6 ÷ 27 = 22%", targets={"t20": (15, 22)},
                count=_balls, min_n=100),
        measure("controlPct", "Control %", lambda t: None if not _balls(t) else 100 - pct(t.m("batting"), _balls(t)),
                "100 − (false shots ÷ balls faced × 100)", "100 − 14.8 = 85%", targets=(75, 82),
                count=_balls, min_n=100, col="Control %"),
        measure("economy", "Economy", lambda t: div(t.f("bowlRuns"), _overs(t)),
                "Runs conceded (wides and no-balls in, byes out) ÷ overs", "29 ÷ 4 = 7.25", unit="rate",
                places=2, better="lower", targets={"t20": (7.5, 8.5), "odi": (5.5, 5.0)},
                text={"t20": ("7.5 or less", "8.5 or less (IPL)"), "odi": ("5.5 or less", "5.0 or less")},
                count=_legal, min_n=120, col="Econ."),
        measure("bowlSR", "Bowling strike rate", lambda t: div(_legal(t), t.f("wickets")),
                "Legal balls ÷ wickets", "96 ÷ 5 = 19.2", unit="rate", places=1, better="lower",
                targets={"t20": (20, 18), "odi": (36, 30)}, count=_legal, min_n=120),
        measure("bowlAvg", "Bowling average", lambda t: div(t.f("bowlRuns"), t.f("wickets")),
                "Runs conceded ÷ wickets", "116 ÷ 5 = 23.2", unit="rate", places=1, better="lower",
                targets=(25, 25), count=_legal, min_n=120),
        measure("bowlDotPct", "Bowling dot-ball %", lambda t: pct(t.f("bowlDots"), _legal(t)),
                "Dots ÷ legal balls × 100", "46 ÷ 96 = 48%", targets={"t20": (45, 40)},
                count=_legal, min_n=120),
        measure("boundaryConcPct", "Boundary-conceded %", lambda t: pct(t.f("boundariesConc"), _legal(t)),
                "(4s + 6s conceded) ÷ legal balls × 100", "11 ÷ 96 = 11.5%", better="lower",
                targets={"t20": (12, 18)}, count=_legal, min_n=120),
        measure("extrasPerOver", "Extras per over", lambda t: div(t.f("wides", "noBalls"), _overs(t)),
                "(Wides + no-balls) ÷ overs", "6 ÷ 16 = 0.38", unit="rate", places=2, better="lower",
                targets=(0.5, 0.25), count=_legal, min_n=120),
        measure("catchEff", "Catch efficiency", lambda t: pct(t.p("catching"), t.p("catching") + t.m("catching")),
                "Catches ÷ (catches + drops) × 100", "7 ÷ 9 = 78%", targets=(70, 80),
                count=lambda t: t.p("catching") + t.m("catching"), min_n=5),
        measure("keeperConv", "Keeper chance conversion",
                lambda t: pct(t.p("keeping"), t.p("keeping") + t.m("keeping")),
                "(Catches + stumpings) ÷ chances × 100", "6 ÷ 7 = 86%", targets=(80, 90),
                count=lambda t: t.p("keeping") + t.m("keeping"), min_n=5),
        measure("runs", "Runs", lambda t: t.f("runs"), unit="count", extra=True),
        measure("balls", "Balls faced", _balls, unit="count", extra=True, col="Balls"),
        measure("overs", "Overs bowled", _legal, unit="overs", extra=True, col="Overs"),
        measure("wicketsM", "Wickets", lambda t: t.f("wickets"), unit="count", extra=True, col="Wkts"),
        measure("catches", "Catches", lambda t: t.p("catching"), unit="count", extra=True, col="Ct"),
        # team summary
        measure("runRate", "Run rate", lambda t: _run_rate(t, 0), unit="rate", places=2, extra=True, team=True),
        measure("oppRunRate", "Opponent run rate", lambda t: _run_rate(t, 1), unit="rate", places=2,
                extra=True, team=True),
        measure("netBoundary", "Net boundary %",
                lambda t: None if not (_balls(t) and _legal(t) > 0) else
                pct(t.f("fours", "sixes"), _balls(t)) - pct(t.f("boundariesConc"), _legal(t)),
                unit="signed", places=1, extra=True, team=True,
                note="The side with more boundaries wins about 85% of T20 matches."),
        measure("netDot", "Net dot %",
                lambda t: None if not (_balls(t) and _legal(t) > 0) else
                pct(t.f("bowlDots"), _legal(t)) - pct(t.f("dots"), _balls(t)),
                unit="signed", places=1, extra=True, team=True),
        measure("widesT", "Wides bowled", lambda t: t.f("wides"), unit="count", extra=True, team=True),
        measure("noBallsT", "No-balls bowled", lambda t: t.f("noBalls"), unit="count", extra=True, team=True),
        measure("drops", "Drops", lambda t: t.m("catching"), unit="count", extra=True, team=True),
        *_phase("pp", 0), *_phase("mid", 1), *_phase("death", 2),
        # for the position engine
        efficiency("runningEff", "Running efficiency %", ["running"], (5, 25)),
        efficiency("fieldingEff", "Ground-fielding efficiency %", ["fielding"], (20, 40)),
        mix("mixBat", "Share of balls: batting", ["batting"], 60, of=CR_ROLE),
        mix("mixBowl", "Share of balls: bowling", ["bowling"], 60, of=CR_ROLE),
        mix("mixKeep", "Share of balls: keeping", ["keeping"], 60, of=CR_ROLE),
        measure("openerPct", "Innings opening the batting", lambda t: _innings_share(t, 1, 2),
                extra=True, role=True, anchors=(0, 100), count=_innings,
                min_n=3, note="Share of innings batting at 1 or 2."),
        measure("middlePct", "Innings in the middle order", lambda t: _innings_share(t, 3, 7),
                extra=True, role=True, anchors=(0, 100), count=_innings,
                min_n=3, note="Share of innings batting at 3 to 7."),
    ],
    "partC": ["pos", "batPos", "runs", "balls", "battingSR", "controlPct", "overs", "bowlRuns", "wicketsM",
              "economy", "catches", "coord", "overall", "strength", "improve"],
    "partD": ["match_no", "date", "opponent", "result", "runs", "balls", "battingSR", "controlPct", "overs",
              "wicketsM", "economy", "catches", "coord", "overall", "trend", "remarks"],
    "team": ["runRate", "oppRunRate", "netBoundary", "netDot", "controlPct", "widesT", "noBallsT", "byes",
             "legByes", "catchEff", "drops", "runsAfterDrops",
             "ppRuns", "ppWkts", "ppRR", "ppDotPct", "midRuns", "midWkts", "midRR", "midDotPct",
             "deathRuns", "deathWkts", "deathRR", "deathDotPct", "top:runs:1", "top:wicketsM:1"],
    "team_fields": [
        team_field("byes", "Byes conceded", hi=100),
        team_field("legByes", "Leg-byes conceded", hi=100),
        team_field("runsAfterDrops", "Runs scored after our drops", hi=500),
        *[team_field(f"{p}{what}", f"{phase} {label}", hi=400)
          for p, phase in (("pp", "Powerplay"), ("mid", "Middle overs"), ("death", "Death overs"))
          for what, label in (("Runs", "runs"), ("Wkts", "wickets"), ("Dots", "dot balls"))],
    ],
    "team_labels": {"controlPct": "Team control %"},
    "team_note": "Phases are overs 1–6, 7–15 and 16–20 in T20, and 1–10, 11–40 and 41–50 in 50-over "
                 "matches — our batting innings.",
    "score": {"label": "Score (us – them)", "parts": ["Runs", "Wickets", "Overs"]},
    "results": ["Won", "Lost", "Tied", "No result"],
    "sheet_note": "Tally every ball: batters for each ball faced, bowlers for each delivery. Circle 4s and 6s.",
    "b2_note": "Some University bowling targets look stricter than Elite because IPL scoring is so fast "
               "(9.6–9.9 runs an over), not because students bowl better. Rates count towards the report "
               "after about 100 balls faced or 20 overs bowled. 50-over matches: phases become overs "
               "1–10, 11–40 and 41–50, and bowlers need a spell log and maidens.",
    "coordination": "Coordination = calling and running between the wickets, backing up and "
                    "communication in the field, field awareness, and support for the bowler. It is a "
                    "coach's rating, not a tally.",
    "b4": ["Phase splits of strike rate, economy, dot % and boundary %.",
           "Match-ups (vs pace or spin, vs right- or left-handers).",
           "Expected wickets (about one per 5 false shots induced).",
           "Attacking-shot %.",
           "Death-over execution (yorker %).",
           "Fielding runs saved and drop cost."],
    "zones": [
        zone("wagon", "A. BATTING — WAGON WHEEL (mirror it for left-handers)", "Sector",
             ["Fine leg", "Square leg", "Midwicket", "Long-on", "Long-off", "Cover", "Point", "Third man"],
             ["Runs", "4s", "6s", "False shots", "Out (X)"]),
        zone("length", "B. BOWLING — LENGTH", "Length",
             ["Yorker", "Full", "Good", "Back of a length", "Short"],
             ["Balls", "Dots", "Runs", "Wickets", "4s / 6s", "False shots"]),
        zone("line", "C. BOWLING — LINE", "Line",
             ["Wide outside off", "Off stump", "Stumps", "Leg"],
             ["Balls", "Dots", "Runs", "Wickets", "4s / 6s", "False shots"]),
        zone("keeping", "D. WICKETKEEPING", "Position", ["Standing up", "Standing back"],
             ["Takes", "Catches", "Stumpings", "Byes / misses"]),
        zone("fielding", "E. FIELDING", "Where", ["Close / slips", "Inner ring", "Outfield"],
             ["Chances", "Catches", "Drops", "Saves", "Misfields"]),
        zone("overs", "F. OVER LOG", "Over", [str(i) for i in range(1, 21)],
             ["Bowler (jersey no.)", "Runs", "Wickets", "Dots", "Extras"], total=False, print_only=True),
        support(("Backing up", "Communication / call", "Emergency stop / save")),
    ],
    "weights": {
        "Opening Batsman": {"openerPct": 0.30, "battingSR": 0.20, "controlPct": 0.20, "battingAvg": 0.15,
                            "runningEff": 0.15},
        "Middle-order Batsman": {"middlePct": 0.25, "battingAvg": 0.25, "controlPct": 0.20,
                                 "battingSR": 0.15, "runningEff": 0.15},
        "Fast Bowler": {"mixBowl": 0.25, "economy": 0.20, "bowlSR": 0.25, "bowlDotPct": 0.15,
                        "extrasPerOver": 0.15},
        "Spin Bowler": {"mixBowl": 0.25, "economy": 0.30, "bowlDotPct": 0.20, "bowlAvg": 0.15,
                        "extrasPerOver": 0.10},
        "Wicketkeeper": {"mixKeep": 0.50, "keeperConv": 0.35, "battingSR": 0.15},
        "All-rounder": {"mixBat": 0.20, "mixBowl": 0.20, "battingSR": 0.15, "economy": 0.15, "bowlSR": 0.15,
                        "controlPct": 0.15},
    },
}


# --------------------------------------------------------------------------- #
# Badminton — one player, shot by shot (each doubles partner scored separately)
# --------------------------------------------------------------------------- #

RACKET_PART_A = ("Score one player shot by shot. In doubles, tally each partner separately and write "
                 "their formation. Write U beside a − that was an unforced error (the player had time "
                 "and was in position).")

BADMINTON = {
    "layout": "player",
    "b1_head": "Playing style that relies on it",
    "header_extra": [("event", "Event", ["Singles", "Doubles", "Mixed doubles"]),
                     ("duration", "Duration (min)", None)],
    "skills": [
        skill("serve", "Serve (short or flick)", ("Winner / attack", "Neutral", "Fault"),
              "Service winner, or a high or loose reply you attack", "Neutral net reply or lift",
              "Fault (above 1.15 m, net, out), or the receiver rushes and kills it", "All; decisive in doubles",
              sheet="SERVE"),
        skill("receive", "Receive", ("Attack", "Neutral", "Error"),
              "Push, rush or kill that wins or forces a lift", "Neutral net shot or lift",
              "Error, or a loose lift that gets smashed", "Attacking, All-court"),
        skill("smash", "Smash (incl. jump smash)", ("Winner", "Returned", "Error"),
              "Winner, or forces a weak block you then kill", "Returned, neutral",
              "Net or out, or countered for a winner", "Attacking", sheet="SMASH"),
        skill("net", "Net play (net shot, spin, kill, push)", ("Tight / kill", "Playable", "Error"),
              "Tight shot that forces a lift or error, or a net-kill winner", "Playable reply",
              "Net or out, or a loose shot the opponent kills", "All styles", sheet="NET PLAY"),
        skill("lift", "Lift / clear", ("Deep", "Adequate", "Short / out"),
              "Deep to the back line, pulls the opponent out of position", "Adequate length",
              "Short lift that gets smashed, or out", "Defensive"),
        skill("drop", "Drop / slice", ("Winner / lift", "Neutral", "Error"),
              "Winner, or forces a lift from low", "Neutral", "Net, or floats up and gets killed",
              "All-court, Defensive"),
        skill("defence", "Defence (block, return of smash)", ("Counter", "Pressure", "Error"),
              "Counter-winner, or a tight block that makes the attacker lift", "Returned but still under pressure",
              "Error, or a weak return that gets killed", "Defensive", sheet="DEFENCE"),
        skill("drive", "Drive", ("Winner", "Flat", "Error"),
              "Winner, or forces a pop-up", "Flat exchange continues", "Error, or pops up and gets killed",
              "Attacking, doubles"),
    ],
    "fields": [field("winners", "Winners", "W"),
               field("unforced", "Unforced errors (U)", "UE"),
               field("servesWon", "Rallies won on own serve", "Won serving"),
               field("receiveWon", "Rallies won receiving", "Won receiving"),
               field("smashWinners", "Smash winners"),
               field("netKills", "Net kills"),
               field("netKillWinners", "Net-kill winners")],
    "measures": [
        measure("wue", "Winner : unforced error", lambda t: t.f("winners") / max(t.f("unforced"), 1),
                "Winners ÷ unforced errors", "14 ÷ 12 = 1.17", unit="ratio", targets=(1.0, 1.2),
                count=lambda t: t.f("winners", "unforced"), min_n=20, col="W : UE"),
        measure("serveWonPct", "Points won on own serve %", lambda t: pct(t.f("servesWon"), t.n("serve")),
                "Rallies won serving ÷ rallies served × 100", "22 ÷ 40 = 55%", targets=(48, 50),
                count=lambda t: t.n("serve"), min_n=40, col="Won on serve %"),
        measure("serveErrPct", "Serve error %", lambda t: pct(t.m("serve"), t.n("serve")),
                "Serve − ÷ serves × 100", "1 ÷ 40 = 2.5%", better="lower", targets=(3, 1),
                count=lambda t: t.n("serve"), min_n=40, col="Serve err. %"),
        measure("receiveErrPct", "Receive error %", lambda t: pct(t.m("receive"), t.n("receive")),
                "Receive errors ÷ receives × 100", "4 ÷ 40 = 10%", better="lower", targets=(12, 7),
                count=lambda t: t.n("receive"), min_n=40, col="Receive err. %"),
        measure("smashWinPct", "Smash winner %", lambda t: pct(t.f("smashWinners"), t.n("smash")),
                "Smash winners ÷ smashes × 100", "3 ÷ 20 = 15%", targets=(12, 13), row="smash",
                count=lambda t: t.n("smash"), min_n=20, col="Smash win %"),
        measure("smashErrPct", "Smash error %", lambda t: pct(t.m("smash"), t.n("smash")),
                "Smash errors ÷ smashes × 100", "3 ÷ 20 = 15%", better="lower", targets=(10, 7), row="smash",
                count=lambda t: t.n("smash"), min_n=20),
        measure("netErrPct", "Net-shot error %", lambda t: pct(t.m("net"), t.n("net")),
                "Net-shot errors ÷ net shots × 100", "2 ÷ 25 = 8%", better="lower", targets=(8, 5),
                count=lambda t: t.n("net"), min_n=25, col="Net err. %"),
        measure("netKillPct", "Net-kill conversion %", lambda t: pct(t.f("netKillWinners"), t.f("netKills")),
                "Net-kill winners ÷ net kills × 100", "4 ÷ 6 = 67%", targets=(50, 60),
                count=lambda t: t.f("netKills"), min_n=10),
        measure("liftNegPct", "Lift / clear − %", lambda t: pct(t.m("lift"), t.n("lift")),
                "Lift and clear − ÷ all lifts and clears × 100", "6 ÷ 30 = 20%", better="lower",
                targets=(25, 15), count=lambda t: t.n("lift"), min_n=30, col="Lift − %"),
        measure("skillEff", "Skill efficiency", lambda t: t.eff(), "(+ − −) ÷ attempts, per skill",
                "Smash (8 − 3) ÷ 20 = 25%", text=("Attacking shots 15%; defence 0% or better",
                                                   "Set from the squad")),
        measure("winnersM", "Winners", lambda t: t.f("winners"), unit="count", extra=True, col="W"),
        measure("unforcedM", "Unforced errors", lambda t: t.f("unforced"), unit="count", extra=True, col="UE"),
        measure("servesWonT", "Rallies won serving", lambda t: t.f("servesWon"), unit="count", extra=True,
                team=True),
        measure("receiveWonT", "Rallies won receiving", lambda t: t.f("receiveWon"), unit="count", extra=True,
                team=True),
        efficiency("effDefence", "Defence efficiency %", ["defence"], (-10, 10), min_n=20),
        efficiency("effDrop", "Drop efficiency %", ["drop"], (10, 30), min_n=15),
        mix("mixAttack", "Share of shots: smashes, drives, net play", ["smash", "drive", "net"], 60),
        mix("mixDefence", "Share of shots: defence, lifts and clears", ["defence", "lift"], 50),
    ],
    "partC": ["pos", "winnersM", "unforcedM", "wue", "serveWonPct", "serveErrPct", "receiveErrPct",
              "smashWinPct", "netErrPct", "coord", "overall", "strength", "improve"],
    "partD": ["match_no", "date", "opponent", "result", "winnersM", "unforcedM", "wue", "serveWonPct",
              "smashWinPct", "netErrPct", "liftNegPct", "coord", "overall", "trend", "remarks"],
    "team": ["servesWonT", "receiveWonT", "winnersM", "unforcedM", "wue", "serveErrPct", "receiveErrPct",
             "longestStreak", "gpWon", "gpChances", "gpSaved", "gpFaced"],
    "team_fields": [team_field("longestStreak", "Longest point streak", hi=30),
                    team_field("gpWon", "Game points converted", hi=20),
                    team_field("gpChances", "Game points held", hi=20),
                    team_field("gpSaved", "Game points saved", hi=20),
                    team_field("gpFaced", "Game points faced", hi=20)],
    "team_title": "Match summary",
    "score": {"label": "Game scores", "parts": ["G1", "G2", "G3"]},
    "results": ["Won", "Lost"],
    "sheet_note": RACKET_PART_A,
    "b2_note": "Elite figures come from Tokyo 2020 men's singles and the BWF top 15. Weaker defence lets "
               "university smashes win more often than elite ones, so smashes are judged on errors and "
               "+ %, not winners alone.",
    "coordination": "Coordination = footwork and court coverage, reading the opponent, and (in doubles) "
                    "rotation and communication with the partner. It is a coach's rating, not a tally.",
    "b4": ["Rear-court smash choice % (BWF top 15: 55%, university: 45%).",
           "Smash after a lift vs after a clear.",
           "Count of \"negative\" shots (loose lifts and short clears).",
           "Long-rally win %.",
           "Receive-attack rate."],
    "zones": [
        zone("court", "A. COURT ZONES", "Zone",
             ["Front – forehand", "Front – backhand", "Mid – forehand", "Mid – backhand",
              "Rear – forehand", "Rear – backhand"],
             ["Attempts", "Winners", "Errors"]),
        zone("serve", "B. SERVE BOX", "Serve", ["Short – T", "Short – wide", "Flick"],
             ["Serves", "Rallies won", "Faults"]),
        support(("Cover / recovery", "Communication / call (doubles)", "Emergency retrieve"), letter="C"),
    ],
    "weights": {
        "Attacking / Power player": {"mixAttack": 0.25, "smashWinPct": 0.25, "smashErrPct": 0.15, "wue": 0.20,
                                     "netKillPct": 0.15},
        "Defensive / Counter player": {"mixDefence": 0.30, "effDefence": 0.25, "liftNegPct": 0.20,
                                       "receiveErrPct": 0.10, "netErrPct": 0.15},
        "All-court / Balanced": {"wue": 0.30, "serveWonPct": 0.20, "netErrPct": 0.15, "effDrop": 0.15,
                                 "receiveErrPct": 0.20},
    },
}


# --------------------------------------------------------------------------- #
# Tennis — Elite = seeded players at Grand Slams (men's figure first in the doc)
# --------------------------------------------------------------------------- #

TN_RALLY = ["ret", "forehand", "backhand", "net", "defence"]

TENNIS = {
    "layout": "player",
    "b1_head": "Playing style that relies on it",
    "header_extra": [("event", "Event", ["Singles", "Doubles", "Mixed doubles"]),
                     ("duration", "Duration (min)", None)],
    "skills": [
        skill("first", "1st serve", ("Ace / attack", "In", "Fault"),
              "Ace, unreturned, or a weak return the server attacks", "In, returned neutrally",
              "Fault (tallied; the point goes on), or the return puts the server on defence",
              "Attacking, All-court"),
        skill("second", "2nd serve", ("Ace / attack", "In", "DF"),
              "Same as 1st serve", "In, neutral", "Double fault, or the return attacks it", "All"),
        skill("ret", "Return", ("Winner / deep", "In play", "Error"),
              "Winner, forces an error, or a deep return that turns the point", "In play",
              "Return error, or a short sitter", "Defensive, All-court"),
        skill("forehand", "Forehand", ("Winner", "In play", "Error (U)"),
              "Winner, or forces an error", "In play",
              "Error (U if unforced), or a short ball that gets attacked", "Attacking"),
        skill("backhand", "Backhand", ("Winner", "In play", "Error (U)"),
              "Winner, or forces an error", "In play",
              "Error (U if unforced), or a short ball that gets attacked", "All-court, Defensive"),
        skill("net", "Net play (approach, volley, overhead)", ("Winner", "In play", "Error / passed"),
              "Winner, or forces an error", "Volley stays in play", "Error, or passed", "All-court",
              sheet="NET PLAY"),
        skill("defence", "Defence (lob, slice, passing shot)", ("Pass / neutral", "Alive", "Error"),
              "Passing winner, forces an error, or neutralises the point", "Keeps the rally alive",
              "Error, or a sitter", "Defensive", sheet="DEFENCE"),
    ],
    "fields": [
        field("firstServes", "1st serves hit", "1st hit"),
        field("firstIn", "1st serves in", "1st in"),
        field("firstWon", "Points won on 1st serve", "Won 1st"),
        field("secondPts", "2nd-serve points", "2nd pts"),
        field("secondWon", "Points won on 2nd serve", "Won 2nd"),
        field("aces", "Aces"),
        field("doubleFaults", "Double faults", "DF"),
        field("winners", "Winners", "W"),
        field("unforced", "Unforced errors (U)", "UE"),
        field("netPts", "Net approaches", "Net pts"),
        field("netWon", "Net points won", "Net won"),
        field("bpChances", "Break-point chances", "BP chances"),
        field("bpWon", "Break points won", "BP won"),
        field("bpFaced", "Break points faced", "BP faced"),
        field("bpSaved", "Break points saved", "BP saved"),
        field("returnPts", "Return points played", "Ret. pts"),
        field("returnWon", "Return points won", "Ret. won"),
    ],
    "measures": [
        measure("firstInPct", "1st serve in %", lambda t: pct(t.f("firstIn"), t.f("firstServes")),
                "1st serves in ÷ 1st serves hit × 100", "30 ÷ 50 = 60%", targets=(55, 62),
                count=lambda t: t.f("firstServes"), min_n=50, col="1st in %"),
        measure("firstWonPct", "1st-serve points won %", lambda t: pct(t.f("firstWon"), t.f("firstIn")),
                "Points won ÷ 1st serves in × 100", "20 ÷ 30 = 67%", targets={"M": (62, 72), "W": (57, 64)},
                count=lambda t: t.f("firstIn"), min_n=30, col="1st won %"),
        measure("secondWonPct", "2nd-serve points won %", lambda t: pct(t.f("secondWon"), t.f("secondPts")),
                "Points won ÷ 2nd-serve points × 100", "9 ÷ 20 = 45%", targets={"M": (45, 50), "W": (40, 46)},
                count=lambda t: t.f("secondPts"), min_n=20, col="2nd won %"),
        measure("acePct", "Aces %", lambda t: pct(t.f("aces"), t.f("firstServes")),
                "Aces ÷ service points × 100", "3 ÷ 50 = 6%", targets={"M": (5, 10), "W": (2, 4)},
                text={"M": ("5%", "10% (lower on clay)"), "W": ("2%", "4% (lower on clay)")},
                count=lambda t: t.f("firstServes"), min_n=50, col="Ace %"),
        measure("dfPct", "Double faults %", lambda t: pct(t.f("doubleFaults"), t.f("secondPts")),
                "Double faults ÷ 2nd serves × 100", "3 ÷ 20 = 15%", better="lower",
                targets={"M": (15, 10), "W": (15, 12)}, count=lambda t: t.f("secondPts"), min_n=20, col="DF %"),
        measure("wue", "Winner : unforced error", lambda t: t.f("winners") / max(t.f("unforced"), 1),
                "Winners ÷ unforced errors", "18 ÷ 24 = 0.75", unit="ratio",
                targets={"M": (0.8, 1.3), "W": (0.7, 0.85)}, count=lambda t: t.f("winners", "unforced"),
                min_n=20, col="W : UE"),
        measure("netWonPct", "Net points won %", lambda t: pct(t.f("netWon"), t.f("netPts")),
                "Points won at net ÷ net approaches × 100", "12 ÷ 18 = 67%", targets={"M": (58, 67), "W": (58, 65)},
                count=lambda t: t.f("netPts"), min_n=15, col="Net won %"),
        measure("bpConvPct", "Break points converted %", lambda t: pct(t.f("bpWon"), t.f("bpChances")),
                "Break points won ÷ chances × 100", "4 ÷ 10 = 40%", targets={"M": (35, 40), "W": (40, 45)},
                count=lambda t: t.f("bpChances"), min_n=10),
        measure("bpSavedPct", "Break points saved %", lambda t: pct(t.f("bpSaved"), t.f("bpFaced")),
                "Saved ÷ faced × 100", "5 ÷ 8 = 63%", targets={"M": (50, 60), "W": (50, 54)},
                count=lambda t: t.f("bpFaced"), min_n=10),
        measure("returnWonPct", "Return points won %", lambda t: pct(t.f("returnWon"), t.f("returnPts")),
                "Return points won ÷ return points × 100", "26 ÷ 70 = 37%", targets={"M": (35, 38), "W": (40, 43)},
                count=lambda t: t.f("returnPts"), min_n=50, col="Return won %"),
        measure("winnersM", "Winners", lambda t: t.f("winners"), unit="count", extra=True, col="W"),
        measure("unforcedM", "Unforced errors", lambda t: t.f("unforced"), unit="count", extra=True, col="UE"),
        measure("acesT", "Aces", lambda t: t.f("aces"), unit="count", extra=True, team=True),
        measure("dfT", "Double faults", lambda t: t.f("doubleFaults"), unit="count", extra=True, team=True),
        measure("pointsWonPct", "Total points won %", lambda t: pct(t.team("pointsWon"), t.team("totalPoints")),
                extra=True, team=True),
        *[measure(f"rally{k}Pct", f"Points won, {label} shots", 
                  lambda t, k=k: pct(t.team(f"rally{k}Won"), t.team(f"rally{k}Played")), extra=True, team=True)
          for k, label in (("04", "0–4"), ("58", "5–8"), ("9", "9+"))],
        efficiency("effForehand", "Forehand efficiency %", ["forehand"], (0, 20), min_n=30),
        efficiency("effBackhand", "Backhand efficiency %", ["backhand"], (-5, 15), min_n=30),
        efficiency("effDefence", "Defence efficiency %", ["defence"], (-10, 10), min_n=15),
        mix("mixNet", "Share of rally shots: net play", ["net"], 25, of=TN_RALLY),
        mix("mixDefence", "Share of rally shots: defence", ["defence"], 30, of=TN_RALLY),
    ],
    "partC": ["pos", "winnersM", "unforcedM", "wue", "firstInPct", "firstWonPct", "secondWonPct", "acePct",
              "dfPct", "netWonPct", "returnWonPct", "coord", "overall", "strength", "improve"],
    "partD": ["match_no", "date", "opponent", "result", "winnersM", "unforcedM", "wue", "firstInPct",
              "firstWonPct", "secondWonPct", "returnWonPct", "coord", "overall", "trend", "remarks"],
    "team": ["serviceGames", "gamesHeld", "breaksWon", "pointsWonPct", "firstInPct", "firstWonPct",
             "secondWonPct", "acesT", "dfT", "winnersM", "unforcedM", "wue", "netWonPct", "bpConvPct",
             "bpSavedPct", "returnWonPct", "rally04Pct", "rally58Pct", "rally9Pct"],
    "team_fields": [team_field("serviceGames", "Service games played", hi=60),
                    team_field("gamesHeld", "Service games held", hi=60),
                    team_field("breaksWon", "Breaks of serve won", hi=60),
                    team_field("totalPoints", "Total points played", hi=500),
                    team_field("pointsWon", "Total points won", hi=500),
                    *[team_field(f"rally{k}{what}", f"Rallies of {label} shots: {word}", hi=500)
                      for k, label in (("04", "0–4"), ("58", "5–8"), ("9", "9+"))
                      for what, word in (("Played", "played"), ("Won", "won"))]],
    "team_title": "Match summary",
    "score": {"label": "Set scores", "parts": ["S1", "S2", "S3"]},
    "results": ["Won", "Lost"],
    "sheet_note": RACKET_PART_A,
    "b2_note": "Elite figures are seeded players at Grand Slams. University targets sit below NCAA "
               "Division I men, who play close to pro level (66% of 1st-serve points won, vs 71% on the ATP tour).",
    "coordination": "Coordination = shot selection and tactics, court positioning and recovery, composure "
                    "between points and, in doubles, teamwork with the partner. It is a coach's rating, "
                    "not a tally.",
    "b4": ["Serve effectiveness: how often the serve wins or sets up the point (ATP tour average 58% on "
           "1st serves, 23% on 2nd).",
           "First-serve rating (in % × won %).",
           "Rally-length split.",
           "Winners and unforced errors as a % of points.",
           "Win % by serve direction."],
    "zones": [
        zone("first", "A. 1ST SERVE TARGETS", "Target",
             ["Deuce – wide", "Deuce – body", "Deuce – T", "Ad – wide", "Ad – body", "Ad – T"],
             ["Serves", "In", "Won", "Aces"]),
        zone("second", "B. 2ND SERVE TARGETS", "Target",
             ["Deuce – wide", "Deuce – body", "Deuce – T", "Ad – wide", "Ad – body", "Ad – T"],
             ["Serves", "In", "Won", "Double faults"]),
        zone("landing", "C. RALLY LANDING", "Where it landed",
             ["Deep – ad side", "Deep – middle", "Deep – deuce side",
              "Short – ad side", "Short – middle", "Short – deuce side"],
             ["Shots", "Winners", "Errors"]),
        zone("misses", "D. ERRORS BY MISS TYPE", "Miss", ["Net", "Long", "Wide"],
             ["Forehand", "Backhand", "Volley / overhead"]),
        zone("net", "E. NET BOX", "Shot", ["Approach", "Volley", "Overhead"],
             ["Played", "Won", "Errors / passed"]),
        support(("Cover / recovery", "Communication / call (doubles)", "Emergency retrieve"), letter="F"),
    ],
    "weights": {
        "Attacking / Power player": {"firstWonPct": 0.25, "acePct": 0.20, "wue": 0.20, "effForehand": 0.20,
                                     "firstInPct": 0.15},
        "Defensive / Counter player": {"returnWonPct": 0.30, "mixDefence": 0.25, "effDefence": 0.20,
                                       "dfPct": 0.10, "bpSavedPct": 0.15},
        "All-court / Balanced": {"netWonPct": 0.25, "mixNet": 0.25, "wue": 0.20, "secondWonPct": 0.15,
                                 "effBackhand": 0.15},
    },
}


# --------------------------------------------------------------------------- #
# Kho-kho — the mat format by default; traditional chosen per match
# --------------------------------------------------------------------------- #

TURN_MINUTES = {"mat": 7, "traditional": 9}
POINTS_PER_OUT = {"mat": 2, "traditional": 1}
KK_CHASE = ["touch", "pole", "sky", "kho", "turn", "sitting"]
KK_DIVES = ["touch", "pole", "sky"]


def _outs(t):
    return t.p(*KK_DIVES)


KHOKHO = {
    "formats": {"mat": "Mat (7-minute turns, 2 points per out)",
                "traditional": "Traditional (9-minute turns, 1 point per out)"},
    "b1_head": "Positions who record it",
    "skills": [
        skill("touch", "Touch attempt (running touch, tapping)", ("Out", "Turned", "Miss / foul"),
              "Defender out by a legal touch",
              "Missed, but the defender had to turn or was pushed toward a post or sitting chaser",
              "Missed with a foul (receding, turning the shoulder more than 90°, touching the central lane), "
              "a touch voided by a foul, or an overrun", "Chaser (active, Wazir)", sheet="TOUCH"),
        skill("pole", "Pole dive", ("Out", "Blocked", "Miss"),
              "Out with the hand at the post", "Missed, but the defender's pole turn was blocked",
              "Missed and left grounded; post kicked; central lane crossed", "Chaser"),
        skill("sky", "Sky dive", ("Out", "Cut line", "Miss / foul"),
              "Out while fully in the air", "Missed, but the escape line was cut",
              "Missed and left grounded, or a foul", "Chaser"),
        skill("kho", "Giving kho", ("Leads to out", "Legal", "Foul"),
              "Legal kho that leads to an out or an immediate chance", "Legal kho, no advantage",
              "Late kho (feet past the cross lane), \"kho\" said before the touch, wrong word, kho on an "
              "extended limb", "Chaser (active)"),
        skill("turn", "Direction / pole turn", ("Cuts off", "Legal", "Foul"),
              "Turn round the post that cuts off the defender", "Routine legal turn",
              "Receding, shoulder turned more than 90°, post kicked, entering the other half without "
              "rounding the post", "Chaser", sheet="POLE TURN"),
        skill("sitting", "Sitting / receiving kho", ("Sudden attack", "Normal", "Foul"),
              "Fast legal rise and an immediate out (sudden attack)", "Normal rise",
              "Rising before the kho, or leaning into or obstructing a defender", "Chaser (sitting)",
              sheet="SITTING"),
        skill("run", "Defensive run (timed from entry)", ("In / 90 s+", "Out 30–89 s", "Out < 30 s"),
              "Still in at the end of the turn, or 90 s or more", "Out after 30–89 s",
              "Out in under 30 s, or out by own error", "Runner / Dodger", sheet="DEFENSIVE RUN"),
        skill("dodge", "Dodge (zig-zag, single or double chain, ring, pole dodge, feint)",
              ("Beats it", "Pinned", "Out"),
              "Beats a touch or dive, or draws a foul",
              "Survives but gives up ground (pinned at a post or the boundary)", "Touched out, or stepped out",
              "Runner / Dodger", sheet="DODGE"),
        skill("entry", "Entry and discipline", ("On time", None, "Error"),
              "Enters through the entry zone on time", "—",
              "Late entry, boundary out, touching a sitting chaser (warning, then out), self-out",
              "Runner / Dodger", sheet="ENTRY", marks="+-"),
    ],
    "fields": [field("matSeconds", "Time on the mat (seconds)", "Time on mat", kind="seconds", hi=3600),
               field("notOuts", "Runs still in at the end of the turn", "Not out", hi=20)],
    "measures": [
        measure("touchSuccess", "Touch success %", lambda t: pct(_outs(t), t.n(*KK_DIVES)),
                "Outs ÷ (touch + dive attempts) × 100", "6 ÷ 16 = 37.5%", targets=(35, 50),
                count=lambda t: t.n(*KK_DIVES), min_n=10, col="Touch %"),
        measure("outsPerMin", "Team outs per attacking minute",
                lambda t: div(_outs(t), (t.team("attackTurns") or 0) * TURN_MINUTES.get(t.format, 7)),
                "Team outs ÷ attacking minutes", "17 ÷ 14 = 1.2", unit="rate", places=2, targets=(0.9, 1.4),
                text=("0.9 (about 6 a turn)", "1.4 (about 10 a turn)"), team=True),
        measure("chaserOuts", "Chaser outs per match", lambda t: div(_outs(t), t.matches),
                "Player's outs ÷ matches", "7 ÷ 3 = 2.3", unit="rate", places=1, targets=(1.5, 3),
                count=lambda t: t.matches, min_n=2, col="Outs"),
        measure("diveShare", "Dive share %", lambda t: pct(t.p("pole", "sky"), _outs(t)),
                "(Pole-dive + sky-dive outs) ÷ outs × 100", "3 ÷ 7 = 43%", targets=(30, 60),
                count=_outs, min_n=5, col="Dive share %"),
        measure("khoQuality", "Kho quality %", lambda t: pct(t.p("kho"), t.n("kho")),
                "Kho + ÷ all khos", "9 ÷ 32 = 28%", targets=(25, 40), row="kho",
                count=lambda t: t.n("kho"), min_n=10, col="Kho + %"),
        measure("khoFoul", "Kho foul %", lambda t: pct(t.m("kho"), t.n("kho")),
                "Kho − ÷ all khos", "3 ÷ 32 = 9%", better="lower", targets=(10, 5), row="kho",
                count=lambda t: t.n("kho"), min_n=10, col="Kho foul %"),
        measure("foulsPerTurn", "Attacking fouls per turn",
                lambda t: div(t.m(*KK_CHASE), t.team("attackTurns")),
                "Team fouls ÷ attacking turns", "7 ÷ 2 = 3.5", unit="rate", places=1, better="lower",
                targets=(3, 1.5), team=True),
        measure("defendTime", "Defending time per match", lambda t: div(t.f("matSeconds"), t.matches),
                "Total seconds on the mat ÷ matches", "0:48 + 1:35 = 2:23", unit="seconds",
                targets=(60, 100), count=lambda t: t.matches, min_n=2),
        measure("avgRun", "Average time per run", lambda t: div(t.f("matSeconds"), t.n("run")),
                "Total seconds on the mat ÷ runs", "273 ÷ 3 = 91 s", unit="seconds", targets=(45, 75),
                count=lambda t: t.n("run"), min_n=3, col="Avg run"),
        measure("notOutPct", "Not-out %", lambda t: pct(t.f("notOuts"), t.n("run")),
                "Runs still in at the end of the turn ÷ runs × 100", "2 ÷ 9 = 22%", targets=(10, 20),
                count=lambda t: t.n("run"), min_n=5),
        measure("batch", "Batch survival & dream runs",
                lambda t: None if not t.team("batches") else
                f"{_clock(t.team('batchSeconds') / t.team('batches'))} average, "
                f"{t.team('dreamRuns') or 0} of {t.team('batches')} reached 3:00",
                "Average batch time; batches reaching 3:00 ÷ batches", "1:51 average, 1 in 4", unit="text",
                text=("1:45; 1 dream run a match", "1 dream run every defending turn"), team=True),
        measure("dreamPts", "Dream-run points", lambda t: t.team("dreamPoints"),
                "1 point at 3:00, then 1 more every 30 s", "4:10 → 3 points", unit="count",
                text=("—", "—"), team=True),
        measure("teamPoints", "Team points",
                lambda t: POINTS_PER_OUT.get(t.format, 2) * _outs(t) + (t.team("dreamPoints") or 0),
                "2 × outs + dream-run points (traditional: 1 × outs)", "7 outs + 3 = 17", unit="count",
                text=("—", "—"), team=True),
        measure("defErrors", "Defender errors per match", lambda t: div(t.m("entry"), t.matches),
                "(Boundary outs + late entries + self-outs + warnings) ÷ matches", "2 ÷ 2 = 1.0", unit="rate",
                places=1, better="lower", targets=(0.5, 0), count=lambda t: t.matches, min_n=2,
                col="Def. errors"),
        measure("outs", "Outs", _outs, unit="count", extra=True),
        measure("runs", "Runs", lambda t: t.n("run"), unit="count", extra=True),
        measure("outsS", "Outs: simple touch (S)", lambda t: t.p("touch"), unit="count", extra=True, team=True),
        measure("outsP", "Outs: pole dive (P)", lambda t: t.p("pole"), unit="count", extra=True, team=True),
        measure("outsD", "Outs: dive (D)", lambda t: t.p("sky"), unit="count", extra=True, team=True),
        measure("outsSA", "Outs: sudden attack (SA)", lambda t: t.p("sitting"), unit="count", extra=True,
                team=True),
        measure("khoCount", "Khos given", lambda t: t.n("kho"), unit="count", extra=True, team=True),
        measure("matTime", "Time on the mat", lambda t: t.f("matSeconds"), unit="seconds", extra=True),
        efficiency("dodgeEff", "Dodge efficiency %", ["dodge"], (0, 30)),
        mix("mixChase", "Share of actions: chasing", KK_CHASE, 80, min_n=10),
        mix("mixDefend", "Share of actions: defending", ["run", "dodge"], 80, min_n=10),
    ],
    "partC": ["pos", "outs", "touchSuccess", "diveShare", "khoQuality", "khoFoul", "runs", "matSeconds",
              "avgRun", "notOuts", "defErrors", "coord", "overall", "strength", "improve"],
    "partD": ["match_no", "date", "opponent", "result", "outs", "touchSuccess", "diveShare", "khoQuality",
              "matSeconds", "avgRun", "notOuts", "defErrors", "coord", "overall", "trend", "remarks"],
    "team": ["teamPoints", "dreamPts", "outsS", "outsP", "outsD", "outsSA", "outsO", "outsL", "outsPerMin",
             "firstOut", "batch", "khoCount", "khoQuality", "khoFoul", "foulsPerTurn", "warnings", "cards",
             "top:outs:1", "top:matTime:1", "wazirOuts", "powerplayOuts"],
    "team_fields": [
        team_field("attackTurns", "Attacking turns played", hi=4),
        team_field("dreamPoints", "Dream-run points", hi=60),
        team_field("outsO", "Outs: out of field (O)", hi=40),
        team_field("outsL", "Outs: late entry (L)", hi=40),
        team_field("firstOut", "Time to the first out (average per turn)", kind="seconds", hi=540),
        team_field("batches", "Batches sent in", hi=60),
        team_field("batchSeconds", "Total batch time", kind="seconds", hi=3600),
        team_field("dreamRuns", "Batches reaching 3:00", hi=60),
        team_field("warnings", "Warnings", hi=40),
        team_field("cards", "Cards", hi=20),
        team_field("wazirOuts", "Wazir outs", hi=40),
        team_field("powerplayOuts", "Power-play outs", hi=40),
    ],
    "team_labels": {"khoQuality": "Kho quality %", "khoFoul": "Kho foul %"},
    "score": {"label": "Points by turn", "parts": ["Turn 1", "Turn 2", "Turn 3", "Turn 4"]},
    "results": ["Won", "Lost", "Tied"],
    "sheet_note": "Write the time (m:ss) beside every out and time each defender from entry. Out codes as "
                  "on the KKFI score sheet: S simple touch, P pole dive, D dive, SA sudden attack, "
                  "O out of field, L late entry.",
    "b2_note": "Elite targets come from Ultimate Kho Kho and the 2025 World Cup. Nobody publishes touch "
               "attempts, kho quality or foul rates, so those targets are estimates. Official matches use a "
               "scorer, an assistant scorer and two timekeepers; this card needs one person for attack, one "
               "for defence and a stopwatch.",
    "coordination": "Coordination = chase-chain communication and kho timing, covering the lanes, and batch "
                    "planning in defence. It is a coach's rating, not a tally.",
    "b4": ["Time to the first out each turn.",
           "Khos per out (length of the chase chain).",
           "Pole-dive and sky-dive conversion, separately.",
           "Wazir and power-play outs per batch.",
           "Split times of the 1st, 2nd and 3rd out in each batch.",
           "Reviews won."],
    "zones": [
        zone("chase", "A. FIELD ZONES — CHASERS", "Zone",
             ["Side A – post A end", "Side A – centre", "Side A – post B end", "Side B – post A end",
              "Side B – centre", "Side B – post B end", "Free zone – post A", "Free zone – post B"],
             ["Touch attempts", "Dive attempts", "Outs", "Errors"]),
        zone("defend", "B. FIELD ZONES — DEFENDERS", "Zone",
             ["Side A – post A end", "Side A – centre", "Side A – post B end", "Side B – post A end",
              "Side B – centre", "Side B – post B end", "Free zone – post A", "Free zone – post B"],
             ["Dodges", "Out here"]),
        zone("blocks", "C. SITTING BLOCKS", "Block",
             [f"Block {i}" for i in range(1, 7)] + ["Square 7 (traditional)", "Square 8 (traditional)"],
             ["Khos given", "Khos received", "Sitting fouls"]),
        zone("boundary", "D. BOUNDARY STRIP", "Side", ["Side A", "Side B", "Post A end", "Post B end"],
             ["Boundary outs"]),
        support(("Cover for a teammate", "Communication / call", "Emergency save"), letter="E"),
    ],
    "weights": {
        "Chaser": {"mixChase": 0.30, "touchSuccess": 0.25, "chaserOuts": 0.20, "diveShare": 0.10,
                   "khoQuality": 0.15},
        "Runner / Dodger": {"mixDefend": 0.30, "avgRun": 0.25, "defendTime": 0.15, "notOutPct": 0.15,
                            "dodgeEff": 0.15},
    },
}


def _clock(seconds):
    s = round(seconds)
    return f"{s // 60}:{s % 60:02d}"


# --------------------------------------------------------------------------- #
# The engine
# --------------------------------------------------------------------------- #

SPORTS = {"Football": FOOTBALL, "Basketball": BASKETBALL, "Volleyball": VOLLEYBALL, "Cricket": CRICKET,
          "Badminton": BADMINTON, "Tennis": TENNIS, "Kho-Kho": KHOKHO}

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


def _clock(seconds):
    s = round(seconds)
    return f"{s // 60}:{s % 60:02d}"


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
    got = {k: _value(VOLLEYBALL["measure"][k], t) for k in ("attackEff", "receptionPos", "serveAce",
                                                            "serveFault", "points")}
    assert got == {"attackEff": 20, "receptionPos": 40, "serveAce": 15, "serveFault": 10, "points": 14}, got
    assert show(20.0, "%") == "20%" and show(38.888, "%") == "38.9%" and show(3, "signed") == "+3"
    assert anchors(VOLLEYBALL["measure"]["attackEff"], "W", None) == (5, 30)
    assert target_text(CRICKET["measure"]["economy"], "W", "t20") == ("7.5 or less", "8.5 or less (IPL)")
    assert target_text(TENNIS["measure"]["firstWonPct"], "M", None) == ("62%", "72%")
    print("match cards: ok")
