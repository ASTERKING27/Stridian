"""
Kho-kho — the mat format by default; traditional chosen per match.

Kho-Kho's match card: what the scorer tallies in Part A, what counts as + / 0 / − and the
formulas with their targets in Part B, the coach's review (Part C), a player's tournament
(Part D) and the player card by zone. match_cards.py lays it out, works the numbers and
checks what is typed in; this file is only what the card holds.
"""

from sports.kit import skill, field, team_field, measure, zone, support, pct, div, mix, efficiency, clock


TURN_MINUTES = {"mat": 7, "traditional": 9}
POINTS_PER_OUT = {"mat": 2, "traditional": 1}
KK_CHASE = ["touch", "pole", "sky", "kho", "turn", "sitting"]
KK_DIVES = ["touch", "pole", "sky"]


def _outs(t):
    return t.p(*KK_DIVES)


CARD = {
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
                f"{clock(t.team('batchSeconds') / t.team('batches'))} average, "
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
