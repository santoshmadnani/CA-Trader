"""Next-session outlook: direction, opening gap and expected range for the next trading day, with walk-forward validation.

Features (all known at today's close, from Upstox data):
  ret_1d      today's close-to-close return (in ATR units)
  clv         close location in the day's range (-1 at the low, +1 at the high)
  last_hour   move over the final hour of the session (in ATR units, from 60-minute candles)
  trend       close vs 20-day EMA (in ATR units)
  slope       5-day change of the 20-day EMA (in ATR units)
  rsi         14-day RSI, centred and scaled
  vix_chg     India VIX 1-day change (%), when available
  us_ret      S&P 500 return of the US session that closes after India's close the same date (known before India's next open)

Model: L2-regularised logistic regression (numpy, no external ML libs). It is validated walk-forward: for every test day
the model is fitted only on days before it, so the reported accuracy is out-of-sample. The expected range is
close +/- k x ATR(14), with k picked so that ~70% of past next-day ranges fell inside it.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

import numpy as np

IST = timezone(timedelta(hours=5, minutes=30))
FEATURES = ["ret_1d", "clv", "last_hour", "trend", "slope", "rsi", "vix_chg", "us_ret"]


def _d(c: dict[str, Any]) -> date:
    return datetime.fromisoformat(str(c["timestamp"]).replace("Z", "+00:00")).astimezone(IST).date()


def _ema(vals: list[float], n: int) -> list[float]:
    k, e, out = 2 / (n + 1), vals[0], []
    for v in vals:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def build_dataset(daily: list[dict[str, Any]], hourly: list[dict[str, Any]] | None = None,
                  vix_daily: list[dict[str, Any]] | None = None, us_returns: dict[date, float] | None = None) -> list[dict[str, Any]]:
    days = sorted({_d(c): c for c in daily if c.get("close") is not None}.items())
    if len(days) < 60:
        return []
    o = [float(c["open"]) for _, c in days]
    h = [float(c["high"]) for _, c in days]
    lo = [float(c["low"]) for _, c in days]
    cl = [float(c["close"]) for _, c in days]
    dts = [d for d, _ in days]
    tr = [h[0] - lo[0]] + [max(h[i] - lo[i], abs(h[i] - cl[i - 1]), abs(lo[i] - cl[i - 1])) for i in range(1, len(cl))]
    atr, prev = [], None
    for t in tr:
        prev = t if prev is None else (prev * 13 + t) / 14
        atr.append(max(prev, 1e-6))
    e20 = _ema(cl, 20)
    gains = [0.0] + [max(0.0, cl[i] - cl[i - 1]) for i in range(1, len(cl))]
    losses = [0.0] + [max(0.0, cl[i - 1] - cl[i]) for i in range(1, len(cl))]
    ag, al, rsi = 0.0, 0.0, []
    for i in range(len(cl)):
        ag = (ag * 13 + gains[i]) / 14
        al = (al * 13 + losses[i]) / 14
        rsi.append(100 - 100 / (1 + ag / max(al, 1e-9)))
    last_hour: dict[date, float] = {}
    if hourly:
        by_day: dict[date, list[dict[str, Any]]] = {}
        for c in sorted(hourly, key=lambda c: c["timestamp"]):
            by_day.setdefault(_d(c), []).append(c)
        for d, bars in by_day.items():
            if len(bars) >= 2:
                last_hour[d] = float(bars[-1]["close"]) - float(bars[-1]["open"])
    vix: dict[date, float] = {}
    if vix_daily:
        vs = sorted({_d(c): float(c["close"]) for c in vix_daily if c.get("close")}.items())
        for i in range(1, len(vs)):
            vix[vs[i][0]] = (vs[i][1] / vs[i - 1][1] - 1) * 100 if vs[i - 1][1] else 0.0
    rows = []
    for i in range(25, len(cl)):
        a = atr[i - 1]
        rng = h[i] - lo[i]
        row = {
            "date": dts[i].isoformat(),
            "close": cl[i], "atr": atr[i],
            "ret_1d": (cl[i] - cl[i - 1]) / a,
            "clv": ((cl[i] - lo[i]) - (h[i] - cl[i])) / rng if rng > 0 else 0.0,
            "last_hour": last_hour.get(dts[i], 0.0) / a,
            "trend": (cl[i] - e20[i]) / a,
            "slope": (e20[i] - e20[i - 5]) / a,
            "rsi": (rsi[i] - 50) / 25,
            "vix_chg": vix.get(dts[i], 0.0) / 5,
            "us_ret": (us_returns or {}).get(dts[i], 0.0),
            "us_known": dts[i] in (us_returns or {}),
        }
        if i + 1 < len(cl):
            row["next_up"] = 1 if cl[i + 1] > cl[i] else 0
            row["next_gap_up"] = 1 if o[i + 1] > cl[i] else 0
            row["next_range_atr"] = (max(h[i + 1], cl[i]) - min(lo[i + 1], cl[i])) / atr[i]
            row["next_ret"] = cl[i + 1] / cl[i] - 1
        rows.append(row)
    return rows


def _fit(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 300, lr: float = 0.2) -> np.ndarray:
    Xb = np.hstack([np.ones((len(X), 1)), X])
    w = np.zeros(Xb.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        grad = Xb.T @ (p - y) / len(y) + l2 * np.r_[0, w[1:]] / len(y)
        w -= lr * grad
    return w


def _prob(w: np.ndarray, x: np.ndarray) -> float:
    return float(1 / (1 + np.exp(-(w[0] + x @ w[1:]))))


def walk_forward(rows: list[dict[str, Any]], target: str, min_train: int = 120, refit_every: int = 10) -> dict[str, Any]:
    data = [r for r in rows if target in r]
    if len(data) < min_train + 30:
        return {"available": False, "reason": f"need {min_train + 30} days, have {len(data)}"}
    X = np.array([[r[f] for f in FEATURES] for r in data])
    y = np.array([r[target] for r in data], dtype=float)
    preds, w = [], None
    for i in range(min_train, len(data)):
        if w is None or (i - min_train) % refit_every == 0:
            w = _fit(X[:i], y[:i])
        preds.append((_prob(w, X[i]), y[i]))
    p = np.array([a for a, _ in preds])
    t = np.array([b for _, b in preds])
    acc = float(((p >= 0.5) == (t == 1)).mean())
    base_rate = float(y[:min_train].mean())
    baseline = float(((base_rate >= 0.5) == (t == 1)).mean())  # always predict the training-majority side
    confident = np.abs(p - 0.5) >= 0.1
    return {
        "available": True, "target": target, "test_days": int(len(t)),
        "from": data[min_train]["date"], "to": data[-1]["date"],
        "accuracy_pct": round(acc * 100, 1), "baseline_pct": round(baseline * 100, 1),
        "confident_days": int(confident.sum()),
        "confident_accuracy_pct": round(float(((p[confident] >= 0.5) == (t[confident] == 1)).mean()) * 100, 1) if confident.any() else None,
        "brier": round(float(((p - t) ** 2).mean()), 4),
    }


def range_multiplier(rows: list[dict[str, Any]], coverage: float = 0.7) -> tuple[float, float]:
    vals = sorted(r["next_range_atr"] / 2 for r in rows if "next_range_atr" in r)
    if not vals:
        return 0.6, 0.0
    k = vals[min(len(vals) - 1, int(len(vals) * coverage))]
    return round(k, 3), round(sum(1 for v in vals if v <= k) / len(vals) * 100, 1)


def predict(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Fit on all labelled history and score the latest (unlabelled) day."""
    if not rows:
        return {"available": False, "reason": "no daily history"}
    hist = [r for r in rows if "next_up" in r]
    last = rows[-1]
    x = np.array([last[f] for f in FEATURES])
    out: dict[str, Any] = {"available": True, "as_of": last["date"], "close": last["close"], "atr": round(last["atr"], 2),
                           "features": {f: round(last[f], 3) for f in FEATURES}}
    for target, key in (("next_up", "p_up"), ("next_gap_up", "p_gap_up")):
        w = _fit(np.array([[r[f] for f in FEATURES] for r in hist]), np.array([r[target] for r in hist], dtype=float))
        out[key] = round(_prob(w, x) * 100, 1)
        out[key + "_drivers"] = sorted(({"feature": f, "effect": round(float(w[j + 1] * x[j]), 3)} for j, f in enumerate(FEATURES)),
                                       key=lambda d: -abs(d["effect"]))[:3]
    k, cov = range_multiplier(hist)
    out["expected_range"] = {"low": round(last["close"] - k * last["atr"], 2), "high": round(last["close"] + k * last["atr"], 2),
                             "k_atr": k, "historical_coverage_pct": cov}
    p = out["p_up"]
    out["bias"] = "UP" if p >= 57 else "DOWN" if p <= 43 else "NEUTRAL"
    return out
