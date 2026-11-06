"""Measured health of the live trade plans, and the learning step that needs no human.

Everything here reads only what the app itself recorded: every BUY/SELL plan it issued (`signal_plans`) and how it was
graded against 1-minute Upstox candles. Nothing is invented and nothing is applied silently:

* `forward_table`   - per symbol and horizon, how issued plans really ended (hit rate with a 95% interval, average R).
* `factor_report`   - which factor scores actually lined up with the outcome of plans (information coefficient), and the
                      weights that would follow from it. It is a proposal: weights change only after a person approves.
* journal helpers   - one JSON line per weekly review, so drift is visible over time.

`db` is a callable with the same signature as app.db_exec(sql, params, fetch).
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from backend.services import trade_plan as TP

RUNTIME_DIR = Path(__file__).resolve().parents[2] / "data" / "runtime"
JOURNAL_PATH = RUNTIME_DIR / "model_journal.jsonl"
CLOSED = ("T1", "T2", "SL", "TIME")
HITS = ("T1", "T2")
MIN_FACTOR_N = 150      # closed plans with a factor snapshot needed before weights are even proposed
BLEND_WITH_CURRENT = 0.5  # a proposal moves only half-way from the current weights toward the measured ones


def _since(days: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()


def forward_table(db: Callable, days: int = 30) -> list[dict[str, Any]]:
    """Live record per symbol and horizon over the last `days` days (gross R, before costs)."""
    rows = db("SELECT symbol, horizon, status, r FROM signal_plans WHERE created_at >= ?", [_since(days)], "all") or []
    groups: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for r in rows:
        groups.setdefault((str(r["symbol"]), str(r["horizon"])), []).append(r)
    out: list[dict[str, Any]] = []
    for (sym, hz), rs in sorted(groups.items()):
        closed = [x for x in rs if x["status"] in CLOSED]
        hits = [x for x in closed if x["status"] in HITS]
        rr = [float(x["r"] or 0) for x in closed]
        avg = sum(rr) / len(rr) if rr else None
        lo, hi = TP.wilson(len(hits), len(closed)) if closed else (None, None)
        if len(closed) < TP.MIN_FWD_N:
            verdict = "TOO_FEW"
        else:
            verdict = "FAILING" if (avg is not None and avg < 0) else "POSITIVE"
        out.append({"symbol": sym, "horizon": hz, "days": days, "issued": len(rs), "closed": len(closed), "hits": len(hits),
                    "expired_unfilled": sum(1 for x in rs if x["status"] == "EXPIRED"),
                    "hit_pct": round(len(hits) / len(closed) * 100, 1) if closed else None, "ci_low": lo, "ci_high": hi,
                    "avg_r": round(avg, 3) if avg is not None else None, "verdict": verdict})
    return out


def _pearson(xs: list[float], ys: list[float]) -> float | None:
    n = len(xs)
    if n < 3:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    sy = math.sqrt(sum((y - my) ** 2 for y in ys))
    if sx < 1e-9 or sy < 1e-9:
        return None
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / (sx * sy)


def factor_report(db: Callable, days: int = 120, min_n: int = MIN_FACTOR_N) -> dict[str, Any]:
    """Correlation between each factor score (signed so that positive means "agrees with the plan's side") and the plan's
    result in R. Needs plans recorded with their factor snapshot (column signal_plans.factors_json)."""
    try:
        rows = db("SELECT side, r, factors_json FROM signal_plans WHERE status IN ('T1','T2','SL','TIME') "
                  "AND factors_json IS NOT NULL AND created_at >= ?", [_since(days)], "all") or []
    except Exception as exc:   # column not created yet on this host
        return {"n": 0, "min_n": min_n, "ic": {}, "proposal": None, "note": f"factor snapshots unavailable: {exc}"}
    xs: dict[str, list[float]] = {k: [] for k in TP.WEIGHTS}
    ys: dict[str, list[float]] = {k: [] for k in TP.WEIGHTS}
    n = 0
    for r in rows:
        try:
            snap = json.loads(r["factors_json"])
            f = snap.get("factors") or {}
            sign = 1.0 if r["side"] == "BUY" else -1.0
            y = float(r["r"] or 0)
        except Exception:
            continue
        n += 1
        for k in TP.WEIGHTS:
            if f.get(k) is not None:
                xs[k].append(sign * float(f[k]))
                ys[k].append(y)
    ic = {k: (round(v, 3) if (v := _pearson(xs[k], ys[k])) is not None else None) for k in TP.WEIGHTS}
    rep: dict[str, Any] = {"n": n, "min_n": min_n, "days": days, "ic": ic, "current_weights": dict(TP.WEIGHTS), "proposal": None}
    if n < min_n:
        rep["note"] = f"{n} closed plans with factor snapshots; {min_n} are needed before any weight change is proposed."
        return rep
    pos = {k: max(0.0, v) for k, v in ic.items() if v is not None}
    tot = sum(pos.values())
    if tot <= 0:
        rep["note"] = "No factor showed a positive relationship with results; weights stay as they are."
        return rep
    measured = {k: pos.get(k, 0.0) / tot for k in TP.WEIGHTS}
    cur_tot = sum(TP.WEIGHTS.values())
    blended = {k: round(BLEND_WITH_CURRENT * (TP.WEIGHTS[k] / cur_tot) + (1 - BLEND_WITH_CURRENT) * measured[k], 3) for k in TP.WEIGHTS}
    rep["proposal"] = blended
    rep["note"] = "Proposal only: it is not applied automatically. Apply it after checking it on data it was not fitted on."
    return rep


def append_journal(entry: dict[str, Any], path: Path = JOURNAL_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, default=str) + "\n")


def latest_journal(path: Path = JOURNAL_PATH) -> dict[str, Any] | None:
    """The most recent review, or None. Reads only the tail of the file."""
    try:
        with path.open("rb") as fh:
            fh.seek(0, 2)
            size = fh.tell()
            fh.seek(max(0, size - 65536))
            lines = fh.read().decode("utf-8", errors="ignore").strip().splitlines()
        for line in reversed(lines):
            try:
                return json.loads(line)
            except Exception:
                continue
    except Exception:
        return None
    return None
