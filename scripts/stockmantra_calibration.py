#!/usr/bin/env python3
"""Recalibrate the signal model against Stock Mantra Index (@stockmantraindex) calls.

Steps
  1. Download the channel history with the app's Telegram user session (TELEGRAM_API_ID / TELEGRAM_API_HASH in .env).
  2. Keep only trade calls: "<UNDERLYING> <STRIKE> CE|PE ... NEAR|ABOVE <price>"; replies that are bare prices are his
     follow-up "pulses" and give his reported peak.
  3. For every call, load Upstox 1-minute candles up to the call minute (no look-ahead) and compute the signal model's
     factor scores with the same code the live app uses (backend/services/signal_model.py).
  4. Truth = which comes first within 2 hours on the underlying: a 0.3% move in the call's direction or 0.3% against.
  5. Fit factor weights (logistic regression of factor scores on his call direction, first 80% of calls), measure the
     result on the last 20%, build confidence buckets from call times plus random control times, and write
     data/signal_calibration.json and data/stockmantra_comparison.json.

Usage (on the server):  /home/ubuntu/venv/bin/python3 scripts/stockmantra_calibration.py [--days 45] [--with-old-engines]
Then commit the two data files (or restart the service) so the live model picks up the new weights.
"""
from __future__ import annotations

import argparse, asyncio, json, math, os, random, re, shutil, statistics, sys, tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
IST = timezone(timedelta(hours=5, minutes=30))
UND = {"NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX", "BANKEX", "CRUDEOIL", "NATURALGAS"}
CALL_RE = re.compile(r"\b(BANK\s*NIFTY|BANKNIFTY|FIN\s*NIFTY|FINNIFTY|MIDCP\s*NIFTY|MIDCPNIFTY|NIFTY|SENSEX|BANKEX|CRUDE\s*OIL|CRUDEOIL|NATURAL\s*GAS|NATURALGAS)\s*(\d{3,6})\s*(CE|PE|CALL|PUT)\b", re.I)
ENTRY_RE = re.compile(r"\b(NEAR|ABOVE|AROUND|AT|BUY(?:\s+(?:NEAR|ABOVE|AT|AROUND))?|@)\s*[:\-]?\s*(\d{1,5}(?:\.\d+)?)(?:\s*[-–/]\s*(\d{1,5}))?", re.I)
SL_RE = re.compile(r"\b(?:SL|STOP\s*LOSS|STOPLOSS)\s*[:\-]?\s*(\d{1,5}(?:\.\d+)?)\b", re.I)
TGT_RE = re.compile(r"\b(?:TGT|TARGET)S?\s*[:\-]?\s*(\d{1,5}(?:\.\d+)?)\b", re.I)
PULSE_RE = re.compile(r"^\s*\**\s*(\d{1,5}(?:\.\d+)?)\s*[^\w\s]*\s*\**\s*$")
FACTORS = ["trend", "vwap", "momentum", "price_action", "day_change"]


# ---------------------------------------------------------------- 1. download
async def fetch_messages(days: int) -> list[dict]:
    from dotenv import load_dotenv
    from telethon import TelegramClient
    load_dotenv(ROOT / ".env")
    api_id, api_hash = int(os.getenv("TELEGRAM_API_ID", "0")), os.getenv("TELEGRAM_API_HASH", "")
    session = os.getenv("TELEGRAM_SESSION_PATH", str(ROOT / "catrader_telegram"))
    if not api_id or not api_hash:
        raise SystemExit("TELEGRAM_API_ID / TELEGRAM_API_HASH missing in .env")
    tmp = Path(tempfile.mkdtemp()) / "s"
    shutil.copy(session + ".session", str(tmp) + ".session")  # copy so the running app keeps its own session file
    client = TelegramClient(str(tmp), api_id, api_hash)
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Telegram session is not logged in. Log in once, then rerun.")
    ent = await client.get_entity(os.getenv("STOCKMANTRA_CHANNEL", "stockmantraindex"))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    out = []
    async for m in client.iter_messages(ent, limit=None):
        if m.date < cutoff:
            break
        if m.text:
            out.append({"id": m.id, "date": m.date.isoformat(), "text": m.text, "reply_to": getattr(m.reply_to, "reply_to_msg_id", None)})
    await client.disconnect()
    return out


