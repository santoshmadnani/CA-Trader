"""Time-bound, multi-timeframe trade plans (scalp / intraday / swing).

Each plan is built only from Upstox candles (and the Upstox option chain for premium levels):

* direction  - weighted factor score on the plan's own timeframe (trend, VWAP, momentum, structure),
               confirmed by the trend on two higher timeframes; a plan never fires against them.
* entry      - a zone, not a single price: the pullback area between the nearest support (VWAP / EMA21 /
               swing pivot) and the current price. Extended moves get a "wait for pullback" zone instead of a chase.
* stop loss  - beyond the nearest swing pivot, bounded to 0.8-2.2 ATR so it is neither noise-tight nor huge.
* targets    - T1 = 1R (capped at the nearest opposing pivot when that is still >= 0.8R), T2 = 2R.
* time       - the zone expires after `validity_bars`; an open trade is closed at `time_stop_bars` if T1 never came.

`backtest()` replays the same rules bar by bar (no look-ahead: higher timeframes use only closed bars) and reports
fill rate, T1-before-SL hit rate and expectancy in R, so every plan can show how often it actually worked.
"""
from __future__ import annotations

import bisect
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

IST = timezone(timedelta(hours=5, minutes=30))

TF_MIN = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30, "60m": 60, "1D": 375}

HORIZONS: dict[str, dict[str, Any]] = {
    "scalp": {"label": "Scalp", "tf": "1m", "htf": ("5m", "15m"), "validity_bars": 10, "time_stop_bars": 25,
              "hold": "10-25 min"},
    "intraday": {"label": "Intraday", "tf": "5m", "htf": ("15m", "60m"), "validity_bars": 6, "time_stop_bars": 24,
                 "hold": "30 min-2 h"},
    "swing": {"label": "Swing", "tf": "15m", "htf": ("60m", "1D"), "validity_bars": 4, "time_stop_bars": 26,
              "hold": "same day-next day"},
}

WEIGHTS = {"trend": 0.30, "vwap": 0.20, "momentum": 0.25, "structure": 0.25}
GATE = 35.0

# Tunable rule parameters (per horizon); data/trade_plan_config.json (written by scripts/tune_trade_plans.py) overrides them.
DEFAULT_PARAMS = {"gate": 35.0, "strict_htf": False, "t1_r": 1.0, "t2_r": 2.0, "sl_min_atr": 0.8, "sl_max_atr": 2.2, "pullback_only": False}
CONFIG_PATH = Path(__file__).resolve().parents[2] / "data" / "trade_plan_config.json"
_CONFIG_CACHE: dict[str, Any] = {"mtime": None, "data": {}}


def params_for(horizon: str) -> dict[str, Any]:
    try:
        mtime = CONFIG_PATH.stat().st_mtime
        if mtime != _CONFIG_CACHE["mtime"]:
            _CONFIG_CACHE.update(mtime=mtime, data=json.loads(CONFIG_PATH.read_text(encoding="utf-8")))
    except Exception:
        _CONFIG_CACHE.update(mtime=None, data={})
    tuned = ((_CONFIG_CACHE["data"].get("horizons") or {}).get(horizon) or {}).get("params") or {}
    return {**DEFAULT_PARAMS, **tuned}


# ---------------------------------------------------------------------------
# indicators
# ---------------------------------------------------------------------------

def _ts(c: dict[str, Any]) -> datetime | None:
    try:
        return datetime.fromisoformat(str(c.get("timestamp")).replace("Z", "+00:00")).astimezone(IST)
    except Exception:
        return None


def _ema_series(vals: list[float], n: int) -> list[float]:
    if not vals:
        return []
    k, e, out = 2 / (n + 1), vals[0], []
    for v in vals:
        e = v * k + e * (1 - k)
        out.append(e)
    return out


def _atr_series(h: list[float], l: list[float], c: list[float], n: int = 14) -> list[float]:
    out, prev = [], None
    for i in range(len(c)):
        tr = h[i] - l[i] if i == 0 else max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
        prev = tr if prev is None else (prev * (n - 1) + tr) / n
        out.append(max(prev, 1e-6))
    return out


