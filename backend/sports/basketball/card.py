"""
Basketball — FIBA Statisticians' Manual; University = NCAA D-I median, Elite = NBA.

Basketball's match card: what the scorer tallies in Part A, what counts as + / 0 / − and the
formulas with their targets in Part B, the coach's review (Part C), a player's tournament
(Part D) and the player card by zone. match_cards.py lays it out, works the numbers and
checks what is typed in; this file is only what the card holds.
"""

from sports.kit import skill, field, team_field, measure, zone, support, pct, div, mix


def _fga(t):
    return t.p("two", "three") + t.m("two", "three")      # a fouled miss (0) is not an attempt


def _bb_points(t):
    return 2 * t.p("two") + 3 * t.p("three") + t.p("ft")


def _turnovers(t):
    return t.m("passing", "handling")


BB_PLAY = ["two", "three", "passing", "handling", "rebound", "defence"]

CARD = {
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
