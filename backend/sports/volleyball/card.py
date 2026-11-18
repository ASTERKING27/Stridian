"""
Volleyball — the Directorate of Sports hardcopy, word for word.

Volleyball's match card: what the scorer tallies in Part A, what counts as + / 0 / − and the
formulas with their targets in Part B, the coach's review (Part C), a player's tournament
(Part D) and the player card by zone. match_cards.py lays it out, works the numbers and
checks what is typed in; this file is only what the card holds.
"""

from sports.kit import skill, field, team_field, measure, zone, support, pct, div, mix, efficiency


VB_SKILLS = ["serve", "attack", "reception", "set", "dig", "block"]

CARD = {
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
