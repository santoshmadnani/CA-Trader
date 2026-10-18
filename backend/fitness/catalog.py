"""Exercise library, calorie estimates, nutrient definitions and unit conversion for the fitness app.

Calories burnt use MET values in the style of the Adult Compendium of Physical Activities (2024 update):
kcal = MET x body weight (kg) x hours. They are estimates; the app labels them as such.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

DATA = Path(__file__).resolve().parents[2] / "data" / "fitness"
IMG_BASE = "https://cdn.jsdelivr.net/gh/yuhonas/free-exercise-db@main/exercises/"

# ------------------------------------------------------------------ body parts
BODY_PARTS: dict[str, list[str]] = {
    "Chest": ["chest"], "Back": ["lats", "middle back", "lower back", "traps"], "Shoulders": ["shoulders"],
    "Biceps": ["biceps"], "Triceps": ["triceps"], "Forearms": ["forearms"], "Core": ["abdominals"],
    "Quads": ["quadriceps"], "Hamstrings": ["hamstrings"], "Glutes": ["glutes", "abductors", "adductors"], "Calves": ["calves"],
    "Neck": ["neck"], "Cardio": [],
}
EQUIPMENT = ["barbell", "dumbbell", "machine", "cable", "body only", "kettlebells", "bands", "e-z curl bar", "medicine ball",
             "exercise ball", "foam roll", "other"]
EQUIP_LABEL = {"body only": "Bodyweight", "kettlebells": "Kettlebell", "e-z curl bar": "EZ bar", "bands": "Bands", "other": "Other"}

# Names people use in Indian gyms -> library names (search aliases)
ALIASES = {
    "Butterfly": ["pec deck", "pec fly machine", "chest fly machine"],
    "Leverage Chest Press": ["chest press machine", "machine chest press"],
    "Wide-Grip Lat Pulldown": ["lat pulldown", "lat pull down"],
    "Seated Cable Rows": ["seated row", "cable row"],
    "Leg Extensions": ["leg extension machine"],
    "Lying Leg Curls": ["hamstring curl", "leg curl machine"],
    "Barbell Squat": ["back squat", "squat"],
    "Barbell Deadlift": ["deadlift"],
    "Barbell Bench Press - Medium Grip": ["bench press", "flat bench"],
    "Pullups": ["pull up", "pull-ups"],
    "Pushups": ["push up", "push-ups"],
    "Thigh Abductor": ["hip abduction machine", "abductor machine"],
    "Thigh Adductor": ["hip adduction machine", "adductor machine"],
    "Triceps Pushdown - Rope Attachment": ["rope pushdown", "tricep rope"],
    "Hack Squat": ["hack squat machine"],
}

# Cardio, gym cardio machines and sports that the library lacks, with MET values (Compendium-style estimates).
EXTRA: list[dict[str, Any]] = [
    {"id": "x-treadmill-walk", "name": "Treadmill walk (5 km/h)", "met": 4.3, "equipment": "machine"},
    {"id": "x-treadmill-incline", "name": "Treadmill incline walk", "met": 6.0, "equipment": "machine"},
    {"id": "x-treadmill-jog", "name": "Treadmill jog (8 km/h)", "met": 8.3, "equipment": "machine"},
    {"id": "x-treadmill-run", "name": "Treadmill run (10 km/h)", "met": 9.8, "equipment": "machine"},
    {"id": "x-run-outdoor", "name": "Running outdoors", "met": 9.8, "equipment": "body only"},
    {"id": "x-walk-outdoor", "name": "Walking (brisk)", "met": 4.3, "equipment": "body only"},
    {"id": "x-walk-casual", "name": "Walking (casual)", "met": 3.0, "equipment": "body only"},
    {"id": "x-cycle-stationary", "name": "Stationary bike (moderate)", "met": 6.8, "equipment": "machine"},
    {"id": "x-cycle-stationary-hard", "name": "Stationary bike (vigorous)", "met": 8.8, "equipment": "machine"},
    {"id": "x-spin", "name": "Spin class", "met": 8.5, "equipment": "machine"},
    {"id": "x-air-bike", "name": "Air / assault bike", "met": 9.0, "equipment": "machine"},
    {"id": "x-cycle-outdoor", "name": "Cycling outdoors", "met": 6.8, "equipment": "other"},
    {"id": "x-elliptical", "name": "Elliptical / cross trainer", "met": 5.0, "equipment": "machine"},
    {"id": "x-rower", "name": "Rowing machine (moderate)", "met": 7.0, "equipment": "machine"},
    {"id": "x-rower-hard", "name": "Rowing machine (vigorous)", "met": 8.5, "equipment": "machine"},
    {"id": "x-stair", "name": "Stair climber / stepmill", "met": 9.0, "equipment": "machine"},
    {"id": "x-jump-rope", "name": "Jump rope", "met": 11.0, "equipment": "other"},
    {"id": "x-swim", "name": "Swimming laps", "met": 7.0, "equipment": "other"},
    {"id": "x-hiit", "name": "HIIT / circuit training", "met": 8.0, "equipment": "body only"},
    {"id": "x-battle-ropes", "name": "Battle ropes", "met": 8.0, "equipment": "other"},
    {"id": "x-boxing-bag", "name": "Boxing (heavy bag)", "met": 5.5, "equipment": "other"},
    {"id": "x-yoga", "name": "Yoga", "met": 2.5, "equipment": "body only"},
    {"id": "x-power-yoga", "name": "Power yoga", "met": 4.0, "equipment": "body only"},
    {"id": "x-surya", "name": "Surya namaskar", "met": 3.8, "equipment": "body only"},
    {"id": "x-pilates", "name": "Pilates", "met": 3.0, "equipment": "body only"},
    {"id": "x-zumba", "name": "Zumba / aerobic dance", "met": 6.5, "equipment": "body only"},
    {"id": "x-badminton", "name": "Badminton", "met": 5.5, "equipment": "other"},
    {"id": "x-cricket", "name": "Cricket", "met": 4.8, "equipment": "other"},
    {"id": "x-football", "name": "Football", "met": 7.0, "equipment": "other"},
    {"id": "x-basketball", "name": "Basketball", "met": 6.5, "equipment": "other"},
    {"id": "x-tennis", "name": "Tennis", "met": 7.3, "equipment": "other"},
    {"id": "x-table-tennis", "name": "Table tennis", "met": 4.0, "equipment": "other"},
    {"id": "x-volleyball", "name": "Volleyball", "met": 4.0, "equipment": "other"},
    {"id": "x-kabaddi", "name": "Kabaddi", "met": 7.0, "equipment": "other"},
    {"id": "x-trek", "name": "Hiking / trekking", "met": 6.0, "equipment": "other"},
    {"id": "x-stretch", "name": "Stretching / mobility", "met": 2.3, "equipment": "body only"},
]


def met_for(ex: dict[str, Any]) -> float:
    if ex.get("met"):
        return float(ex["met"])
    cat, eq, mech, name = ex.get("category") or "", ex.get("equipment") or "", ex.get("mechanic") or "", (ex.get("name") or "").lower()
    if cat == "cardio":
        if re.search(r"run|sprint", name):
            return 9.8
        if re.search(r"jog", name):
            return 7.0
        if re.search(r"rope|jump", name):
            return 11.0
        if re.search(r"row", name):
            return 7.0
        if re.search(r"stair|step", name):
            return 9.0
        if re.search(r"bicycl|bike|cycl", name):
            return 6.8
        if re.search(r"elliptical", name):
            return 5.0
        if re.search(r"walk", name):
            return 4.3
        return 7.0
    if cat == "stretching":
        return 2.3
    if cat == "plyometrics":
        return 8.0
    if cat in ("olympic weightlifting", "powerlifting", "strongman"):
        return 6.0
    if mech == "compound" and eq in ("barbell", "dumbbell", "kettlebells", "e-z curl bar"):
        return 5.0
    if eq == "body only":
        return 3.8
    return 3.5


def is_cardio(ex: dict[str, Any]) -> bool:
    return ex.get("category") == "cardio" or str(ex.get("id", "")).startswith("x-")


def body_part(ex: dict[str, Any]) -> str:
    if is_cardio(ex):
        return "Cardio"
    for part, muscles in BODY_PARTS.items():
        if any(m in muscles for m in ex.get("primary") or []):
            return part
    return "Other"


@lru_cache(maxsize=1)
def exercises() -> list[dict[str, Any]]:
    try:
        lib = json.loads((DATA / "exercises.json").read_text(encoding="utf-8"))
    except Exception:
        lib = []
    out = []
    for e in lib:
        e = dict(e)
        e["met"] = met_for(e)
        e["part"] = body_part(e)
        e["aliases"] = ALIASES.get(e["name"], [])
        e["image"] = IMG_BASE + e["images"][0] if e.get("images") else None
        e["kind"] = "cardio" if is_cardio(e) else "time" if e.get("category") == "stretching" or e["name"] in ("Plank",) else "strength"
        out.append(e)
    for x in EXTRA:
        out.append({**x, "category": "cardio", "mechanic": None, "force": None, "level": "beginner", "primary": [], "secondary": [],
                    "instructions": [], "images": [], "image": None, "part": "Cardio", "aliases": [], "kind": "cardio"})
    return out


@lru_cache(maxsize=1)
def exercise_index() -> dict[str, dict[str, Any]]:
    return {e["id"]: e for e in exercises()}


def search_exercises(q: str = "", part: str = "", equipment: str = "", limit: int = 60) -> list[dict[str, Any]]:
    words = [w for w in re.split(r"\W+", (q or "").lower()) if w]
    res = []
    for e in exercises():
        if part and e["part"] != part:
            continue
        if equipment and e.get("equipment") != equipment:
            continue
        hay = " ".join([e["name"], *e.get("aliases", []), e.get("equipment") or "", *e.get("primary", [])]).lower()
        if words and not all(w in hay for w in words):
            continue
        score = 0 if not words else (0 if e["name"].lower().startswith(words[0]) else 1) + (0 if any(" ".join(words) in a for a in e.get("aliases", [])) else 1)
        res.append((score, e["level"] != "beginner", e["name"], e))
    res.sort(key=lambda r: r[:3])
    return [r[3] for r in res[:limit]]


def brief(e: dict[str, Any]) -> dict[str, Any]:
    return {k: e.get(k) for k in ("id", "name", "part", "equipment", "kind", "met", "image", "primary", "level")}


# ------------------------------------------------------------------ calories
def kcal(met: float, weight_kg: float, minutes: float) -> float:
    return round(float(met) * float(weight_kg) * (max(0.0, float(minutes)) / 60.0), 1)


def strength_minutes(sets: list[dict[str, Any]]) -> float:
    """Working time for logged strength sets when no session clock is available: ~3 s per rep plus ~90 s rest per set."""
    m = 0.0
    for s in sets:
        reps = float(s.get("reps") or 0)
        m += (reps * 3 + 90) / 60.0 if reps else 1.5
    return m


# ------------------------------------------------------------------ nutrients
NUTRIENTS: list[tuple[str, str, str, str]] = [   # key, label, unit, group
    ("kcal", "Energy", "kcal", "main"), ("protein_g", "Protein", "g", "main"), ("carb_g", "Carbs", "g", "main"), ("fat_g", "Fat", "g", "main"),
    ("fibre_g", "Fibre", "g", "main"), ("sugar_g", "Sugar", "g", "main"),
    ("sfa_g", "Saturated fat", "g", "fat"), ("mufa_g", "Monounsaturated fat", "g", "fat"), ("pufa_g", "Polyunsaturated fat", "g", "fat"),
    ("chol_mg", "Cholesterol", "mg", "fat"),
    ("sodium_mg", "Sodium", "mg", "min"), ("potassium_mg", "Potassium", "mg", "min"), ("calcium_mg", "Calcium", "mg", "min"),
    ("iron_mg", "Iron", "mg", "min"), ("magnesium_mg", "Magnesium", "mg", "min"), ("phosphorus_mg", "Phosphorus", "mg", "min"),
    ("zinc_mg", "Zinc", "mg", "min"), ("copper_mg", "Copper", "mg", "min"), ("manganese_mg", "Manganese", "mg", "min"),
    ("selenium_ug", "Selenium", "µg", "min"),
    ("vita_ug", "Vitamin A", "µg", "vit"), ("vitc_mg", "Vitamin C", "mg", "vit"), ("vitd_ug", "Vitamin D", "µg", "vit"),
    ("vite_mg", "Vitamin E", "mg", "vit"), ("vitk_ug", "Vitamin K", "µg", "vit"), ("b1_mg", "Thiamin (B1)", "mg", "vit"),
    ("b2_mg", "Riboflavin (B2)", "mg", "vit"), ("b3_mg", "Niacin (B3)", "mg", "vit"), ("b5_mg", "Pantothenic acid (B5)", "mg", "vit"),
    ("b6_mg", "Vitamin B6", "mg", "vit"), ("b7_ug", "Biotin (B7)", "µg", "vit"), ("b12_ug", "Vitamin B12", "µg", "vit"), ("folate_ug", "Folate", "µg", "vit"),
]
NUTRIENT_KEYS = [n[0] for n in NUTRIENTS]


def scale(per100: dict[str, Any], grams: float) -> dict[str, float]:
    f = float(grams) / 100.0
    return {k: round(float(v) * f, 3) for k, v in (per100 or {}).items() if v is not None}


def add_into(total: dict[str, float], part: dict[str, Any]) -> None:
    for k, v in (part or {}).items():
        try:
            total[k] = round(total.get(k, 0.0) + float(v), 3)
        except (TypeError, ValueError):
            pass


# ------------------------------------------------------------------ units
GENERIC_UNITS = [("tsp", "1 tsp", 5.0), ("tbsp", "1 tbsp", 15.0), ("katori", "1 katori", 150.0), ("cup", "1 cup", 240.0)]

# Typical weight of one piece of common countable foods (household estimates, marked approx in the UI).
_NOT_WHOLE = r"curry|bhurji|masala|biryani|pulao|rice|roll|sandwich|shake|juice|lassi|smoothie|milk|pickle|chutney|halwa|kheer|pudding|cake|salad|raita|soup|sabzi|subzi|jam"
PIECES: list[tuple[str, str, float]] = [
    (r"\beggs?\b", "egg", 50), (r"\bbananas?\b", "banana", 118), (r"\bapples?\b", "apple", 180), (r"\boranges?\b", "orange", 130),
    (r"\bmangoe?s?\b", "mango", 200), (r"\bguavas?\b", "guava", 100), (r"\bidli", "idli", 40), (r"\bdosa", "dosa", 90),
    (r"\buttapam", "uttapam", 120), (r"\bvada\b|\bwada\b", "vada", 45), (r"\bparatha|\bparantha", "paratha", 90),
    (r"\bp(oo|u)ris?\b", "puri", 25), (r"\bnaan\b", "naan", 90), (r"\bbhatura", "bhatura", 80), (r"\bkulcha", "kulcha", 80),
    (r"\bthepla", "thepla", 40), (r"\bsamosa", "samosa", 60), (r"\bkachori", "kachori", 50), (r"\bpa?koda|\bpakora", "pakora", 20),
    (r"\bdhokla", "dhokla", 30), (r"\bla?d(d|o)o", "ladoo", 40), (r"\bgulab jamun", "gulab jamun", 40), (r"\brasgull?a", "rasgulla", 40),
    (r"\bjalebi", "jalebi", 30), (r"\bbarfi|\bburfi", "barfi", 30), (r"\bmodak", "modak", 40), (r"\bmomos?\b", "momo", 25),
    (r"\bbiscuits?\b|\bcookies?\b", "biscuit", 10), (r"\bbread\b|\btoast\b", "slice", 28), (r"\balmonds?\b", "almond", 1.2),
    (r"\bcashews?\b", "cashew", 1.5), (r"\bwalnuts?\b", "walnut", 4), (r"\bdates?\b", "date", 8), (r"\bcutlet|\btikki", "cutlet", 60),
    (r"\bkebab|\bkabab", "kebab", 40), (r"\bchapati|\broti\b|\bphulka", "roti", 36),
]


def units_for(food: dict[str, Any]) -> list[dict[str, Any]]:
    """Units a food can be logged in, each with its gram weight. The food's own serving and portions come first."""
    out: list[dict[str, Any]] = []
    if food.get("serving_g"):
        lbl = food.get("serving_label") or "serving"
        out.append({"u": "serving", "label": f"1 {lbl}", "g": round(float(food["serving_g"]), 1)})
    for p in food.get("portions") or []:
        if p.get("g"):
            out.append({"u": f"p:{p['label']}", "label": p["label"], "g": round(float(p["g"]), 1)})
    name = food.get("name", "") or ""
    # INDB dishes are weighed with their cooking water, so a gram-based piece weight would be wrong; their serving is one portion.
    if food.get("source") != "indb" and not any(x["u"] == "piece" for x in out) and not re.search(_NOT_WHOLE, name, re.I):
        for pat, lbl, g in PIECES:
            if re.search(pat, name, re.I):
                out.append({"u": "piece", "label": f"1 {lbl}", "g": float(g), "approx": True})
                break
    if re.search(r"whey|protein powder|mass gainer|casein", name, re.I):
        out.append({"u": "scoop", "label": "1 scoop", "g": 30.0, "approx": True})
    out.append({"u": "g", "label": "grams", "g": 1.0})
    liquid = bool(re.search(r"milk|juice|tea|coffee|shake|lassi|chaas|buttermilk|water|soup|smoothie|drink|beverage", name, re.I))
    if liquid:
        out.append({"u": "ml", "label": "ml", "g": 1.0})
        out.append({"u": "glass", "label": "1 glass", "g": 250.0, "approx": True})
    for u, lbl, g in GENERIC_UNITS:
        if not any(x["u"] == u for x in out):
            out.append({"u": u, "label": lbl, "g": g, "approx": True})
    return out


