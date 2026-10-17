"""High-conviction signal alerts: phone push notifications (Web Push) and Telegram.

A plan is alerted only when every filter passes; the filters use the plan's own measured backtest, never a made-up
confidence. Nothing here is a guarantee: even plans that pass every filter lose sometimes, and the message says so.

Web Push is implemented directly on top of `cryptography` (RFC 8291 aes128gcm payload encryption + RFC 8292 VAPID),
so no extra native build is needed on the server. If `cryptography` is missing, push is reported as unavailable and
Telegram still works.
"""
from __future__ import annotations

import base64
import json
import logging
import os
import struct
import time
from typing import Any, Callable
from urllib.parse import urlparse

import requests

log = logging.getLogger("ca-trader.alerts")

DEFAULTS: dict[str, Any] = {
    "enabled": True,           # master switch for strict-signal alerts
    "push": True,              # phone notifications from the app
    "telegram": True,          # also send to the configured Telegram chat
    "outcomes": True,          # follow up when an alerted plan hits T1/T2/SL or expires
    "min_score_margin": 20,    # |score| must clear the no-trade gate by at least this many points
    "min_hit_rate": 60,        # backtest: % of past signals that reached T1 before SL
    "min_expectancy_r": 0.05,  # backtest: average result per trade, in R, after the time stop
    "min_signals": 50,         # backtest sample size
    "require_htf_agree": True, # every higher timeframe must point the same way (none neutral)
    "horizons": ["scalp", "intraday", "swing"],
    "use_net": True,           # judge the average result after round-trip costs (brokerage, STT, charges, slippage)
    "context_edge": True,      # skip plans whose time-of-day or volatility bucket lost money in the backtest
    "min_context_n": 15,       # a context bucket needs this many past trades before it can block a plan
    "max_per_day": 10,         # never send more than this many new-signal alerts in one day
    "scan_watchlist": 2,       # also scan this many watchlist symbols (besides NIFTY and BANKNIFTY), 0-6
    "per_order": 20,           # brokerage per order, in rupees (used for net results)
    "slippage_ticks": 1,       # assumed slippage per side, in ticks
}
LIMITS = {"min_score_margin": (0, 60), "min_hit_rate": (30, 95), "min_expectancy_r": (-0.5, 1.0), "min_signals": (10, 1000), "min_context_n": (5, 200),
          "max_per_day": (1, 50), "scan_watchlist": (0, 6), "per_order": (0, 100), "slippage_ticks": (0, 10)}
_SETTINGS_KEY = "signal_alerts"
_VAPID_KEY = "webpush_vapid"
_SUBJECT = os.getenv("WEBPUSH_SUBJECT", "mailto:alerts@catrader.site")


def b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def b64u_dec(s: str) -> bytes:
    s = s.strip()
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


# ------------------------------------------------------------------ settings
def get_config(db: Callable, user_id: int = 1) -> dict[str, Any]:
    row = db("SELECT value_json FROM settings WHERE user_id=? AND key=?", [user_id, _SETTINGS_KEY], "one")
    cfg = dict(DEFAULTS)
    if row and row.get("value_json"):
        try:
            cfg.update({k: v for k, v in json.loads(row["value_json"]).items() if k in DEFAULTS})
        except Exception:
            pass
    return cfg


def save_config(db: Callable, patch: dict[str, Any], user_id: int = 1) -> dict[str, Any]:
    cfg = get_config(db, user_id)
    for k, v in (patch or {}).items():
        if k not in DEFAULTS:
            continue
        d = DEFAULTS[k]
        if isinstance(d, bool):
            cfg[k] = bool(v)
        elif isinstance(d, int) and not isinstance(d, bool):
            cfg[k] = int(float(v))
        elif isinstance(d, float):
            cfg[k] = float(v)
        elif isinstance(d, list):
            cfg[k] = [x for x in (v or []) if x in DEFAULTS["horizons"]]
        if k in LIMITS:
            lo, hi = LIMITS[k]
            cfg[k] = type(d)(max(lo, min(hi, cfg[k])))
    db("INSERT INTO settings(user_id,key,value_json) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value_json=excluded.value_json",
       [user_id, _SETTINGS_KEY, json.dumps(cfg)])
    return cfg


