"""One event stream for everything that happens in CA Trader.

Every happening (a new call, an entry fill, live P&L, an exit, a bullish or bearish run, an agent action, important news,
market open/close, server housekeeping) is written once to the `app_events` table. From there it feeds:

* the app (the Activity feed and the mascot read `/api/events`),
* Telegram (a dispatcher sends queued events, respecting market hours, quiet hours, a rate limit and de-duplication).

Nothing here invents data: callers pass real prices, times and numbers. `SAMPLES` holds clearly-labelled example data used only
by `render_samples()` to show what each message looks like.

`db` is a callable with the signature of app.db_exec(sql, params, fetch).
"""
from __future__ import annotations

import json
import html
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

IST = timezone(timedelta(hours=5, minutes=30))
KEEP_DAYS = 14

# kind -> (icon, label, when it may go to Telegram)
#   market : only while the instrument's market is open (an event older than STALE_S when the dispatcher gets to it is dropped)
#   always : any time, except quiet hours (23:45-07:30 IST) unless severity is "critical"
KINDS: dict[str, tuple[str, str, str]] = {
    "call_new": ("🟢", "New trade call", "market"),
    "call_filled": ("✅", "Entry filled", "market"),
    "call_pnl": ("📊", "Live P&L", "market"),
    "call_t1": ("🎯", "Target 1 hit", "market"),
    "call_partial": ("🎯", "Closed after target 1", "market"),
    "call_target": ("🏁", "Target hit", "market"),
    "call_sl": ("🛑", "Stop-loss hit", "market"),
    "call_time": ("⏱️", "Time exit", "market"),
    "call_expired": ("⌛", "Call expired", "market"),
    "run": ("🚀", "Bullish / bearish run", "market"),
    "pattern": ("🕯️", "Pattern confirmed", "market"),
    "option_flow": ("🧩", "Option-chain shift", "market"),
    "news": ("📰", "Important news", "always"),
    "agent": ("🤖", "Agent update", "always"),
    "market": ("🔔", "Market status", "always"),
    "brief": ("🌅", "Brief", "always"),
    "summary": ("🧾", "Day summary", "always"),
    "risk": ("⚠️", "Risk", "always"),
    "system": ("🛠️", "Server", "always"),
}
STALE_S = {"call_pnl": 180, "run": 300, "pattern": 600, "option_flow": 600}
DEFAULT_STALE_S = 900
QUIET = ((23, 45), (7, 30))         # IST window with no Telegram except critical events
MAX_PER_MINUTE = 12                 # Telegram flood guard


def ensure_tables(db: Callable) -> None:
    db("""CREATE TABLE IF NOT EXISTS app_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT, ts TEXT NOT NULL, kind TEXT NOT NULL, severity TEXT NOT NULL DEFAULT 'info',
        symbol TEXT, title TEXT NOT NULL, body TEXT, data_json TEXT, dedupe TEXT,
        tg TEXT NOT NULL DEFAULT 'QUEUED', tg_note TEXT, tg_at TEXT)""")
    db("CREATE UNIQUE INDEX IF NOT EXISTS idx_app_events_dedupe ON app_events(dedupe) WHERE dedupe IS NOT NULL")
    db("CREATE INDEX IF NOT EXISTS idx_app_events_ts ON app_events(ts)")
    db("CREATE INDEX IF NOT EXISTS idx_app_events_tg ON app_events(tg)")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def esc(x: Any) -> str:
    return html.escape("" if x is None else str(x), quote=False)


def px(v: Any) -> str:
    try:
        return f"{float(v):,.2f}"
    except (TypeError, ValueError):
        return "—"


def sgn(v: Any, dp: int = 2) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{'+' if f > 0 else '−' if f < 0 else ''}{abs(f):,.{dp}f}"


def rs(v: Any) -> str:
    try:
        f = float(v)
    except (TypeError, ValueError):
        return "—"
    return f"{'+' if f > 0 else '−' if f < 0 else ''}₹{abs(f):,.0f}"


def hhmm(iso: Any) -> str:
    try:
        return datetime.fromisoformat(str(iso)).astimezone(IST).strftime("%H:%M")
    except Exception:
        return "—"


