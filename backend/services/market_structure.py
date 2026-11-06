"""Technical-analysis pack: indicators, candlestick patterns (live and back-tested), chart patterns and option-chain structure.

Every function is pure (lists in, dicts out), uses only closed candles the caller passes in, and returns plain-language readings so a
beginner can see what each number means. Nothing here places or changes a trade; it explains and cross-checks the call.

Candle input: dict of equal-length lists  {"t": [...], "o": [...], "h": [...], "l": [...], "c": [...], "v": [...]}
"""
from __future__ import annotations

import math
from typing import Any

# ---------------------------------------------------------------- helpers


def _ema(x: list[float], n: int) -> list[float]:
    if not x:
        return []
    k, out = 2 / (n + 1), [x[0]]
    for v in x[1:]:
        out.append(v * k + out[-1] * (1 - k))
    return out


def _sma(x: list[float], n: int) -> list[float | None]:
    out: list[float | None] = []
    run = 0.0
    for i, v in enumerate(x):
        run += v
        if i >= n:
            run -= x[i - n]
        out.append(run / n if i >= n - 1 else None)
    return out


def _wilder(x: list[float], n: int) -> list[float]:
    if not x:
        return []
    out = [x[0]]
    for v in x[1:]:
        out.append((out[-1] * (n - 1) + v) / n)
    return out


def _tr(h: list[float], l: list[float], c: list[float]) -> list[float]:
    return [h[0] - l[0]] + [max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1])) for i in range(1, len(c))]


def _rsi(c: list[float], n: int = 14) -> list[float]:
    if len(c) < 2:
        return [50.0] * len(c)
    up = [0.0] + [max(0.0, c[i] - c[i - 1]) for i in range(1, len(c))]
    dn = [0.0] + [max(0.0, c[i - 1] - c[i]) for i in range(1, len(c))]
    au, ad = _wilder(up, n), _wilder(dn, n)
    return [100.0 if d == 0 else 100 - 100 / (1 + u / d) for u, d in zip(au, ad)]


def _r(v: float | None, p: int = 2) -> float | None:
    return None if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))) else round(float(v), p)


def _bias(score: int) -> str:
    return "bullish" if score > 0 else "bearish" if score < 0 else "neutral"


# ---------------------------------------------------------------- indicators


