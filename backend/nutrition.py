"""
Diet planner.

Energy is derived per kilogram of bodyweight using the sport's demand profile
(endurance sports carry more carbohydrate, power sports more protein), then split
across the training day. Meal suggestions are filtered by the student's diet
preference and declared allergies.

This produces general sports-nutrition guidance for a coach to work from. It is not
medical or individualised dietetic advice, and the API says so in every response.
"""

from sports_config import NUTRITION, get_sport

DISCLAIMER = (
    "General sports-nutrition guidance for training support only — not medical or "
    "individual dietetic advice. Check with a qualified sports dietitian before making "
    "big changes, and always work with a doctor where a medical condition is involved."
)

# Diet preference as a ladder: each level can eat everything at or below it.
DIET_LEVELS = {"vegan": 0, "veg": 1, "egg": 2, "nonveg": 3}
DIET_LABELS = {
    "vegan": "Vegan", "veg": "Vegetarian",
    "egg": "Eggetarian", "nonveg": "Non-vegetarian",
}

ALLERGENS = ["milk", "egg", "peanut", "treenut", "gluten", "soy", "fish", "shellfish"]

# slot keys must match MEAL_SPLIT below
FOODS = [
    # ---------------------------------------------------------------- breakfast
    ("breakfast", "Poha with peanuts and vegetables", 0, {"peanut"}, "carb-led"),
    ("breakfast", "Upma with vegetables", 0, {"gluten"}, "carb-led"),
    ("breakfast", "Idli with sambar", 0, set(), "carb-led"),
    ("breakfast", "Oats porridge with banana and jaggery", 0, {"gluten"}, "carb-led"),
    ("breakfast", "Besan chilla with mint chutney", 0, set(), "protein + carb"),
    ("breakfast", "Paneer paratha with curd", 1, {"milk", "gluten"}, "protein + carb"),
    ("breakfast", "Milk with muesli and dates", 1, {"milk", "gluten", "treenut"}, "carb-led"),
    ("breakfast", "3-egg bhurji with 2 rotis", 2, {"egg", "gluten"}, "protein + carb"),
    ("breakfast", "Boiled eggs with brown bread and fruit", 2, {"egg", "gluten"}, "protein + carb"),

    # ------------------------------------------------------------- mid-morning
    ("snack_am", "Banana with a handful of roasted chana", 0, set(), "quick carbs"),
    ("snack_am", "Seasonal fruit bowl", 0, set(), "quick carbs"),
    ("snack_am", "Peanut chikki and water", 0, {"peanut"}, "quick carbs"),
    ("snack_am", "Sprouts chaat", 0, set(), "protein + carb"),
    ("snack_am", "Curd with honey", 1, {"milk"}, "protein"),

    # -------------------------------------------------------------------- lunch
    ("lunch", "Rice, dal, mixed sabzi and salad", 0, set(), "balanced"),
    ("lunch", "Rajma-chawal with cucumber salad", 0, set(), "balanced"),
    ("lunch", "Chole with 3 rotis and salad", 0, {"gluten"}, "balanced"),
    ("lunch", "Soya chunk curry with rice", 0, {"soy"}, "protein-led"),
    ("lunch", "Paneer sabzi, 3 rotis, dal and curd", 1, {"milk", "gluten"}, "protein-led"),
    ("lunch", "Grilled fish, rice and vegetables", 3, {"fish"}, "protein-led"),
    ("lunch", "Chicken curry with rice and salad", 3, set(), "protein-led"),

    # ------------------------------------------------------------- pre-training
    ("pre", "Banana and dates, 60–90 min before", 0, set(), "quick carbs"),
    ("pre", "Toast with jam and black coffee", 0, {"gluten"}, "quick carbs"),
    ("pre", "Poha or upma, small portion", 0, {"gluten"}, "quick carbs"),
    ("pre", "Fruit smoothie with curd", 1, {"milk"}, "quick carbs + protein"),

    # ------------------------------------------------------------ post-training
    ("post", "Chana and jaggery with lemon water", 0, set(), "recovery"),
    ("post", "Soy milk with banana", 0, {"soy"}, "recovery"),
    ("post", "Peanut butter on toast", 0, {"peanut", "gluten"}, "recovery"),
    ("post", "Milk with banana and honey", 1, {"milk"}, "recovery"),
    ("post", "Whey or curd with fruit", 1, {"milk"}, "recovery"),
    ("post", "2 boiled eggs with fruit", 2, {"egg"}, "recovery"),

    # ------------------------------------------------------------------- dinner
    ("dinner", "Khichdi with vegetables and curd", 0, set(), "balanced"),
    ("dinner", "Dal, 2 rotis and a vegetable", 0, {"gluten"}, "balanced"),
    ("dinner", "Vegetable pulao with raita", 0, set(), "balanced"),
    ("dinner", "Tofu stir-fry with rice", 0, {"soy"}, "protein-led"),
    ("dinner", "Paneer bhurji with 2 rotis", 1, {"milk", "gluten"}, "protein-led"),
    ("dinner", "Egg curry with rice", 2, {"egg"}, "protein-led"),
    ("dinner", "Grilled chicken with vegetables and rice", 3, set(), "protein-led"),
]