# ---------------------------------------------------------------------------------------------------------------------
# message text per kind. `d` carries real values from the caller.
# ---------------------------------------------------------------------------------------------------------------------

def _side_icon(side: Any) -> str:
    return "🟢" if str(side).upper() == "BUY" else "🔴"


def _fmt_call_new(d: dict[str, Any]) -> tuple[str, str]:
    side = str(d.get("side") or "").upper()
    sym = d.get("symbol")
    title = f"{_side_icon(side)} NEW CALL · {side} {sym} · {d.get('label') or d.get('horizon') or ''}".strip()
    lines = [
        f"<b>Entry</b> {px(d.get('entry'))}   (zone {px(d.get('entry_low'))} – {px(d.get('entry_high'))})",
        f"🎯 <b>Target 1</b> {px(d.get('target_1'))}   ·   Target 2 {px(d.get('target_2'))}",
        f"🛑 <b>Stop-loss</b> {px(d.get('stop_loss'))}   (risk {px(d.get('risk'))} pts)",
    ]
    if d.get("confidence_pct") is not None:
        lines.append(f"Chance T1 comes before the stop: <b>{d['confidence_pct']:.0f}%</b> (past n={d.get('confidence_n', '—')}) · R:R {d.get('rr', '—')}")
    if d.get("edge"):
        lines.append(f"Track record: {esc(d['edge'])}")
    for r in (d.get("reasons") or [])[:5]:
        lines.append(f"• {esc(r)}")
    lines.append(f"⏳ Valid until {hhmm(d.get('valid_until'))} IST. <i>Not a trade until price touches the zone.</i>")
    lines.append("<b>What to do:</b> place a limit order inside the zone with the stop-loss attached. If price runs away without touching the zone, skip it.")
    return title, "\n".join(lines)


def _fmt_call_filled(d: dict[str, Any]) -> tuple[str, str]:
    side = str(d.get("side") or "").upper()
    title = f"✅ ENTRY FILLED · {side} {d.get('symbol')} @ {px(d.get('fill_price'))}"
    body = (f"Price touched the entry zone at {hhmm(d.get('filled_at'))} IST, so this call is now live.\n"
            f"🛑 Stop-loss {px(d.get('stop_loss'))}   🎯 Target 1 {px(d.get('target_1'))}   Target 2 {px(d.get('target_2'))}\n"
            "<b>What to do:</b> make sure your stop-loss is in. Do not move it further away.")
    return title, body


def _fmt_call_pnl(d: dict[str, Any]) -> tuple[str, str]:
    side = str(d.get("side") or "").upper()
    pnl = d.get("pnl_rupees")
    title = f"📊 LIVE · {side} {d.get('symbol')} {sgn(d.get('pts'))} pts · {sgn(d.get('r'))}R"
    lines = [f"Entered {px(d.get('fill_price'))} at {hhmm(d.get('filled_at'))} · now <b>{px(d.get('ltp'))}</b>"]
    if pnl is not None:
        lines.append(f"Open P&amp;L: <b>{rs(pnl)}</b> on {d.get('qty')} qty ({esc(d.get('qty_note') or 'one lot')})")
    lines.append(f"🛑 {px(d.get('stop_loss'))}  ·  🎯 {px(d.get('target_1'))}  ·  Best so far {sgn(d.get('best_pts'))} pts")
    if d.get("hint"):
        lines.append(f"<b>What to do:</b> {esc(d['hint'])}")
    return title, "\n".join(lines)


def _fmt_exit(d: dict[str, Any], icon: str, what: str, advice: str) -> tuple[str, str]:
    side = str(d.get("side") or "").upper()
    r = d.get("r")
    title = f"{icon} {what} · {side} {d.get('symbol')} · {sgn(r)}R"
    lines = [f"Entry {px(d.get('fill_price'))} → exit {px(d.get('exit_price'))} at {hhmm(d.get('closed_at'))} IST"]
    if d.get("pnl_rupees") is not None:
        lines.append(f"Result: <b>{rs(d['pnl_rupees'])}</b> on {d.get('qty')} qty (before charges)")
    lines.append(f"<b>What to do:</b> {advice}")
    return title, "\n".join(lines)


