"""Fitness tracker API (/api/fit/*): workouts, diet, body, progress, sharing and Gemini-assisted logging.

Every route is scoped to the signed-in user's session; API tokens are not accepted here, so one user can never read
or write another user's data. Nutrition and calorie numbers come from the bundled databases and published MET values;
Gemini only turns free text or a photo into a list of items, which the user reviews before anything is saved.
"""
from __future__ import annotations

import json
import re
import secrets
import time
from datetime import date, datetime, timedelta, timezone
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException, Request

from backend.fitness import catalog as C
from backend.fitness import foods as F

IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_SLOTS = [("Breakfast", "08:30"), ("Lunch", "13:30"), ("Pre-workout", "18:30"), ("Post-workout", "20:30"), ("Dinner", "21:30")]
AI_DAILY = 40


def _today() -> str:
    return datetime.now(IST).date().isoformat()


def _day(v: str | None) -> str:
    try:
        return date.fromisoformat(str(v)[:10]).isoformat()
    except (TypeError, ValueError):
        return _today()


def _f(v: Any, default: float | None = None) -> float | None:
    try:
        x = float(v)
        return x if x == x else default
    except (TypeError, ValueError):
        return default


def build(*, db: Callable, db_insert: Callable, get_user: Callable, gemini_text: Callable, auth_enabled: bool, idle_hours: float = 720) -> APIRouter:
    r = APIRouter(prefix="/api/fit", tags=["fitness"])

    # ------------------------------------------------------------------ schema
    F.ensure_tables(db)
    for sql in [
        """CREATE TABLE IF NOT EXISTS fit_profiles (user_id INTEGER PRIMARY KEY, sex TEXT, age REAL, height_cm REAL, weight_kg REAL,
           activity TEXT, goal TEXT, overrides TEXT, onboarded INTEGER DEFAULT 0, updated_at TEXT)""",
        "CREATE TABLE IF NOT EXISTS fit_slots (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT NOT NULL, time_hhmm TEXT, builtin INTEGER DEFAULT 0)",
        """CREATE TABLE IF NOT EXISTS fit_logs (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, day TEXT NOT NULL, slot_id INTEGER,
           food_id TEXT, name TEXT, qty REAL, unit TEXT, unit_label TEXT, grams REAL, nutrients TEXT, via TEXT, created_at TEXT)""",
        "CREATE INDEX IF NOT EXISTS idx_fit_logs_day ON fit_logs(user_id, day)",
        """CREATE TABLE IF NOT EXISTS fit_workouts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, day TEXT NOT NULL, name TEXT,
           started_at TEXT, ended_at TEXT, notes TEXT, kcal REAL, share_token TEXT, via TEXT, created_at TEXT)""",
        "CREATE INDEX IF NOT EXISTS idx_fit_workouts_day ON fit_workouts(user_id, day)",
        "CREATE INDEX IF NOT EXISTS idx_fit_workouts_share ON fit_workouts(share_token)",
        """CREATE TABLE IF NOT EXISTS fit_entries (id INTEGER PRIMARY KEY AUTOINCREMENT, workout_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
           exercise_id TEXT, name TEXT, sort INTEGER DEFAULT 0, notes TEXT)""",
        "CREATE INDEX IF NOT EXISTS idx_fit_entries_w ON fit_entries(workout_id)",
        "CREATE INDEX IF NOT EXISTS idx_fit_entries_ex ON fit_entries(user_id, exercise_id)",
        """CREATE TABLE IF NOT EXISTS fit_sets (id INTEGER PRIMARY KEY AUTOINCREMENT, entry_id INTEGER NOT NULL, workout_id INTEGER NOT NULL, user_id INTEGER NOT NULL,
           idx INTEGER, reps REAL, weight_kg REAL, minutes REAL, distance_km REAL, kind TEXT DEFAULT 'normal', done INTEGER DEFAULT 1, created_at TEXT)""",
        "CREATE INDEX IF NOT EXISTS idx_fit_sets_entry ON fit_sets(entry_id)",
        "CREATE TABLE IF NOT EXISTS fit_routines (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT, items TEXT, created_at TEXT)",
        "CREATE TABLE IF NOT EXISTS fit_custom_ex (id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, name TEXT, part TEXT, equipment TEXT, kind TEXT, met REAL)",
        "CREATE TABLE IF NOT EXISTS fit_water (user_id INTEGER, day TEXT, ml REAL, PRIMARY KEY(user_id, day))",
        "CREATE TABLE IF NOT EXISTS fit_body (user_id INTEGER, day TEXT, weight_kg REAL, bodyfat REAL, PRIMARY KEY(user_id, day))",
        "CREATE TABLE IF NOT EXISTS fit_saved_meals (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, name TEXT, items TEXT, created_at TEXT)",
        "CREATE TABLE IF NOT EXISTS fit_favs (user_id INTEGER, food_id TEXT, PRIMARY KEY(user_id, food_id))",
        "CREATE TABLE IF NOT EXISTS fit_ai_usage (user_id INTEGER, day TEXT, n INTEGER, PRIMARY KEY(user_id, day))",
        "CREATE TABLE IF NOT EXISTS fit_ai_cache (user_id INTEGER, key TEXT, text TEXT, created_at TEXT, PRIMARY KEY(user_id, key))",
    ]:
        db(sql)
    try:
        F.load_bundled(db)
    except Exception:
        pass

    # ------------------------------------------------------------------ auth: session only
    def me(request: Request) -> dict[str, Any]:
        if not auth_enabled:
            row = db("SELECT * FROM users ORDER BY id LIMIT 1", [], "one")
            if row:
                return row
        uid = request.session.get("user_id")
        if not uid:
            raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "Sign in to use the fitness tracker"})
        last = request.session.get("last_seen")
        if last and time.time() - float(last) > idle_hours * 3600:
            request.session.clear()
            raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "Session expired, sign in again"})
        u = get_user(int(uid))
        if not u or not int(u.get("is_active", 1) or 0):
            raise HTTPException(401, detail={"code": "AUTH_REQUIRED", "message": "Sign in to use the fitness tracker"})
        request.session["last_seen"] = time.time()
        return u

    def own(table: str, rid: int, uid: int) -> dict[str, Any]:
        row = db(f"SELECT * FROM {table} WHERE id=? AND user_id=?", [rid, uid], "one")
        if not row:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Not found"})
        return row

    # ------------------------------------------------------------------ profile, targets, slots
    def profile(uid: int) -> dict[str, Any]:
        p = db("SELECT * FROM fit_profiles WHERE user_id=?", [uid], "one") or {}
        p = {k: p.get(k) for k in ("sex", "age", "height_cm", "weight_kg", "activity", "goal", "onboarded")} | {"overrides": json.loads(p.get("overrides") or "{}")}
        latest = db("SELECT weight_kg FROM fit_body WHERE user_id=? AND weight_kg IS NOT NULL ORDER BY day DESC LIMIT 1", [uid], "one")
        if latest and latest.get("weight_kg"):
            p["weight_kg"] = latest["weight_kg"]
        t = C.targets(p) if p.get("weight_kg") and p.get("height_cm") and p.get("age") else {}
        p["calculated"] = dict(t)          # before the user's overrides, so the app can keep the calculated macro split
        t.update({k: v for k, v in (p["overrides"] or {}).items() if v not in (None, "")})
        p["targets"] = t
        return p

    def slots(uid: int) -> list[dict[str, Any]]:
        rows = db("SELECT id, name, time_hhmm, builtin FROM fit_slots WHERE user_id=? ORDER BY COALESCE(time_hhmm,'99'), id", [uid], "all") or []
        if not rows:
            for name, t in DEFAULT_SLOTS:
                db("INSERT INTO fit_slots(user_id,name,time_hhmm,builtin) VALUES(?,?,?,1)", [uid, name, t])
            rows = db("SELECT id, name, time_hhmm, builtin FROM fit_slots WHERE user_id=? ORDER BY COALESCE(time_hhmm,'99'), id", [uid], "all") or []
        return rows

    @r.get("/me")
    def get_me(user: dict = Depends(me)) -> dict[str, Any]:
        return {"user": {"id": user["id"], "name": user.get("full_name") or user.get("username"), "email": user.get("email")},
                "profile": profile(user["id"]), "slots": slots(user["id"]), "food_db": F.import_status(db)}

    @r.put("/profile")
    async def put_profile(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        cur = db("SELECT * FROM fit_profiles WHERE user_id=?", [user["id"]], "one") or {}
        vals = {k: b.get(k, cur.get(k)) for k in ("sex", "age", "height_cm", "weight_kg", "activity", "goal")}
        if vals["sex"] not in (None, "male", "female"):
            raise HTTPException(422, detail={"code": "BAD_SEX", "message": "sex must be male or female"})
        if vals["activity"] not in (None, *C.ACTIVITY):
            raise HTTPException(422, detail={"code": "BAD_ACTIVITY", "message": "Unknown activity level"})
        if vals["goal"] not in (None, *C.GOALS):
            raise HTTPException(422, detail={"code": "BAD_GOAL", "message": "Unknown goal"})
        for k in ("age", "height_cm", "weight_kg"):
            vals[k] = _f(vals[k])
        ov = b.get("overrides", json.loads(cur.get("overrides") or "{}"))
        ov = {k: _f(v) for k, v in (ov or {}).items() if k in ("kcal", "protein_g", "carb_g", "fat_g", "fibre_g", "water_ml") and _f(v)}
        db("""INSERT INTO fit_profiles(user_id,sex,age,height_cm,weight_kg,activity,goal,overrides,onboarded,updated_at) VALUES(?,?,?,?,?,?,?,?,1,datetime('now'))
              ON CONFLICT(user_id) DO UPDATE SET sex=excluded.sex, age=excluded.age, height_cm=excluded.height_cm, weight_kg=excluded.weight_kg,
              activity=excluded.activity, goal=excluded.goal, overrides=excluded.overrides, onboarded=1, updated_at=excluded.updated_at""",
           [user["id"], vals["sex"], vals["age"], vals["height_cm"], vals["weight_kg"], vals["activity"], vals["goal"], json.dumps(ov)])
        if vals["weight_kg"] and b.get("weight_kg") is not None:
            db("INSERT INTO fit_body(user_id,day,weight_kg) VALUES(?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET weight_kg=excluded.weight_kg", [user["id"], _today(), vals["weight_kg"]])
        return {"profile": profile(user["id"])}

    @r.post("/slots")
    async def add_slot(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        name = str(b.get("name") or "").strip()[:40]
        t = str(b.get("time") or "").strip()
        if not name:
            raise HTTPException(422, detail={"code": "NAME_REQUIRED", "message": "Give the meal a name"})
        if t and not re.fullmatch(r"[0-2]\d:[0-5]\d", t):
            raise HTTPException(422, detail={"code": "BAD_TIME", "message": "Time must be HH:MM"})
        slots(user["id"])
        db("INSERT INTO fit_slots(user_id,name,time_hhmm,builtin) VALUES(?,?,?,0)", [user["id"], name, t or None])
        return {"slots": slots(user["id"])}

    @r.patch("/slots/{sid}")
    async def edit_slot(sid: int, request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_slots", sid, user["id"])
        b = await request.json()
        if b.get("name"):
            db("UPDATE fit_slots SET name=? WHERE id=?", [str(b["name"])[:40], sid])
        if "time" in b:
            t = str(b.get("time") or "").strip()
            if t and not re.fullmatch(r"[0-2]\d:[0-5]\d", t):
                raise HTTPException(422, detail={"code": "BAD_TIME", "message": "Time must be HH:MM"})
            db("UPDATE fit_slots SET time_hhmm=? WHERE id=?", [t or None, sid])
        return {"slots": slots(user["id"])}

    @r.delete("/slots/{sid}")
    def del_slot(sid: int, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_slots", sid, user["id"])
        if (db("SELECT COUNT(*) AS n FROM fit_logs WHERE slot_id=?", [sid], "one") or {}).get("n"):
            raise HTTPException(409, detail={"code": "SLOT_IN_USE", "message": "This meal has logged food. Move or delete the food first."})
        db("DELETE FROM fit_slots WHERE id=?", [sid])
        return {"slots": slots(user["id"])}

    # ------------------------------------------------------------------ exercises
    def custom_ex(uid: int) -> list[dict[str, Any]]:
        rows = db("SELECT * FROM fit_custom_ex WHERE user_id=?", [uid], "all") or []
        return [{"id": x["id"], "name": x["name"], "part": x["part"] or "Other", "equipment": x["equipment"] or "other", "kind": x["kind"] or "strength",
                 "met": x["met"] or 3.5, "image": None, "primary": [], "level": "custom", "custom": True} for x in rows]

    def ex_lookup(uid: int, eid: str) -> dict[str, Any] | None:
        e = C.exercise_index().get(eid)
        if e:
            return e
        return next((x for x in custom_ex(uid) if x["id"] == eid), None)

    @r.get("/exercises")
    def list_ex(q: str = "", part: str = "", equipment: str = "", user: dict = Depends(me)) -> dict[str, Any]:
        mine = [x for x in custom_ex(user["id"]) if (not part or x["part"] == part) and (not equipment or x["equipment"] == equipment)
                and all(w in x["name"].lower() for w in q.lower().split())]
        lib = [C.brief(e) for e in C.search_exercises(q, part, equipment, limit=80)]
        used = {r_["exercise_id"]: r_["n"] for r_ in (db("SELECT exercise_id, COUNT(*) AS n FROM fit_entries WHERE user_id=? GROUP BY exercise_id", [user["id"]], "all") or [])}
        items = mine + lib
        if not q:
            items.sort(key=lambda e: -used.get(e["id"], 0))
        return {"items": items[:100], "parts": list(C.BODY_PARTS), "equipment": [{"id": e, "label": C.EQUIP_LABEL.get(e, e.title())} for e in C.EQUIPMENT]}

    @r.get("/exercises/{eid}")
    def get_ex(eid: str, user: dict = Depends(me)) -> dict[str, Any]:
        e = ex_lookup(user["id"], eid)
        if not e:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Exercise not found"})
        return {"exercise": {**C.brief(e), **{k: e.get(k) for k in ("instructions", "secondary", "images", "category", "mechanic", "force")}},
                "history": ex_history(user["id"], eid)}

    @r.post("/exercises")
    async def add_ex(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        name = str(b.get("name") or "").strip()[:80]
        if not name:
            raise HTTPException(422, detail={"code": "NAME_REQUIRED", "message": "Name the exercise"})
        kind = b.get("kind") if b.get("kind") in ("strength", "cardio", "time") else "strength"
        eid = "u-" + secrets.token_hex(6)
        db("INSERT INTO fit_custom_ex(id,user_id,name,part,equipment,kind,met) VALUES(?,?,?,?,?,?,?)",
           [eid, user["id"], name, b.get("part") if b.get("part") in C.BODY_PARTS else "Other", b.get("equipment") or "other", kind,
            _f(b.get("met")) or (7.0 if kind == "cardio" else 3.5)])
        return {"exercise": next(x for x in custom_ex(user["id"]) if x["id"] == eid)}

    def e1rm(w: float | None, reps: float | None) -> float:
        return round(float(w) * (1 + float(reps) / 30.0), 1) if w and reps else 0.0

    def ex_history(uid: int, eid: str, before_workout: int | None = None) -> dict[str, Any]:
        q = """SELECT w.id AS wid, w.day, s.reps, s.weight_kg, s.minutes, s.distance_km, s.kind FROM fit_sets s JOIN fit_entries e ON e.id=s.entry_id
               JOIN fit_workouts w ON w.id=s.workout_id WHERE e.user_id=? AND e.exercise_id=? AND s.done=1"""
        args: list[Any] = [uid, eid]
        if before_workout:
            q += " AND w.id<>?"
            args.append(before_workout)
        rows = db(q + " ORDER BY w.started_at DESC, s.idx", args, "all") or []
        last_wid = rows[0]["wid"] if rows else None
        last = [x for x in rows if x["wid"] == last_wid]
        best = max(rows, key=lambda x: (e1rm(x["weight_kg"], x["reps"]), x["weight_kg"] or 0), default=None)
        return {"last_day": last[0]["day"] if last else None, "last": [{k: x[k] for k in ("reps", "weight_kg", "minutes", "distance_km", "kind")} for x in last],
                "best": {"weight_kg": best["weight_kg"], "reps": best["reps"], "e1rm": e1rm(best["weight_kg"], best["reps"]), "day": best["day"]} if best and best.get("weight_kg") else None,
                "sessions": len({x["wid"] for x in rows})}

    # ------------------------------------------------------------------ workouts
    def body_weight(uid: int) -> float:
        return float(profile(uid).get("weight_kg") or 70.0)

    def workout_full(w: dict[str, Any]) -> dict[str, Any]:
        entries = db("SELECT * FROM fit_entries WHERE workout_id=? ORDER BY sort, id", [w["id"]], "all") or []
        sets = db("SELECT * FROM fit_sets WHERE workout_id=? ORDER BY idx, id", [w["id"]], "all") or []
        out = []
        vol = 0.0
        for e in entries:
            ex = ex_lookup(w["user_id"], e["exercise_id"] or "") or {"name": e["name"], "part": "Other", "kind": "strength", "met": 3.5}
            ss = [s for s in sets if s["entry_id"] == e["id"]]
            vol += sum((s["weight_kg"] or 0) * (s["reps"] or 0) for s in ss if s["done"])
            out.append({"id": e["id"], "exercise_id": e["exercise_id"], "name": e["name"] or ex.get("name"), "part": ex.get("part"), "kind": ex.get("kind"),
                        "image": ex.get("image"), "notes": e.get("notes"), "sets": [{k: s[k] for k in ("id", "idx", "reps", "weight_kg", "minutes", "distance_km", "kind", "done")} for s in ss]})
        dur = None
        if w.get("started_at") and w.get("ended_at"):
            dur = round((datetime.fromisoformat(w["ended_at"]) - datetime.fromisoformat(w["started_at"])).total_seconds() / 60, 1)
        return {**{k: w.get(k) for k in ("id", "day", "name", "started_at", "ended_at", "notes", "kcal", "share_token", "via")}, "duration_min": dur,
                "volume_kg": round(vol, 1), "entries": out}

    def compute_kcal(w: dict[str, Any]) -> float:
        full = workout_full(w)
        kg = body_weight(w["user_id"])
        cardio_min, total = 0.0, 0.0
        strength_sets, met_w = [], []
        for e in full["entries"]:
            ex = ex_lookup(w["user_id"], e["exercise_id"] or "") or {"met": 3.5, "kind": "strength"}
            done = [s for s in e["sets"] if s["done"]]
            if e["kind"] in ("cardio", "time"):
                m = sum(float(s["minutes"] or 0) for s in done)
                cardio_min += m
                total += C.kcal(ex.get("met") or 7.0, kg, m)
            else:
                strength_sets += done
                met_w += [float(ex.get("met") or 3.5)] * len(done)
        if strength_sets:
            met = sum(met_w) / len(met_w)
            if full["duration_min"] and full["duration_min"] > 0:
                est = C.strength_minutes(strength_sets)
                mins = max(0.0, min(240.0, full["duration_min"]) - cardio_min)
                mins = min(max(mins, est * 0.5), est * 2.0)   # sets logged after the fact / a timer left running for hours
            else:
                mins = C.strength_minutes(strength_sets)
            total += C.kcal(met, kg, mins)
        return round(total, 1)

    def save_kcal(wid: int) -> dict[str, Any]:
        w = db("SELECT * FROM fit_workouts WHERE id=?", [wid], "one")
        db("UPDATE fit_workouts SET kcal=? WHERE id=?", [compute_kcal(w), wid])
        return workout_full(db("SELECT * FROM fit_workouts WHERE id=?", [wid], "one"))

    @r.get("/workouts")
    def list_workouts(days: int = 60, user: dict = Depends(me)) -> dict[str, Any]:
        since = (datetime.now(IST).date() - timedelta(days=max(1, min(days, 730)))).isoformat()
        ws = db("SELECT * FROM fit_workouts WHERE user_id=? AND day>=? ORDER BY day DESC, id DESC", [user["id"], since], "all") or []
        out = []
        for w in ws:
            full = workout_full(w)
            out.append({**{k: full[k] for k in ("id", "day", "name", "started_at", "ended_at", "kcal", "duration_min", "volume_kg")},
                        "exercises": [e["name"] for e in full["entries"]], "sets": sum(len(e["sets"]) for e in full["entries"])})
        active = db("SELECT id FROM fit_workouts WHERE user_id=? AND ended_at IS NULL AND started_at IS NOT NULL ORDER BY id DESC LIMIT 1", [user["id"]], "one")
        return {"items": out, "active_id": active["id"] if active else None}

    @r.post("/workouts")
    async def start_workout(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        now = datetime.now(IST)
        name = str(b.get("name") or "").strip()[:60] or f"{now.strftime('%A')} workout"
        wid = db_insert("INSERT INTO fit_workouts(user_id,day,name,started_at,via,created_at) VALUES(?,?,?,?,?,datetime('now'))",
                        [user["id"], _day(b.get("day")), name, now.isoformat() if b.get("live", True) else None, "manual"])
        rid = b.get("routine_id")
        if rid:
            rt = own("fit_routines", int(rid), user["id"])
            for i, it in enumerate(json.loads(rt["items"] or "[]")):
                ex = ex_lookup(user["id"], it.get("exercise_id") or "")
                if not ex:
                    continue
                eid = db_insert("INSERT INTO fit_entries(workout_id,user_id,exercise_id,name,sort) VALUES(?,?,?,?,?)", [wid, user["id"], ex["id"], ex["name"], i])
                for k in range(int(it.get("sets") or 3)):
                    db("INSERT INTO fit_sets(entry_id,workout_id,user_id,idx,reps,weight_kg,minutes,kind,done,created_at) VALUES(?,?,?,?,?,?,?,?,0,datetime('now'))",
                       [eid, wid, user["id"], k, _f(it.get("reps")), _f(it.get("weight_kg")), _f(it.get("minutes")), "normal"])
        return {"workout": workout_full(db("SELECT * FROM fit_workouts WHERE id=?", [wid], "one"))}

    @r.get("/workouts/{wid}")
    def get_workout(wid: int, user: dict = Depends(me)) -> dict[str, Any]:
        w = own("fit_workouts", wid, user["id"])
        full = workout_full(w)
        for e in full["entries"]:
            e["history"] = ex_history(user["id"], e["exercise_id"], before_workout=wid) if e["exercise_id"] else None
        return {"workout": full}

    @r.patch("/workouts/{wid}")
    async def edit_workout(wid: int, request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_workouts", wid, user["id"])
        b = await request.json()
        for k in ("name", "notes"):
            if k in b:
                db(f"UPDATE fit_workouts SET {k}=? WHERE id=?", [str(b[k] or "")[:500], wid])
        if "day" in b:
            db("UPDATE fit_workouts SET day=? WHERE id=?", [_day(b["day"]), wid])
        if "duration_min" in b and _f(b["duration_min"]):
            w = own("fit_workouts", wid, user["id"])
            st = datetime.fromisoformat(w["started_at"]) if w.get("started_at") else datetime.now(IST)
            db("UPDATE fit_workouts SET started_at=?, ended_at=? WHERE id=?", [st.isoformat(), (st + timedelta(minutes=_f(b["duration_min"]))).isoformat(), wid])
        return {"workout": save_kcal(wid)}

    @r.delete("/workouts/{wid}")
    def del_workout(wid: int, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_workouts", wid, user["id"])
        for t in ("fit_sets", "fit_entries"):
            db(f"DELETE FROM {t} WHERE workout_id=?", [wid])
        db("DELETE FROM fit_workouts WHERE id=?", [wid])
        return {"ok": True}

    @r.post("/workouts/{wid}/entries")
    async def add_entry(wid: int, request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_workouts", wid, user["id"])
        b = await request.json()
        ex = ex_lookup(user["id"], str(b.get("exercise_id") or ""))
        if not ex:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Exercise not found"})
        n = (db("SELECT COALESCE(MAX(sort),-1)+1 AS n FROM fit_entries WHERE workout_id=?", [wid], "one") or {}).get("n", 0)
        eid = db_insert("INSERT INTO fit_entries(workout_id,user_id,exercise_id,name,sort) VALUES(?,?,?,?,?)", [wid, user["id"], ex["id"], ex["name"], n])
        hist = ex_history(user["id"], ex["id"], before_workout=wid)
        seed = hist["last"] or ([{"minutes": 20}] if ex.get("kind") in ("cardio", "time") else [{"reps": 10, "weight_kg": None}] * 3)
        for i, s in enumerate(seed[: int(b.get("sets") or len(seed) or 3)]):
            db("INSERT INTO fit_sets(entry_id,workout_id,user_id,idx,reps,weight_kg,minutes,distance_km,kind,done,created_at) VALUES(?,?,?,?,?,?,?,?,?,0,datetime('now'))",
               [eid, wid, user["id"], i, s.get("reps"), s.get("weight_kg"), s.get("minutes"), s.get("distance_km"), "normal"])
        return get_workout(wid, user)

    @r.delete("/entries/{eid}")
    def del_entry(eid: int, user: dict = Depends(me)) -> dict[str, Any]:
        e = own("fit_entries", eid, user["id"])
        db("DELETE FROM fit_sets WHERE entry_id=?", [eid])
        db("DELETE FROM fit_entries WHERE id=?", [eid])
        save_kcal(e["workout_id"])
        return get_workout(e["workout_id"], user)

    @r.post("/entries/{eid}/sets")
    async def add_set(eid: int, request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        e = own("fit_entries", eid, user["id"])
        b = await request.json()
        last = db("SELECT * FROM fit_sets WHERE entry_id=? ORDER BY idx DESC LIMIT 1", [eid], "one") or {}
        idx = int(last.get("idx", -1)) + 1
        db("INSERT INTO fit_sets(entry_id,workout_id,user_id,idx,reps,weight_kg,minutes,distance_km,kind,done,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,datetime('now'))",
           [eid, e["workout_id"], user["id"], idx, _f(b.get("reps"), last.get("reps")), _f(b.get("weight_kg"), last.get("weight_kg")),
            _f(b.get("minutes"), last.get("minutes")), _f(b.get("distance_km"), last.get("distance_km")), b.get("kind") or "normal", 1 if b.get("done") else 0])
        return get_workout(e["workout_id"], user)

    @r.patch("/sets/{sid}")
    async def edit_set(sid: int, request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        s = own("fit_sets", sid, user["id"])
        b = await request.json()
        for k in ("reps", "weight_kg", "minutes", "distance_km"):
            if k in b:
                db(f"UPDATE fit_sets SET {k}=? WHERE id=?", [_f(b[k]), sid])
        if "kind" in b and b["kind"] in ("normal", "warmup", "drop", "failure"):
            db("UPDATE fit_sets SET kind=? WHERE id=?", [b["kind"], sid])
        if "done" in b:
            db("UPDATE fit_sets SET done=? WHERE id=?", [1 if b["done"] else 0, sid])
        save_kcal(s["workout_id"])
        pr = None
        if b.get("done"):
            cur = db("SELECT s.*, e.exercise_id FROM fit_sets s JOIN fit_entries e ON e.id=s.entry_id WHERE s.id=?", [sid], "one")
            hist = ex_history(user["id"], cur["exercise_id"], before_workout=s["workout_id"])
            mine = e1rm(cur["weight_kg"], cur["reps"])
            if mine and hist["best"] and mine > hist["best"]["e1rm"]:
                pr = {"e1rm": mine, "previous": hist["best"]["e1rm"]}
        return {**get_workout(s["workout_id"], user), "pr": pr}

    @r.delete("/sets/{sid}")
    def del_set(sid: int, user: dict = Depends(me)) -> dict[str, Any]:
        s = own("fit_sets", sid, user["id"])
        db("DELETE FROM fit_sets WHERE id=?", [sid])
        save_kcal(s["workout_id"])
        return get_workout(s["workout_id"], user)

    @r.post("/workouts/{wid}/finish")
    def finish(wid: int, user: dict = Depends(me)) -> dict[str, Any]:
        w = own("fit_workouts", wid, user["id"])
        db("DELETE FROM fit_sets WHERE workout_id=? AND done=0", [wid])
        for e in db("SELECT id FROM fit_entries WHERE workout_id=?", [wid], "all") or []:
            if not (db("SELECT COUNT(*) AS n FROM fit_sets WHERE entry_id=?", [e["id"]], "one") or {}).get("n"):
                db("DELETE FROM fit_entries WHERE id=?", [e["id"]])
        if not w.get("ended_at"):
            db("UPDATE fit_workouts SET ended_at=? WHERE id=?", [datetime.now(IST).isoformat(), wid])
        full = save_kcal(wid)
        prs = []
        for e in full["entries"]:
            if not e["exercise_id"]:
                continue
            hist = ex_history(user["id"], e["exercise_id"], before_workout=wid)
            top = max((e1rm(s["weight_kg"], s["reps"]) for s in e["sets"]), default=0)
            if top and (not hist["best"] or top > hist["best"]["e1rm"]):
                prs.append({"exercise": e["name"], "e1rm": top, "previous": hist["best"]["e1rm"] if hist["best"] else None})
        return {"workout": full, "prs": prs}

    @r.post("/workouts/{wid}/share")
    def share(wid: int, user: dict = Depends(me)) -> dict[str, Any]:
        w = own("fit_workouts", wid, user["id"])
        tok = w.get("share_token") or secrets.token_urlsafe(9)
        db("UPDATE fit_workouts SET share_token=? WHERE id=?", [tok, wid])
        return {"token": tok, "url": f"/fitnesstracker/w/{tok}"}

    @r.delete("/workouts/{wid}/share")
    def unshare(wid: int, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_workouts", wid, user["id"])
        db("UPDATE fit_workouts SET share_token=NULL WHERE id=?", [wid])
        return {"ok": True}

    @r.get("/public/workout/{token}")
    def public_workout(token: str) -> dict[str, Any]:
        w = db("SELECT * FROM fit_workouts WHERE share_token=?", [token], "one") if token else None
        if not w:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "This shared workout is no longer available"})
        u = get_user(int(w["user_id"])) or {}
        full = workout_full(w)
        return {"workout": {k: full[k] for k in ("day", "name", "duration_min", "volume_kg", "kcal", "entries")},
                "by": (u.get("full_name") or "A CA Trader user").split(" ")[0]}

    # routines
    @r.get("/routines")
    def list_routines(user: dict = Depends(me)) -> dict[str, Any]:
        rows = db("SELECT * FROM fit_routines WHERE user_id=? ORDER BY id DESC", [user["id"]], "all") or []
        out = []
        for x in rows:
            items = json.loads(x["items"] or "[]")
            for it in items:
                ex = ex_lookup(user["id"], it.get("exercise_id") or "")
                it["name"] = ex["name"] if ex else it.get("name", "?")
                it["part"] = ex.get("part") if ex else None
            out.append({"id": x["id"], "name": x["name"], "items": items})
        return {"items": out}

    @r.post("/routines")
    async def add_routine(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        items = [{"exercise_id": it.get("exercise_id"), "sets": int(_f(it.get("sets"), 3) or 3), "reps": _f(it.get("reps")), "weight_kg": _f(it.get("weight_kg")),
                  "minutes": _f(it.get("minutes"))} for it in (b.get("items") or []) if ex_lookup(user["id"], str(it.get("exercise_id") or ""))]
        if b.get("from_workout"):
            full = workout_full(own("fit_workouts", int(b["from_workout"]), user["id"]))
            items = [{"exercise_id": e["exercise_id"], "sets": len(e["sets"]) or 3, "reps": (e["sets"][0]["reps"] if e["sets"] else None),
                      "weight_kg": (e["sets"][0]["weight_kg"] if e["sets"] else None), "minutes": (e["sets"][0]["minutes"] if e["sets"] else None)} for e in full["entries"]]
        if not items:
            raise HTTPException(422, detail={"code": "EMPTY", "message": "Add at least one exercise"})
        db("INSERT INTO fit_routines(user_id,name,items,created_at) VALUES(?,?,?,datetime('now'))", [user["id"], str(b.get("name") or "My routine")[:60], json.dumps(items)])
        return list_routines(user)

    @r.delete("/routines/{rid}")
    def del_routine(rid: int, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_routines", rid, user["id"])
        db("DELETE FROM fit_routines WHERE id=?", [rid])
        return list_routines(user)

    # ------------------------------------------------------------------ foods
    @r.get("/foods/search")
    def food_search(q: str = "", user: dict = Depends(me)) -> dict[str, Any]:
        q = q.strip()[:80]
        if len(q) < 2:
            favs = db("SELECT food_id FROM fit_favs WHERE user_id=?", [user["id"]], "all") or []
            recent = db("SELECT food_id, MAX(id) AS m FROM fit_logs WHERE user_id=? AND food_id IS NOT NULL GROUP BY food_id ORDER BY m DESC LIMIT 20", [user["id"]], "all") or []
            fav_ids = [x["food_id"] for x in favs]
            return {"favourites": [f for f in (F.get(db, i, user["id"]) for i in fav_ids) if f],
                    "recent": [f for f in (F.get(db, x["food_id"], user["id"]) for x in recent) if f], "items": [], "fav_ids": fav_ids}
        items = F.search(db, q, user["id"], limit=30)
        extra = []
        if len(items) < 6 and F.usda_count(db) < 1000:
            extra += F.usda_api_search(db, q)
        if len(items) + len(extra) < 4:
            extra += F.off_search(db, q)
        seen = {f["id"] for f in items}
        items += [f for f in extra if f["id"] not in seen]
        favs = {x["food_id"] for x in (db("SELECT food_id FROM fit_favs WHERE user_id=?", [user["id"]], "all") or [])}
        return {"items": items, "fav_ids": list(favs)}

    WEB_PROMPT = """Find the nutrition facts for this food as it is usually made or sold in India: "{q}".
Search the web and use reliable sources only: food composition tables (IFCT/NIN, USDA FoodData Central), restaurant or brand
nutrition pages, packaged-food labels, or recipe sites that publish a nutrition analysis. Prefer sources that give values per 100 g
or per piece with the piece weight. If sources disagree, use the typical value and say so in "basis".
Return ONLY a JSON object, no prose:
{{"found": true|false, "name": "<common name, e.g. Paneer frankie (paneer kathi roll)>", "aka": "<other names, space separated>",
 "serving_label": "<e.g. roll, piece, plate, bowl, glass>", "serving_g": <grams in one typical serving, or null>,
 "per100": {{"kcal": n, "protein_g": n, "carb_g": n, "fat_g": n, "fibre_g": n|null, "sugar_g": n|null, "sfa_g": n|null, "chol_mg": n|null,
   "sodium_mg": n|null, "potassium_mg": n|null, "calcium_mg": n|null, "iron_mg": n|null, "vitc_mg": n|null, "vita_ug": n|null}},
 "confidence": "high|medium|low", "basis": "<one sentence: which sources, and how per-serving values were converted to per 100 g>"}}
All values per 100 g of the food as eaten. Use null for any nutrient no source reports; never guess one. If this is not a real food
or you cannot find any source with calories, protein, carbs and fat, return {{"found": false, "basis": "<why>"}}."""

    @r.post("/foods/web")
    async def food_web(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        """Look a food up on the web (Gemini + Google Search) when no database has it. Only answers that cite sources and pass the
        calorie/macro consistency check are saved; the saved food (with its sources) then shows up in everyone's search."""
        b = await request.json()
        q = re.sub(r"\s+", " ", str(b.get("q") or "")).strip()[:80]
        if len(q) < 3:
            raise HTTPException(422, detail={"code": "QUERY_SHORT", "message": "Type the food's name first"})
        hit = F.web_cached(db, q)
        if hit:
            return {"food": hit, "cached": True}
        ai_budget(user["id"])
        res = gemini_text(WEB_PROMPT.format(q=q.replace('"', "'")), budget_s=45.0, web_search=True)
        if not res.get("available"):
            raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": res.get("reason") or "Web lookup is unavailable right now"})
        m = re.search(r"\{.*\}", res.get("text") or "", re.S)
        try:
            data = json.loads(m.group(0)) if m else {}
        except Exception:
            data = {}
        sources = res.get("sources") or []
        if not data.get("found"):
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": f"Couldn't find reliable nutrition data for \"{q}\". {str(data.get('basis') or '')[:160]} You can add it as a custom food from its label.".strip()})
        if not sources:
            raise HTTPException(404, detail={"code": "NO_SOURCES", "message": "The web search returned no sources, so nothing was saved. Try a more specific name."})
        per100, why = F.check_web_food(data)
        if not per100:
            raise HTTPException(422, detail={"code": "IMPLAUSIBLE", "message": f"The values found didn't pass checks ({why}), so nothing was saved. Try again or a more specific name."})
        return {"food": F.save_web_food(db, q, data, per100, sources), "cached": False}

    @r.get("/foods/barcode/{code}")
    def food_barcode(code: str, user: dict = Depends(me)) -> dict[str, Any]:
        f = F.barcode(db, code)
        if not f:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "This barcode isn't in Open Food Facts yet. Add it as your own food."})
        return {"food": f}

    @r.get("/foods/{fid:path}")
    def food_get(fid: str, user: dict = Depends(me)) -> dict[str, Any]:
        f = F.get(db, fid, user["id"])
        if not f:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Food not found"})
        return {"food": f, "nutrients": [{"key": k, "label": l, "unit": u, "group": g} for k, l, u, g in C.NUTRIENTS]}

    @r.post("/foods")
    async def add_food(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        name = str(b.get("name") or "").strip()[:100]
        basis_g = _f(b.get("basis_g"), 100.0) or 100.0      # nutrients entered per this many grams (e.g. one 30 g serving)
        raw = b.get("nutrients") or {}
        per100 = {k: round(float(v) * 100.0 / basis_g, 4) for k, v in raw.items() if k in C.NUTRIENT_KEYS and _f(v) is not None}
        if not name or per100.get("kcal") is None:
            raise HTTPException(422, detail={"code": "INCOMPLETE", "message": "Enter a name and at least the calories"})
        fid = "user:" + secrets.token_hex(6)
        F.upsert(db, {"id": fid, "user_id": user["id"], "source": "user", "kind": "food", "name": name, "brand": b.get("brand"), "per100": per100,
                      "serving_g": _f(b.get("serving_g")), "serving_label": str(b.get("serving_label") or "serving")[:30] if _f(b.get("serving_g")) else None,
                      "portions": [], "barcode": re.sub(r"\D", "", str(b.get("barcode") or "")) or None})
        return {"food": F.get(db, fid, user["id"])}

    @r.post("/favs/{fid:path}")
    def fav(fid: str, user: dict = Depends(me)) -> dict[str, Any]:
        if db("SELECT 1 AS x FROM fit_favs WHERE user_id=? AND food_id=?", [user["id"], fid], "one"):
            db("DELETE FROM fit_favs WHERE user_id=? AND food_id=?", [user["id"], fid])
            return {"fav": False}
        db("INSERT INTO fit_favs(user_id,food_id) VALUES(?,?)", [user["id"], fid])
        return {"fav": True}

    # ------------------------------------------------------------------ diet log
    def log_food(uid: int, day: str, slot_id: int | None, food: dict[str, Any], qty: float, unit: str, via: str = "manual") -> int:
        g = C.grams_for(food, qty, unit)
        lbl = next((u["label"] for u in food["units"] if u["u"] == unit), unit)
        return db_insert("INSERT INTO fit_logs(user_id,day,slot_id,food_id,name,qty,unit,unit_label,grams,nutrients,via,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,datetime('now'))",
                         [uid, day, slot_id, food["id"], food["name"], qty, unit, lbl, g, json.dumps(C.scale(food["per100"], g)), via])

    def day_view(uid: int, day: str) -> dict[str, Any]:
        ss = slots(uid)
        logs = db("SELECT * FROM fit_logs WHERE user_id=? AND day=? ORDER BY id", [uid, day], "all") or []
        total: dict[str, float] = {}
        groups = []
        valid = {s["id"] for s in ss}
        for s in ss:
            items = [x for x in logs if x["slot_id"] == s["id"]]
            sub: dict[str, float] = {}
            for x in items:
                C.add_into(sub, json.loads(x["nutrients"] or "{}"))
            C.add_into(total, sub)
            groups.append({**s, "items": [{k: x[k] for k in ("id", "food_id", "name", "qty", "unit", "unit_label", "grams", "via")} | {"n": json.loads(x["nutrients"] or "{}")} for x in items],
                           "totals": sub})
        orphan = [x for x in logs if x["slot_id"] not in valid]
        if orphan:
            sub = {}
            for x in orphan:
                C.add_into(sub, json.loads(x["nutrients"] or "{}"))
            C.add_into(total, sub)
            groups.append({"id": None, "name": "Other", "time_hhmm": None, "items": [{k: x[k] for k in ("id", "food_id", "name", "qty", "unit", "unit_label", "grams", "via")} | {"n": json.loads(x["nutrients"] or "{}")} for x in orphan], "totals": sub})
        ws = db("SELECT * FROM fit_workouts WHERE user_id=? AND day=? ORDER BY id", [uid, day], "all") or []
        burnt = round(sum(float(w["kcal"] or 0) for w in ws), 1)
        water = (db("SELECT ml FROM fit_water WHERE user_id=? AND day=?", [uid, day], "one") or {}).get("ml") or 0
        weight = (db("SELECT weight_kg FROM fit_body WHERE user_id=? AND day=?", [uid, day], "one") or {}).get("weight_kg")
        return {"day": day, "meals": groups, "totals": total, "targets": profile(uid)["targets"], "burnt": burnt, "water_ml": water, "weight_kg": weight,
                "workouts": [{k: w[k] for k in ("id", "name", "kcal", "started_at", "ended_at")} for w in ws],
                "nutrients": [{"key": k, "label": l, "unit": u, "group": g} for k, l, u, g in C.NUTRIENTS]}

    @r.get("/day/{day}")
    def get_day(day: str, user: dict = Depends(me)) -> dict[str, Any]:
        return day_view(user["id"], _day(day))

    @r.post("/logs")
    async def add_log(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        food = F.get(db, str(b.get("food_id") or ""), user["id"])
        if not food:
            raise HTTPException(404, detail={"code": "NOT_FOUND", "message": "Food not found"})
        qty = _f(b.get("qty"), 1.0) or 1.0
        sid = b.get("slot_id")
        if sid is not None:
            own("fit_slots", int(sid), user["id"])
        day = _day(b.get("day"))
        log_food(user["id"], day, int(sid) if sid is not None else None, food, qty, str(b.get("unit") or "serving"))
        return day_view(user["id"], day)

    @r.patch("/logs/{lid}")
    async def edit_log(lid: int, request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        x = own("fit_logs", lid, user["id"])
        b = await request.json()
        food = F.get(db, x["food_id"], user["id"]) if x.get("food_id") else None
        qty = _f(b.get("qty"), x["qty"]) or x["qty"]
        unit = str(b.get("unit") or x["unit"])
        sid = b.get("slot_id", x["slot_id"])
        if sid is not None and sid != x["slot_id"]:
            own("fit_slots", int(sid), user["id"])
        if food:
            g = C.grams_for(food, qty, unit)
            lbl = next((u["label"] for u in food["units"] if u["u"] == unit), unit)
            db("UPDATE fit_logs SET qty=?, unit=?, unit_label=?, grams=?, nutrients=?, slot_id=? WHERE id=?", [qty, unit, lbl, g, json.dumps(C.scale(food["per100"], g)), sid, lid])
        else:
            db("UPDATE fit_logs SET slot_id=? WHERE id=?", [sid, lid])
        return day_view(user["id"], x["day"])

    @r.delete("/logs/{lid}")
    def del_log(lid: int, user: dict = Depends(me)) -> dict[str, Any]:
        x = own("fit_logs", lid, user["id"])
        db("DELETE FROM fit_logs WHERE id=?", [lid])
        return day_view(user["id"], x["day"])

    @r.post("/logs/copy")
    async def copy_logs(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        src, dst = _day(b.get("from")), _day(b.get("to"))
        q, args = "SELECT * FROM fit_logs WHERE user_id=? AND day=?", [user["id"], src]
        if b.get("slot_id") is not None:
            q, args = q + " AND slot_id=?", args + [int(b["slot_id"])]
        n = 0
        for x in db(q, args, "all") or []:
            db("INSERT INTO fit_logs(user_id,day,slot_id,food_id,name,qty,unit,unit_label,grams,nutrients,via,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,'copy',datetime('now'))",
               [user["id"], dst, x["slot_id"], x["food_id"], x["name"], x["qty"], x["unit"], x["unit_label"], x["grams"], x["nutrients"]])
            n += 1
        return {**day_view(user["id"], dst), "copied": n}

    @r.get("/meals")
    def list_meals(user: dict = Depends(me)) -> dict[str, Any]:
        rows = db("SELECT * FROM fit_saved_meals WHERE user_id=? ORDER BY id DESC", [user["id"]], "all") or []
        out = []
        for m in rows:
            items = json.loads(m["items"] or "[]")
            tot: dict[str, float] = {}
            for it in items:
                food = F.get(db, it["food_id"], user["id"])
                if food:
                    C.add_into(tot, C.scale(food["per100"], C.grams_for(food, it["qty"], it["unit"])))
            out.append({"id": m["id"], "name": m["name"], "items": items, "totals": tot})
        return {"items": out}

    @r.post("/meals")
    async def save_meal(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        items = []
        if b.get("from_slot") is not None:
            rows = db("SELECT food_id, name, qty, unit FROM fit_logs WHERE user_id=? AND day=? AND slot_id=? AND food_id IS NOT NULL", [user["id"], _day(b.get("day")), int(b["from_slot"])], "all") or []
            items = [dict(x) for x in rows]
        else:
            items = [{"food_id": it["food_id"], "name": it.get("name"), "qty": _f(it.get("qty"), 1), "unit": it.get("unit") or "serving"} for it in b.get("items") or [] if it.get("food_id")]
        if not items:
            raise HTTPException(422, detail={"code": "EMPTY", "message": "That meal has no foods yet"})
        db("INSERT INTO fit_saved_meals(user_id,name,items,created_at) VALUES(?,?,?,datetime('now'))", [user["id"], str(b.get("name") or "My meal")[:60], json.dumps(items)])
        return list_meals(user)

    @r.post("/meals/{mid}/log")
    async def log_meal(mid: int, request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        m = own("fit_saved_meals", mid, user["id"])
        b = await request.json()
        day = _day(b.get("day"))
        sid = b.get("slot_id")
        if sid is not None:
            own("fit_slots", int(sid), user["id"])
        for it in json.loads(m["items"] or "[]"):
            food = F.get(db, it["food_id"], user["id"])
            if food:
                log_food(user["id"], day, int(sid) if sid is not None else None, food, float(it["qty"] or 1), it["unit"], via="meal")
        return day_view(user["id"], day)

    @r.delete("/meals/{mid}")
    def del_meal(mid: int, user: dict = Depends(me)) -> dict[str, Any]:
        own("fit_saved_meals", mid, user["id"])
        db("DELETE FROM fit_saved_meals WHERE id=?", [mid])
        return list_meals(user)

    @r.post("/water")
    async def water(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        day = _day(b.get("day"))
        cur = (db("SELECT ml FROM fit_water WHERE user_id=? AND day=?", [user["id"], day], "one") or {}).get("ml") or 0
        ml = max(0.0, float(b["set_ml"]) if b.get("set_ml") is not None else cur + float(_f(b.get("add_ml"), 0) or 0))
        db("INSERT INTO fit_water(user_id,day,ml) VALUES(?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET ml=excluded.ml", [user["id"], day, ml])
        return {"day": day, "water_ml": ml}

    @r.post("/body")
    async def body(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        w = _f(b.get("weight_kg"))
        if not w or not (20 <= w <= 400):
            raise HTTPException(422, detail={"code": "BAD_WEIGHT", "message": "Enter a weight between 20 and 400 kg"})
        db("INSERT INTO fit_body(user_id,day,weight_kg,bodyfat) VALUES(?,?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET weight_kg=excluded.weight_kg, bodyfat=COALESCE(excluded.bodyfat, fit_body.bodyfat)",
           [user["id"], _day(b.get("day")), w, _f(b.get("bodyfat"))])
        return {"ok": True, "profile": profile(user["id"])}

    # ------------------------------------------------------------------ progress
    @r.get("/progress")
    def progress(days: int = 30, user: dict = Depends(me)) -> dict[str, Any]:
        days = max(7, min(days, 365))
        end = datetime.now(IST).date()
        start = end - timedelta(days=days - 1)
        uid = user["id"]
        logs = db("SELECT day, nutrients FROM fit_logs WHERE user_id=? AND day>=?", [uid, start.isoformat()], "all") or []
        ws = db("SELECT id, day, kcal FROM fit_workouts WHERE user_id=? AND day>=?", [uid, start.isoformat()], "all") or []
        bw = db("SELECT day, weight_kg FROM fit_body WHERE user_id=? AND day>=? AND weight_kg IS NOT NULL ORDER BY day", [uid, (start - timedelta(days=30)).isoformat()], "all") or []
        series = []
        for i in range(days):
            d = (start + timedelta(days=i)).isoformat()
            tot: dict[str, float] = {}
            for x in logs:
                if x["day"] == d:
                    C.add_into(tot, json.loads(x["nutrients"] or "{}"))
            series.append({"day": d, "kcal": round(tot.get("kcal", 0)), "protein_g": round(tot.get("protein_g", 0), 1), "carb_g": round(tot.get("carb_g", 0), 1),
                           "fat_g": round(tot.get("fat_g", 0), 1), "burnt": round(sum(float(w["kcal"] or 0) for w in ws if w["day"] == d)), "logged": any(x["day"] == d for x in logs)})
        # weekly hard sets per body part (last 8 weeks)
        since8 = (end - timedelta(weeks=8)).isoformat()
        rows = db("""SELECT w.day, e.exercise_id FROM fit_sets s JOIN fit_entries e ON e.id=s.entry_id JOIN fit_workouts w ON w.id=s.workout_id
                     WHERE s.user_id=? AND s.done=1 AND COALESCE(s.kind,'normal')<>'warmup' AND w.day>=?""", [uid, since8], "all") or []
        weekly: dict[str, dict[str, int]] = {}
        for x in rows:
            d = date.fromisoformat(x["day"])
            wk = (d - timedelta(days=d.weekday())).isoformat()
            ex = ex_lookup(uid, x["exercise_id"] or "") or {}
            part = ex.get("part") or "Other"
            if part == "Cardio":
                continue
            weekly.setdefault(wk, {}).setdefault(part, 0)
            weekly[wk][part] += 1
        # PRs: best estimated 1RM per exercise
        prs = db("""SELECT e.exercise_id, e.name, MAX(s.weight_kg*(1+s.reps/30.0)) AS e1rm, MAX(s.weight_kg) AS top FROM fit_sets s JOIN fit_entries e ON e.id=s.entry_id
                    WHERE s.user_id=? AND s.done=1 AND s.weight_kg>0 AND s.reps>0 GROUP BY e.exercise_id ORDER BY e1rm DESC LIMIT 12""", [uid], "all") or []
        logged = [s for s in series if s["logged"]]
        return {"series": series, "weight": bw, "weekly_sets": [{"week": k, "parts": v} for k, v in sorted(weekly.items())],
                "prs": [{"exercise_id": p["exercise_id"], "name": p["name"], "e1rm": round(p["e1rm"], 1), "top_kg": p["top"]} for p in prs],
                "averages": {"kcal": round(sum(s["kcal"] for s in logged) / len(logged)) if logged else None,
                             "protein_g": round(sum(s["protein_g"] for s in logged) / len(logged), 1) if logged else None, "days_logged": len(logged),
                             "workouts": len(ws)}, "targets": profile(uid)["targets"]}

    # ------------------------------------------------------------------ Gemini
    def ai_budget(uid: int) -> None:
        d = _today()
        n = int((db("SELECT n FROM fit_ai_usage WHERE user_id=? AND day=?", [uid, d], "one") or {}).get("n") or 0)
        if n >= AI_DAILY:
            raise HTTPException(429, detail={"code": "AI_LIMIT", "message": f"You've used today's {AI_DAILY} AI requests. Log manually, or try again tomorrow."})
        db("INSERT INTO fit_ai_usage(user_id,day,n) VALUES(?,?,1) ON CONFLICT(user_id,day) DO UPDATE SET n=n+1", [uid, d])

    def ai_json(prompt: str, image: dict | None = None) -> dict[str, Any]:
        res = gemini_text(prompt, image_data=image, budget_s=40.0) if image else gemini_text(prompt, budget_s=40.0)
        if not res.get("available"):
            raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": res.get("reason") or "AI is unavailable right now"})
        txt = res.get("text") or ""
        m = re.search(r"\{.*\}", txt, re.S)
        try:
            return json.loads(m.group(0)) if m else {}
        except Exception:
            raise HTTPException(502, detail={"code": "AI_BAD_JSON", "message": "Couldn't read the AI's answer. Try rephrasing."})

    def match_food(uid: int, name: str, qty: Any, unit: str) -> dict[str, Any]:
        cands = F.search(db, name, uid, limit=4)
        if not cands and F.usda_count(db) < 1000:
            cands = F.usda_api_search(db, name, limit=3)
        out: dict[str, Any] = {"query": name, "qty": _f(qty, 1.0) or 1.0, "unit": unit or "serving", "match": None, "alternatives": []}
        if cands:
            f = cands[0]
            u = unit if any(x["u"] == unit for x in f["units"]) else ("serving" if f.get("serving_g") else "g")
            q = out["qty"]
            if u == "g" and unit not in ("g", "gram", "grams") and not f.get("serving_g"):
                q, u = C.grams_for(f, q, unit), "g"
            g = C.grams_for(f, q, u)
            out.update(qty=q, unit=u, match={"food_id": f["id"], "name": f["name"], "source": f["source"], "grams": g, "units": f["units"], "n": C.scale(f["per100"], g)},
                       alternatives=[{"food_id": c["id"], "name": c["name"], "source": c["source"]} for c in cands[1:4]])
        return out

    def match_ex(uid: int, it: dict[str, Any]) -> dict[str, Any]:
        name = str(it.get("name") or "")
        mine = [x for x in custom_ex(uid) if name.lower() in x["name"].lower()]
        cands = mine + C.search_exercises(name, limit=4)
        if not cands:
            words = name.split()
            cands = C.search_exercises(words[-1] if words else name, limit=4)
        sets = it.get("sets")
        if isinstance(sets, (int, float)) or sets is None:
            n = int(sets or (1 if it.get("minutes") else 3))
            sets = [{"reps": _f(it.get("reps")), "weight_kg": _f(it.get("weight_kg")), "minutes": _f(it.get("minutes")), "distance_km": _f(it.get("distance_km"))} for _ in range(max(1, min(n, 20)))]
        else:
            sets = [{"reps": _f(s.get("reps")), "weight_kg": _f(s.get("weight_kg")), "minutes": _f(s.get("minutes")), "distance_km": _f(s.get("distance_km"))} for s in sets[:20] if isinstance(s, dict)]
        best = cands[0] if cands else None
        return {"query": name, "sets": sets, "match": C.brief(best) if best else None, "alternatives": [C.brief(c) for c in cands[1:4]]}

    def slot_for(uid: int, name: str | None, hhmm: str | None) -> int | None:
        ss = slots(uid)
        if name:
            n = name.lower().replace("-", " ")
            for s in ss:
                if s["name"].lower().replace("-", " ") == n or n in s["name"].lower().replace("-", " "):
                    return s["id"]
        if hhmm and re.fullmatch(r"\d{1,2}:\d{2}", hhmm):
            t = hhmm.zfill(5)
            timed = [s for s in ss if s["time_hhmm"]]
            if timed:
                return min(timed, key=lambda s: abs((int(s["time_hhmm"][:2]) * 60 + int(s["time_hhmm"][3:])) - (int(t[:2]) * 60 + int(t[3:]))))["id"]
        return None

    PARSE_PROMPT = """You turn a person's rough description of their day into structured log items for a fitness tracker.
Return ONLY a JSON object, no prose, with this shape:
{{"foods":[{{"name":"<food as commonly called, e.g. chapati, dal tadka, boiled egg, whey protein>","qty":<number>,"unit":"<serving|piece|g|ml|katori|cup|tbsp|tsp|glass|plate|scoop>","meal":"<one of: {slots} or a short new name>","time":"<HH:MM or null>"}}],
 "exercises":[{{"name":"<exercise name, e.g. barbell bench press, lat pulldown, treadmill run>","sets":[{{"reps":<n or null>,"weight_kg":<n or null>,"minutes":<n or null>,"distance_km":<n or null>}}]}}],
 "water_ml":<total water in ml mentioned, or null>, "weight_kg":<body weight if mentioned, or null>, "notes":"<anything you could not place>"}}
Rules: split combined dishes into separate foods only when the person lists them separately; keep Indian dish names (roti, sabzi, dal, poha);
"2 roti" is qty 2 unit piece; a "plate" or "bowl" of a dish is qty 1 with that unit; "4x8 at 60" means 4 sets of 8 reps at 60 kg;
convert lb to kg; never guess calories or nutrients; if a quantity is missing use 1 serving; do not invent foods or exercises that are not mentioned.
Today is {today}. Text: <<<{text}>>>"""

    @r.post("/ai/parse")
    async def ai_parse(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        text = str(b.get("text") or "").strip()[:3000]
        if len(text) < 3:
            raise HTTPException(422, detail={"code": "EMPTY", "message": "Describe what you ate or did"})
        ai_budget(user["id"])
        names = ", ".join(s["name"] for s in slots(user["id"]))
        data = ai_json(PARSE_PROMPT.format(slots=names, today=_day(b.get("day")), text=text.replace("<<<", "").replace(">>>", "")))
        foods = []
        for it in (data.get("foods") or [])[:40]:
            if not isinstance(it, dict) or not it.get("name"):
                continue
            m = match_food(user["id"], str(it["name"])[:80], it.get("qty"), str(it.get("unit") or "serving"))
            m["slot_id"] = slot_for(user["id"], it.get("meal"), it.get("time"))
            m["meal_hint"] = it.get("meal")
            foods.append(m)
        exs = [match_ex(user["id"], it) for it in (data.get("exercises") or [])[:30] if isinstance(it, dict) and it.get("name")]
        return {"draft": {"day": _day(b.get("day")), "foods": foods, "exercises": exs, "water_ml": _f(data.get("water_ml")), "weight_kg": _f(data.get("weight_kg")),
                          "notes": str(data.get("notes") or "")[:300]}, "slots": slots(user["id"])}

    PHOTO_PROMPT = """Identify the foods on this plate or in this photo for a calorie tracker. Return ONLY JSON:
{"foods":[{"name":"<common name, e.g. chapati, dal, jeera rice, paneer butter masala, salad>","qty":<number>,"unit":"<piece|katori|serving|g|cup|glass|plate>"}],"notes":"<uncertainties>"}
Estimate visible portions in household units (Indian katori ~150 g). Do not give calories. Only list foods you can see."""

    @r.post("/ai/photo")
    async def ai_photo(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        b = await request.json()
        img = str(b.get("image") or "")
        if not img or len(img) > 8_000_000:
            raise HTTPException(422, detail={"code": "BAD_IMAGE", "message": "Attach a photo under 6 MB"})
        mime = "image/jpeg"
        mm = re.match(r"data:(image/[a-z+]+);base64,", img)
        if mm:
            mime = mm.group(1)
        ai_budget(user["id"])
        data = ai_json(PHOTO_PROMPT, image={"mime_type": mime, "data": img})
        sid = b.get("slot_id")
        foods = []
        for it in (data.get("foods") or [])[:20]:
            if isinstance(it, dict) and it.get("name"):
                m = match_food(user["id"], str(it["name"])[:80], it.get("qty"), str(it.get("unit") or "serving"))
                m["slot_id"] = int(sid) if sid is not None else None
                foods.append(m)
        return {"draft": {"day": _day(b.get("day")), "foods": foods, "exercises": [], "water_ml": None, "weight_kg": None, "notes": str(data.get("notes") or "")[:300]},
                "slots": slots(user["id"])}

    @r.post("/ai/commit")
    async def ai_commit(request: Request, user: dict = Depends(me)) -> dict[str, Any]:
        """Save a reviewed draft. Only items the user kept (with a chosen food/exercise) are saved."""
        b = await request.json()
        d = b.get("draft") or {}
        day = _day(d.get("day"))
        uid = user["id"]
        n_food = n_ex = 0
        for it in d.get("foods") or []:
            if it.get("skip") or not it.get("food_id"):
                continue
            food = F.get(db, str(it["food_id"]), uid)
            if not food:
                continue
            sid = it.get("slot_id")
            if sid is not None and not db("SELECT 1 AS x FROM fit_slots WHERE id=? AND user_id=?", [int(sid), uid], "one"):
                sid = None
            if sid is None and it.get("new_slot"):
                slots(uid)
                ns = str(it["new_slot"]).strip()[:40]
                ns = ns[:1].upper() + ns[1:]
                hit = db("SELECT id FROM fit_slots WHERE user_id=? AND lower(name)=lower(?)", [uid, ns], "one")
                sid = hit["id"] if hit else db_insert("INSERT INTO fit_slots(user_id,name,time_hhmm,builtin) VALUES(?,?,?,0)", [uid, ns, None])
            log_food(uid, day, int(sid) if sid is not None else None, food, _f(it.get("qty"), 1) or 1, str(it.get("unit") or "serving"), via="ai")
            n_food += 1
        exs = [e for e in d.get("exercises") or [] if not e.get("skip") and e.get("exercise_id") and ex_lookup(uid, str(e["exercise_id"]))]
        wid = None
        if exs:
            wid = db_insert("INSERT INTO fit_workouts(user_id,day,name,via,created_at) VALUES(?,?,?,?,datetime('now'))", [uid, day, str(d.get("workout_name") or "Logged workout")[:60], "ai"])
            for i, e in enumerate(exs):
                ex = ex_lookup(uid, str(e["exercise_id"]))
                eid = db_insert("INSERT INTO fit_entries(workout_id,user_id,exercise_id,name,sort) VALUES(?,?,?,?,?)", [wid, uid, ex["id"], ex["name"], i])
                for k, s in enumerate(e.get("sets") or [{}]):
                    db("INSERT INTO fit_sets(entry_id,workout_id,user_id,idx,reps,weight_kg,minutes,distance_km,kind,done,created_at) VALUES(?,?,?,?,?,?,?,?,'normal',1,datetime('now'))",
                       [eid, wid, uid, k, _f(s.get("reps")), _f(s.get("weight_kg")), _f(s.get("minutes")), _f(s.get("distance_km"))])
                n_ex += 1
            save_kcal(wid)
        if _f(d.get("water_ml")):
            cur = (db("SELECT ml FROM fit_water WHERE user_id=? AND day=?", [uid, day], "one") or {}).get("ml") or 0
            db("INSERT INTO fit_water(user_id,day,ml) VALUES(?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET ml=excluded.ml", [uid, day, cur + _f(d["water_ml"])])
        if _f(d.get("weight_kg")) and 20 <= _f(d["weight_kg"]) <= 400:
            db("INSERT INTO fit_body(user_id,day,weight_kg) VALUES(?,?,?) ON CONFLICT(user_id,day) DO UPDATE SET weight_kg=excluded.weight_kg", [uid, day, _f(d["weight_kg"])])
        return {"saved": {"foods": n_food, "exercises": n_ex, "workout_id": wid}, "day": day_view(uid, day)}

    @r.get("/ai/review")
    def ai_review(refresh: int = 0, user: dict = Depends(me)) -> dict[str, Any]:
        uid = user["id"]
        key = "review:" + _today()
        if not refresh:
            c = db("SELECT text, created_at FROM fit_ai_cache WHERE user_id=? AND key=?", [uid, key], "one")
            if c:
                return {"text": c["text"], "created_at": c["created_at"], "cached": True}
        prog = progress(7, user)
        p = profile(uid)
        logged = [s for s in prog["series"] if s["logged"]]
        if not logged and not prog["averages"]["workouts"]:
            return {"text": None, "reason": "Log a few meals or a workout first; the review is built from your own entries."}
        ai_budget(uid)
        facts = {"goal": p.get("goal"), "targets": p.get("targets"), "days": prog["series"], "weekly_sets_by_part": prog["weekly_sets"][-2:],
                 "prs": prog["prs"][:5], "weight_entries": prog["weight"][-10:]}
        prompt = ("You are a supportive, evidence-based fitness coach. Using ONLY the numbers in this JSON (do not invent any), write a short weekly review "
                  "for the user in plain English: 1) how calories and protein compared with targets (mention days not logged instead of assuming), "
                  "2) training: which body parts got enough weekly sets (10-20 hard sets is a common guideline) and which were missed, 3) two or three "
                  "specific, practical suggestions for next week (Indian food options welcome). Under 170 words, use short bullet points, no medical claims.\n"
                  + json.dumps(facts, default=str)[:12000])
        res = gemini_text(prompt, budget_s=40.0)
        if not res.get("available"):
            raise HTTPException(503, detail={"code": "AI_UNAVAILABLE", "message": res.get("reason") or "AI is unavailable right now"})
        txt = (res.get("text") or "").strip()
        db("INSERT INTO fit_ai_cache(user_id,key,text,created_at) VALUES(?,?,?,datetime('now')) ON CONFLICT(user_id,key) DO UPDATE SET text=excluded.text, created_at=excluded.created_at", [uid, key, txt])
        return {"text": txt, "created_at": datetime.now(timezone.utc).isoformat(), "cached": False}

    return r