# share of the day's energy, and what the slot is for
MEAL_SPLIT = [
    ("breakfast", "Breakfast", 0.25),
    ("snack_am", "Mid-morning", 0.10),
    ("lunch", "Lunch", 0.28),
    ("pre", "Pre-training", 0.10),
    ("post", "Post-training", 0.12),
    ("dinner", "Dinner", 0.15),
]


def _allowed(food, level, allergies):
    _slot, _name, food_level, food_allergens, _tag = food
    return food_level <= level and not (food_allergens & allergies)


def plan(student, sport_name, recommended_position=None):
    """Build the day's targets and menu. Returns {} when weight is unknown."""
    weight = student.get("weight_kg")
    if not weight:
        return {
            "available": False,
            "reason": "Add the student's weight to generate a plan.",
            "disclaimer": DISCLAIMER,
        }

    profile = NUTRITION.get(sport_name) or NUTRITION["Cricket"]
    age = student.get("age")
    hours = student.get("training_hours_per_day") or 1.5

    # base energy, nudged for training volume and for still-growing athletes
    kcal = weight * profile["kcal_per_kg"]
    kcal *= 1 + 0.06 * (hours - 1.5)          # ±6% per hour either side of 1.5
    if age is not None and age < 18:
        kcal *= 1.05
    kcal = round(kcal / 25) * 25

    carbs_g = round(weight * profile["carb_g_per_kg"])
    protein_g = round(weight * profile["protein_g_per_kg"])

    # Fat takes what's left, but is held inside 22-30% of energy; carbohydrate absorbs
    # the difference so the three macros always add back up to the calorie target.
    fat_kcal = min(max(kcal - (carbs_g + protein_g) * 4, kcal * 0.22), kcal * 0.30)
    carbs_g = round((kcal - fat_kcal - protein_g * 4) / 4)
    fat_g = round(fat_kcal / 9)

    level = DIET_LEVELS.get(student.get("diet_preference") or "nonveg", 3)
    allergies = {a.strip().lower() for a in (student.get("allergies") or "").split(",") if a.strip()}

    meals = []
    for slot, label, share in MEAL_SPLIT:
        options = [f for f in FOODS if f[0] == slot and _allowed(f, level, allergies)]
        meals.append({
            "slot": slot,
            "label": label,
            "kcal": round(kcal * share / 10) * 10,
            "share": share,
            "options": [{"name": f[1], "tag": f[4]} for f in options[:4]],
        })

    hydration_ml = round((35 * weight + 600 * hours) / 50) * 50

    notes = [
        f"Carbohydrate is the priority fuel for {sport_name.lower()} — keep it high on "
        f"match days and heavy sessions, and eat the pre-training meal 60–90 minutes before.",
        f"Spread protein across the day in 4–5 portions of roughly {round(protein_g / 4.5)} g "
        f"rather than one large serving.",
        f"Drink around {hydration_ml} ml across the day, plus 500–750 ml for every extra "
        f"hour of hard training or hot weather.",
        "Eat within 45 minutes of finishing a session — carbohydrate plus protein together "
        "recovers better than either alone.",
    ]
    if recommended_position:
        notes.append(
            f"Targets here assume the workload of a {recommended_position.lower()}. "
            "Adjust with the coach if the actual training load is much higher or lower."
        )
    if allergies:
        notes.append("Menu already excludes: " + ", ".join(sorted(allergies)) + ".")

    return {
        "available": True,
        "dietPreference": DIET_LABELS.get(student.get("diet_preference") or "nonveg", "Non-vegetarian"),
        "allergies": sorted(allergies),
        "style": profile["style"],
        "targets": {
            "kcal": int(kcal),
            "carbs_g": carbs_g,
            "protein_g": protein_g,
            "fat_g": fat_g,
            "carbs_kcal": carbs_g * 4,
            "protein_kcal": protein_g * 4,
            "fat_kcal": fat_g * 9,
            "hydration_ml": hydration_ml,
            "per_kg": {
                "kcal": profile["kcal_per_kg"],
                "carbs": profile["carb_g_per_kg"],
                "protein": profile["protein_g_per_kg"],
            },
        },
        "meals": meals,
        "notes": notes,
        "disclaimer": DISCLAIMER,
    }


def sport_positions_note(sport_name):
    sport = get_sport(sport_name)
    return sport["note"] if sport else ""
