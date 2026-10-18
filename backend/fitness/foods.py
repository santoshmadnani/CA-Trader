"""Food database for the fitness app.

Sources, all stored per 100 g in one nutrient schema (see catalog.NUTRIENTS):
- indb:  Indian Nutrient Databank (1,014 Indian recipes + raw ingredients), bundled in data/fitness/foods_indb.json.
- usda:  USDA FoodData Central: SR Legacy (~7,800 everyday foods) and FNDDS (~5,400 prepared dishes and meals: wraps,
         sandwiches, curries, naan...), both with household portions. The server downloads the official CSV releases once
         in the background; until then, and if that fails, foods are looked up on the FDC API (USDA_API_KEY, else the
         rate-limited DEMO_KEY) and cached.
- web:   a dish none of the above has (e.g. "paneer frankie"), looked up on request by Gemini with Google Search grounding.
         Saved only when the answer cites web sources and its calories agree with its own macros; the sources are stored
         with the food and shown to the user, and the food then appears in everyone's search.
- off:   Open Food Facts for packaged foods and barcodes, looked up on demand and cached.
- user:  foods a user creates.
Values are never invented: a food without data from one of these sources is not offered.
"""
from __future__ import annotations

import csv
import io
import json
import logging
import os
import re
import threading
import time
import zipfile
from pathlib import Path
from typing import Any, Callable

import requests

from backend.fitness import catalog as C

log = logging.getLogger("ca-trader.fitness.foods")
DATA = Path(__file__).resolve().parents[2] / "data" / "fitness"
_FDC = "https://fdc.nal.usda.gov/fdc-datasets/"
# Each dataset: tried in order until one URL downloads. FNDDS prefers the small 2019-2020 release (the 2021-2023 one is 200 MB).
USDA_DATASETS = {
    "sr": {"types": ("sr_legacy_food",), "urls": [_FDC + "FoodData_Central_sr_legacy_food_csv_2018-04.zip"]},
    "fndds": {"types": ("survey_fndds_food",), "urls": [_FDC + "FoodData_Central_survey_food_csv_2022-10-28.zip",
                                                        _FDC + "FoodData_Central_survey_food_csv_2021-10-28.zip",
                                                        _FDC + "FoodData_Central_survey_food_csv_2024-10-31.zip"]},
}
SR_URLS = USDA_DATASETS["sr"]["urls"]
UA = {"User-Agent": "CATrader-Fitness/1.0 (https://catrader.site)"}

# USDA legacy nutrient numbers -> our keys
SR_NBR = {"208": "kcal", "203": "protein_g", "204": "fat_g", "205": "carb_g", "291": "fibre_g", "269": "sugar_g", "606": "sfa_g",
          "645": "mufa_g", "646": "pufa_g", "601": "chol_mg", "307": "sodium_mg", "306": "potassium_mg", "301": "calcium_mg",
          "303": "iron_mg", "304": "magnesium_mg", "305": "phosphorus_mg", "309": "zinc_mg", "312": "copper_mg", "315": "manganese_mg",
          "317": "selenium_ug", "320": "vita_ug", "401": "vitc_mg", "328": "vitd_ug", "323": "vite_mg", "430": "vitk_ug", "404": "b1_mg",
          "405": "b2_mg", "406": "b3_mg", "410": "b5_mg", "415": "b6_mg", "418": "b12_ug", "417": "folate_ug"}

_FTS = {"ok": None}
_IMPORT = {"state": "idle", "detail": "", "at": 0.0}


