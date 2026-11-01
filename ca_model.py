"""CA Trader backtested signal model.

Same maths as the CA Trader Terminal's signal web and the Model Lab's backtest
(train Sep 2022 - Dec 2024, tested on unseen 2025-26 data). Parameters live in
ca_model_params.json next to this file; the Model Lab's daily run updates that
file when an approved proposal changes the model.

Exposed through mcp_server.py as the `get_model_signal` connector tool and the
GET /api/model/signal/{instrument} route.
"""
from __future__ import annotations

import asyncio
import json
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

PARAMS_PATH = Path(os.getenv("CA_MODEL_PARAMS") or Path(__file__).with_name("ca_model_params.json"))
VIX_KEY = "NSE_INDEX|India VIX"
BANKS = {"HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK", "INDUSINDBK"}
CANDLE_TTL = 300  # seconds

_params_cache: dict[str, Any] = {"mtime": None, "data": None}
_candle_cache: dict[str, tuple[float, pd.DataFrame]] = {}


def load_params() -> dict[str, Any]:
    mtime = PARAMS_PATH.stat().st_mtime
    if _params_cache["mtime"] != mtime:
        _params_cache["data"] = json.loads(PARAMS_PATH.read_text(encoding="utf-8"))
        _params_cache["mtime"] = mtime
    return _params_cache["data"]


def _frame(candles: list[dict[str, Any]]) -> pd.DataFrame:
    df = pd.DataFrame(candles)
    if df.empty:
        return df
    df["date"] = (pd.to_datetime(df["timestamp"], utc=True) + pd.Timedelta(hours=5, minutes=30)).dt.tz_localize(None).dt.normalize()
    df = df.drop_duplicates("date", keep="last").set_index("date")
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def _ema(s: pd.Series, n: int) -> pd.Series:
    return s.ewm(span=n, adjust=False).mean()


