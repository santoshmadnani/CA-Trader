"""Build the fitness app's bundled data files from their public sources (run locally, commit the output).

  python scripts/build_fitness_data.py <free-exercise-db dir> <Indian-Nutrient-Databank-INDB- dir>

Sources
- Exercises: github.com/yuhonas/free-exercise-db (dist/exercises.json), released under the Unlicense (public domain).
  Images are served from jsDelivr's GitHub CDN at runtime, not copied.
- Foods: github.com/lindsayjaacks/Indian-Nutrient-Databank-INDB- (INDB.xlsx: 1,014 Indian recipes, per 100 g and per
  serving; UK_fct.xlsx / US_fct.xlsx: raw ingredients used by those recipes), described in Current
  Developments in Nutrition (2024, CC BY). Nutrients are stored per 100 g in one common schema.

Outputs: data/fitness/exercises.json, data/fitness/foods_indb.json
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "fitness"

# common nutrient schema (per 100 g) -> INDB column(s) and divisor
INDB_MAP = {
    "kcal": ("energy_kcal",), "protein_g": ("protein_g",), "carb_g": ("carb_g",), "fat_g": ("fat_g",), "fibre_g": ("fibre_g",),
    "sugar_g": ("freesugar_g",), "sfa_g": ("sfa_mg", 1000), "mufa_g": ("mufa_mg", 1000), "pufa_g": ("pufa_mg", 1000),
    "chol_mg": ("cholesterol_mg",), "sodium_mg": ("sodium_mg",), "potassium_mg": ("potassium_mg",), "calcium_mg": ("calcium_mg",),
    "iron_mg": ("iron_mg",), "magnesium_mg": ("magnesium_mg",), "phosphorus_mg": ("phosphorus_mg",), "zinc_mg": ("zinc_mg",),
    "copper_mg": ("copper_mg",), "selenium_ug": ("selenium_ug",), "manganese_mg": ("manganese_mg",), "vita_ug": ("vita_ug",),
    "vitc_mg": ("vitc_mg",), "vitd_ug": ("vitd2_ug", "vitd3_ug"), "vite_mg": ("vite_mg",), "vitk_ug": ("vitk1_ug", "vitk2_ug"),
    "b1_mg": ("vitb1_mg",), "b2_mg": ("vitb2_mg",), "b3_mg": ("vitb3_mg",), "b5_mg": ("vitb5_mg",), "b6_mg": ("vitb6_mg",),
    "b7_ug": ("vitb7_ug",), "folate_ug": ("folate_ug",),
}

# Indian serving units in INDB -> grams (approximate household measures; INDB gives per-serving nutrients directly,
# so this is only used to express "1 serving" in grams for unit conversion)
UNIT_GRAMS = {"tea cup": 150, "cup": 200, "katori": 150, "bowl": 200, "glass": 250, "plate": 250, "piece": 50, "no.": 50, "number": 50,
              "slice": 30, "tablespoon": 15, "tbsp": 15, "teaspoon": 5, "tsp": 5, "serving": 150, "ladle": 100, "small bowl": 120}


def _num(v):
    try:
        f = float(v)
        return f if f == f else None
    except (TypeError, ValueError):
        return None


def _nutrients(row: dict, prefix: str = "") -> dict:
    out = {}
    for key, spec in INDB_MAP.items():
        cols, div = (spec[:-1], spec[-1]) if isinstance(spec[-1], (int, float)) else (spec, 1)
        vals = [_num(row.get(prefix + c)) for c in cols]
        vals = [v for v in vals if v is not None]
        if vals:
            out[key] = round(sum(vals) / div, 4)
    return out


def _sheet(path: Path) -> list[dict]:
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    rows = list(ws.iter_rows(values_only=True))
    head = [str(h).strip() if h is not None else f"col{i}" for i, h in enumerate(rows[0])]
    return [dict(zip(head, r)) for r in rows[1:] if any(c is not None for c in r)]


def build_foods(indb_dir: Path) -> list[dict]:
    foods = []
    for r in _sheet(indb_dir / "INDB.xlsx"):
        code, name = str(r.get("food_code") or "").strip(), str(r.get("food_name") or "").strip()
        if not code or not name:
            continue
        per100, per_serv = _nutrients(r), _nutrients(r, "unit_serving_")
        unit = str(r.get("servings_unit") or "").strip().lower() or "serving"
        # grams in one serving, from the ratio of per-serving to per-100 g energy (exact, since both come from the recipe)
        serving_g = None
        if per100.get("kcal") and per_serv.get("kcal"):
            serving_g = round(per_serv["kcal"] / per100["kcal"] * 100, 1)
        elif unit in UNIT_GRAMS:
            serving_g = UNIT_GRAMS[unit]
        foods.append({"id": f"indb:{code}", "source": "indb", "kind": "dish", "name": name, "per100": per100,
                      "serving_g": serving_g, "serving_label": unit})
    for fname, src in (("UK_fct.xlsx", "uk"), ("US_fct.xlsx", "us")):
        p = indb_dir / fname
        if not p.exists():
            continue
        for r in _sheet(p):
            code, name = str(r.get("food_code") or "").strip(), str(r.get("food_name") or "").strip()
            if not code or not name:
                continue
            per100 = _nutrients(r)
            if not per100.get("kcal") and not per100.get("protein_g"):
                continue
            foods.append({"id": f"ing:{code}", "source": f"indb-{src}", "kind": "ingredient", "name": re.sub(r"\s+", " ", name),
                          "per100": per100, "serving_g": None, "serving_label": None})
    return foods


def build_exercises(fedb_dir: Path) -> list[dict]:
    raw = json.loads((fedb_dir / "dist" / "exercises.json").read_text(encoding="utf-8"))
    out = []
    for e in raw:
        out.append({"id": e["id"], "name": e["name"], "category": e.get("category"), "equipment": e.get("equipment") or "other",
                    "mechanic": e.get("mechanic"), "force": e.get("force"), "level": e.get("level"),
                    "primary": e.get("primaryMuscles") or [], "secondary": e.get("secondaryMuscles") or [],
                    "instructions": e.get("instructions") or [], "images": (e.get("images") or [])[:2]})
    return out


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    fedb, indb = Path(sys.argv[1]), Path(sys.argv[2])
    OUT.mkdir(parents=True, exist_ok=True)
    ex, foods = build_exercises(fedb), build_foods(indb)
    (OUT / "exercises.json").write_text(json.dumps(ex, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    (OUT / "foods_indb.json").write_text(json.dumps(foods, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"exercises: {len(ex)}  foods: {len(foods)} ({sum(1 for f in foods if f['kind'] == 'dish')} dishes)")


if __name__ == "__main__":
    main()
