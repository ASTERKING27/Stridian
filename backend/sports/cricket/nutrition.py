"""
Cricket: what a training day costs, in grams (or kcal) per kilogram of bodyweight.

nutrition.py turns this into the day's targets and menu for a student. The numbers follow
general sports-nutrition guidance for athletes in regular training — endurance sports
sit higher on carbohydrate, power sports higher on protein — tuned so carbohydrate lands
around 50-55% of energy, protein 13-16% and fat 25-33%. They are starting points for a
coach to adjust, not prescriptions.
"""

PROFILE = {
    "kcal_per_kg": 41,           # energy
    "carb_g_per_kg": 5.5,
    "protein_g_per_kg": 1.6,
    "style": "mixed",        # "endurance", "power" or "mixed"
}