# ------------------------------------------------------------------ the filter
def check(*, side: str, horizon: str, score: float, gate: float, htf_all: bool, track: dict[str, Any], ctx: dict[str, str] | None,
          ctx_stats: dict[str, Any] | None, cfg: dict[str, Any]) -> tuple[bool, list[str]]:
    """The alert rule, shared by live plans and the history preview. Returns (passes, reasons)."""
    if horizon not in (cfg.get("horizons") or []):
        return False, [f"{horizon} alerts are switched off"]
    need = float(gate) + float(cfg["min_score_margin"])
    if abs(float(score)) < need:
        return False, [f"score {float(score):+.0f} is below ±{need:.0f}"]
    reasons = [f"score {float(score):+.0f} (needs ±{need:.0f})"]
    if cfg.get("require_htf_agree"):
        if not htf_all:
            return False, ["higher timeframes do not all agree"]
        reasons.append("all higher timeframes agree")
    n, hit = int(track.get("filled") or track.get("signals") or 0), track.get("t1_hit_rate")
    net = bool(cfg.get("use_net")) and track.get("expectancy_r_net") is not None
    exp = track.get("expectancy_r_net") if net else track.get("expectancy_r")
    if n < int(cfg["min_signals"]):
        return False, [f"only {n} backtested trades (needs {cfg['min_signals']})"]
    if hit is None or float(hit) < float(cfg["min_hit_rate"]):
        return False, [f"backtest T1 hit rate {hit}% is below {cfg['min_hit_rate']}%"]
    if exp is None or float(exp) < float(cfg["min_expectancy_r"]):
        return False, [f"backtest average {exp}R{' after costs' if net else ''} is below {cfg['min_expectancy_r']}R"]
    reasons.append(f"backtest: T1 first {float(hit):.0f}% of {n}, average {float(exp):+.2f}R{' after costs' if net else ''}")
    if cfg.get("context_edge") and ctx and ctx_stats:
        key = "exp_net" if net else "exp"
        for dim, label in (("tod", "time of day"), ("vol", "volatility")):
            b = (ctx_stats.get(dim) or {}).get(ctx.get(dim)) or {}
            if int(b.get("n") or 0) >= int(cfg["min_context_n"]) and b.get(key) is not None and float(b[key]) <= 0:
                return False, [f"{label} '{ctx.get(dim)}' averaged {float(b[key]):+.2f}R in the backtest ({b['n']} trades)"]
        reasons.append(f"context {ctx.get('tod')}/{ctx.get('vol')} not negative in the backtest")
    return True, reasons


def qualifies(plan: dict[str, Any], cfg: dict[str, Any]) -> tuple[bool, list[str]]:
    """Return (passes, reasons) for a live plan. Reasons describe what passed, or the first thing that failed."""
    side = plan.get("decision")
    if side not in ("BUY", "SELL") or plan.get("expired") or not plan.get("available", True):
        return False, ["not a live BUY/SELL plan"]
    want = 1 if side == "BUY" else -1
    htf = plan.get("higher_timeframes") or []
    tr = plan.get("track_record") or {}
    return check(side=side, horizon=str(plan.get("horizon")), score=float(plan.get("score") or 0), gate=float(plan.get("gate") or 0),
                 htf_all=bool(htf) and all((h.get("bias") or 0) * want > 0 for h in htf), track=tr, ctx=plan.get("context"),
                 ctx_stats=tr.get("context"), cfg=cfg)


# ------------------------------------------------------------------ history preview (walk-forward)
def _stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    from backend.services import trade_plan as TP
    return {**TP.summarize(rows), "context": TP.context_stats(rows)}