def indicators(d: dict[str, list]) -> dict[str, Any]:
    """The usual indicator set with what each one says right now. `vote` is +1 bullish, -1 bearish, 0 neutral."""
    o, h, l, c, v = d["o"], d["h"], d["l"], d["c"], d.get("v") or [0] * len(d["c"])
    n = len(c)
    if n < 30:
        return {"available": False, "reason": f"Only {n} candles; at least 30 are needed"}
    px = c[-1]
    rows: list[dict[str, Any]] = []

    def add(name: str, group: str, value: Any, vote: int, reading: str, meaning: str) -> None:
        rows.append({"name": name, "group": group, "value": value, "vote": vote, "bias": _bias(vote), "reading": reading, "meaning": meaning})

    e9, e21, e50 = _ema(c, 9), _ema(c, 21), _ema(c, 50)
    add("EMA 9 / 21", "Trend", f"{_r(e9[-1])} / {_r(e21[-1])}", 1 if e9[-1] > e21[-1] else -1,
        "9 above 21: short-term trend up" if e9[-1] > e21[-1] else "9 below 21: short-term trend down",
        "Moving averages smooth the price. When the faster one is above the slower one, buyers are in control.")
    add("EMA 50", "Trend", _r(e50[-1]), 1 if px > e50[-1] else -1, "Price above the 50-average" if px > e50[-1] else "Price below the 50-average",
        "The 50-average is the medium-term trend line. Trading above it is healthier for buyers.")
    if n >= 200:
        e200 = _ema(c, 200)
        add("EMA 200", "Trend", _r(e200[-1]), 1 if px > e200[-1] else -1, "Above the 200-average: long-term uptrend" if px > e200[-1] else "Below the 200-average: long-term downtrend",
            "The 200-average separates long-term bull and bear markets.")
    rsi = _rsi(c)
    rv = rsi[-1]
    add("RSI (14)", "Momentum", _r(rv, 1), 1 if 55 <= rv < 70 else -1 if 30 < rv <= 45 else 0,
        "Overbought: may pause or pull back" if rv >= 70 else "Oversold: may bounce" if rv <= 30 else "Strong, buyers ahead" if rv >= 55 else "Weak, sellers ahead" if rv <= 45 else "Balanced",
        "RSI measures how fast price moved. Above 70 is stretched up, below 30 is stretched down, 45 to 55 is a tug of war.")
    ef, es = _ema(c, 12), _ema(c, 26)
    macd = [a - b for a, b in zip(ef, es)]
    sig = _ema(macd, 9)
    hist = macd[-1] - sig[-1]
    add("MACD (12, 26, 9)", "Momentum", f"{_r(macd[-1])} / {_r(sig[-1])}", 1 if hist > 0 else -1,
        "MACD above signal and " + ("rising" if hist > macd[-2] - sig[-2] else "fading") if hist > 0 else "MACD below signal and " + ("falling" if hist < macd[-2] - sig[-2] else "recovering"),
        "MACD compares two moving averages. Above its signal line, momentum favours buyers.")
    # stochastic
    k_raw = []
    for i in range(n):
        lo, hi = min(l[max(0, i - 13):i + 1]), max(h[max(0, i - 13):i + 1])
        k_raw.append(100 * (c[i] - lo) / (hi - lo) if hi > lo else 50.0)
    kk = _sma(k_raw, 3)
    st = kk[-1] if kk[-1] is not None else k_raw[-1]
    add("Stochastic (14, 3)", "Momentum", _r(st, 1), -1 if st >= 80 else 1 if st <= 20 else 0, "Overbought zone" if st >= 80 else "Oversold zone" if st <= 20 else "Mid range",
        "Shows where price closed inside its recent range. Above 80 means near the top of the range, below 20 near the bottom.")
    # CCI
    tp = [(a + b + cc) / 3 for a, b, cc in zip(h, l, c)]
    sm = _sma(tp, 20)
    if sm[-1] is not None:
        md = sum(abs(x - sm[-1]) for x in tp[-20:]) / 20
        cci = (tp[-1] - sm[-1]) / (0.015 * md) if md else 0.0
        add("CCI (20)", "Momentum", _r(cci, 0), 1 if 0 < cci < 200 else -1 if -200 < cci < 0 else 0, "Above zero: price above its average" if cci > 0 else "Below zero: price below its average",
            "CCI measures how far price is from its recent average. Beyond ±100 is a strong move; beyond ±200 is stretched.")
    # Williams %R
    lo14, hi14 = min(l[-14:]), max(h[-14:])
    wr = -100 * (hi14 - px) / (hi14 - lo14) if hi14 > lo14 else -50.0
    add("Williams %R (14)", "Momentum", _r(wr, 1), -1 if wr > -20 else 1 if wr < -80 else 0, "Near the top of the range" if wr > -20 else "Near the bottom of the range" if wr < -80 else "Middle of the range",
        "Like Stochastic, upside down: −20 to 0 is overbought, −100 to −80 is oversold.")
    # Bollinger
    sma20 = _sma(c, 20)[-1]
    sd = math.sqrt(sum((x - sma20) ** 2 for x in c[-20:]) / 20) if sma20 else 0.0
    up, lo = sma20 + 2 * sd, sma20 - 2 * sd
    pb = (px - lo) / (up - lo) if up > lo else 0.5
    bw = (up - lo) / sma20 * 100 if sma20 else 0
    add("Bollinger Bands (20, 2)", "Volatility", f"%B {_r(pb, 2)} · width {_r(bw, 2)}%", -1 if pb > 1 else 1 if pb < 0 else 0,
        "Price outside the upper band: stretched" if pb > 1 else "Price outside the lower band: stretched" if pb < 0 else "Price near the upper band" if pb > 0.8 else "Price near the lower band" if pb < 0.2 else "Price inside the bands",
        "Bands show the normal price range (about 95% of the time). Narrow bands often come before a big move.")
    # ATR
    atr = _wilder(_tr(h, l, c), 14)[-1]
    add("ATR (14)", "Volatility", f"{_r(atr)} ({_r(atr / px * 100, 2)}% of price)", 0, "The usual candle range", "ATR is the typical size of a candle. Stop-losses are sized in ATR so they are not hit by normal noise.")
    # ADX / DI
    trs = _tr(h, l, c)
    pdm = [0.0] + [max(h[i] - h[i - 1], 0) if (h[i] - h[i - 1]) > (l[i - 1] - l[i]) else 0.0 for i in range(1, n)]
    ndm = [0.0] + [max(l[i - 1] - l[i], 0) if (l[i - 1] - l[i]) > (h[i] - h[i - 1]) else 0.0 for i in range(1, n)]
    atr_s, p_s, n_s = _wilder(trs, 14), _wilder(pdm, 14), _wilder(ndm, 14)
    pdi = [100 * a / b if b else 0 for a, b in zip(p_s, atr_s)]
    ndi = [100 * a / b if b else 0 for a, b in zip(n_s, atr_s)]
    dx = [100 * abs(a - b) / (a + b) if (a + b) else 0 for a, b in zip(pdi, ndi)]
    adx = _wilder(dx, 14)[-1]
    add("ADX (14)", "Trend", f"{_r(adx, 1)} · +DI {_r(pdi[-1], 1)} · −DI {_r(ndi[-1], 1)}", (1 if pdi[-1] > ndi[-1] else -1) if adx >= 20 else 0,
        ("Strong " + ("up" if pdi[-1] > ndi[-1] else "down") + "trend") if adx >= 25 else "Trend is forming" if adx >= 20 else "No trend: sideways market",
        "ADX measures how strong a trend is, not its direction. Below 20 the market is choppy and trend signals fail more often.")
    # Supertrend (10, 3)
    atr10 = _wilder(trs, 10)
    fu, fl, trend = 0.0, 0.0, 1
    for i in range(n):
        mid = (h[i] + l[i]) / 2
        bu, bl = mid + 3 * atr10[i], mid - 3 * atr10[i]
        if i == 0:
            fu, fl = bu, bl
            continue
        fu = bu if (bu < fu or c[i - 1] > fu) else fu
        fl = bl if (bl > fl or c[i - 1] < fl) else fl
        trend = 1 if c[i] > fu else -1 if c[i] < fl else trend
    add("Supertrend (10, 3)", "Trend", _r(fl if trend == 1 else fu), trend, "Buy mode: the line trails below price" if trend == 1 else "Sell mode: the line trails above price",
        "Supertrend flips when price closes beyond a volatility-based line. It is a simple trend-follower with a built-in stop level.")
    # VWAP (session cumulative for the series given) + volume tools
    if sum(v) > 0:
        pv = sum(((hh + ll + cc) / 3) * vv for hh, ll, cc, vv in zip(h[-75:], l[-75:], c[-75:], v[-75:]))
        vs = sum(v[-75:])
        vwap = pv / vs if vs else px
        add("VWAP (recent session)", "Volume", _r(vwap), 1 if px > vwap else -1, "Price above the average traded price: buyers in profit" if px > vwap else "Price below the average traded price: sellers in profit",
            "VWAP is the average price weighted by volume. Big players use it as a fair-value line.")
        obv = [0.0]
        for i in range(1, n):
            obv.append(obv[-1] + (v[i] if c[i] > c[i - 1] else -v[i] if c[i] < c[i - 1] else 0))
        ob_sl = obv[-1] - obv[-10]
        add("OBV (10 bars)", "Volume", _r(ob_sl, 0), 1 if ob_sl > 0 else -1 if ob_sl < 0 else 0, "Volume is flowing in" if ob_sl > 0 else "Volume is flowing out" if ob_sl < 0 else "Flat",
            "On-Balance Volume adds volume on up candles and subtracts it on down candles. If it rises with price, the move is backed by real buying.")
        avg_v = sum(v[-21:-1]) / 20 if len(v) > 21 else 0
        if avg_v:
            rv_x = v[-1] / avg_v
            add("Relative volume", "Volume", f"{_r(rv_x, 2)}x", (1 if c[-1] > o[-1] else -1) if rv_x >= 1.5 else 0, "Heavy volume on this candle" if rv_x >= 1.5 else "Normal volume" if rv_x >= 0.7 else "Thin volume",
                "How busy this candle was compared with the last 20. A move on heavy volume is more trustworthy.")
    # pivots from the previous completed day-ish block (last 75 bars when intraday, else last bar)
    ph, pl, pc = max(h[-150:-75] or h[-75:]), min(l[-150:-75] or l[-75:]), c[-76] if n > 76 else c[-2]
    pp = (ph + pl + pc) / 3
    levels = {"R2": pp + (ph - pl), "R1": 2 * pp - pl, "Pivot": pp, "S1": 2 * pp - ph, "S2": pp - (ph - pl)}
    nearest = min(levels.items(), key=lambda kv: abs(kv[1] - px))
    add("Pivot points", "Levels", " · ".join(f"{k} {_r(x)}" for k, x in levels.items()), 1 if px > pp else -1, f"Price is {'above' if px > pp else 'below'} the pivot; nearest level {nearest[0]} {_r(nearest[1])}",
        "Pivots are levels computed from the previous period's high, low and close. Traders watch them as likely turning points.")
    # Ichimoku cloud
    if n >= 52:
        def mid(a: int, b: int) -> float:
            return (max(h[-a:]) + min(l[-a:])) / 2
        tenkan, kijun = mid(9, 9), mid(26, 26)
        span_a = (tenkan + kijun) / 2
        span_b = mid(52, 52)
        top, bot = max(span_a, span_b), min(span_a, span_b)
        add("Ichimoku cloud", "Trend", f"cloud {_r(bot)}-{_r(top)}", 1 if px > top else -1 if px < bot else 0, "Price above the cloud: bullish" if px > top else "Price below the cloud: bearish" if px < bot else "Price inside the cloud: no clear direction",
            "The cloud is a zone of support and resistance. Price above it is bullish, below it is bearish, inside it is undecided.")
    votes = [r["vote"] for r in rows]
    bull, bear = sum(1 for x in votes if x > 0), sum(1 for x in votes if x < 0)
    tot = bull + bear
    return {"available": True, "rows": rows, "bull": bull, "bear": bear, "neutral": len(votes) - tot,
            "net": round(100 * (bull - bear) / tot) if tot else 0,
            "verdict": "Most indicators lean bullish" if tot and bull / tot >= 0.65 else "Most indicators lean bearish" if tot and bear / tot >= 0.65 else "Indicators are mixed: no clear edge from them",
            "atr": _r(atr), "price": _r(px)}