def _rsi_series(c: list[float], n: int = 14) -> list[float]:
    out, ag, al = [50.0] * len(c), 0.0, 0.0
    for i in range(1, len(c)):
        g, lo = max(0.0, c[i] - c[i - 1]), max(0.0, c[i - 1] - c[i])
        if i <= n:
            ag += g / n
            al += lo / n
        else:
            ag = (ag * (n - 1) + g) / n
            al = (al * (n - 1) + lo) / n
        out[i] = 100 - 100 / (1 + ag / max(al, 1e-9)) if i >= n else 50.0
    return out


class Series:
    """Candles of one timeframe with precomputed indicators (index-aligned)."""

    def __init__(self, candles: list[dict[str, Any]], tf: str, day_close: tuple[int, int] = (15, 30)):
        rows = [(t, c) for c in candles if c.get("close") is not None for t in [_ts(c)] if t is not None]
        rows.sort(key=lambda r: r[0])
        self.tf = tf
        self.t = [r[0] for r in rows]
        self.o = [float(r[1].get("open") or r[1]["close"]) for r in rows]
        self.h = [float(r[1].get("high") or r[1]["close"]) for r in rows]
        self.l = [float(r[1].get("low") or r[1]["close"]) for r in rows]
        self.c = [float(r[1]["close"]) for r in rows]
        self.v = [float(r[1].get("volume") or 0) for r in rows]
        self.e9 = _ema_series(self.c, 9)
        self.e21 = _ema_series(self.c, 21)
        self.e50 = _ema_series(self.c, 50)
        self.atr = _atr_series(self.h, self.l, self.c)
        self.rsi = _rsi_series(self.c)
        macd = [a - b for a, b in zip(_ema_series(self.c, 12), _ema_series(self.c, 26))]
        sig = _ema_series(macd, 9)
        self.hist = [m - s for m, s in zip(macd, sig)]
        self.vwap = self._session_vwap()
        # bar close times, used to pick only *closed* higher-timeframe bars (no look-ahead)
        if tf == "1D":
            # a daily bar only counts as closed when its exchange session ends (15:30 NSE/BSE, 23:30 MCX),
            # so intraday replays never see the day's own candle before the close
            self.close_t = [t.replace(hour=day_close[0], minute=day_close[1], second=0, microsecond=0) for t in self.t]
        else:
            step = timedelta(minutes=TF_MIN.get(tf, 5))
            self.close_t = [t + step for t in self.t]

    def __len__(self) -> int:
        return len(self.c)

    def _session_vwap(self) -> list[float]:
        out, day, pv, vv, tp_sum, n = [], None, 0.0, 0.0, 0.0, 0
        for i, t in enumerate(self.t):
            if self.tf == "1D":
                out.append(self.c[i])
                continue
            if t.date() != day:
                day, pv, vv, tp_sum, n = t.date(), 0.0, 0.0, 0.0, 0
            tp = (self.h[i] + self.l[i] + self.c[i]) / 3
            pv += tp * self.v[i]
            vv += self.v[i]
            tp_sum += tp
            n += 1
            out.append(pv / vv if vv > 0 else tp_sum / n)  # indices carry no volume: equal-weight typical price
        return out

    def last_closed_index(self, at: datetime) -> int:
        """Index of the last bar that had fully closed at time `at` (-1 if none)."""
        return bisect.bisect_right(self.close_t, at) - 1

    def pivots(self, i: int, lookback: int = 40, k: int = 2) -> tuple[list[float], list[float]]:
        """Confirmed swing highs/lows (k bars each side) within the lookback window ending at bar i."""
        hi, lo = [], []
        start = max(k, i - lookback)
        for j in range(start, i - k + 1):
            if all(self.h[j] >= self.h[j - d] and self.h[j] >= self.h[j + d] for d in range(1, k + 1)):
                hi.append(self.h[j])
            if all(self.l[j] <= self.l[j - d] and self.l[j] <= self.l[j + d] for d in range(1, k + 1)):
                lo.append(self.l[j])
        return hi, lo


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def _clamp(x: float) -> float:
    return max(-100.0, min(100.0, x))