def evaluate(cfg: dict[str, Any], keyed_rows: dict[str, list[dict[str, Any]]], fit: tuple[float, float] = (0.0, 0.6),
             test: tuple[float, float] = (0.6, 1.0), _cache: dict | None = None) -> dict[str, Any]:
    """Replay the alert rule on past signals. Track records and context stats come only from the `fit` slice of each
    symbol/horizon history; alerts are counted on the later `test` slice, so the result is out-of-sample."""
    alerts: list[dict[str, Any]] = []
    days_by_key: dict[str, int] = {}
    for key, rows in keyed_rows.items():
        if not rows:
            continue
        sym, hz = key.split(":", 1)
        n = len(rows)
        fit_rows, test_rows = rows[int(n * fit[0]):int(n * fit[1])], rows[int(n * test[0]):int(n * test[1])]
        if not fit_rows or not test_rows:
            continue
        ck = (key, fit)
        st = _cache.get(ck) if _cache is not None else None
        if st is None:
            st = _stats(fit_rows)
            if _cache is not None:
                _cache[ck] = st
        days_by_key[key] = len({r["d"] for r in test_rows}) or 1
        for r in test_rows:
            ok, _ = check(side=r["side"], horizon=hz, score=r["score"], gate=r.get("g", 30), htf_all=r["htf"] == "all", track=st,
                          ctx={"tod": r["tod"], "vol": r["vol"]}, ctx_stats=st["context"], cfg=cfg)
            if ok:
                alerts.append({**r, "sym": sym, "hz": hz})
    alerts.sort(key=lambda a: (a["d"], a["t"]))
    capped, per_day = [], {}
    for a in alerts:   # the daily cap, in time order across all symbols
        if per_day.get(a["d"], 0) < int(cfg.get("max_per_day") or 999):
            per_day[a["d"]] = per_day.get(a["d"], 0) + 1
            capped.append(a)
    rate = sum(sum(1 for a in capped if f"{a['sym']}:{a['hz']}" == k) / d for k, d in days_by_key.items())
    filled = [a for a in capped if a["o"] != "NOT_FILLED"]
    by_hz = {}
    for hz in ("scalp", "intraday", "swing"):
        f = [a for a in filled if a["hz"] == hz]
        if f or any(k.endswith(":" + hz) for k in days_by_key):
            by_hz[hz] = {"alerts": sum(1 for a in capped if a["hz"] == hz), "filled": len(f),
                         "hit": round(sum(1 for a in f if a["o"] in ("T1", "T2")) / len(f) * 100, 1) if f else None,
                         "exp_net": round(sum(a["rn"] for a in f) / len(f), 3) if f else None}
    return {"per_day": round(min(rate, float(cfg.get("max_per_day") or rate)), 1), "alerts": len(capped), "filled": len(filled),
            "hit": round(sum(1 for a in filled if a["o"] in ("T1", "T2")) / len(filled) * 100, 1) if filled else None,
            "exp": round(sum(a["r"] for a in filled) / len(filled), 3) if filled else None,
            "exp_net": round(sum(a["rn"] for a in filled) / len(filled), 3) if filled else None,
            "by_horizon": by_hz, "keys": sorted(days_by_key), "recent": [{k: a[k] for k in ("sym", "hz", "d", "t", "side", "score", "o", "rn")} for a in capped[-8:]]}