# ---------------------------------------------------------------- candlestick patterns

CANDLE_PATTERNS = {
    # name: (direction, plain-language meaning)
    "Doji": (0, "Open and close are almost equal: buyers and sellers are balanced. A pause, often before a turn."),
    "Hammer": (1, "Long lower shadow after a fall: sellers pushed down but buyers took it back. Possible bottom."),
    "Inverted hammer": (1, "Long upper shadow after a fall: buyers tried to push up. Possible bottom, needs a green candle after it."),
    "Shooting star": (-1, "Long upper shadow after a rise: buyers pushed up but sellers took it back. Possible top."),
    "Hanging man": (-1, "Hammer shape after a rise: selling appeared at the top. Needs a red candle after it."),
    "Bullish marubozu": (1, "A strong green candle with almost no shadows: buyers controlled the whole period."),
    "Bearish marubozu": (-1, "A strong red candle with almost no shadows: sellers controlled the whole period."),
    "Spinning top": (0, "Small body with shadows on both sides: indecision."),
    "Bullish engulfing": (1, "A green candle that fully covers the previous red one: buyers took over."),
    "Bearish engulfing": (-1, "A red candle that fully covers the previous green one: sellers took over."),
    "Bullish harami": (1, "A small green candle inside the previous big red one: selling is losing steam."),
    "Bearish harami": (-1, "A small red candle inside the previous big green one: buying is losing steam."),
    "Piercing line": (1, "A green candle that closes above the middle of the previous red one: buyers fighting back."),
    "Dark cloud cover": (-1, "A red candle that closes below the middle of the previous green one: sellers fighting back."),
    "Morning star": (1, "Red candle, small candle, then a strong green one: a classic three-candle bottom."),
    "Evening star": (-1, "Green candle, small candle, then a strong red one: a classic three-candle top."),
    "Three white soldiers": (1, "Three strong green candles in a row, each closing higher: steady buying."),
    "Three black crows": (-1, "Three strong red candles in a row, each closing lower: steady selling."),
    "Tweezer bottom": (1, "Two candles with the same low: the level held twice. Possible bottom."),
    "Tweezer top": (-1, "Two candles with the same high: the level held twice. Possible top."),
}