# ---------------------------------------------------------------- 2. parse
def parse_calls(msgs: list[dict]) -> list[dict]:
    msgs = sorted(msgs, key=lambda m: m["date"])
    calls, by_id = [], {}
    for m in msgs:
        t = m["text"].replace("*", "")
        ts = datetime.fromisoformat(m["date"]).astimezone(IST)
        cm = CALL_RE.search(t)
        if cm:
            em = ENTRY_RE.search(t[cm.end():]) or ENTRY_RE.search(t)
            und = re.sub(r"\s+", "", cm.group(1).upper())
            if not em or und not in UND:
                continue
            lo = float(em.group(2)); hi_s = em.group(3)
            hi = (float(hi_s) if len(hi_s) >= len(em.group(2)) else float(em.group(2)[:len(em.group(2)) - len(hi_s)] + hi_s)) if hi_s else lo
            slm, tgm = SL_RE.search(t), TGT_RE.search(t)
            c = {"msg_id": m["id"], "time_ist": ts.isoformat(), "underlying": und, "strike": int(cm.group(2)),
                 "side": "CE" if cm.group(3).upper() in ("CE", "CALL") else "PE", "entry_lo": lo, "entry_hi": max(lo, hi),
                 "entry": round((lo + max(lo, hi)) / 2, 2), "sl_stated": float(slm.group(1)) if slm else None,
                 "target_stated": float(tgm.group(1)) if tgm else None, "pulses": [], "text": t.strip()[:160]}
            calls.append(c); by_id[m["id"]] = c
            continue
        pm = PULSE_RE.match(t)
        if pm:
            v = float(pm.group(1))
            target = by_id.get(m.get("reply_to"))
            if target is None and calls and ts - datetime.fromisoformat(calls[-1]["time_ist"]) <= timedelta(hours=3):
                target = calls[-1]
            if target and 0.3 * target["entry"] <= v <= 8 * target["entry"]:
                target["pulses"].append(v)
    out = []
    for c in calls:  # merge reposts of the same contract within 20 minutes
        if out and (out[-1]["underlying"], out[-1]["strike"], out[-1]["side"]) == (c["underlying"], c["strike"], c["side"]) \
                and datetime.fromisoformat(c["time_ist"]) - datetime.fromisoformat(out[-1]["time_ist"]) < timedelta(minutes=20):
            out[-1]["pulses"] += c["pulses"]; continue
        out.append(c)
    for c in out:
        c["claimed_peak"] = max(c["pulses"], default=None)
        del c["pulses"]
    return out


# ---------------------------------------------------------------- option maths (implied index move)
def ncdf(x): return 0.5 * (1 + math.erf(x / math.sqrt(2)))
def bs(S, K, T, iv, r, side):
    if T <= 0 or iv <= 0:
        return max(0.0, S - K) if side == "CE" else max(0.0, K - S)
    d1 = (math.log(S / K) + (r + iv * iv / 2) * T) / (iv * math.sqrt(T)); d2 = d1 - iv * math.sqrt(T)
    return S * ncdf(d1) - K * math.exp(-r * T) * ncdf(d2) if side == "CE" else K * math.exp(-r * T) * ncdf(-d2) - S * ncdf(-d1)
def solve(f, lo, hi):
    if f(lo) * f(hi) > 0: return None
    for _ in range(80):
        mid = (lo + hi) / 2
        if f(lo) * f(mid) <= 0: hi = mid
        else: lo = mid
    return (lo + hi) / 2