def suggest(cfg: dict[str, Any], keyed_rows: dict[str, list[dict[str, Any]]], target: tuple[float, float] = (5, 10)) -> dict[str, Any]:
    """Pick filter settings that give `target` alerts/day with the best net result. Selection uses only the older part
    of history (stats from 0-36%, chosen on 36-60%); the chosen settings are then reported on the untouched last 40%."""
    best, cache = None, {}
    for margin in (0, 5, 10, 15, 20, 25, 30):
        for hit in (45, 50, 55, 60, 65):
            for exp in (-0.05, 0.0, 0.05):
                for htf in (True, False):
                    for ctx in (True, False):
                        c = {**cfg, "min_score_margin": margin, "min_hit_rate": hit, "min_expectancy_r": exp, "require_htf_agree": htf, "context_edge": ctx,
                             "max_per_day": max(int(cfg.get("max_per_day") or 0), int(target[1]))}
                        r = evaluate(c, keyed_rows, fit=(0.0, 0.36), test=(0.36, 0.6), _cache=cache)
                        if r["filled"] < 8 or r["exp_net"] is None:
                            continue
                        in_band = target[0] <= r["per_day"] <= target[1]
                        dist = 0 if in_band else min(abs(r["per_day"] - target[0]), abs(r["per_day"] - target[1]))
                        rank = (dist, -r["exp_net"])
                        if best is None or rank < best[0]:
                            best = (rank, c, r)
    if not best:
        return {"available": False, "reason": "Not enough backtested trades yet to suggest settings."}
    _, c, sel = best
    keys = ("min_score_margin", "min_hit_rate", "min_expectancy_r", "require_htf_agree", "context_edge", "max_per_day")
    chk = evaluate(c, keyed_rows)
    meets = target[0] <= sel["per_day"] <= target[1]
    profitable = (chk.get("exp_net") or 0) > 0 and (sel.get("exp_net") or 0) > 0
    note = ("These settings gave the target number of alerts with a positive result after costs, both when chosen and on the most recent, untouched period."
            if meets and profitable else
            f"No setting gave {target[0]:g}-{target[1]:g} alerts a day with a positive result after costs. This is the closest; consider scanning more symbols or accepting fewer alerts."
            if not meets else
            "These settings give the target count, but the most recent period lost money after costs. Fewer, stricter alerts are the safer choice.")
    return {"available": True, "settings": {k: c[k] for k in keys}, "selection": sel, "check": chk, "meets_target": meets, "profitable": profitable, "note": note}


def _fmt(v: Any, d: int = 2) -> str:
    try:
        return f"{float(v):,.{d}f}"
    except (TypeError, ValueError):
        return "—"