def _parts(o: float, h: float, l: float, c: float) -> tuple[float, float, float, float]:
    rng = max(h - l, 1e-9)
    body = abs(c - o)
    return rng, body, h - max(o, c), min(o, c) - l


def candle_patterns_at(d: dict[str, list], i: int, atr: float) -> list[str]:
    """Patterns that complete on candle i (uses candles up to and including i only)."""
    o, h, l, c = d["o"], d["h"], d["l"], d["c"]
    if i < 5:
        return []
    out: list[str] = []
    rng, body, up, lo = _parts(o[i], h[i], l[i], c[i])
    green, red = c[i] > o[i], c[i] < o[i]
    down_trend = c[i - 1] < c[i - 4] and c[i - 4] < c[i - 5] + atr * 0.2 or c[i - 1] < c[i - 5] - atr
    up_trend = c[i - 1] > c[i - 4] and c[i - 4] > c[i - 5] - atr * 0.2 or c[i - 1] > c[i - 5] + atr
    small = body <= 0.1 * rng
    if small and rng >= 0.3 * atr:
        out.append("Doji")
    if body > 0 and lo >= 2 * body and up <= 0.3 * body + 1e-9 and rng >= 0.6 * atr:
        out.append("Hammer" if down_trend else "Hanging man" if up_trend else "")
    if body > 0 and up >= 2 * body and lo <= 0.3 * body + 1e-9 and rng >= 0.6 * atr:
        out.append("Inverted hammer" if down_trend else "Shooting star" if up_trend else "")
    if body >= 0.9 * rng and rng >= 0.8 * atr:
        out.append("Bullish marubozu" if green else "Bearish marubozu")
    if 0.1 * rng < body <= 0.3 * rng and up >= 0.25 * rng and lo >= 0.25 * rng:
        out.append("Spinning top")
    pr, pb, _, _ = _parts(o[i - 1], h[i - 1], l[i - 1], c[i - 1])
    pg, pred = c[i - 1] > o[i - 1], c[i - 1] < o[i - 1]
    big_prev = pb >= 0.6 * atr
    if green and pred and big_prev and o[i] <= c[i - 1] and c[i] >= o[i - 1] and body > pb:
        out.append("Bullish engulfing")
    if red and pg and big_prev and o[i] >= c[i - 1] and c[i] <= o[i - 1] and body > pb:
        out.append("Bearish engulfing")
    if green and pred and big_prev and o[i] > c[i - 1] and c[i] < o[i - 1] and body < 0.5 * pb:
        out.append("Bullish harami")
    if red and pg and big_prev and o[i] < c[i - 1] and c[i] > o[i - 1] and body < 0.5 * pb:
        out.append("Bearish harami")
    if green and pred and big_prev and o[i] < c[i - 1] and c[i] > (o[i - 1] + c[i - 1]) / 2 and c[i] < o[i - 1]:
        out.append("Piercing line")
    if red and pg and big_prev and o[i] > c[i - 1] and c[i] < (o[i - 1] + c[i - 1]) / 2 and c[i] > o[i - 1]:
        out.append("Dark cloud cover")
    _, b2, _, _ = _parts(o[i - 2], h[i - 2], l[i - 2], c[i - 2])
    mid2 = (o[i - 2] + c[i - 2]) / 2
    if c[i - 2] < o[i - 2] and b2 >= 0.6 * atr and pb <= 0.35 * b2 and green and body >= 0.6 * atr and c[i] > mid2:
        out.append("Morning star")
    if c[i - 2] > o[i - 2] and b2 >= 0.6 * atr and pb <= 0.35 * b2 and red and body >= 0.6 * atr and c[i] < mid2:
        out.append("Evening star")
    if all(c[k] > o[k] and (c[k] - o[k]) >= 0.5 * atr for k in (i - 2, i - 1, i)) and c[i] > c[i - 1] > c[i - 2] and o[i - 1] > o[i - 2] and o[i] > o[i - 1]:
        out.append("Three white soldiers")
    if all(c[k] < o[k] and (o[k] - c[k]) >= 0.5 * atr for k in (i - 2, i - 1, i)) and c[i] < c[i - 1] < c[i - 2] and o[i - 1] < o[i - 2] and o[i] < o[i - 1]:
        out.append("Three black crows")
    tol = 0.05 * atr
    if abs(l[i] - l[i - 1]) <= tol and pred and green and down_trend:
        out.append("Tweezer bottom")
    if abs(h[i] - h[i - 1]) <= tol and pg and red and up_trend:
        out.append("Tweezer top")
    return [p for p in out if p]