def _score(s: Series, i: int) -> dict[str, Any]:
    px, atr = s.c[i], s.atr[i]
    e9, e21, e50 = s.e9[i], s.e21[i], s.e50[i]
    trend = _clamp(((e9 > e21) - (e9 < e21)) * 40 + ((e21 > e50) - (e21 < e50)) * 30 + _clamp((e9 - e21) / atr * 30))
    vwap = _clamp((px - s.vwap[i]) / atr / 1.5 * 100) if s.tf != "1D" else 0.0
    h, hp = s.hist[i], s.hist[i - 1]
    momentum = _clamp((s.rsi[i] - 50) * 3 + (25 if h > 0 and h > hp else -25 if h < 0 and h < hp else 0))
    highs, lows = s.pivots(i)
    last_hi = highs[-1] if highs else max(s.h[max(0, i - 20):i] or [px])
    last_lo = lows[-1] if lows else min(s.l[max(0, i - 20):i] or [px])
    structure = 0.0
    if px > last_hi:
        structure += 60
    elif px < last_lo:
        structure -= 60
    if len(highs) >= 2 and len(lows) >= 2:
        structure += 40 if (highs[-1] > highs[-2] and lows[-1] > lows[-2]) else -40 if (highs[-1] < highs[-2] and lows[-1] < lows[-2]) else 0
    scores = {"trend": trend, "vwap": vwap, "momentum": momentum, "structure": _clamp(structure)}
    w = dict(WEIGHTS)
    if s.tf == "1D":
        w["vwap"] = 0.0
    total = sum(scores[k] * w[k] for k in scores) / (sum(w.values()) or 1)
    return {"total": round(total, 1), "scores": {k: round(v, 1) for k, v in scores.items()},
            "inputs": {"price": px, "atr": atr, "ema9": e9, "ema21": e21, "ema50": e50, "vwap": s.vwap[i], "rsi": s.rsi[i],
                       "macd_hist": h, "last_pivot_high": last_hi, "last_pivot_low": last_lo}}


def _htf_bias(s: Series | None, at: datetime) -> dict[str, Any]:
    if s is None or len(s) < 30:
        return {"tf": getattr(s, "tf", None), "bias": 0, "text": "not enough data"}
    j = s.last_closed_index(at)
    if j < 25:
        return {"tf": s.tf, "bias": 0, "text": "not enough closed bars"}
    px, e9, e21 = s.c[j], s.e9[j], s.e21[j]
    bias = 1 if (px > e21 and e9 > e21) else -1 if (px < e21 and e9 < e21) else 0
    text = {1: "up", -1: "down", 0: "mixed"}[bias]
    return {"tf": s.tf, "bias": bias, "text": f"{s.tf} {text} (close {px:,.1f} vs EMA21 {e21:,.1f})"}


# ---------------------------------------------------------------------------
# plan construction
# ---------------------------------------------------------------------------

def _session_end(t: datetime, mcx: bool) -> datetime:
    return t.replace(hour=23, minute=25, second=0, microsecond=0) if mcx else t.replace(hour=15, minute=25, second=0, microsecond=0)