def _ist_hhmm(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        from datetime import datetime
        from zoneinfo import ZoneInfo
        return datetime.fromisoformat(iso).astimezone(ZoneInfo("Asia/Kolkata")).strftime("%H:%M")
    except Exception:
        return ""


def build_alert(symbol: str, plan: dict[str, Any], reasons: list[str]) -> dict[str, Any]:
    side, o, tr = plan["decision"], plan.get("option") or {}, plan.get("track_record") or {}
    head = f"{'🟢 BUY' if side == 'BUY' else '🔴 SELL'} {symbol} · {plan.get('label', plan.get('horizon', '')).title()}"
    if o.get("symbol"):
        body = (f"Buy {o['symbol']} {_fmt(o.get('entry_low'))}–{_fmt(o.get('entry_high'))} · SL {_fmt(o.get('stop_loss'))} · "
                f"T1 {_fmt(o.get('target_1'))} · T2 {_fmt(o.get('target_2'))}")
    else:
        body = (f"Entry {_fmt(plan.get('entry_low'))}–{_fmt(plan.get('entry_high'))} · SL {_fmt(plan.get('stop_loss'))} · "
                f"T1 {_fmt(plan.get('target_1'))} · T2 {_fmt(plan.get('target_2'))}")
    until = _ist_hhmm(plan.get("valid_until"))
    body += f"\nEnter by {until} IST · past hit rate {_fmt(tr.get('t1_hit_rate'), 0)}%" if until else ""
    return {"title": head, "body": body, "tag": f"plan-{symbol}-{plan.get('horizon')}", "url": "/terminal?ui=mobile",
            "symbol": symbol, "horizon": plan.get("horizon"), "reasons": reasons}


def telegram_html(alert: dict[str, Any]) -> str:
    esc = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    lines = [f"<b>{esc(alert['title'])}</b>", esc(alert["body"])]
    if alert.get("reasons"):
        lines.append("<i>Passed: " + esc("; ".join(alert["reasons"])) + "</i>")
    lines.append("<i>High-conviction filter, not a guarantee. Size the trade so the stop loss is affordable.</i>")
    return "\n".join(lines)


OUTCOME_TEXT = {"T1": "✅ Target 1 hit", "T2": "✅ Target 2 hit", "SL": "❌ Stop loss hit", "TIME": "⏱ Time exit", "EXPIRED": "⌛ Zone never reached — no trade"}


def build_outcome(row: dict[str, Any]) -> dict[str, Any] | None:
    txt = OUTCOME_TEXT.get(row.get("status") or "")
    if not txt:
        return None
    r = row.get("r")
    tail = f" · {float(r):+.2f}R" if r is not None else ""
    return {"title": f"{txt} · {row.get('symbol')} {str(row.get('horizon', '')).title()}", "body": f"{row.get('side')} plan from {_ist_hhmm(row.get('created_at'))} IST{tail}",
            "tag": f"plan-{row.get('symbol')}-{row.get('horizon')}", "url": "/terminal?ui=mobile"}


# ------------------------------------------------------------------ Web Push (RFC 8291 + RFC 8292) on `cryptography`
def _crypto():
    try:
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import ec
        from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
        from cryptography.hazmat.primitives.kdf.hkdf import HKDF
        return hashes, serialization, ec, decode_dss_signature, AESGCM, HKDF
    except Exception:
        return None


def push_available() -> bool:
    return _crypto() is not None


def vapid_keys(db: Callable) -> dict[str, str] | None:
    """The server's VAPID key pair, created once and kept in app_secrets (server-only, never sent to clients except the public key)."""
    c = _crypto()
    if not c:
        return None
    hashes, serialization, ec, *_ = c
    row = db("SELECT value_json FROM app_secrets WHERE key=?", [_VAPID_KEY], "one")
    if row and row.get("value_json"):
        try:
            v = json.loads(row["value_json"])
            if v.get("private_pem") and v.get("public"):
                return v
        except Exception:
            pass
    k = ec.generate_private_key(ec.SECP256R1())
    v = {"private_pem": k.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(),
         "public": b64u(k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint))}
    db("INSERT INTO app_secrets(key,value_json) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value_json=excluded.value_json", [_VAPID_KEY, json.dumps(v)])
    return v


def _vapid_header(keys: dict[str, str], endpoint: str) -> str:
    hashes, serialization, ec, decode_dss_signature, *_ = _crypto()
    u = urlparse(endpoint)
    header = b64u(json.dumps({"typ": "JWT", "alg": "ES256"}, separators=(",", ":")).encode())
    claims = b64u(json.dumps({"aud": f"{u.scheme}://{u.netloc}", "exp": int(time.time()) + 12 * 3600, "sub": _SUBJECT}, separators=(",", ":")).encode())
    signing_input = f"{header}.{claims}".encode()
    key = serialization.load_pem_private_key(keys["private_pem"].encode(), password=None)
    r, s = decode_dss_signature(key.sign(signing_input, ec.ECDSA(hashes.SHA256())))
    jwt = f"{header}.{claims}.{b64u(r.to_bytes(32, 'big') + s.to_bytes(32, 'big'))}"
    return f"vapid t={jwt}, k={keys['public']}"