def candle_scan(d: dict[str, list], atr_series: list[float], horizon: int = 5, min_n: int = 8) -> dict[str, Any]:
    """Live patterns on the last 3 closed candles plus a back-test of each pattern on the same series:
    after a pattern, did price move in its direction within `horizon` candles before moving 1 ATR against it?"""
    n = len(d["c"])
    if n < 60:
        return {"available": False, "reason": f"Only {n} candles; at least 60 are needed to back-test patterns"}
    stats: dict[str, dict[str, Any]] = {}
    for i in range(10, n - horizon):
        a = atr_series[i]
        if not a:
            continue
        for p in candle_patterns_at(d, i, a):
            direction = CANDLE_PATTERNS[p][0]
            if direction == 0:
                continue
            entry = d["c"][i]
            fav, adv = entry + direction * a, entry - direction * a
            res = 0
            for j in range(i + 1, i + 1 + horizon):
                hit_f = d["h"][j] >= fav if direction > 0 else d["l"][j] <= fav
                hit_a = d["l"][j] <= adv if direction > 0 else d["h"][j] >= adv
                if hit_a:      # adverse first when both happen on one candle: the honest, conservative reading
                    res = -1
                    break
                if hit_f:
                    res = 1
                    break
            s = stats.setdefault(p, {"n": 0, "win": 0, "loss": 0, "flat": 0})
            s["n"] += 1
            s["win" if res > 0 else "loss" if res < 0 else "flat"] += 1
    live = []
    for i in range(max(10, n - 3), n):
        a = atr_series[i]
        for p in candle_patterns_at(d, i, a or 1e-9):
            s = stats.get(p)
            direction, meaning = CANDLE_PATTERNS[p]
            hit = round(100 * s["win"] / (s["win"] + s["loss"]), 1) if s and (s["win"] + s["loss"]) else None
            solid = bool(s and s["n"] >= min_n)
            live.append({"pattern": p, "direction": _bias(direction), "bars_ago": n - 1 - i, "meaning": meaning, "backtest_n": s["n"] if s else 0, "hit_pct": hit,
                         "reliable": solid and hit is not None and hit >= 55, "note": ("Back-tested: " + (f"{hit}% of {s['n']} past cases moved 1 ATR your way before 1 ATR against" if solid and hit is not None else "too few past cases to trust")) if direction != 0 else "Neutral pattern: it signals indecision, not direction"})
    table = [{"pattern": p, "direction": _bias(CANDLE_PATTERNS[p][0]), "n": s["n"], "win": s["win"], "loss": s["loss"], "hit_pct": round(100 * s["win"] / (s["win"] + s["loss"]), 1) if (s["win"] + s["loss"]) else None}
             for p, s in sorted(stats.items(), key=lambda kv: -kv[1]["n"])]
    return {"available": True, "live": live, "backtest": table, "horizon_bars": horizon, "bars": n,
            "method": f"Each pattern is counted when it completes; it wins if price reaches +1 ATR in its direction within {horizon} candles before -1 ATR against it (a candle touching both counts as a loss)."}


# ---------------------------------------------------------------- chart patterns


def pivots(h: list[float], l: list[float], k: int = 3) -> list[tuple[int, str, float]]:
    """Swing highs/lows: a bar higher/lower than k bars on each side. Only confirmed pivots are returned (k bars of confirmation)."""
    out: list[tuple[int, str, float]] = []
    for i in range(k, len(h) - k):
        if h[i] == max(h[i - k:i + k + 1]) and h[i] > max(h[i - k:i]):
            out.append((i, "H", h[i]))
        elif l[i] == min(l[i - k:i + k + 1]) and l[i] < min(l[i - k:i]):
            out.append((i, "L", l[i]))
    cleaned: list[tuple[int, str, float]] = []
    for p in out:
        if cleaned and cleaned[-1][1] == p[1]:
            if (p[1] == "H" and p[2] > cleaned[-1][2]) or (p[1] == "L" and p[2] < cleaned[-1][2]):
                cleaned[-1] = p
        else:
            cleaned.append(p)
    return cleaned