def grams_for(food: dict[str, Any], qty: float, unit: str) -> float:
    unit = (unit or "g").strip()
    for u in units_for(food):
        if u["u"] == unit or u["label"].lower() == unit.lower():
            return round(float(qty) * u["g"], 2)
    aliases = {"gram": "g", "grams": "g", "gm": "g", "teaspoon": "tsp", "tablespoon": "tbsp", "bowl": "katori", "piece": "serving",
               "pc": "piece", "pcs": "piece", "pieces": "piece", "nos": "piece", "plate": "serving", "glass": "serving", "roti": "serving", "chapati": "serving"}
    alt = aliases.get(unit.lower())
    if alt:
        return grams_for(food, qty, alt)
    if food.get("serving_g"):
        return round(float(qty) * float(food["serving_g"]), 2)
    return round(float(qty) * 100.0, 2)


# ------------------------------------------------------------------ targets
ACTIVITY = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725, "very_active": 1.9}
GOALS = {"cut": -0.18, "lean_cut": -0.10, "maintain": 0.0, "lean_bulk": 0.08, "bulk": 0.15}


def targets(p: dict[str, Any]) -> dict[str, Any]:
    """Mifflin-St Jeor BMR x activity, adjusted for the goal. Protein 2.0 g/kg when gaining or cutting, 1.6 to maintain;
    fat 25% of energy; carbs fill the rest."""
    try:
        w, h, age = float(p["weight_kg"]), float(p["height_cm"]), float(p["age"])
    except (KeyError, TypeError, ValueError):
        return {}
    male = (p.get("sex") or "male") == "male"
    bmr = 10 * w + 6.25 * h - 5 * age + (5 if male else -161)
    tdee = bmr * ACTIVITY.get(p.get("activity") or "moderate", 1.55)
    goal = p.get("goal") or "maintain"
    kcal_t = tdee * (1 + GOALS.get(goal, 0.0))
    prot = w * (1.6 if goal == "maintain" else 2.0)
    fat = kcal_t * 0.25 / 9
    carb = max(0.0, (kcal_t - prot * 4 - fat * 9) / 4)
    return {"bmr": round(bmr), "tdee": round(tdee), "kcal": round(kcal_t), "protein_g": round(prot), "fat_g": round(fat), "carb_g": round(carb),
            "fibre_g": 30 if male else 25, "water_ml": round(w * 35 / 250) * 250}
