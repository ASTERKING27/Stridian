"""
Every sport Stridian covers, one folder each:

  football/  basketball/  volleyball/  cricket/  badminton/  tennis/  khokho/

Each folder holds the whole sport — its tests and positions (tests.py), its video analyser
(analyser.py), its nutrition (nutrition.py), its match card (card.py) and its level
targets (levels.json). The shared engines read them from here: sports_config.py builds
the batteries, match_cards.py lays out the cards, levels.py reads the ladders,
nutrition.py plans the day, pose_sports.py runs the analysers. Adding a sport is a new
folder plus a line below.

kit.py and pose.py are what the sports' scripts are written with; they know no sport.
"""

from . import badminton, basketball, cricket, football, khokho, tennis, volleyball

# in the order the app lists them
ALL = (football, basketball, volleyball, cricket, badminton, tennis, khokho)
BY_NAME = {sport.NAME: sport for sport in ALL}