def _slope(pts: list[tuple[int, float]]) -> float:
    n = len(pts)
    mx, my = sum(p[0] for p in pts) / n, sum(p[1] for p in pts) / n
    den = sum((p[0] - mx) ** 2 for p in pts)
    return sum((p[0] - mx) * (p[1] - my) for p in pts) / den if den else 0.0


def chart_patterns(d: dict[str, list], atr: float) -> dict[str, Any]:
    """Classic chart patterns from the latest confirmed swing points, each with the neckline/breakout level, a measured target and the level that cancels it."""
    h, l, c = d["h"], d["l"], d["c"]
    n = len(c)
    if n < 40 or not atr:
        return {"available": False, "reason": f"Only {n} candles; at least 40 are needed"}
    pv = pivots(h, l, 3)
    px = c[-1]
    found: list[dict[str, Any]] = []
    tol = 0.6 * atr

    def add(name: str, direction: int, status: str, level: float, target: float, cancel: float, why: str, start: int) -> None:
        found.append({"pattern": name, "direction": _bias(direction), "status": status, "level": _r(level), "target": _r(target), "invalidates_at": _r(cancel), "why": why, "starts_bars_ago": n - 1 - start})

    highs = [p for p in pv if p[1] == "H"][-4:]
    lows = [p for p in pv if p[1] == "L"][-4:]
    # double top / bottom
    if len(highs) >= 2:
        a, b = highs[-2], highs[-1]
        if abs(a[2] - b[2]) <= tol and b[0] - a[0] >= 6 and max(a[2], b[2]) - min(l[a[0]:b[0] + 1]) >= 1.5 * atr:
            neck = min(l[a[0]:b[0] + 1])
            if px < neck:
                add("Double top", -1, "confirmed (neckline broken)", neck, neck - (max(a[2], b[2]) - neck), max(a[2], b[2]), "Price failed twice at the same high and then broke the low between them.", a[0])
            elif neck + 0.3 * atr < px <= max(a[2], b[2]) + 0.5 * atr and b[0] > n - 25:
                add("Double top", -1, "forming (waiting for the neckline to break)", neck, neck - (max(a[2], b[2]) - neck), max(a[2], b[2]), "Price failed twice at the same high. A close below the neckline confirms it.", a[0])
    if len(lows) >= 2:
        a, b = lows[-2], lows[-1]
        if abs(a[2] - b[2]) <= tol and b[0] - a[0] >= 6 and max(h[a[0]:b[0] + 1]) - min(a[2], b[2]) >= 1.5 * atr:
            neck = max(h[a[0]:b[0] + 1])
            if px > neck:
                add("Double bottom", 1, "confirmed (neckline broken)", neck, neck + (neck - min(a[2], b[2])), min(a[2], b[2]), "Price held the same low twice and then broke the high between them.", a[0])
            elif min(a[2], b[2]) - 0.5 * atr <= px < neck - 0.3 * atr and b[0] > n - 25:
                add("Double bottom", 1, "forming (waiting for the neckline to break)", neck, neck + (neck - min(a[2], b[2])), min(a[2], b[2]), "Price held the same low twice. A close above the neckline confirms it.", a[0])
    # head & shoulders (three highs, middle highest)
    if len(highs) >= 3 and len(lows) >= 2:
        l1, hd, r1 = highs[-3], highs[-2], highs[-1]
        if hd[2] > l1[2] + 0.5 * atr and hd[2] > r1[2] + 0.5 * atr and abs(l1[2] - r1[2]) <= 1.2 * atr:
            nk = [p for p in lows if l1[0] < p[0] < r1[0]]
            if len(nk) >= 2:
                neck = (nk[0][2] + nk[-1][2]) / 2
                add("Head and shoulders", -1, "confirmed (neckline broken)" if px < neck else "forming (waiting for the neckline to break)", neck, neck - (hd[2] - neck), hd[2], "A higher peak between two lower, similar peaks: buyers are running out of strength.", l1[0])
    if len(lows) >= 3 and len(highs) >= 2:
        l1, hd, r1 = lows[-3], lows[-2], lows[-1]
        if hd[2] < l1[2] - 0.5 * atr and hd[2] < r1[2] - 0.5 * atr and abs(l1[2] - r1[2]) <= 1.2 * atr:
            nk = [p for p in highs if l1[0] < p[0] < r1[0]]
            if len(nk) >= 2:
                neck = (nk[0][2] + nk[-1][2]) / 2
                add("Inverse head and shoulders", 1, "confirmed (neckline broken)" if px > neck else "forming (waiting for the neckline to break)", neck, neck + (neck - hd[2]), hd[2], "A lower dip between two higher, similar dips: sellers are running out of strength.", l1[0])
    # triangles / wedges from the last three highs and lows
    if len(highs) >= 3 and len(lows) >= 3:
        hs, ls = _slope([(p[0], p[2]) for p in highs[-3:]]), _slope([(p[0], p[2]) for p in lows[-3:]])
        flat = 0.05 * atr
        top, bot = highs[-1][2], lows[-1][2]
        height = top - bot
        if height < 1.5 * atr:
            hs = ls = 0.0
        if height >= 1.5 * atr and abs(hs) <= flat and ls > flat:
            add("Ascending triangle", 1, "forming" if px <= top else "broken out", top, top + height, bot, "Flat resistance with rising lows: buyers keep pushing into the same ceiling. Breakouts usually go up.", highs[-3][0])
        elif height >= 1.5 * atr and abs(ls) <= flat and hs < -flat:
            add("Descending triangle", -1, "forming" if px >= bot else "broken down", bot, bot - height, top, "Flat support with falling highs: sellers keep pushing into the same floor. Breakdowns usually go down.", lows[-3][0])
        elif hs < -flat and ls > flat:
            add("Symmetrical triangle", 0, "forming", (top + bot) / 2, top + height, bot, "Highs falling and lows rising: price is being squeezed. It breaks out one way or the other; wait for the close beyond either side.", min(highs[-3][0], lows[-3][0]))
        elif hs > flat and ls > flat and ls > hs * 1.2:
            add("Rising wedge", -1, "forming", bot, bot - height, top, "Both lines rising but the lows rise faster: momentum is tiring. Often resolves down.", min(highs[-3][0], lows[-3][0]))
        elif hs < -flat and ls < -flat and hs < ls * 1.2:
            add("Falling wedge", 1, "forming", top, top + height, bot, "Both lines falling but the highs fall faster: selling is tiring. Often resolves up.", min(highs[-3][0], lows[-3][0]))
    # range breakout of the last 20 bars
    prev_hi, prev_lo = max(h[-21:-1]), min(l[-21:-1])
    if c[-1] > prev_hi and c[-2] <= prev_hi:
        add("Range breakout (up)", 1, "confirmed on the last candle", prev_hi, prev_hi + (prev_hi - prev_lo) * 0.5, prev_lo + (prev_hi - prev_lo) * 0.5, "Price closed above the highest high of the last 20 candles.", n - 21)
    elif c[-1] < prev_lo and c[-2] >= prev_lo:
        add("Range breakout (down)", -1, "confirmed on the last candle", prev_lo, prev_lo - (prev_hi - prev_lo) * 0.5, prev_lo + (prev_hi - prev_lo) * 0.5, "Price closed below the lowest low of the last 20 candles.", n - 21)
    # support and resistance from recent pivots
    res = sorted({round(p[2], 2) for p in highs if p[2] > px})[:2]
    sup = sorted({round(p[2], 2) for p in lows if p[2] < px}, reverse=True)[:2]
    return {"available": True, "patterns": found, "support": sup, "resistance": res, "swings": len(pv)}


