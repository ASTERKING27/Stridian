"""
Cricket — ball by ball; T20 by default, 50-over chosen per match.

Cricket's match card: what the scorer tallies in Part A, what counts as + / 0 / − and the
formulas with their targets in Part B, the coach's review (Part C), a player's tournament
(Part D) and the player card by zone. match_cards.py lays it out, works the numbers and
checks what is typed in; this file is only what the card holds.
"""

from sports.kit import skill, field, team_field, measure, zone, support, pct, div, mix, efficiency


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

CARD = {
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