def ensure_tables(db: Callable) -> None:
    db("""CREATE TABLE IF NOT EXISTS fit_foods (id TEXT PRIMARY KEY, user_id INTEGER, source TEXT, kind TEXT, name TEXT NOT NULL,
          brand TEXT, per100 TEXT NOT NULL, serving_g REAL, serving_label TEXT, portions TEXT, barcode TEXT, search TEXT, created_at TEXT)""")
    db("CREATE INDEX IF NOT EXISTS idx_fit_foods_src ON fit_foods(source)")
    db("CREATE INDEX IF NOT EXISTS idx_fit_foods_user ON fit_foods(user_id)")
    db("CREATE INDEX IF NOT EXISTS idx_fit_foods_barcode ON fit_foods(barcode)")
    db("CREATE TABLE IF NOT EXISTS fit_meta (key TEXT PRIMARY KEY, value TEXT)")
    try:
        db("ALTER TABLE fit_foods ADD COLUMN meta TEXT")      # {"sources": [{title,url}], "note": ..., "query": ...} for web foods
    except Exception:
        pass
    try:
        db("CREATE VIRTUAL TABLE IF NOT EXISTS fit_foods_fts USING fts5(name, search, tokenize='unicode61 remove_diacritics 2')")
        _FTS["ok"] = True
    except Exception as exc:
        log.info("FTS5 unavailable, using LIKE search: %s", exc)
        _FTS["ok"] = False


def _search_text(name: str, extra: str = "") -> str:
    return re.sub(r"[^a-z0-9 ]+", " ", f"{name} {extra}".lower())


def _rowid(db: Callable, fid: str) -> int | None:
    r = db("SELECT rowid AS r FROM fit_foods WHERE id=?", [fid], "one")
    return int(r["r"]) if r else None


def upsert(db: Callable, f: dict[str, Any]) -> None:
    search = _search_text(f["name"], " ".join(filter(None, [f.get("brand"), f.get("alt")])))
    db("""INSERT INTO fit_foods(id,user_id,source,kind,name,brand,per100,serving_g,serving_label,portions,barcode,search,meta,created_at)
          VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'))
          ON CONFLICT(id) DO UPDATE SET name=excluded.name, brand=excluded.brand, per100=excluded.per100, serving_g=excluded.serving_g,
          serving_label=excluded.serving_label, portions=excluded.portions, barcode=excluded.barcode, search=excluded.search, meta=excluded.meta""",
       [f["id"], f.get("user_id"), f["source"], f.get("kind", "food"), f["name"], f.get("brand"), json.dumps(f["per100"]), f.get("serving_g"),
        f.get("serving_label"), json.dumps(f.get("portions") or []), f.get("barcode"), search, json.dumps(f["meta"]) if f.get("meta") else None])
    if _FTS["ok"]:
        rid = _rowid(db, f["id"])
        db("DELETE FROM fit_foods_fts WHERE rowid=?", [rid])
        db("INSERT INTO fit_foods_fts(rowid, name, search) VALUES(?,?,?)", [rid, f["name"], search])


def load_bundled(db: Callable) -> int:
    """Load INDB foods once (or again when the bundled file changes)."""
    p = DATA / "foods_indb.json"
    try:
        stamp = str(int(p.stat().st_mtime)) + ":" + str(p.stat().st_size)
    except OSError:
        return 0
    row = db("SELECT value FROM fit_meta WHERE key='indb_stamp'", [], "one")
    if row and row.get("value") == stamp:
        return 0
    foods = json.loads(p.read_text(encoding="utf-8"))
    for f in foods:
        upsert(db, {**f, "user_id": None})
    db("INSERT INTO fit_meta(key,value) VALUES('indb_stamp',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", [stamp])
    return len(foods)


def _row_to_food(r: dict[str, Any]) -> dict[str, Any]:
    f = {k: r.get(k) for k in ("id", "source", "kind", "name", "brand", "serving_g", "serving_label", "barcode", "user_id")}
    f["per100"] = json.loads(r.get("per100") or "{}")
    f["portions"] = json.loads(r.get("portions") or "[]")
    sg, kc = f.get("serving_g") or 0, (f["per100"].get("kcal") or 0)
    if f.get("source") == "indb" and sg and (sg > 700 or kc * sg / 100 > 1500):
        # INDB records the whole recipe batch as one "serving" for some dishes (e.g. kofta curries at 4,000+ kcal)
        f["serving_g"], f["serving_label"] = None, None
        f["note"] = "The source lists an unusually large serving for this dish, so log it by weight or katori."
    f["units"] = C.units_for(f)
    if r.get("meta"):
        try:
            m = json.loads(r["meta"])
            f["sources"], f["note"] = m.get("sources") or [], m.get("note")
        except Exception:
            pass
    return f