# ---------------------------------------------------------------- option chain


def chain_analysis(chain: dict[str, Any] | None, spot: float | None = None) -> dict[str, Any]:
    """What the option chain says: walls, put-call ratio, max pain, buildup, expected move and IV, each as a plain sentence."""
    strikes = (chain or {}).get("strikes") or []
    spot = float(spot or (chain or {}).get("spot") or 0) or None
    if not strikes or not spot:
        return {"available": False, "reason": "No option chain for this instrument right now (only indices, F&O stocks and MCX options have one)"}

    def g(s: dict, side: str, k: str) -> float:
        try:
            return float((s.get(side) or {}).get(k) or 0)
        except Exception:
            return 0.0

    ks = sorted(strikes, key=lambda s: float(s["strike"]))
    atm = min(ks, key=lambda s: abs(float(s["strike"]) - spot))
    atm_k = float(atm["strike"])
    coi, poi = sum(g(s, "call", "oi") for s in ks), sum(g(s, "put", "oi") for s in ks)
    pcr = round(poi / coi, 2) if coi else None
    call_wall = max((s for s in ks if float(s["strike"]) >= spot), key=lambda s: g(s, "call", "oi"), default=None)
    put_wall = max((s for s in ks if float(s["strike"]) <= spot), key=lambda s: g(s, "put", "oi"), default=None)

    def pain(k: float) -> float:
        return sum(max(0.0, k - float(s["strike"])) * g(s, "call", "oi") + max(0.0, float(s["strike"]) - k) * g(s, "put", "oi") for s in ks)

    max_pain = min((float(s["strike"]) for s in ks), key=pain)
    straddle = g(atm, "call", "ltp") + g(atm, "put", "ltp")
    civ, piv = g(atm, "call", "iv"), g(atm, "put", "iv")
    # buildup: where did OI change most, and what does that mean next to price
    adds = []
    for s in ks:
        for side, lbl in (("call", "CE"), ("put", "PE")):
            ch = g(s, side, "change_oi")
            if ch:
                adds.append({"strike": float(s["strike"]), "side": lbl, "change_oi": ch, "oi": g(s, side, "oi"), "ltp": g(s, side, "ltp")})
    adds.sort(key=lambda a: -abs(a["change_oi"]))
    near = [s for s in ks if abs(float(s["strike"]) - atm_k) <= 5 * max(1.0, (float(ks[1]["strike"]) - float(ks[0]["strike"])) if len(ks) > 1 else 1.0)]
    d_call_oi = sum(g(s, "call", "change_oi") for s in near)
    d_put_oi = sum(g(s, "put", "change_oi") for s in near)
    net_delta = sum(g(s, "call", "oi") * g(s, "call", "delta") + g(s, "put", "oi") * g(s, "put", "delta") for s in near)
    gamma_atm = g(atm, "call", "gamma") + g(atm, "put", "gamma")
    notes: list[str] = []
    bias = 0
    if pcr is not None:
        if pcr >= 1.3:
            bias += 1
            notes.append(f"PCR {pcr}: far more puts than calls are open. Put writers are confident, which usually supports the market.")
        elif pcr <= 0.7:
            bias -= 1
            notes.append(f"PCR {pcr}: far more calls than puts are open. Call writers are confident, which usually caps the market.")
        else:
            notes.append(f"PCR {pcr}: balanced between puts and calls.")
    if put_wall:
        notes.append(f"Support wall at {int(float(put_wall['strike']))}: the most put contracts are open there, so sellers defend it.")
    if call_wall:
        notes.append(f"Resistance wall at {int(float(call_wall['strike']))}: the most call contracts are open there, so sellers cap price there.")
    if abs(spot - max_pain) / spot >= 0.003:
        notes.append(f"Max pain is {int(max_pain)}: on expiry day price tends to drift toward it.")
    if d_put_oi > 0 and d_put_oi > 1.5 * max(d_call_oi, 1):
        bias += 1
        notes.append("Fresh put writing near the money is much larger than call writing: a bullish build-up.")
    elif d_call_oi > 0 and d_call_oi > 1.5 * max(d_put_oi, 1):
        bias -= 1
        notes.append("Fresh call writing near the money is much larger than put writing: a bearish build-up.")
    if straddle:
        notes.append(f"The at-the-money straddle costs {_r(straddle)} ({_r(straddle / spot * 100, 2)}% of price): the market is pricing about that much movement until expiry.")
    return {"available": True, "expiry": (chain or {}).get("expiry"), "spot": _r(spot), "atm_strike": atm_k, "pcr_oi": pcr,
            "call_wall": int(float(call_wall["strike"])) if call_wall else None, "put_wall": int(float(put_wall["strike"])) if put_wall else None,
            "max_pain": int(max_pain), "expected_move": _r(straddle), "expected_move_pct": _r(straddle / spot * 100, 2) if straddle else None,
            "atm_iv": _r((civ + piv) / 2 if civ and piv else civ or piv), "iv_skew_put_minus_call": _r(piv - civ) if civ and piv else None,
            "near_money_oi_change": {"calls": d_call_oi, "puts": d_put_oi}, "net_delta_oi": _r(net_delta, 0), "atm_gamma": _r(gamma_atm, 5),
            "buildup": adds[:6], "bias": _bias(bias), "notes": notes, "source": "Upstox option chain (nearest expiry)"}