def _rsi(s: pd.Series, n: int = 14) -> pd.Series:
    d = s.diff()
    g = d.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    l = (-d.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    return 100 - 100 / (1 + g / l)


def _f(x: Any) -> float | None:
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return x if np.isfinite(x) else None


def raw_criteria(sym: str, df: pd.DataFrame, nifty: pd.DataFrame, bank: pd.DataFrame, vix: pd.DataFrame, breadth: float | None) -> dict[str, float | None]:
    """The 14 raw criteria for the last row of df. Pure function (no I/O)."""
    c = df.close
    t = df.index[-1]
    r = _rsi(c).iloc[-1]
    hi, lo, op, vol = df.high.iloc[-1], df.low.iloc[-1], df.open.iloc[-1], df.volume.iloc[-1]
    ret1 = c.pct_change().iloc[-1]
    raw: dict[str, float | None] = {
        "rsi": -0.4 if r > 75 else 0.4 if r < 25 else float(np.clip((r - 50) / 20, -1, 1)),
        "daychg": float(np.clip(ret1 * 100 / 1.5, -1, 1)),
        "rev5": _f(-c.pct_change(5).iloc[-1]),
        "bollb": _f(-((c.iloc[-1] - c.tail(20).mean()) / (2 * c.tail(20).std()))),
        "clv": _f(((c.iloc[-1] - lo) - (hi - c.iloc[-1])) / (hi - lo)) if hi > lo else None,
        "gap": _f(op / c.iloc[-2] - 1),
        "hi52": _f(c.iloc[-1] / c.tail(252).max() - 1) if len(c) >= 120 else None,
        "volspike": _f(np.sign(ret1) * np.clip(vol / df.volume.tail(20).mean() - 1, -1, 3)) if vol > 0 else None,
        "breadth": _f(breadth),
    }
    down = (c.diff() < 0).astype(int)
    k = 0
    while k < len(down) - 1 and down.iloc[-1 - k] == 1:
        k += 1
    raw["downstreak"] = float(k)
    n20 = nifty.close.pct_change(20)
    raw["sector"] = _f((bank.close.pct_change(20).get(t, np.nan) - n20.get(t, np.nan)) * (1 if sym in BANKS else 0)) if t in bank.index and t in nifty.index else None
    vz = (vix.close - vix.close.rolling(60).mean()) / vix.close.rolling(60).std()
    raw["vix_z"] = _f(-vz.get(t, np.nan)) if t in vix.index else None
    raw["vix_spike"] = _f(-vix.close.pct_change(5).get(t, np.nan)) if t in vix.index else None
    raw["mkt_regime"] = _f(np.sign(nifty.close.get(t, np.nan) / _ema(nifty.close, 200).get(t, np.nan) - 1)) if t in nifty.index else None
    return raw


def score(P: dict[str, Any], raw: dict[str, float | None]) -> dict[str, Any]:
    """Standardise with training-period mean/sd, weight by training IC, threshold at the training 20/80 percentiles."""
    total = sum(abs(v["w"]) for v in P["criteria"].values())
    crit: dict[str, Any] = {}
    num = den = 0.0
    for key, p in P["criteria"].items():
        x = raw.get(key)
        if x is None:
            crit[key] = {"raw": None, "z": None, "weight": round(abs(p["w"]) / total, 4)}
            continue
        z = float(np.clip((x - p["mu"]) / p["sd"], -3, 3) / 3)
        crit[key] = {"raw": round(x, 5), "z": round(z, 4), "bullish": round(z * np.sign(p["w"]), 4), "weight": round(abs(p["w"]) / total, 4)}
        num += z * p["w"]
        den += abs(p["w"])
    s = num / den if den >= 0.6 * total else None
    verdict = None if s is None else "BUY" if s > P["hi"] else "SELL" if s < P["lo"] else "HOLD"
    pct = None if s is None else int(np.clip(np.searchsorted(P["quantiles"], s, side="right") - 1, 0, 100))
    return {"score": None if s is None else round(s, 4), "verdict": verdict, "percentile": pct, "coverage": round(den / total, 3), "criteria": crit}


async def _daily(core: Any, symbol: str, days: int, user: dict[str, Any]) -> pd.DataFrame:
    hit = _candle_cache.get(f"{symbol}:{days}")
    if hit and time.time() - hit[0] < CANDLE_TTL:
        return hit[1]
    res = await core.market_candles(symbol, timeframe="1D", days=days, user=user)
    if hasattr(res, "body"):  # a JSONResponse error from the route
        res = json.loads(bytes(res.body).decode("utf-8"))
    df = _frame((res or {}).get("candles") or [])
    _candle_cache[f"{symbol}:{days}"] = (time.time(), df)
    return df


async def _breadth(core: Any, universe: list[str], user: dict[str, Any]) -> float | None:
    try:
        res = await core.market_quotes(instruments=",".join(universe), user=user)
        items = (res or {}).get("items") or []
        ch = [i.get("change_pct") for i in items if i.get("change_pct") is not None]
        if not ch:
            return None
        return (sum(1 for x in ch if x > 0) - sum(1 for x in ch if x < 0)) / len(ch)
    except Exception:
        return None


async def model_signal(core: Any, symbol: str, user: dict[str, Any]) -> dict[str, Any]:
    P = load_params()
    sym = symbol.upper() if "|" not in symbol else symbol
    stock, nifty, bank, vix, breadth = await asyncio.gather(
        _daily(core, sym, 420, user), _daily(core, "NIFTY", 420, user), _daily(core, "BANKNIFTY", 420, user),
        _daily(core, VIX_KEY, 200, user), _breadth(core, P.get("universe") or [], user))
    if len(stock) < 30 or len(nifty) < 30 or len(vix) < 30:
        return {"symbol": sym, "available": False, "reason": "Not enough daily history from Upstox for this symbol", "model_version": P.get("version")}
    raw = raw_criteria(sym, stock, nifty, bank, vix, breadth)
    out = score(P, raw)
    t = P["stats"]["improved"]["test"]
    out.update({
        "symbol": sym, "available": True, "as_of": str(stock.index[-1].date()), "close": float(stock.close.iloc[-1]),
        "model_version": P.get("version"), "built": P.get("built"),
        "thresholds": {"buy_above": P["hi"], "sell_below": P["lo"]},
        "in_training_universe": sym in (P.get("universe") or []),
        "backtest_unseen": {"period": P.get("test"), "buy_avg10": t["BUY"]["avg10"], "sell_avg10": t["SELL"]["avg10"],
                            "all_days_avg10": P.get("base10", {}).get("test"), "buy_hit5": t["BUY"]["hit5"], "sell_hit5": t["SELL"]["hit5"]},
        "note": "Composite of mean-reversion, flow and market-risk criteria backtested on Nifty large caps. Small edge; for paper trading and study, not investment advice.",
    })
    return out