def est_expiry(und, d):
    nxt = lambda wd: d + timedelta(days=(wd - d.weekday()) % 7)
    def last_tue(y, m):
        e = date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)
        return e - timedelta(days=(e.weekday() - 1) % 7)
    if und == "NIFTY": return nxt(1)
    if und in ("SENSEX", "BANKEX"): return nxt(3)
    if und in ("CRUDEOIL", "NATURALGAS"):
        e = date(d.year, d.month, 16); return e if e >= d else date(d.year + (d.month == 12), d.month % 12 + 1, 16)
    e = last_tue(d.year, d.month); return e if e >= d else last_tue(d.year + (d.month == 12), d.month % 12 + 1)


# ---------------------------------------------------------------- 3/4. replay
def replay(calls: list[dict], with_old_engines: bool) -> tuple[list[dict], list[dict]]:
    import logging; logging.disable(logging.WARNING)
    import app as A
    from backend.services import signal_model as SM
    A.recommendation_news_evidence = lambda *a, **k: {"stock": {"signal": "NEUTRAL", "materiality": 0}, "global": {"signal": "NEUTRAL", "materiality": 0}}
    A.get_stock_mantra_setup = lambda *a, **k: None
    cache: dict = {}
    def c1m(und, d):
        if (und, d) not in cache:
            try: cache[(und, d)] = A.UPSTOX.candles_between(und, "1", "minutes", d - timedelta(days=6), d)
            except Exception: cache[(und, d)] = []
        return cache[(und, d)]
    ts = lambda c: datetime.fromisoformat(str(c["timestamp"])).astimezone(IST)
    def first_touch(rows, t, up, dn):
        for c in rows:
            if ts(c) <= t or ts(c) > t + timedelta(hours=2) or ts(c).date() != t.date(): continue
            if float(c["high"]) >= up and float(c["low"]) <= dn: return "both"
            if float(c["high"]) >= up: return "up"
            if float(c["low"]) <= dn: return "down"
        return "none"
    out, controls = [], []
    for c in calls:
        t = datetime.fromisoformat(c["time_ist"]); d = t.date(); row = dict(c)
        rows = c1m(c["underlying"], d)
        day = [x for x in rows if ts(x).date() == d]; upto = [x for x in rows if ts(x) <= t]
        if len([x for x in day if ts(x) <= t]) < 16:
            row["skip"] = "fewer than 15 minutes of session data before the call" if day else "no Upstox candles"; out.append(row); continue
        S0 = float(upto[-1]["close"]); row["spot_at_call"] = S0
        f = SM.compute_factors(A.resample_candles_to_tf(upto, 5))
        if not f.get("available"):
            row["skip"] = f.get("reason"); out.append(row); continue
        row["factors"] = {k: f["scores"][k] for k in FACTORS}
        exp = est_expiry(c["underlying"], d)
        T = max(((datetime.combine(exp, datetime.min.time(), IST) + timedelta(hours=15, minutes=30)) - t).total_seconds() / (365 * 86400), 1 / 35040)
        iv = solve(lambda v: bs(S0, c["strike"], T, v, 0.065, c["side"]) - c["entry"], 0.01, 4.0) or 0.14
        d1 = (math.log(S0 / c["strike"]) + (0.065 + iv * iv / 2) * T) / (iv * math.sqrt(T)); dl = ncdf(d1) if c["side"] == "CE" else ncdf(d1) - 1
        row.update({"expiry_used": exp.isoformat(), "expiry_estimated": True, "iv_from_entry": round(iv, 4), "delta": round(dl, 3)})
        peak = c["claimed_peak"] or c["target_stated"]
        if peak and peak > c["entry"]:
            s_t = solve(lambda S: bs(S, c["strike"], T, iv, 0.065, c["side"]) - peak, S0 * 0.7, S0 * 1.3)
            if s_t: row["implied_index_target"], row["implied_index_move"] = round(s_t, 2), round(s_t - S0, 2)
        mv = first_touch(day, t, S0 * 1.003, S0 * 0.997)
        row["actual_first_0p3pct"] = {"up": "UP", "down": "DOWN"}.get(mv, "NO 0.3% MOVE")
        row["mantra_right"] = (mv == ("up" if c["side"] == "CE" else "down")) if mv in ("up", "down") else None
        if with_old_engines:
            c5 = A.resample_candles_to_tf(upto, 5)[-300:]
            try: row["old_backtest_engine"] = asyncio.run(A.backtest_evaluate({"symbol": c["underlying"], "candles": c5}, user={"id": 1})).get("signal")
            except Exception: pass
            try: row["old_live_engine"] = A.overall_recommendation(c["underlying"], "5m", candles_override=c5).get("direction")
            except Exception: pass
        out.append(row)
        # random control moments (no call within 20 minutes) for confidence buckets
        random.seed(c["msg_id"]); call_ts = [datetime.fromisoformat(x["time_ist"]) for x in calls if x["underlying"] == c["underlying"]]
        for tt in random.sample([ts(x) for x in day[20:-15]], min(3, max(0, len(day) - 35))):
            if all(abs((tt - ct).total_seconds()) > 1200 for ct in call_ts):
                fc = SM.compute_factors(A.resample_candles_to_tf([x for x in rows if ts(x) <= tt], 5))
                if fc.get("available"):
                    px = float([x for x in rows if ts(x) <= tt][-1]["close"])
                    controls.append({"factors": {k: fc["scores"][k] for k in FACTORS}, "move": first_touch(day, tt, px * 1.003, px * 0.997)})
        print(f"{c['time_ist'][:16]} {c['underlying']} {c['strike']} {c['side']} -> {row.get('actual_first_0p3pct')}", flush=True)
    return out, controls