def _fmt_run(d: dict[str, Any]) -> tuple[str, str]:
    up = str(d.get("direction")).lower() == "up"
    title = f"{'🚀 BULLISH' if up else '🔻 BEARISH'} RUN · {d.get('symbol')} {sgn(d.get('move_pct'))}% in {d.get('minutes')} min"
    lines = [f"{d.get('candles')} straight {'green' if up else 'red'} {d.get('timeframe')} candles from {px(d.get('from_price'))} to <b>{px(d.get('to_price'))}</b>",
             f"Move = {d.get('atr_multiple')}× the normal candle range · volume {d.get('volume_x', '—')}× average"]
    for r in (d.get("reasons") or [])[:3]:
        lines.append(f"• {esc(r)}")
    lines.append("<b>What to do:</b> " + (esc(d.get("advice")) or ("Do not chase a run that has already moved a lot. Wait for a small pullback and a fresh call before buying." if up else "Do not short after a big fall. Wait for a small bounce that fails, with a fresh call.")))
    return title, "\n".join(lines)


def _fmt_news(d: dict[str, Any]) -> tuple[str, str]:
    tone = str(d.get("tone") or "").upper()
    icon = "🟢" if tone == "POSITIVE" else "🔴" if tone == "NEGATIVE" else "📰"
    title = f"{icon} NEWS · {d.get('symbol') or 'Market'} · {esc(d.get('headline'))[:110]}"
    body = (f"Source: {esc(d.get('source'))} ({esc(d.get('source_tier') or '')})\n"
            f"Why it matters: {esc(d.get('why'))}\n"
            f"Expected effect: <b>{esc(tone or 'UNCLEAR')}</b> · impact {d.get('impact', '—')}/100")
    if d.get("url"):
        body += f"\n{esc(d['url'])}"
    return title, body


def _fmt_pattern(d: dict[str, Any]) -> tuple[str, str]:
    title = f"🕯️ {esc(d.get('name'))} · {d.get('symbol')} {d.get('timeframe')} ({esc(d.get('bias'))})"
    body = f"{esc(d.get('meaning'))}\nSeen at {px(d.get('price'))}; confirmation: {esc(d.get('confirm'))}.\n<b>What to do:</b> {esc(d.get('advice') or 'Treat it as a hint, not a call. Act only on a published call.')}"
    return title, body


def _fmt_option_flow(d: dict[str, Any]) -> tuple[str, str]:
    title = f"🧩 OPTION CHAIN · {d.get('symbol')} · {esc(d.get('headline'))}"
    body = "\n".join(f"• {esc(x)}" for x in (d.get("points") or [])[:5]) + f"\n<b>Reading:</b> {esc(d.get('reading'))}"
    return title, body


def _fmt_agent(d: dict[str, Any]) -> tuple[str, str]:
    title = f"🤖 {esc(d.get('agent'))} · {esc(d.get('action'))}"
    return title, esc(d.get("detail") or "")


def _fmt_market(d: dict[str, Any]) -> tuple[str, str]:
    return f"🔔 {esc(d.get('title'))}", esc(d.get("detail") or "")


def _fmt_brief(d: dict[str, Any]) -> tuple[str, str]:
    lines = [esc(x) for x in (d.get("lines") or [])]
    return f"🌅 {esc(d.get('title') or 'Pre-market brief')}", "\n".join(lines)


def _fmt_summary(d: dict[str, Any]) -> tuple[str, str]:
    title = f"🧾 DAY SUMMARY · {esc(d.get('date'))}"
    lines = [f"Calls issued {d.get('issued', 0)} · filled {d.get('filled', 0)} · never reached entry {d.get('unfilled', 0)}",
             f"Winners {d.get('wins', 0)} · stopped {d.get('losses', 0)} · time exits {d.get('time_exits', 0)}",
             f"Total <b>{sgn(d.get('total_r'))}R</b>" + (f" · {rs(d.get('pnl_rupees'))}" if d.get("pnl_rupees") is not None else "")]
    for x in (d.get("notes") or [])[:4]:
        lines.append(f"• {esc(x)}")
    return title, "\n".join(lines)


