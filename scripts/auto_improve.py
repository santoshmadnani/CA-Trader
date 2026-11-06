#!/usr/bin/env python3
"""Weekly, unattended self-review of the trade-plan model. Safe to run with nobody watching.

What it does, in order (each step is isolated: one failing never stops the others):
  1. Reads how every plan the app issued actually ended (signal_plans) and grades each symbol and horizon.
  2. Measures which factor scores lined up with real outcomes and writes a weight *proposal* (never applied automatically).
  3. Re-runs the parameter tuner (scripts/tune_trade_plans.py: train on the first 70% of history, accept only if the last
     30% it never saw is positive and beats the defaults), then applies one more rule: a tuned set is kept only if it beats
     the defaults on that unseen window by at least MIN_MARGIN_R, otherwise the defaults stay. The previous config is kept
     as data/runtime/trade_plan_config.prev.json so it can be rolled back by copying it back.
  4. Appends one line to data/runtime/model_journal.jsonl (shown on the terminal's Model health card).

It never edits tracked code, never changes factor weights, never places orders, and skips the heavy tuning step when the
1 GB VM does not have enough free memory.

Usage (server, repo root):  /home/ubuntu/venv/bin/python scripts/auto_improve.py [--skip-tune] [--db PATH]
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.services import model_health as MH  # noqa: E402
from backend.services import trade_plan as TP  # noqa: E402

MIN_MARGIN_R = 0.03       # tuned parameters must beat the defaults by this much (R per trade) on unseen data
MIN_FREE_MB = 350         # do not start the tuner with less available memory than this
TUNE_TIMEOUT_S = 25 * 60


def mem_available_mb() -> float | None:
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024.0
    except Exception:
        pass
    return None


def find_db(arg: str | None) -> Path | None:
    cands = [arg, os.getenv("CA_DATABASE_PATH"), str(ROOT / "ca_trader.sqlite3"), str(ROOT / "ca_trader.db"), str(ROOT / "data" / "ca_trader.sqlite3")]
    for c in cands:
        if c and Path(c).exists():
            return Path(c)
    return None


def make_db(path: Path):
    """Read-only db_exec look-alike (SELECT only) so this script never touches the live tables."""
    conn = sqlite3.connect(str(path), timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only=ON")

    def db(sql: str, params: Any = (), fetch: str | None = None):
        if not sql.lstrip().upper().startswith("SELECT"):
            raise PermissionError("auto_improve is read-only on the database")
        cur = conn.execute(sql, tuple(params))
        if fetch == "one":
            row = cur.fetchone()
            return dict(row) if row else None
        if fetch == "all":
            return [dict(r) for r in cur.fetchall()]
        return cur.rowcount
    return db


def run_tuner() -> dict[str, Any]:
    free = mem_available_mb()
    if free is not None and free < MIN_FREE_MB:
        return {"ran": False, "reason": f"only {free:.0f} MB free (need {MIN_FREE_MB} MB); tuning skipped this week"}
    rt = TP.RUNTIME_CONFIG_PATH
    prev = rt.with_name("trade_plan_config.prev.json")
    had_prior = rt.exists()
    if had_prior:
        shutil.copy2(rt, prev)
    t0 = time.time()
    cmd = ["nice", "-n", "15", sys.executable, str(ROOT / "scripts" / "tune_trade_plans.py")]
    try:
        res = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=TUNE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return {"ran": True, "ok": False, "reason": f"tuner exceeded {TUNE_TIMEOUT_S // 60} min and was stopped", "secs": round(time.time() - t0)}
    out: dict[str, Any] = {"ran": True, "ok": res.returncode == 0, "rc": res.returncode, "secs": round(time.time() - t0),
                           "tail": (res.stdout or "").strip().splitlines()[-6:], "err_tail": (res.stderr or "").strip().splitlines()[-4:]}
    if res.returncode != 0 or not rt.exists():
        if had_prior and prev.exists():
            shutil.copy2(prev, rt)   # a failed run must never leave a half-written config behind
        out["ok"] = False
        return out
    cfg = json.loads(rt.read_text(encoding="utf-8"))
    summary: dict[str, Any] = {}
    for hz, h in (cfg.get("horizons") or {}).items():
        test = h.get("test") or {}
        tuned, default = test.get("tuned_avg_expectancy_r"), test.get("default_avg_expectancy_r")
        margin = round(tuned - default, 3) if tuned is not None and default is not None else None
        kept = bool(h.get("accepted_tuned")) and margin is not None and margin >= MIN_MARGIN_R
        if h.get("accepted_tuned") and not kept:
            h["params"] = dict(TP.DEFAULT_PARAMS)
            h["accepted_tuned"] = False
            h["note"] = f"tuned set beat the defaults by only {margin} R on unseen data (needs {MIN_MARGIN_R}); defaults kept"
        summary[hz] = {"kept_tuned": kept, "tuned_r": tuned, "default_r": default, "margin_r": margin, "params": h.get("params")}
    rt.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    out["horizons"] = summary
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-tune", action="store_true")
    ap.add_argument("--db")
    args = ap.parse_args()
    entry: dict[str, Any] = {"ts": datetime.now(timezone.utc).isoformat(), "mem_free_mb": mem_available_mb(), "notes": []}

    dbp = find_db(args.db)
    if dbp is None:
        entry["notes"].append("database not found; plan outcomes were not reviewed")
    else:
        try:
            db = make_db(dbp)
            entry["forward_30d"] = MH.forward_table(db, 30)
            entry["factors"] = MH.factor_report(db)
            failing = [f"{r['symbol']} {r['horizon']}" for r in entry["forward_30d"] if r["verdict"] == "FAILING"]
            if failing:
                entry["notes"].append("failing live: " + ", ".join(failing) + " (alerts for these horizons are paused automatically)")
        except Exception as exc:
            entry["notes"].append(f"outcome review failed: {exc}")

    if args.skip_tune:
        entry["tuner"] = {"ran": False, "reason": "skipped by flag"}
    else:
        try:
            entry["tuner"] = run_tuner()
        except Exception as exc:
            entry["tuner"] = {"ran": True, "ok": False, "reason": f"tuner step failed: {exc}"}

    MH.append_journal(entry)
    print(json.dumps({k: entry[k] for k in entry if k != "factors"}, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
