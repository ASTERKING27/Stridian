"""
Volleyball — everything Stridian knows about the sport, one script for each part:

  tests.py      the test battery, the positions with their starting weights, training tips
  analyser.py   the video analyser: technique from a drill clip, and how match footage is read
  nutrition.py  what a training day costs, per kilogram of bodyweight
  card.py       the match card: skills, formulas, targets, Parts C and D, the player card
  levels.json   what a player posts at University, Zonal, State, National and International
                level, men and women, with where each number comes from
"""

import json
from pathlib import Path

from . import analyser, card, nutrition, tests  # noqa: F401 — the parts, for whoever reads the sport

NAME = "Volleyball"
LEVELS = json.loads((Path(__file__).parent / "levels.json").read_text(encoding="utf-8"))