def _fmt_risk(d: dict[str, Any]) -> tuple[str, str]:
    return f"⚠️ {esc(d.get('title'))}", esc(d.get("detail") or "")


def _fmt_system(d: dict[str, Any]) -> tuple[str, str]:
    return f"🛠️ {esc(d.get('title'))}", esc(d.get("detail") or "")


FORMATTERS: dict[str, Callable[[dict[str, Any]], tuple[str, str]]] = {
    "call_new": _fmt_call_new, "call_filled": _fmt_call_filled, "call_pnl": _fmt_call_pnl,
    "call_t1": lambda d: _fmt_exit(d, "🎯", "TARGET 1 HIT", "book half the position and move the stop to your entry. Let the rest run to target 2."),
    "call_partial": lambda d: _fmt_exit(d, "🎯", "CLOSED AFTER TARGET 1", "half was banked at target 1 and the rest was closed at your entry price (or by the time limit). Nothing more to do."),
    "call_target": lambda d: _fmt_exit(d, "🏁", "TARGET HIT", "close the trade. Do not re-enter at the same level."),
    "call_sl": lambda d: _fmt_exit(d, "🛑", "STOP-LOSS HIT", "the trade is over. A small planned loss is normal; do not average down or re-enter at once."),
    "call_time": lambda d: _fmt_exit(d, "⏱️", "TIME EXIT", "the call did not work out in time. Close it at the market and stand aside."),
    "call_expired": lambda d: (f"⌛ EXPIRED · {d.get('side')} {d.get('symbol')} never reached the entry zone", "Price did not come to the entry zone before the call expired, so no trade was taken and nothing is counted as profit or loss."),
    "run": _fmt_run, "news": _fmt_news, "pattern": _fmt_pattern, "option_flow": _fmt_option_flow, "agent": _fmt_agent,
    "market": _fmt_market, "brief": _fmt_brief, "summary": _fmt_summary, "risk": _fmt_risk, "system": _fmt_system,
}


def build(kind: str, d: dict[str, Any]) -> tuple[str, str]:
    fn = FORMATTERS.get(kind)
    if fn is None:
        return esc(d.get("title") or kind), esc(d.get("detail") or "")
    return fn(d)


# ---------------------------------------------------------------------------------------------------------------------
# write / read
# ---------------------------------------------------------------------------------------------------------------------

def emit(db: Callable, kind: str, data: dict[str, Any], *, symbol: str | None = None, severity: str = "info",
         dedupe: str | None = None, telegram: bool = True) -> int | None:
    """Store one event. Returns its id, or None when `dedupe` was already used. Never raises."""
    try:
        title, body = build(kind, {**data, "symbol": data.get("symbol", symbol)})
        tg = "QUEUED" if (telegram and kind in KINDS) else "OFF"
        db("INSERT OR IGNORE INTO app_events(ts, kind, severity, symbol, title, body, data_json, dedupe, tg) VALUES(?,?,?,?,?,?,?,?,?)",
           [_now().isoformat(), kind, severity, symbol or data.get("symbol"), title, body, json.dumps(data, default=str), dedupe, tg])
        row = db("SELECT id FROM app_events WHERE dedupe IS ? ORDER BY id DESC LIMIT 1", [dedupe], "one") if dedupe else db("SELECT MAX(id) AS id FROM app_events", [], "one")
        return int(row["id"]) if row and row.get("id") else None
    except Exception:
        return None