def _levels(s: Series, i: int, side: str, prm: dict[str, Any] | None = None) -> dict[str, Any]:
    """Entry zone, stop and targets for `side` at bar i (all on the underlying's price scale)."""
    prm = prm or DEFAULT_PARAMS
    sl_lo, sl_hi, t1_r, t2_r = prm["sl_min_atr"], prm["sl_max_atr"], prm["t1_r"], prm["t2_r"]
    px, atr = s.c[i], s.atr[i]
    highs, lows = s.pivots(i, lookback=60)
    if side == "BUY":
        supports = [x for x in [s.vwap[i] if s.tf != "1D" else None, s.e21[i]] + lows if x is not None and x < px and px - x <= 2.0 * atr]
        support = max(supports) if supports else px - 0.6 * atr
        extended = px - support > (0.3 if prm["pullback_only"] else 1.0) * atr
        entry_hi = support + 0.3 * atr if extended else px
        entry_lo = max(support, entry_hi - 0.6 * atr)
        if entry_lo >= entry_hi:
            entry_lo = entry_hi - 0.25 * atr
        ref = (entry_lo + entry_hi) / 2
        below = [x for x in lows if x < entry_lo]
        sl = (max(below) if below else entry_lo - 0.6 * atr) - 0.1 * atr
        risk = min(max(ref - sl, sl_lo * atr), sl_hi * atr)
        sl = ref - risk
        res = [x for x in highs if x > ref + 0.8 * risk]
        t1 = min(ref + t1_r * risk, min(res)) if res else ref + t1_r * risk
        t2 = ref + t2_r * risk
    else:
        resist = [x for x in [s.vwap[i] if s.tf != "1D" else None, s.e21[i]] + highs if x is not None and x > px and x - px <= 2.0 * atr]
        resistance = min(resist) if resist else px + 0.6 * atr
        extended = resistance - px > (0.3 if prm["pullback_only"] else 1.0) * atr
        entry_lo = resistance - 0.3 * atr if extended else px
        entry_hi = min(resistance, entry_lo + 0.6 * atr)
        if entry_hi <= entry_lo:
            entry_hi = entry_lo + 0.25 * atr
        ref = (entry_lo + entry_hi) / 2
        above = [x for x in highs if x > entry_hi]
        sl = (min(above) if above else entry_hi + 0.6 * atr) + 0.1 * atr
        risk = min(max(sl - ref, sl_lo * atr), sl_hi * atr)
        sl = ref + risk
        sup = [x for x in lows if x < ref - 0.8 * risk]
        t1 = max(ref - t1_r * risk, max(sup)) if sup else ref - t1_r * risk
        t2 = ref - t2_r * risk
    return {"entry_low": entry_lo, "entry_high": entry_hi, "entry": ref, "stop_loss": sl, "target_1": t1, "target_2": t2,
            "risk": risk, "atr": atr, "wait_for_pullback": extended}