def get(db: Callable, fid: str, user_id: int | None = None) -> dict[str, Any] | None:
    r = db("SELECT * FROM fit_foods WHERE id=? AND (user_id IS NULL OR user_id=?)", [fid, user_id], "one")
    return _row_to_food(r) if r else None


SOURCE_RANK = {"user": 0, "indb": 1, "usda": 2, "web": 3, "indb-us": 3, "indb-uk": 3, "off": 4}


def search(db: Callable, q: str, user_id: int | None, limit: int = 30) -> list[dict[str, Any]]:
    words = [w for w in re.split(r"[^a-z0-9]+", (q or "").lower()) if w]
    if not words:
        return []
    rows: list[dict[str, Any]] = []
    if _FTS["ok"]:
        match = " ".join(f'"{w}"*' for w in words)
        try:
            rows = db("""SELECT f.* FROM fit_foods_fts s JOIN fit_foods f ON f.rowid = s.rowid
                         WHERE fit_foods_fts MATCH ? AND (f.user_id IS NULL OR f.user_id=?) LIMIT 400""", [match, user_id], "all") or []
        except Exception as exc:
            log.debug("fts search failed: %s", exc)
            rows = []
    if not rows:
        cond = " AND ".join("search LIKE ?" for _ in words)
        rows = db(f"SELECT * FROM fit_foods WHERE {cond} AND (user_id IS NULL OR user_id=?) LIMIT 400", [f"%{w}%" for w in words] + [user_id], "all") or []
    first = words[0]
    whole = " ".join(words)

    def rank(r):
        n = (r.get("name") or "").lower()
        segs = {re.sub(r"[^a-z0-9 ]+", " ", x).strip() for x in re.split(r"[/,()]", n)}
        segs = {" ".join(x.split()) for x in segs}
        return (0 if whole in segs else 1 if n.startswith(first) else 2 if re.search(rf"\b{re.escape(first)}", n) else 3, SOURCE_RANK.get(r.get("source"), 5), len(n))
    rows.sort(key=rank)
    return [_row_to_food(r) for r in rows[:limit]]


# ------------------------------------------------------------------ USDA SR Legacy (one-time background import)
def usda_count(db: Callable) -> int:
    return int((db("SELECT COUNT(*) AS n FROM fit_foods WHERE source='usda'", [], "one") or {}).get("n") or 0)


def import_status(db: Callable) -> dict[str, Any]:
    return {**_IMPORT, "usda_foods": usda_count(db)}


def _ds_done(db: Callable, ds: str) -> bool:
    r = db("SELECT value FROM fit_meta WHERE key=?", ["usda_ds_" + ds], "one")
    if r and r.get("value"):
        return True
    # the SR Legacy import ran before per-dataset tracking existed
    return ds == "sr" and usda_count(db) > 5000


def start_usda_import(db: Callable) -> None:
    if _IMPORT["state"] == "running" or all(_ds_done(db, d) for d in USDA_DATASETS):
        return
    last = db("SELECT value FROM fit_meta WHERE key='usda_import_failed_at'", [], "one")
    if last and time.time() - float(last["value"] or 0) < 6 * 3600:
        return
    _IMPORT.update(state="running", detail="downloading", at=time.time())
    threading.Thread(target=_usda_import, args=(db,), daemon=True, name="fit-usda-import").start()


def _download(urls: list[str], tmp: Path) -> bool:
    for url in urls:
        try:
            with requests.get(url, stream=True, timeout=60, headers=UA) as r:
                if r.status_code != 200:
                    continue
                with open(tmp, "wb") as fh:
                    for chunk in r.iter_content(1 << 16):
                        fh.write(chunk)
            if zipfile.is_zipfile(tmp):
                return True
        except Exception as exc:
            log.info("USDA download %s failed: %s", url, exc)
    return False