def recent(db: Callable, limit: int = 60, since_id: int = 0, kinds: list[str] | None = None, symbol: str | None = None) -> list[dict[str, Any]]:
    sql, args = "SELECT id, ts, kind, severity, symbol, title, body, data_json, tg, tg_note FROM app_events WHERE id > ?", [int(since_id)]
    if kinds:
        sql += f" AND kind IN ({','.join('?' * len(kinds))})"
        args += kinds
    if symbol:
        sql += " AND (symbol = ? OR symbol IS NULL)"
        args.append(symbol)
    sql += " ORDER BY id DESC LIMIT ?"
    args.append(max(1, min(int(limit), 300)))
    out = []
    for r in db(sql, args, "all") or []:
        try:
            r["data"] = json.loads(r.pop("data_json") or "{}")
        except Exception:
            r["data"] = {}
            r.pop("data_json", None)
        out.append(r)
    return out


def prune(db: Callable, days: int = KEEP_DAYS) -> int:
    cut = (_now() - timedelta(days=days)).isoformat()
    n = (db("SELECT COUNT(*) AS n FROM app_events WHERE ts < ?", [cut], "one") or {}).get("n") or 0
    if n:
        db("DELETE FROM app_events WHERE ts < ?", [cut])
    return int(n)


# ---------------------------------------------------------------------------------------------------------------------
# Telegram policy (pure functions so they can be tested)
# ---------------------------------------------------------------------------------------------------------------------

def in_quiet_hours(now: datetime | None = None) -> bool:
    t = (now or datetime.now(IST)).astimezone(IST)
    hm = (t.hour, t.minute)
    return hm >= QUIET[0] or hm < QUIET[1]


def decide(kind: str, severity: str, age_s: float, market_open: bool, now: datetime | None = None) -> tuple[bool, str]:
    """May this queued event go to Telegram right now? Returns (send, reason_if_not)."""
    if kind not in KINDS:
        return False, "unknown kind"
    when = KINDS[kind][2]
    if when == "market":
        if not market_open:
            return False, "market closed"
        if age_s > STALE_S.get(kind, DEFAULT_STALE_S):
            return False, "stale"
    else:
        if in_quiet_hours(now) and severity != "critical":
            return False, "quiet hours"
        if age_s > 6 * 3600:
            return False, "stale"
    return True, ""


def lot_pnl(side: str, entry: float, price: float, qty: int) -> float:
    return ((price - entry) if str(side).upper() == "BUY" else (entry - price)) * qty


# ---------------------------------------------------------------------------------------------------------------------
# sample data (clearly labelled) used only by render_samples()
# ---------------------------------------------------------------------------------------------------------------------

def _t(mins: int) -> str:
    return (datetime.now(IST).replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(minutes=mins)).isoformat()