# ---------------------------------------------------------------- 5. fit + write
def fit(rows: list[dict], controls: list[dict], gate: float = 30.0) -> tuple[dict, dict]:
    ok = sorted([r for r in rows if r.get("factors")], key=lambda r: r["time_ist"])
    X = [[r["factors"][k] / 100 for k in FACTORS] for r in ok]; Y = [1 if r["side"] == "CE" else 0 for r in ok]
    cut = int(len(X) * 0.8); w = [0.0] * len(FACTORS); b = 0.0
    for _ in range(4000):
        gw = [0.0] * len(w); gb = 0.0
        for x, y in zip(X[:cut], Y[:cut]):
            p = 1 / (1 + math.exp(-max(-30, min(30, b + sum(a * c for a, c in zip(w, x)))))); gb += p - y
            for i, xi in enumerate(x): gw[i] += (p - y) * xi
        n = max(1, cut); b -= 0.3 * gb / n; w = [wi - 0.3 * (g / n + 0.05 * wi) for wi, g in zip(w, gw)]
    pos = {k: max(0.0, wi) for k, wi in zip(FACTORS, w)}; s = sum(pos.values()) or 1
    weights = {k: round(v / s, 3) for k, v in pos.items()}; weights["option_flow"] = 0.0
    score = lambda f: sum(f[k] * weights[k] for k in FACTORS)
    def val(sub):
        fired = [r for r in sub if abs(score(r["factors"])) >= gate]
        res = [r for r in fired if r["actual_first_0p3pct"] in ("UP", "DOWN")]
        mres = [r for r in sub if r["mantra_right"] is not None]
        return {"calls": len(sub), "fired": len(fired), "agree_with_mantra": sum(1 for r in fired if (score(r["factors"]) > 0) == (r["side"] == "CE")),
                "resolved": len(res), "model_right": sum(1 for r in res if (score(r["factors"]) > 0) == (r["actual_first_0p3pct"] == "UP")),
                "mantra_resolved": len(mres), "mantra_right": sum(1 for r in mres if r["mantra_right"])}
    validation = {"all": val(ok), "test": val(ok[cut:]),
                  "train_period": [ok[0]["time_ist"][:10], ok[cut - 1]["time_ist"][:10]] if cut else None,
                  "test_period": [ok[cut]["time_ist"][:10], ok[-1]["time_ist"][:10]] if len(ok) > cut else None}
    moments = [(r["factors"], {"UP": "up", "DOWN": "down"}.get(r["actual_first_0p3pct"])) for r in ok] + [(c["factors"], c["move"]) for c in controls]
    buckets = []
    for lo, hi in zip([0, 10, 20, 30, 40, 55, 70], [10, 20, 30, 40, 55, 70, 101]):
        sel = [(f, m) for f, m in moments if m in ("up", "down") and lo <= abs(score(f)) < hi]
        buckets.append({"lo": lo, "hi": hi, "n": len(sel), "hit": sum(1 for f, m in sel if (score(f) > 0) == (m == "up"))})
    by_und = {}
    for u in sorted({r["underlying"] for r in ok}):
        sub = [r for r in ok if r["underlying"] == u and r["mantra_right"] is not None]
        by_und[u] = [sum(1 for r in sub if r["mantra_right"]), len(sub)]
    for r in rows:
        if r.get("factors"):
            sc = round(score(r["factors"]), 1); r["new_model_score"] = sc
            r["new_model_decision"] = "BUY" if sc >= gate else "SELL" if sc <= -gate else "NO_TRADE"
    cal = {"version": datetime.now(IST).strftime("%Y-%m-%d") + "-stockmantra", "generated": datetime.now(IST).isoformat(),
           "source": f"Fitted on {len(ok)} Stock Mantra Index calls replayed on Upstox 1-minute candles (first 80% for fitting)",
           "weights": weights, "gate": gate, "min_agree": 3, "buckets": buckets,
           "bucket_definition": "Share of real moments (call times + random control times) where the underlying moved 0.3% in the score's direction first, within 2 hours",
           "validation": validation, "stock_mantra_accuracy_by_underlying": by_und}
    return cal, {"validation": validation, "by_underlying": by_und}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--with-old-engines", action="store_true", help="also replay the legacy engines (slow on small VMs)")
    ap.add_argument("--messages", help="use a saved JSON of messages instead of downloading")
    a = ap.parse_args()
    msgs = json.load(open(a.messages, encoding="utf-8")) if a.messages else asyncio.run(fetch_messages(a.days))
    calls = parse_calls(msgs)
    print(f"{len(msgs)} messages, {len(calls)} calls", flush=True)
    rows, controls = replay(calls, a.with_old_engines)
    cal, info = fit(rows, controls)
    (ROOT / "data" / "signal_calibration.json").write_text(json.dumps(cal, indent=1), encoding="utf-8")
    ok = [r for r in rows if r.get("factors")]
    mres = [r for r in ok if r.get("mantra_right") is not None]
    comparison = {"generated": cal["generated"], "period": f"{calls[0]['time_ist'][:10]} to {calls[-1]['time_ist'][:10]}" if calls else "",
                  "messages_downloaded": len(msgs), "calls_parsed": len(calls), "calls_analysed": len(ok),
                  "method": {"replay": "Upstox 1-minute candles up to the call minute only; factor scores from the live signal model code",
                             "implied_index_move": "Underlying level at which the option is worth his reported peak (Black-Scholes, IV from his entry premium)",
                             "truth": "First 0.3% move within 2 hours on the underlying"},
                  "summary": {"stock_mantra_right": {"n": len(mres), "right": sum(1 for r in mres if r["mantra_right"]),
                                                     "pct": round(100 * sum(1 for r in mres if r["mantra_right"]) / len(mres), 1) if mres else None},
                              "new_model": info["validation"], "stock_mantra_by_underlying": info["by_underlying"]},
                  "calls": [{**r, "contract": f"{r['underlying']} {r['strike']} {r['side']}"} for r in rows]}
    (ROOT / "data" / "stockmantra_comparison.json").write_text(json.dumps(comparison, indent=1, ensure_ascii=False, default=str), encoding="utf-8")
    print(json.dumps({"weights": cal["weights"], "validation": cal["validation"]}, indent=1))


if __name__ == "__main__":
    main()