# ---------------------------------------------------------------- one call for everything


def pack(d: dict[str, list], chain: dict[str, Any] | None = None, spot: float | None = None) -> dict[str, Any]:
    """Indicators + candlestick + chart patterns + option chain, with one combined lean (-100..+100) and the reasons behind it."""
    n = len(d.get("c") or [])
    ind = indicators(d) if n >= 30 else {"available": False, "reason": f"Only {n} candles"}
    atr_s = _wilder(_tr(d["h"], d["l"], d["c"]), 14) if n else []
    cs = candle_scan(d, atr_s) if n >= 60 else {"available": False, "reason": f"Only {n} candles"}
    cp = chart_patterns(d, atr_s[-1]) if n >= 40 else {"available": False, "reason": f"Only {n} candles"}
    oc = chain_analysis(chain, spot)
    parts, reasons = [], []
    if ind.get("available"):
        parts.append(ind["net"])
        reasons.append(f"Indicators: {ind['bull']} bullish, {ind['bear']} bearish, {ind['neutral']} neutral")
    if cs.get("available"):
        live = [p for p in cs["live"] if p["direction"] != "neutral" and p["bars_ago"] <= 1]
        sc = sum((1 if p["direction"] == "bullish" else -1) * (1.0 if p["reliable"] else 0.4) for p in live)
        if live:
            parts.append(max(-100, min(100, round(50 * sc))))
            reasons.append("Candles: " + ", ".join(f"{p['pattern']}{' (reliable)' if p['reliable'] else ''}" for p in live))
    if cp.get("available"):
        act = [p for p in cp["patterns"] if p["direction"] != "neutral" and p["status"].startswith(("confirmed", "broken"))]
        if act:
            parts.append(max(-100, min(100, 60 * sum(1 if p["direction"] == "bullish" else -1 for p in act))))
            reasons.append("Chart: " + ", ".join(p["pattern"] for p in act))
    if oc.get("available"):
        parts.append({"bullish": 60, "bearish": -60, "neutral": 0}[oc["bias"]])
        reasons.append(f"Option chain: {oc['bias']} (PCR {oc.get('pcr_oi')})")
    lean = round(sum(parts) / len(parts)) if parts else 0
    return {"available": bool(parts), "indicators": ind, "candles": cs, "chart": cp, "options": oc, "lean": lean,
            "lean_label": "Bullish" if lean >= 25 else "Bearish" if lean <= -25 else "Mixed", "reasons": reasons, "inputs": len(parts)}