def _usda_import(db: Callable) -> None:
    done, failed = [], []
    for ds, spec in USDA_DATASETS.items():
        if _ds_done(db, ds):
            continue
        tmp = DATA / f"usda_{ds}.zip"
        try:
            _IMPORT["detail"] = f"downloading {ds}"
            if not _download(spec["urls"], tmp):
                raise RuntimeError(f"could not download the USDA {ds} dataset")
            _IMPORT["detail"] = f"parsing {ds}"
            n = import_sr_zip(db, tmp, spec["types"])
            db("INSERT INTO fit_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ["usda_ds_" + ds, str(n)])
            done.append(f"{n} {ds}")
            log.info("USDA %s import: %s foods", ds, n)
        except Exception as exc:
            failed.append(str(exc)[:120])
            log.warning("USDA %s import failed: %s", ds, exc)
        finally:
            try:
                tmp.unlink()
            except OSError:
                pass
    if failed:
        db("INSERT INTO fit_meta(key,value) VALUES('usda_import_failed_at',?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", [str(time.time())])
        _IMPORT.update(state="failed", detail="; ".join(done + failed)[:200])
    else:
        _IMPORT.update(state="done", detail=("loaded " + ", ".join(done)) if done else "up to date")


def _open_member(z: zipfile.ZipFile, base: str):
    name = next((n for n in z.namelist() if n.rsplit("/", 1)[-1] == base), None)
    if not name:
        raise RuntimeError(f"{base} missing from the USDA archive")
    return io.TextIOWrapper(z.open(name), encoding="utf-8", newline="")


def import_sr_zip(db: Callable, path: Path, types: tuple[str, ...] = ("sr_legacy_food",)) -> int:
    """Parse a FoodData Central CSV release (SR Legacy or FNDDS; streamed, low memory) into fit_foods."""
    with zipfile.ZipFile(path) as z:
        nut_key = {}
        for r in csv.DictReader(_open_member(z, "nutrient.csv")):
            k = SR_NBR.get(str(r.get("nutrient_nbr") or "").split(".")[0])
            if k:
                nut_key[r["id"]] = k
        foods = {r["fdc_id"]: {"name": r["description"].strip(), "per100": {}, "portions": []}
                 for r in csv.DictReader(_open_member(z, "food.csv")) if (r.get("data_type") or types[0]) in types}
        for r in csv.DictReader(_open_member(z, "food_nutrient.csv")):
            k = nut_key.get(r.get("nutrient_id"))
            f = foods.get(r.get("fdc_id"))
            if k and f is not None:
                try:
                    f["per100"][k] = round(float(r["amount"]), 4)
                except (TypeError, ValueError):
                    pass
        units = {}
        try:
            units = {r["id"]: r["name"] for r in csv.DictReader(_open_member(z, "measure_unit.csv"))}
        except RuntimeError:
            pass
        for r in csv.DictReader(_open_member(z, "food_portion.csv")):
            f = foods.get(r.get("fdc_id"))
            if f is None:
                continue
            try:
                g = float(r.get("gram_weight") or 0)
                amt = float(r.get("amount") or 1) or 1
            except ValueError:
                continue
            if g <= 0:
                continue
            unit = units.get(r.get("measure_unit_id") or "", "")
            desc = " ".join(x for x in [(r.get("modifier") or "").strip(), (r.get("portion_description") or "").strip()] if x and x != "undetermined")
            if re.match(r"\d|quantity", desc, re.I) or not unit or unit == "undetermined":
                label = desc if re.match(r"\d|quantity", desc, re.I) else f"{amt:g} {desc}".strip()   # FNDDS: "1 wrap", "Quantity not specified"
            else:
                label = f"{amt:g} {unit} {desc}".replace("  ", " ").strip()
            if not label or label.lower().startswith("quantity not"):
                label = label or "serving"
            f["portions"].append({"label": label[:60], "g": round(g, 1)})
    n = 0
    for fdc_id, f in foods.items():
        if not f["per100"].get("kcal") and not f["per100"].get("protein_g"):
            continue
        portions = f["portions"][:8]
        upsert(db, {"id": f"usda:{fdc_id}", "user_id": None, "source": "usda", "kind": "food", "name": f["name"], "per100": f["per100"],
                    "serving_g": portions[0]["g"] if portions else None, "serving_label": re.sub(r"^1\s+", "", portions[0]["label"]) if portions else None,
                    "portions": portions[1:]})
        n += 1
    return n


def usda_api_search(db: Callable, q: str, limit: int = 8) -> list[dict[str, Any]]:
    """Fallback while the local USDA table is empty: FoodData Central search API, results cached locally."""
    key = os.getenv("USDA_API_KEY") or "DEMO_KEY"
    try:
        r = requests.get("https://api.nal.usda.gov/fdc/v1/foods/search", timeout=8, headers=UA,
                         params={"api_key": key, "query": q, "pageSize": limit, "dataType": "Survey (FNDDS),SR Legacy,Foundation"})
        if r.status_code != 200:
            return []
        out = []
        for it in r.json().get("foods") or []:
            per100 = {}
            for n in it.get("foodNutrients") or []:
                k = SR_NBR.get(str(n.get("nutrientNumber") or "").split(".")[0])
                if k and n.get("value") is not None:
                    per100[k] = round(float(n["value"]), 4)
            if not per100.get("kcal") and not per100.get("protein_g"):
                continue
            f = {"id": f"usda:{it['fdcId']}", "user_id": None, "source": "usda", "kind": "food", "name": it.get("description", "").strip(),
                 "per100": per100, "serving_g": None, "serving_label": None, "portions": []}
            upsert(db, f)
            out.append(get(db, f["id"]))
        return [f for f in out if f]
    except Exception as exc:
        log.debug("USDA API search failed: %s", exc)
        return []


# ------------------------------------------------------------------ Open Food Facts (packaged foods, barcodes)
OFF_MAP = {"energy-kcal_100g": ("kcal", 1), "proteins_100g": ("protein_g", 1), "carbohydrates_100g": ("carb_g", 1), "fat_100g": ("fat_g", 1),
           "fiber_100g": ("fibre_g", 1), "sugars_100g": ("sugar_g", 1), "saturated-fat_100g": ("sfa_g", 1), "cholesterol_100g": ("chol_mg", 1000),
           "sodium_100g": ("sodium_mg", 1000), "potassium_100g": ("potassium_mg", 1000), "calcium_100g": ("calcium_mg", 1000),
           "iron_100g": ("iron_mg", 1000), "vitamin-c_100g": ("vitc_mg", 1000), "vitamin-a_100g": ("vita_ug", 1e6), "vitamin-d_100g": ("vitd_ug", 1e6)}
OFF_FIELDS = "code,product_name,brands,nutriments,serving_size,serving_quantity"


def _off_food(p: dict[str, Any]) -> dict[str, Any] | None:
    nut = p.get("nutriments") or {}
    per100 = {}
    for src, (k, mul) in OFF_MAP.items():
        v = nut.get(src)
        if v not in (None, ""):
            try:
                per100[k] = round(float(v) * mul, 4)
            except (TypeError, ValueError):
                pass
    if "kcal" not in per100 and nut.get("energy_100g"):
        try:
            per100["kcal"] = round(float(nut["energy_100g"]) / 4.184, 1)
        except (TypeError, ValueError):
            pass
    name = (p.get("product_name") or "").strip()
    if not name or not per100.get("kcal"):
        return None
    sq = None
    try:
        sq = float(p.get("serving_quantity")) if p.get("serving_quantity") else None
    except (TypeError, ValueError):
        sq = None
    return {"id": f"off:{p.get('code')}", "user_id": None, "source": "off", "kind": "packaged", "name": name, "brand": (p.get("brands") or "").split(",")[0].strip() or None,
            "per100": per100, "serving_g": sq, "serving_label": (p.get("serving_size") or "serving")[:40] if sq else None, "portions": [], "barcode": p.get("code")}


def barcode(db: Callable, code: str) -> dict[str, Any] | None:
    code = re.sub(r"\D", "", code or "")
    if not code:
        return None
    r = db("SELECT * FROM fit_foods WHERE barcode=? LIMIT 1", [code], "one")
    if r:
        return _row_to_food(r)
    try:
        res = requests.get(f"https://world.openfoodfacts.org/api/v2/product/{code}.json", params={"fields": OFF_FIELDS}, timeout=8, headers=UA)
        p = res.json().get("product") if res.status_code == 200 else None
    except Exception:
        p = None
    f = _off_food(p or {}) if p else None
    if not f:
        return None
    upsert(db, f)
    return get(db, f["id"])


def off_search(db: Callable, q: str, limit: int = 8) -> list[dict[str, Any]]:
    try:
        res = requests.get("https://world.openfoodfacts.org/cgi/search.pl", timeout=6, headers=UA,
                           params={"search_terms": q, "json": 1, "page_size": limit, "fields": OFF_FIELDS, "countries_tags_en": "india"})
        prods = res.json().get("products") or [] if res.status_code == 200 else []
    except Exception:
        return []
    out = []
    for p in prods:
        f = _off_food(p)
        if f:
            upsert(db, f)
            out.append(get(db, f["id"]))
    return [f for f in out if f]


# ------------------------------------------------------------------ web lookup (Gemini + Google Search), validated before saving
WEB_KEYS = ["kcal", "protein_g", "carb_g", "fat_g", "fibre_g", "sugar_g", "sfa_g", "chol_mg", "sodium_mg", "potassium_mg", "calcium_mg",
            "iron_mg", "vitc_mg", "vita_ug"]


def slug(q: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (q or "").lower()).strip("-")[:60]


def check_web_food(data: dict[str, Any]) -> tuple[dict[str, float] | None, str]:
    """Plausibility checks on a web-sourced nutrition answer. Returns (per100, "") or (None, reason)."""
    raw = data.get("per100") or {}
    per100: dict[str, float] = {}
    for k in WEB_KEYS:
        v = raw.get(k)
        try:
            if v is not None and v != "":
                fv = float(v)
                if fv < 0:
                    return None, f"negative {k}"
                per100[k] = round(fv, 3)
        except (TypeError, ValueError):
            continue
    kcal = per100.get("kcal")
    p, c, f = per100.get("protein_g"), per100.get("carb_g"), per100.get("fat_g")
    if kcal is None or p is None or c is None or f is None:
        return None, "the sources didn't give calories and all three macros"
    if not (0 < kcal <= 902):
        return None, "calories per 100 g are out of range"
    if p + c + f > 101:
        return None, "macros add up to more than 100 g per 100 g"
    est = 4 * p + 4 * c + 9 * f + 2 * per100.get("fibre_g", 0)
    if abs(est - kcal) > max(0.25 * kcal, 40):
        return None, f"calories ({kcal:.0f}) don't match the macros (~{est:.0f})"
    return per100, ""


def save_web_food(db: Callable, query: str, data: dict[str, Any], per100: dict[str, float], sources: list[dict[str, str]]) -> dict[str, Any]:
    name = str(data.get("name") or query).strip()[:90]
    sg = data.get("serving_g")
    try:
        sg = float(sg) if sg not in (None, "") else None
    except (TypeError, ValueError):
        sg = None
    if sg is not None and not (3 <= sg <= 1500):
        sg = None
    fid = "web:" + slug(name)
    upsert(db, {"id": fid, "user_id": None, "source": "web", "kind": "recipe", "name": name, "brand": None, "per100": per100,
                "serving_g": sg, "serving_label": str(data.get("serving_label") or "serving")[:30] if sg else None, "portions": [],
                "alt": " ".join([query, str(data.get("aka") or "")]),
                "meta": {"sources": sources[:6], "note": str(data.get("basis") or "")[:300], "query": query, "confidence": data.get("confidence")}})
    db("INSERT INTO fit_meta(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ["web_q:" + slug(query), fid])
    return get(db, fid)


def web_cached(db: Callable, query: str) -> dict[str, Any] | None:
    r = db("SELECT value FROM fit_meta WHERE key=?", ["web_q:" + slug(query)], "one")
    return get(db, r["value"]) if r and r.get("value") else None