SAMPLES: dict[str, dict[str, Any]] = {
    "call_new": {"symbol": "NIFTY", "side": "BUY", "label": "Intraday", "entry": 24520.0, "entry_low": 24512.0, "entry_high": 24528.0,
                 "target_1": 24566.0, "target_2": 24598.0, "stop_loss": 24488.0, "risk": 32.0, "confidence_pct": 57.6, "confidence_n": 412, "rr": 1.4,
                 "edge": "Unproven (backtest +0.08R after costs)", "valid_until": _t(30),
                 "reasons": ["Trend: 9 EMA above 21 above 50 on 5m", "15m and 60m both point up", "Price holding above VWAP 24,505", "Call-writers retreating at 24,600 (OI −8%)", "No negative news in the last 2 hours"]},
    "call_filled": {"symbol": "NIFTY", "side": "BUY", "fill_price": 24526.5, "filled_at": _t(12), "stop_loss": 24488.0, "target_1": 24566.0, "target_2": 24598.0},
    "call_pnl": {"symbol": "NIFTY", "side": "BUY", "fill_price": 24526.5, "filled_at": _t(12), "ltp": 24551.0, "pts": 24.5, "r": 0.77, "pnl_rupees": 1592.5, "qty": 65,
                 "qty_note": "1 lot", "stop_loss": 24488.0, "target_1": 24566.0, "best_pts": 29.0, "hint": "Price is 60% of the way to target 1. Keep the stop where it is."},
    "call_t1": {"symbol": "NIFTY", "side": "BUY", "fill_price": 24526.5, "exit_price": 24566.0, "closed_at": _t(41), "r": 1.23, "pnl_rupees": 2567.5, "qty": 65},
    "call_target": {"symbol": "NIFTY", "side": "BUY", "fill_price": 24526.5, "exit_price": 24598.0, "closed_at": _t(66), "r": 2.2, "pnl_rupees": 4647.5, "qty": 65},
    "call_sl": {"symbol": "BANKNIFTY", "side": "SELL", "fill_price": 52410.0, "exit_price": 52470.0, "closed_at": _t(55), "r": -1.0, "pnl_rupees": -1800.0, "qty": 30},
    "call_time": {"symbol": "RELIANCE", "side": "BUY", "fill_price": 2458.2, "exit_price": 2461.0, "closed_at": _t(120), "r": 0.25, "pnl_rupees": 280.0, "qty": 100},
    "call_expired": {"symbol": "TCS", "side": "SELL"},
    "run": {"symbol": "BANKNIFTY", "direction": "up", "move_pct": 0.62, "minutes": 25, "candles": 5, "timeframe": "5m", "from_price": 52180.0, "to_price": 52504.0,
            "atr_multiple": 2.4, "volume_x": 1.8, "reasons": ["Broke the morning high 52,420", "HDFCBANK and ICICIBANK leading"]},
    "news": {"symbol": "RELIANCE", "headline": "Reliance Jio wins ₹12,000 crore enterprise contract", "source": "Economic Times", "source_tier": "trusted business press",
             "why": "Large new revenue order, directly about this company", "tone": "POSITIVE", "impact": 72, "url": "https://example.com/sample"},
    "pattern": {"symbol": "HDFCBANK", "timeframe": "15m", "name": "Bullish engulfing at support", "bias": "bullish", "price": 1678.4,
                "meaning": "Buyers overwhelmed sellers right on a level where price bounced before.", "confirm": "next candle closes above 1,681"},
    "option_flow": {"symbol": "NIFTY", "headline": "Put writers building at 24,500", "points": ["Put OI at 24,500 +14% in 30 min", "PCR 1.12 (was 0.98)", "Max pain 24,500"],
                    "reading": "Support is being defended at 24,500. Favours buying dips, not chasing."},
    "agent": {"agent": "Plan Tracker", "action": "graded 3 plans", "detail": "NIFTY intraday: target 1 reached. BANKNIFTY scalp: stopped. TCS swing: still waiting for entry."},
    "market": {"title": "NSE market open", "detail": "Regular session 09:15–15:30 IST. Calls start after the first 15 minutes settle."},
    "brief": {"title": "Pre-market brief · 08:50", "lines": ["Global: S&P 500 +0.4%, Nasdaq +0.6%, Brent −0.8%", "India VIX 13.8 (calm)", "Watching: NIFTY, BANKNIFTY, RELIANCE", "No trades are taken before 09:30."]},
    "summary": {"date": "Fri 06 Nov", "issued": 6, "filled": 4, "unfilled": 2, "wins": 3, "losses": 1, "time_exits": 0, "total_r": 2.4, "pnl_rupees": 5300.0,
                "notes": ["Best: NIFTY intraday +2.2R", "Scalps were flat after costs"]},
    "risk": {"title": "Daily loss limit reached", "detail": "Auto-trade paused for today after ₹5,000 of paper losses. It resumes tomorrow after the open."},
    "system": {"title": "Server cleanup done", "detail": "Cleared 220 MB of old logs and caches. Free disk 61%, free RAM 310 MB."},
}


SAMPLES["call_partial"] = {"symbol": "NIFTY", "side": "BUY", "fill_price": 24526.5, "exit_price": 24526.5, "closed_at": _t(80), "r": 0.62, "pnl_rupees": 1300.0, "qty": 65}


def render_samples(label: bool = True) -> list[tuple[str, str, str]]:
    """(kind, title, body) for every kind. With label=True each title is prefixed so nobody mistakes it for a live call."""
    out = []
    for kind in KINDS:
        d = SAMPLES.get(kind)
        if d is None:
            continue
        title, body = build(kind, d)
        if label:
            title = "🧪 SAMPLE · " + title
            body = body + "\n<i>Example numbers, not a real trade.</i>"
        out.append((kind, title, body))
    return out
