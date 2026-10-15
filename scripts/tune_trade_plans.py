#!/usr/bin/env python3
"""Tune the trade-plan rule parameters per horizon with a train/test split, then write data/trade_plan_config.json.

For each horizon (scalp 1m, intraday 5m, swing 15m) a small grid of rule parameters is replayed on the first 70% of the
Upstox history of every symbol (train). The best combination by average expectancy (R per trade, with at least
MIN_TRADES per symbol) is then replayed on the last 30% (test), which it never saw. It is written only if its test
expectancy is positive and beats the default parameters on the same test window; otherwise the defaults stay.

Usage (on the server, from the repo root):  /home/ubuntu/venv/bin/python scripts/tune_trade_plans.py [SYMBOL ...]
"""
from __future__ import annotations

import itertools
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as A  # noqa: E402  (loads the Upstox adapter and candle helpers; does not start the server)
from backend.services import trade_plan as TP  # noqa: E402

SYMBOLS = [s.upper() for s in sys.argv[1:]] or ["NIFTY", "BANKNIFTY"]
GRID = {
    "gate": [35.0, 45.0, 55.0],
    "strict_htf": [False, True],
    "t1_r": [0.8, 1.0, 1.3],
    "sl_min_atr": [0.8, 1.2],
    "pullback_only": [False, True],
}
MIN_TRADES = 15
SPLIT = 0.70


def run(h: str, series: dict, prm: dict, lo: int, hi: int, mcx: bool) -> dict:
    return TP.backtest(h, series, mcx=mcx, params=prm, start=lo, stop=hi, max_signals=5000)


def main() -> None:
    t0 = time.time()
    data = {}
    for sym in SYMBOLS:
        mcx = A.get_symbol_segment(sym) == "MCX"
        data[sym] = (A._load_plan_series(sym, A._PLAN_BT_DAYS), mcx)
        print(f"loaded {sym}: " + ", ".join(f"{tf}={len(s)}" for tf, s in data[sym][0].items()), flush=True)

    out = {"generated": datetime.now(timezone.utc).isoformat(), "symbols": SYMBOLS, "split": SPLIT, "horizons": {}}
    keys = list(GRID)
    for h, cfg in TP.HORIZONS.items():
        combos = [dict(zip(keys, vals)) for vals in itertools.product(*(GRID[k] for k in keys))]
        best, best_train = None, None
        for prm in combos:
            full = {**TP.DEFAULT_PARAMS, **prm}
            exps, ok = [], True
            for sym, (series, mcx) in data.items():
                n = len(series.get(cfg["tf"]) or [])
                r = run(h, series, full, 60, int(n * SPLIT), mcx)
                if not r.get("available") or (r.get("filled") or 0) < MIN_TRADES:
                    ok = False
                    break
                exps.append(r["expectancy_r"])
            if ok and (best_train is None or sum(exps) / len(exps) > best_train):
                best, best_train = full, sum(exps) / len(exps)
        test_best, test_def = {}, {}
        for sym, (series, mcx) in data.items():
            n = len(series.get(cfg["tf"]) or [])
            if best:
                test_best[sym] = run(h, series, best, int(n * SPLIT), n, mcx)
            test_def[sym] = run(h, series, dict(TP.DEFAULT_PARAMS), int(n * SPLIT), n, mcx)

        def avg(res: dict, k: str):
            vals = [r.get(k) for r in res.values() if r.get(k) is not None]
            return round(sum(vals) / len(vals), 3) if vals else None

        accept = bool(best) and (avg(test_best, "expectancy_r") or -9) > 0 and (avg(test_best, "expectancy_r") or -9) > (avg(test_def, "expectancy_r") or -9)
        summary = lambda res: {s: {k: r.get(k) for k in ("from", "to", "signals", "filled", "t1_hit_rate", "expectancy_r")} for s, r in res.items()}
        out["horizons"][h] = {
            "params": best if accept else dict(TP.DEFAULT_PARAMS),
            "accepted_tuned": accept,
            "train_expectancy_r": round(best_train, 3) if best_train is not None else None,
            "test": {"tuned": summary(test_best), "default": summary(test_def),
                     "tuned_avg_expectancy_r": avg(test_best, "expectancy_r"), "default_avg_expectancy_r": avg(test_def, "expectancy_r"),
                     "tuned_avg_t1_hit_rate": avg(test_best, "t1_hit_rate"), "default_avg_t1_hit_rate": avg(test_def, "t1_hit_rate")},
        }
        print(f"{h}: tuned={best} train={best_train} test tuned={avg(test_best, 'expectancy_r')}R "
              f"default={avg(test_def, 'expectancy_r')}R accept={accept}", flush=True)

    TP.CONFIG_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"wrote {TP.CONFIG_PATH} in {time.time() - t0:.0f}s")


if __name__ == "__main__":
    main()
