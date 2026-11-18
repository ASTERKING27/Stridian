"""
Sport-specific technique from the MediaPipe drill lane: which sport's analyser to run.

video.py measures what matters in every sport — symmetry, trunk stability, joint ranges.
What only matters in one is that sport's own analyser, backend/sports/<sport>/analyser.py:
how a footballer plants and strikes, how a spiker reaches at contact, how a shooter's elbow
sits at release, whether a bowler's arm straightens more than the Law allows, a badminton
player's overhead and lunge, a tennis serve's reach and leg drive, a kho-kho chase's turns
and dive. Each one's technique() finds the moment that matters in the clip, measures it,
and turns anything outside the expected band into a drill.

The geometry they share, and the limits of measuring from one camera in 2D, are in
sports/pose.py.
"""

from sports import ALL
from sports.pose import CAMERA_NOTE

ANALYSERS = {sport.NAME: sport.analyser.technique for sport in ALL}
LABELS = {sport.NAME: sport.analyser.LABELS for sport in ALL}      # (name on screen, unit)


def analyse(sport, points, fps, height_cm=None):
    """{metrics, labels, drills, note} for the sport, or empty when there's no analyser."""
    analyser = ANALYSERS.get(sport)
    if analyser is None:
        return {}
    try:
        metrics, drills = analyser(points, fps, height_cm)
    except Exception:
        return {}
    if not metrics:
        return {}
    labels = LABELS[sport]
    return {
        "sport": sport,
        "metrics": metrics,
        "labels": {k: labels.get(k, (k, ""))[0] for k in metrics},
        "units": {k: labels.get(k, (k, ""))[1] for k in metrics},
        "drills": drills,
        "note": CAMERA_NOTE,
    }