def encrypt_payload(payload: bytes, p256dh: str, auth: str, *, _as_key=None, _salt: bytes | None = None) -> bytes:
    """aes128gcm body for one push message (single record)."""
    hashes, serialization, ec, _, AESGCM, HKDF = _crypto()
    ua_pub_bytes, auth_secret = b64u_dec(p256dh), b64u_dec(auth)
    ua_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), ua_pub_bytes)
    as_key = _as_key or ec.generate_private_key(ec.SECP256R1())
    as_pub_bytes = as_key.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)
    shared = as_key.exchange(ec.ECDH(), ua_pub)
    ikm = HKDF(algorithm=hashes.SHA256(), length=32, salt=auth_secret, info=b"WebPush: info\x00" + ua_pub_bytes + as_pub_bytes).derive(shared)
    salt = _salt or os.urandom(16)
    cek = HKDF(algorithm=hashes.SHA256(), length=16, salt=salt, info=b"Content-Encoding: aes128gcm\x00").derive(ikm)
    nonce = HKDF(algorithm=hashes.SHA256(), length=12, salt=salt, info=b"Content-Encoding: nonce\x00").derive(ikm)
    cipher = AESGCM(cek).encrypt(nonce, payload + b"\x02", None)
    return salt + struct.pack("!IB", 4096, len(as_pub_bytes)) + as_pub_bytes + cipher


def send_push(db: Callable, sub: dict[str, Any], message: dict[str, Any], ttl: int = 1800) -> tuple[bool, int, str]:
    """Send one notification. Returns (ok, http_status, detail). 404/410 mean the subscription is gone."""
    keys = vapid_keys(db)
    if not keys:
        return False, 0, "push unavailable (cryptography not installed)"
    endpoint = sub["endpoint"]
    body = encrypt_payload(json.dumps(message, ensure_ascii=False).encode(), sub["keys"]["p256dh"], sub["keys"]["auth"])
    try:
        r = requests.post(endpoint, data=body, timeout=10, headers={
            "Authorization": _vapid_header(keys, endpoint), "Content-Encoding": "aes128gcm", "Content-Type": "application/octet-stream",
            "TTL": str(ttl), "Urgency": "high"})
        return r.status_code in (200, 201, 202), r.status_code, (r.text or "")[:200]
    except Exception as exc:
        return False, 0, str(exc)[:200]


# ------------------------------------------------------------------ subscriptions
def ensure_tables(db: Callable) -> None:
    db("CREATE TABLE IF NOT EXISTS app_secrets (key TEXT PRIMARY KEY, value_json TEXT NOT NULL)")
    db("""CREATE TABLE IF NOT EXISTS push_subscriptions (endpoint TEXT PRIMARY KEY, user_id INTEGER, p256dh TEXT, auth TEXT,
          user_agent TEXT, created_at TEXT, last_ok_at TEXT, failures INTEGER DEFAULT 0)""")
    try:
        db("ALTER TABLE signal_plans ADD COLUMN alerted INTEGER DEFAULT 0")
    except Exception:
        pass   # column exists


def subscriptions(db: Callable, user_id: int = 1) -> list[dict[str, Any]]:
    rows = db("SELECT endpoint, p256dh, auth FROM push_subscriptions WHERE user_id=?", [user_id], "all") or []
    return [{"endpoint": r["endpoint"], "keys": {"p256dh": r["p256dh"], "auth": r["auth"]}} for r in rows]


def push_to_all(db: Callable, message: dict[str, Any], now_iso: Callable[[], str], user_id: int = 1) -> dict[str, int]:
    sent = failed = removed = 0
    for sub in subscriptions(db, user_id):
        ok, status, detail = send_push(db, sub, message)
        if ok:
            sent += 1
            db("UPDATE push_subscriptions SET last_ok_at=?, failures=0 WHERE endpoint=?", [now_iso(), sub["endpoint"]])
        elif status in (404, 410):
            removed += 1
            db("DELETE FROM push_subscriptions WHERE endpoint=?", [sub["endpoint"]])
        else:
            failed += 1
            log.warning("push failed %s: %s", status, detail)
            db("UPDATE push_subscriptions SET failures=COALESCE(failures,0)+1 WHERE endpoint=?", [sub["endpoint"]])
    return {"sent": sent, "failed": failed, "removed": removed}