def build_plan(horizon: str, series: dict[str, Series], at_index: int | None = None, mcx: bool = False,
               news_bias: float = 0.0, params: dict[str, Any] | None = None) -> dict[str, Any]:
    """Plan for one horizon. `series` maps timeframe -> Series. `news_bias` in [-100, 100] nudges the score (max 10%)."""
    cfg = HORIZONS[horizon]
    prm = {**params_for(horizon), **(params or {})}
    gate = float(prm["gate"])
    s = series.get(cfg["tf"])
    if s is None or len(s) < 60:
        return {"horizon": horizon, "label": cfg["label"], "timeframe": cfg["tf"], "available": False,
                "reason": f"Need at least 60 {cfg['tf']} candles from Upstox, got {0 if s is None else len(s)}"}
    i = len(s) - 1 if at_index is None else at_index
    t = s.t[i]
    bar_close = s.close_t[i]
    sc = _score(s, i)
    total = _clamp(sc["total"] + 0.1 * max(-100.0, min(100.0, news_bias)))
    htf = [_htf_bias(series.get(tf), bar_close) for tf in cfg["htf"]]
    htf_sum = sum(h["bias"] for h in htf)

    decision, reason = "NO_TRADE", ""
    up_ok = all(h["bias"] > 0 for h in htf) if prm["strict_htf"] else (htf_sum > 0 or (htf_sum == 0 and all(h["bias"] >= 0 for h in htf)))
    dn_ok = all(h["bias"] < 0 for h in htf) if prm["strict_htf"] else (htf_sum < 0 or (htf_sum == 0 and all(h["bias"] <= 0 for h in htf)))
    if total >= gate:
        decision, reason = ("BUY", "") if up_ok else ("NO_TRADE", "higher timeframes do not confirm the long side")
    elif total <= -gate:
        decision, reason = ("SELL", "") if dn_ok else ("NO_TRADE", "higher timeframes do not confirm the short side")
    else:
        reason = f"score {total:+.0f} is inside the ±{gate:.0f} no-trade band"

    end = _session_end(t, mcx)
    tf_step = timedelta(minutes=TF_MIN[cfg["tf"]])
    valid_until = min(bar_close + tf_step * cfg["validity_bars"], end)
    if horizon != "swing" and (end - bar_close) < tf_step * max(3, cfg["validity_bars"] // 2):
        decision, reason = "NO_TRADE", "too close to the session close for a new trade"

    plan: dict[str, Any] = {
        "horizon": horizon, "label": cfg["label"], "timeframe": cfg["tf"], "hold": cfg["hold"], "available": True,
        "decision": decision, "score": round(total, 1), "gate": gate, "factors": sc["scores"], "inputs": sc["inputs"],
        "higher_timeframes": htf, "as_of": t.isoformat(), "reason": reason,
    }
    if decision in ("BUY", "SELL"):
        lv = _levels(s, i, decision, prm)
        plan.update({k: round(v, 2) if isinstance(v, float) else v for k, v in lv.items()})
        plan["valid_until"] = valid_until.isoformat()
        plan["time_stop_bars"] = cfg["time_stop_bars"]
        plan["time_stop_at_latest"] = min(valid_until + tf_step * cfg["time_stop_bars"], end).isoformat()
        plan["rr_t1"] = round(abs(lv["target_1"] - lv["entry"]) / lv["risk"], 2) if lv["risk"] else None
        plan["instructions"] = _instructions(plan)
    return plan


def _instructions(p: dict[str, Any]) -> str:
    side = p["decision"]
    zone = f"{p['entry_low']:,.2f}-{p['entry_high']:,.2f}"
    until = datetime.fromisoformat(p["valid_until"]).strftime("%H:%M")
    wait = "Wait for a pullback into " if p.get("wait_for_pullback") else ""
    verb = "Buy" if side == "BUY" else "Sell"
    return (f"{wait}{verb} in {zone} until {until} IST; skip the trade if price does not trade there by then. "
            f"Stop loss {p['stop_loss']:,.2f}; book part at T1 {p['target_1']:,.2f}, trail the rest to T2 {p['target_2']:,.2f}. "
            f"Exit after {p['time_stop_bars']} {p['timeframe']} bars if T1 has not come.")


def option_levels(plan: dict[str, Any], contract: dict[str, Any] | None, spot: float) -> dict[str, Any] | None:
    """Translate underlying levels into option-premium levels using the contract's delta and gamma (Taylor, 2nd order)."""
    if not contract or plan.get("decision") not in ("BUY", "SELL"):
        return None
    try:
        ltp = float(contract.get("ltp") or 0)
        delta = float(contract.get("delta") or 0)
        gamma = float(contract.get("gamma") or 0)
    except (TypeError, ValueError):
        return None
    if ltp <= 0 or delta == 0:
        return None

    def prem(level: float) -> float:
        d = level - spot
        return round(max(0.05, ltp + delta * d + 0.5 * gamma * d * d), 2)

    lo, hi = sorted((prem(plan["entry_low"]), prem(plan["entry_high"])))
    return {"symbol": contract.get("symbol") or contract.get("trading_symbol"), "instrument_key": contract.get("instrument_key"),
            "strike": contract.get("strike"), "option_type": contract.get("option_type"), "ltp": ltp, "delta": delta,
            "entry_low": lo, "entry_high": hi, "stop_loss": prem(plan["stop_loss"]), "target_1": prem(plan["target_1"]),
            "target_2": prem(plan["target_2"]),
            "basis": f"premium ≈ LTP {ltp:,.2f} + delta {delta:+.2f} × move + ½ gamma × move² (theta and IV changes not included)"}


# ---------------------------------------------------------------------------
# backtest
# ---------------------------------------------------------------------------

def backtest(horizon: str, series: dict[str, Series], mcx: bool = False, step: int = 1, max_signals: int = 400,
             params: dict[str, Any] | None = None, start: int = 60, stop: int | None = None) -> dict[str, Any]:
    """Replay `horizon` over the loaded history. One open idea at a time; same-bar SL/T1 counts as a loss."""
    cfg = HORIZONS[horizon]
    s = series.get(cfg["tf"])
    if s is None or len(s) < 120:
        return {"horizon": horizon, "available": False, "reason": "not enough history"}
    trades: list[dict[str, Any]] = []
    i = max(60, start)
    end_i = min(len(s) - 2, stop if stop is not None else len(s) - 2)
    while i < end_i and len(trades) < max_signals:
        p = build_plan(horizon, series, at_index=i, mcx=mcx, params=params)
        if p.get("decision") not in ("BUY", "SELL"):
            i += step
            continue
        res = _simulate(p, s, i, cfg)
        trades.append(res)
        i = max(i + step, res["exit_index"] + 1)
    filled = [t for t in trades if t["outcome"] != "NOT_FILLED"]
    wins = [t for t in filled if t["outcome"] in ("T1", "T2")]
    r_vals = [t["r"] for t in filled]
    days = sorted({str(s.t[k].date()) for k in range(len(s))})
    return {
        "horizon": horizon, "timeframe": cfg["tf"], "available": True, "from": days[0] if days else None, "to": days[-1] if days else None,
        "signals": len(trades), "filled": len(filled), "fill_rate": round(len(filled) / len(trades) * 100, 1) if trades else None,
        "t1_hit_rate": round(len(wins) / len(filled) * 100, 1) if filled else None,
        "t2_hit_rate": round(sum(1 for t in filled if t["outcome"] == "T2") / len(filled) * 100, 1) if filled else None,
        "stopped": sum(1 for t in filled if t["outcome"] == "SL"), "time_exits": sum(1 for t in filled if t["outcome"] == "TIME"),
        "expectancy_r": round(sum(r_vals) / len(r_vals), 3) if r_vals else None,
        "rule": "T1 before stop loss after the entry zone was touched; same-bar touches of both count as a loss",
        "recent": trades[-15:],
    }


def _simulate(p: dict[str, Any], s: Series, i: int, cfg: dict[str, Any]) -> dict[str, Any]:
    buy = p["decision"] == "BUY"
    valid_until = datetime.fromisoformat(p["valid_until"])
    j, fill_j, fill = i + 1, None, None
    while j < len(s) and s.t[j] < valid_until:
        if (buy and s.l[j] <= p["entry_high"]) or (not buy and s.h[j] >= p["entry_low"]):
            fill_j = j
            fill = min(s.o[j], p["entry_high"]) if buy else max(s.o[j], p["entry_low"])
            break
        j += 1
    base = {"time": s.t[i].isoformat(), "side": p["decision"], "entry_low": p["entry_low"], "entry_high": p["entry_high"],
            "stop_loss": p["stop_loss"], "target_1": p["target_1"], "target_2": p["target_2"]}
    if fill_j is None:
        return {**base, "outcome": "NOT_FILLED", "r": 0.0, "exit_index": j}
    risk = abs(fill - p["stop_loss"]) or p["risk"]
    hit_t1 = False
    end = min(len(s) - 1, fill_j + cfg["time_stop_bars"])
    for k in range(fill_j, end + 1):
        lo_, hi_ = s.l[k], s.h[k]
        stop_hit = lo_ <= p["stop_loss"] if buy else hi_ >= p["stop_loss"]
        t1_hit = hi_ >= p["target_1"] if buy else lo_ <= p["target_1"]
        t2_hit = hi_ >= p["target_2"] if buy else lo_ <= p["target_2"]
        if not hit_t1:
            if stop_hit:
                return {**base, "fill": round(fill, 2), "outcome": "SL", "r": -1.0, "exit_index": k}
            if t1_hit:
                hit_t1 = True
                if t2_hit:
                    r = 0.5 * abs(p["target_1"] - fill) / risk + 0.5 * abs(p["target_2"] - fill) / risk
                    return {**base, "fill": round(fill, 2), "outcome": "T2", "r": round(r, 2), "exit_index": k}
                continue
        else:
            # after T1, half is booked and the stop moves to entry for the rest
            if (lo_ <= fill) if buy else (hi_ >= fill):
                return {**base, "fill": round(fill, 2), "outcome": "T1", "r": round(0.5 * abs(p["target_1"] - fill) / risk, 2), "exit_index": k}
            if t2_hit:
                r = 0.5 * abs(p["target_1"] - fill) / risk + 0.5 * abs(p["target_2"] - fill) / risk
                return {**base, "fill": round(fill, 2), "outcome": "T2", "r": round(r, 2), "exit_index": k}
    last = s.c[end]
    move = (last - fill) if buy else (fill - last)
    if hit_t1:
        return {**base, "fill": round(fill, 2), "outcome": "T1", "r": round(0.5 * abs(p["target_1"] - fill) / risk + 0.5 * move / risk, 2), "exit_index": end}
    return {**base, "fill": round(fill, 2), "outcome": "TIME", "r": round(move / risk, 2), "exit_index": end}

def evaluate_live(plan: dict[str, Any], one_min: Series, now: datetime) -> dict[str, Any]:
    """Outcome of a recorded plan from 1-minute candles after it was issued (same rules as the backtest, by clock time).

    Returns status: PENDING (zone not touched yet, still valid), EXPIRED (zone never touched), OPEN (filled, running),
    T1 / T2 (target reached; stop moves to entry after T1), SL (stopped before T1), TIME (time stop hit)."""
    buy = plan["side"] == "BUY"
    issued = datetime.fromisoformat(plan["created_at"]).astimezone(IST)
    valid_until = datetime.fromisoformat(plan["valid_until"]).astimezone(IST)
    tf_min = TF_MIN.get(plan["timeframe"], 5)
    fill_t, fill, hit_t1 = None, None, False
    res: dict[str, Any] = {"status": "PENDING"}
    for k in range(len(one_min)):
        t = one_min.t[k]
        if t < issued:
            continue
        lo_, hi_, o_ = one_min.l[k], one_min.h[k], one_min.o[k]
        if fill_t is None:
            if t >= valid_until:
                return {"status": "EXPIRED", "closed_at": valid_until.isoformat()}
            if (buy and lo_ <= plan["entry_high"]) or (not buy and hi_ >= plan["entry_low"]):
                fill_t = t
                fill = min(o_, plan["entry_high"]) if buy else max(o_, plan["entry_low"])
                res = {"status": "OPEN", "fill_price": round(fill, 2), "filled_at": t.isoformat()}
            else:
                continue
        risk = abs(fill - plan["stop_loss"]) or 1e-6
        time_stop = min(fill_t + timedelta(minutes=tf_min * int(plan["time_stop_bars"])),
                        datetime.fromisoformat(plan["time_stop_at_latest"]).astimezone(IST))
        stop_hit = lo_ <= plan["stop_loss"] if buy else hi_ >= plan["stop_loss"]
        t1_hit = hi_ >= plan["target_1"] if buy else lo_ <= plan["target_1"]
        t2_hit = hi_ >= plan["target_2"] if buy else lo_ <= plan["target_2"]
        part1 = abs(plan["target_1"] - fill) / risk
        if not hit_t1:
            if stop_hit:
                return {**res, "status": "SL", "exit_price": plan["stop_loss"], "closed_at": t.isoformat(), "r": -1.0}
            if t1_hit:
                hit_t1 = True
                res = {**res, "status": "OPEN", "t1_at": t.isoformat()}
                if t2_hit:
                    return {**res, "status": "T2", "exit_price": plan["target_2"], "closed_at": t.isoformat(),
                            "r": round(0.5 * part1 + 0.5 * abs(plan["target_2"] - fill) / risk, 2)}
                continue
        else:
            if (lo_ <= fill) if buy else (hi_ >= fill):
                return {**res, "status": "T1", "exit_price": round(fill, 2), "closed_at": t.isoformat(), "r": round(0.5 * part1, 2)}
            if t2_hit:
                return {**res, "status": "T2", "exit_price": plan["target_2"], "closed_at": t.isoformat(),
                        "r": round(0.5 * part1 + 0.5 * abs(plan["target_2"] - fill) / risk, 2)}
        if t >= time_stop:
            move = (one_min.c[k] - fill) if buy else (fill - one_min.c[k])
            r = (0.5 * part1 + 0.5 * move / risk) if hit_t1 else move / risk
            return {**res, "status": "T1" if hit_t1 else "TIME", "exit_price": one_min.c[k], "closed_at": t.isoformat(), "r": round(r, 2)}
    if fill_t is None and now >= valid_until:
        return {"status": "EXPIRED", "closed_at": valid_until.isoformat()}
    return res
