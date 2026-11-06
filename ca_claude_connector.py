"""
CA Trader MCP server (read-only).

Exposes CA Trader's existing market, recommendation and portfolio data to
Claude as a remote MCP connector over Streamable HTTP (JSON responses, no SSE).

Endpoint:  POST https://<your-domain>/mcp/<CA_TRADER_MCP_SECRET>

Security:
  * Disabled unless CA_TRADER_MCP_SECRET is set (min 24 chars).
  * The secret lives only in the URL path you paste into claude.ai.
  * Read-only: there are no order-placing, square-off or modify tools.
  * Data is returned as the user in CA_TRADER_MCP_USER_EMAIL
    (default: the first admin email).

Registered from app.py with:  register_mcp(app, sys.modules[__name__])
"""
from __future__ import annotations

import asyncio
import base64
import contextlib
import hashlib
import hmac
import inspect
import json
import math
import os
import secrets
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType
from typing import Any, Awaitable, Callable

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

BASE_DIR = Path(__file__).resolve().parent

SERVER_NAME = "ca-trader"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL = "2025-06-18"
TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "60m", "1D"]
MOVER_CATEGORIES = ["gainers", "losers", "high_volume", "unusual_volume", "turnover"]

INSTRUCTIONS = (
    "CA Trader: Santosh's Indian-market trading terminal backed by Upstox. "
    "Symbols are NSE/BSE trading symbols such as RELIANCE, TCS, NIFTY, BANKNIFTY "
    "(use search_instruments when unsure). Data tools are read-only. place_paper_order, square_off_position and send_alert "
    "act on the app's PAPER book and notifications only (never a real broker). Prices are Upstox quotes at call time."
)


# ---------------------------------------------------------------------------
# JSON helpers
# ---------------------------------------------------------------------------
def _clean(value: Any) -> Any:
    """Make any route result JSON-safe (numpy, datetimes, NaN/inf -> None)."""
    if isinstance(value, Response):
        try:
            return _clean(json.loads(bytes(value.body).decode("utf-8")))
        except Exception:
            return {"status_code": value.status_code}
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_clean(v) for v in value]
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if value is None or isinstance(value, (str, int, bool)):
        return value
    try:
        return _clean(jsonable_encoder(value))
    except Exception:
        try:
            f = float(value)  # numpy scalars
            return f if math.isfinite(f) else None
        except Exception:
            return str(value)


def _rpc_result(msg_id: Any, result: Any) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "result": result}


def _rpc_error(msg_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": code, "message": message}}


# ---------------------------------------------------------------------------
# Tool catalogue
# ---------------------------------------------------------------------------
def _schema(props: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {"type": "object", "properties": props, "required": required or [], "additionalProperties": False}


SYMBOL = {"type": "string", "description": "Trading symbol, e.g. RELIANCE, TCS, NIFTY, BANKNIFTY, or an Upstox instrument key"}

TOOLS: list[dict[str, Any]] = [
    {
        "name": "search_instruments",
        "description": "Search NSE/BSE/MCX instruments by name or symbol. Returns symbol, name, instrument_key, type, exchange, expiry, strike.",
        "inputSchema": _schema({"query": {"type": "string", "description": "Name or symbol fragment, e.g. 'hdfc bank'"}}, ["query"]),
    },
    {
        "name": "get_quotes",
        "description": "Current Upstox quotes (LTP, change, % change, OHLC, volume) for up to 50 symbols in one call.",
        "inputSchema": _schema({"symbols": {"type": "array", "items": {"type": "string"}, "minItems": 1, "maxItems": 50, "description": "List of trading symbols"}}, ["symbols"]),
    },
    {
        "name": "get_candles",
        "description": "OHLCV candles for charting, with the live quote merged into the last candle. Returns the most recent max_candles rows plus market session and staleness flags.",
        "inputSchema": _schema({
            "symbol": SYMBOL,
            "timeframe": {"type": "string", "enum": TIMEFRAMES, "default": "15m"},
            "days": {"type": "integer", "minimum": 1, "maximum": 3650, "default": 7, "description": "Look-back window in days"},
            "max_candles": {"type": "integer", "minimum": 20, "maximum": 2000, "default": 400},
        }, ["symbol"]),
    },
    {
        "name": "get_recommendation",
        "description": "CA Trader's full recommendation for a symbol: BUY/SELL/HOLD, confidence, entry, stop-loss, targets, technical indicators (RSI, MACD, ADX, Supertrend, ATR), patterns, news evidence and reasoning.",
        "inputSchema": _schema({
            "symbol": SYMBOL,
            "timeframe": {"type": "string", "enum": TIMEFRAMES, "default": "5m"},
            "desired_profit": {"type": "number", "description": "Optional target profit in rupees"},
            "bearable_loss": {"type": "number", "description": "Optional maximum loss in rupees"},
        }, ["symbol"]),
    },
    {
        "name": "get_market_movers",
        "description": "Top market movers by category.",
        "inputSchema": _schema({
            "category": {"type": "string", "enum": MOVER_CATEGORIES, "default": "gainers"},
            "limit": {"type": "integer", "minimum": 5, "maximum": 20, "default": 10},
        }),
    },
    {
        "name": "get_market_session",
        "description": "Whether the market segment is open now, plus session timings.",
        "inputSchema": _schema({"segment": {"type": "string", "enum": ["NSE_EQ", "NSE_FO", "BSE_EQ", "MCX_FO", "NSE_INDEX"], "default": "NSE_EQ"}}),
    },
    {
        "name": "get_option_chain",
        "description": "Option chain summary for an underlying (strikes, CE/PE LTP, OI, IV, greeks, PCR) for the nearest or given expiry.",
        "inputSchema": _schema({
            "underlying": {"type": "string", "description": "e.g. NIFTY, BANKNIFTY, RELIANCE"},
            "expiry": {"type": "string", "description": "Optional expiry date YYYY-MM-DD"},
        }, ["underlying"]),
    },
    {
        "name": "get_market_depth",
        "description": "Top-5 bid/ask market depth for a symbol.",
        "inputSchema": _schema({"symbol": SYMBOL}, ["symbol"]),
    },
    {
        "name": "get_news",
        "description": "Classified market news for a symbol or index with sentiment tags.",
        "inputSchema": _schema({
            "symbol": {"type": "string", "default": "NIFTY"},
            "limit": {"type": "integer", "minimum": 10, "maximum": 200, "default": 40},
        }),
    },
    {
        "name": "get_model_signal",
        "description": "CA Trader's backtested model call for a symbol at the latest daily close (live during market hours): BUY/SELL/HOLD, score, percentile, the 14 criteria with z-scores and weights, and the model's out-of-sample backtest stats.",
        "inputSchema": _schema({"symbol": SYMBOL}, ["symbol"]),
    },
    {
        "name": "get_trade_plans",
        "description": "CA Trader's official time-bound trade plans for a symbol: scalp (1m), intraday (5m) and swing (15m), each with BUY/SELL/NO_TRADE, entry zone, stop-loss, targets T1/T2, expiry, the factor scores and levels arithmetic behind it, the measured confidence (with sample size and 95% interval), the backtest track record, the live graded record and an edge grade.",
        "inputSchema": _schema({"symbol": SYMBOL}, ["symbol"]),
    },
    {
        "name": "get_plan_history",
        "description": "Plans CA Trader issued in the last N days and how each ended (T1, T2, stop-loss, time exit, expired), with hit rate and average R per horizon.",
        "inputSchema": _schema({
            "symbol": {"type": "string", "description": "Optional symbol filter, e.g. NIFTY"},
            "days": {"type": "integer", "minimum": 1, "maximum": 90, "default": 7},
            "horizon": {"type": "string", "enum": ["scalp", "intraday", "swing"], "description": "Optional horizon filter"},
        }),
    },
    {"name": "get_model_health", "description": "Latest weekly self-review of the trade-plan model (parameter tuning outcome, factor study, notes) and the live graded record per symbol and horizon over the last 30 days.", "inputSchema": _schema({})},
    {"name": "get_watchlists", "description": "The user's CA Trader watchlists and their symbols.", "inputSchema": _schema({})},
    {"name": "get_positions", "description": "Open paper-trading positions with live mark-to-market P&L.", "inputSchema": _schema({})},
    {"name": "get_holdings", "description": "Paper-trading holdings.", "inputSchema": _schema({})},
    {"name": "get_portfolio_snapshot", "description": "One-call snapshot of funds, positions, holdings and day P&L from the paper book.", "inputSchema": _schema({})},
    {"name": "get_context_log", "description": "Logged live context (order-book imbalance, option PCR, news tone; MCX front-month crude price as kind crude_fut) recorded every 30 minutes during market hours, for backtesting. Returns rows for a symbol (or all) over the last N days.",
     "inputSchema": _schema({"symbol": {"type": "string", "description": "Optional symbol, e.g. NIFTY"}, "days": {"type": "integer", "minimum": 1, "maximum": 365, "default": 30}})},
    {"name": "place_paper_order", "description": "Place a PAPER order in the CA Trader app's paper book (never a real broker). Market order at the live price, optional target and stop-loss which the app's paper risk engine enforces.",
     "inputSchema": _schema({
         "symbol": SYMBOL, "side": {"type": "string", "enum": ["BUY", "SELL"]},
         "quantity": {"type": "integer", "minimum": 1, "maximum": 1000000},
         "product": {"type": "string", "enum": ["I", "D"], "default": "I", "description": "I = intraday, D = delivery"},
         "target": {"type": "number"}, "stop_loss": {"type": "number"},
         "note": {"type": "string", "description": "Optional tag, e.g. the terminal call that triggered it"},
     }, ["symbol", "side", "quantity"])},
    {"name": "square_off_position", "description": "Close an open PAPER position at the live price.", "inputSchema": _schema({"position_id": {"type": "string"}}, ["position_id"])},
    {"name": "send_alert", "description": "Send a notification to the CA Trader app (bell icon) and the user's Telegram alerts, e.g. a new trade call or a 'consider exiting' warning.",
     "inputSchema": _schema({"title": {"type": "string", "maxLength": 120}, "body": {"type": "string", "maxLength": 600}, "severity": {"type": "string", "enum": ["info", "success", "warning", "critical"], "default": "info"}}, ["title", "body"])},
]
WRITE_TOOLS = {"place_paper_order", "square_off_position", "send_alert"}

for _t in TOOLS:
    _t["annotations"] = {"readOnlyHint": _t["name"] not in WRITE_TOOLS, "destructiveHint": False, "openWorldHint": True}


# ---------------------------------------------------------------------------
# Secret handling
# ---------------------------------------------------------------------------
def _resolve_secret(core: ModuleType, log: Any) -> str:
    """Env var wins; otherwise a random secret persisted next to the database
    (on the data volume, so it survives redeploys). Never stored in the repo."""
    env_secret = (os.getenv("CA_TRADER_MCP_SECRET") or "").strip()
    if len(env_secret) >= 24:
        return env_secret
    try:
        db_path = Path(str(getattr(core, "DB_PATH")))
        secret_file = db_path.parent / "mcp_secret.txt"
        if secret_file.exists():
            saved = secret_file.read_text(encoding="utf-8").strip()
            if len(saved) >= 24:
                return saved
        secret_file.parent.mkdir(parents=True, exist_ok=True)
        fresh = secrets.token_urlsafe(32)
        secret_file.write_text(fresh, encoding="utf-8")
        with contextlib.suppress(Exception):
            os.chmod(secret_file, 0o600)
        if log:
            log.info("Generated MCP connector secret at %s", secret_file)
        return fresh
    except Exception as exc:
        if log:
            log.warning("Could not create MCP secret file: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def register_mcp(app: FastAPI, core: ModuleType) -> None:
    """Mount the MCP endpoint on the FastAPI app. `core` is the app.py module."""
    log = getattr(core, "log", None)

    @app.get("/api/model/signal/{instrument}", include_in_schema=False)
    async def model_signal_route(instrument: str, request: Request) -> Response:
        """Backtested model call for the logged-in user (same result as the get_model_signal connector tool)."""
        user = core.current_user(request)
        if not user:
            return JSONResponse({"error": {"code": "AUTH_REQUIRED", "message": "Authentication required"}}, status_code=401)
        try:
            import ca_model
            data = await ca_model.model_signal(core, instrument if "|" in instrument else instrument.upper(), user)
        except Exception as exc:
            if log:
                log.warning("model signal failed for %s: %s", instrument, exc)
            return JSONResponse({"error": {"code": "MODEL_UNAVAILABLE", "message": "Model signal is unavailable right now"}}, status_code=503)
        return JSONResponse(_clean(data), headers={"Cache-Control": "no-store"})

    def _mcp_user() -> dict[str, Any]:
        email = (os.getenv("CA_TRADER_MCP_USER_EMAIL") or "santoshmadnani553@gmail.com").strip().lower()
        row = core.db_exec("SELECT id FROM users WHERE LOWER(email)=? AND is_active=1", [email], "one")
        if not row:
            row = core.db_exec("SELECT id FROM users WHERE role='admin' AND is_active=1 ORDER BY id LIMIT 1", fetch="one")
        if not row:
            raise RuntimeError("No CA Trader user found for the MCP connector")
        user = core.get_user(int(row["id"]))
        if not user:
            raise RuntimeError("MCP user is inactive")
        return user

    def _dummy_request() -> Request:
        return Request({"type": "http", "method": "GET", "path": "/mcp", "headers": [], "query_string": b"", "session": {}})

    def _sym(args: dict[str, Any], key: str = "symbol") -> str:
        value = str(args.get(key) or "").strip()
        if not value:
            raise ValueError(f"'{key}' is required")
        return value.upper() if "|" not in value else value

    def _tf(args: dict[str, Any], default: str) -> str:
        tf = str(args.get("timeframe") or default)
        if tf not in TIMEFRAMES:
            raise ValueError(f"timeframe must be one of {', '.join(TIMEFRAMES)}")
        return tf

    def _int(args: dict[str, Any], key: str, default: int, lo: int, hi: int) -> int:
        try:
            v = int(args.get(key, default))
        except (TypeError, ValueError):
            v = default
        return max(lo, min(hi, v))

    def _num(args: dict[str, Any], key: str) -> float | None:
        v = args.get(key)
        if v is None or v == "":
            return None
        return float(v)

    # ---- tool implementations (each reuses the app's own route logic) ----
    async def t_search(args, user):
        return await core.instrument_search(q=str(args.get("query") or "").strip()[:50], user=user)

    async def t_quotes(args, user):
        syms = [str(s).strip() if "|" in str(s) else str(s).strip().upper() for s in (args.get("symbols") or []) if str(s).strip()][:50]  # instrument keys keep their case (e.g. NSE_INDEX|India VIX)
        if not syms:
            raise ValueError("'symbols' must contain at least one symbol")
        return await core.market_quotes(instruments=",".join(syms), user=user)

    async def t_candles(args, user):
        res = _clean(await core.market_candles(_sym(args), timeframe=_tf(args, "15m"), days=_int(args, "days", 7, 1, 3650), user=user))
        cap = _int(args, "max_candles", 400, 20, 2000)
        if isinstance(res, dict) and isinstance(res.get("candles"), list):
            total = len(res["candles"])
            res["candles"] = res["candles"][-cap:]
            res["candles_total"] = total
        return res

    def _route_kwargs(fn: Callable[..., Any], **kwargs: Any) -> dict[str, Any]:
        """Some app routes take a `request` argument and some builds don't; pass one only when the route asks for it."""
        try:
            params = inspect.signature(fn).parameters
        except (TypeError, ValueError):
            return kwargs
        if "request" in params and "request" not in kwargs:
            kwargs["request"] = _dummy_request()
        return kwargs

    async def t_reco(args, user):
        fn = core.analysis_overall
        return await fn(_sym(args), **_route_kwargs(fn, timeframe=_tf(args, "5m"), desired_profit=_num(args, "desired_profit"), bearable_loss=_num(args, "bearable_loss"), user=user))

    async def t_model(args, user):
        import ca_model  # imported lazily so a missing file can never stop the app from starting
        return await ca_model.model_signal(core, _sym(args), user)

    async def t_plans(args, user):
        return await core.api_signals(_sym(args), user=user)

    async def t_plan_history(args, user):
        hz = str(args.get("horizon") or "").strip().lower() or None
        if hz is not None and hz not in ("scalp", "intraday", "swing"):
            raise ValueError("horizon must be scalp, intraday or swing")
        sym = str(args.get("symbol") or "").strip() or None
        return await core.api_signals_history(days=_int(args, "days", 7, 1, 90), symbol=sym, horizon=hz, user=user)

    async def t_model_health(args, user):
        from backend.services import model_health as mh   # lazy: a missing file can never stop the app from starting
        fwd = await asyncio.to_thread(mh.forward_table, core.db_exec, 30)
        return {"latest_review": mh.latest_journal(), "forward_30d": fwd}

    async def t_movers(args, user):
        cat = str(args.get("category") or "gainers")
        if cat not in MOVER_CATEGORIES:
            raise ValueError(f"category must be one of {', '.join(MOVER_CATEGORIES)}")
        return await core.market_movers(category=cat, limit=_int(args, "limit", 10, 5, 20), user=user)

    async def t_session(args, user):
        return core.market_session(str(args.get("segment") or "NSE_EQ"))

    async def t_options(args, user):
        expiry = str(args.get("expiry") or "").strip() or None
        return await core.options_summary(_sym(args, "underlying"), expiry=expiry, user=user)

    async def t_depth(args, user):
        return await core.market_depth(_sym(args), user=user)

    async def t_news(args, user):
        res = _clean(await core.news_unified(symbol=str(args.get("symbol") or "NIFTY").upper(), limit=150, user=user))
        cap = _int(args, "limit", 40, 10, 200)
        if isinstance(res, dict):
            for k in ("items", "articles", "events", "news"):
                if isinstance(res.get(k), list):
                    res[k] = res[k][:cap]
        return res

    async def t_watchlists(args, user):
        return await core.get_watchlists(_dummy_request(), user=user)

    async def t_positions(args, user):
        return await core.positions(_dummy_request(), user=user)

    async def t_holdings(args, user):
        return await core.holdings(_dummy_request(), user=user)

    async def t_paper_order(args, user):
        side = str(args.get("side") or "").upper()
        if side not in ("BUY", "SELL"):
            raise ValueError("side must be BUY or SELL")
        qty = _int(args, "quantity", 0, 0, 1_000_000)
        if qty < 1:
            raise ValueError("quantity must be at least 1")
        prod = "D" if str(args.get("product") or "I").upper() == "D" else "I"
        payload = core.OrderIn(symbol=_sym(args), side=side, quantity=qty, order_type="MARKET", product=prod, paper=True, live=False,
                               target=_num(args, "target"), stop_loss=_num(args, "stop_loss"),
                               entry_reco_json=json.dumps({"source": "claude-terminal", "note": str(args.get("note") or "")[:200]}))
        res = await core.order_create(payload, _dummy_request(), user=user)
        return res if isinstance(res, dict) else {"result": res}

    async def t_square_off(args, user):
        pid = str(args.get("position_id") or "").strip()
        if not pid:
            raise ValueError("'position_id' is required")
        return await core.position_square_off(pid, _dummy_request(), user=user)

    async def t_alert(args, user):
        title = str(args.get("title") or "").strip()[:120]
        body = str(args.get("body") or "").strip()[:600]
        if not title or not body:
            raise ValueError("title and body are required")
        sev = str(args.get("severity") or "info")
        sev = sev if sev in ("info", "success", "warning", "critical") else "info"
        key = "claude:" + hashlib.sha1((title + body).encode()).hexdigest()[:16]
        await core.add_notification(int(user["id"]), "risk_event", sev, 90.0, title, body, key)
        return {"ok": True, "sent": True}

    async def t_context_log(args, user):
        _ensure_context_table()
        days = _int(args, "days", 30, 1, 365)
        since = (datetime.utcnow().timestamp() - days * 86400)
        sym = str(args.get("symbol") or "").strip().upper()
        sql = "SELECT ts, symbol, kind, value, extra FROM ca_context_log WHERE ts >= ?" + (" AND symbol = ?" if sym else "") + " ORDER BY ts DESC LIMIT 5000"
        rows = core.db_exec(sql, [since] + ([sym] if sym else []), "all") or []
        return {"rows": rows, "count": len(rows)}

    async def t_snapshot(args, user):
        return await core.portfolio_snapshot(_dummy_request(), user=user)

    handlers: dict[str, Callable[[dict[str, Any], dict[str, Any]], Awaitable[Any]]] = {
        "search_instruments": t_search,
        "get_quotes": t_quotes,
        "get_candles": t_candles,
        "get_recommendation": t_reco,
        "get_model_signal": t_model,
        "get_trade_plans": t_plans,
        "get_plan_history": t_plan_history,
        "get_model_health": t_model_health,
        "get_market_movers": t_movers,
        "get_market_session": t_session,
        "get_option_chain": t_options,
        "get_market_depth": t_depth,
        "get_news": t_news,
        "get_watchlists": t_watchlists,
        "get_positions": t_positions,
        "get_holdings": t_holdings,
        "get_portfolio_snapshot": t_snapshot,
        "get_context_log": t_context_log,
        "place_paper_order": t_paper_order,
        "square_off_position": t_square_off,
        "send_alert": t_alert,
    }

    # ---- the shared terminal page on the app itself: same page as the Claude artifact, fed by the same handlers ----
    @app.post("/api/term/call", include_in_schema=False)
    async def term_call(request: Request) -> Response:
        """Run one read-only connector tool for the logged-in user. Body: {"tool": name, "args": {...}}."""
        user = core.current_user(request)
        if not user:
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        try:
            body = await request.json()
        except Exception:
            body = None
        name = str((body or {}).get("tool") or "")
        args = (body or {}).get("args") or {}
        fn = handlers.get(name)
        if fn is None or not isinstance(args, dict):
            return JSONResponse({"detail": f"Unknown tool: {name}"}, status_code=400)
        try:
            data = _clean(await fn(args, user))
        except Exception as exc:
            msg = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
            if log:
                log.warning("terminal tool %s failed: %s", name, msg)
            return JSONResponse({"detail": f"{name} failed: {msg}"}, status_code=502)
        return JSONResponse(data if isinstance(data, dict) else {"items": data}, headers={"Cache-Control": "no-store"})

    @app.get("/api/model/params", include_in_schema=False)
    async def model_params_route(request: Request) -> Response:
        if not core.current_user(request):
            return JSONResponse({"detail": "Authentication required"}, status_code=401)
        path = BASE_DIR / "ca_model_params.json"
        if not path.exists():
            return JSONResponse({"detail": "Model parameters are missing"}, status_code=404)
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")), headers={"Cache-Control": "no-store"})

    @app.get("/signals", include_in_schema=False)
    async def signals_page(request: Request) -> Response:
        """The CA Trader signal terminal (same page as the Claude artifact), fed by /api/term/call."""
        page = BASE_DIR / "ca_terminal.html"
        if not page.exists():
            return JSONResponse({"detail": "ca_terminal.html is missing"}, status_code=404)
        if getattr(core, "AUTH_ENABLED", True) and not core.current_user(request):
            return RedirectResponse("/login")
        headers = getattr(core, "HTML_PAGE_HEADERS", {"Cache-Control": "no-store"})
        wrap = getattr(core, "terminal_page_html", None)
        return HTMLResponse((wrap() if wrap else None) or page.read_text(encoding="utf-8"), headers=headers)

    # ---- context logger: order-book imbalance, PCR and news tone every 30 min in market hours ----
    def _ensure_context_table() -> None:
        core.db_exec("CREATE TABLE IF NOT EXISTS ca_context_log(ts REAL, symbol TEXT, kind TEXT, value REAL, extra TEXT)", fetch=None)
        core.db_exec("CREATE INDEX IF NOT EXISTS ix_ca_context_log ON ca_context_log(symbol, ts)", fetch=None)

    CONTEXT_SYMBOLS = ["NIFTY", "BANKNIFTY", "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "TCS", "SBIN", "AXISBANK", "KOTAKBANK", "LT",
                       "ITC", "BHARTIARTL", "HINDUNILVR", "MARUTI", "M&M", "SUNPHARMA", "TITAN", "NTPC", "POWERGRID", "BAJFINANCE",
                       "ASIANPAINT", "HCLTECH", "WIPRO", "ULTRACEMCO"]

    async def _log_context_once() -> int:
        user = _mcp_user(); now = datetime.utcnow().timestamp(); rows = []
        for sym in CONTEXT_SYMBOLS:
            try:
                d = _clean(await core.market_depth(sym, user=user))
                tb, ts = float(d.get("total_buy_quantity") or 0), float(d.get("total_sell_quantity") or 0)
                if tb + ts > 0:
                    rows.append((now, sym, "book_imbalance", (tb - ts) / (tb + ts), None))
            except Exception:
                pass
            await asyncio.sleep(0.3)
        for und in ("NIFTY", "BANKNIFTY"):
            try:
                ch = _clean(await core.options_summary(und, expiry=None, user=user))
                c = sum(float((x.get("call") or {}).get("oi") or 0) for x in ch.get("strikes") or [])
                p = sum(float((x.get("put") or {}).get("oi") or 0) for x in ch.get("strikes") or [])
                if c > 0:
                    rows.append((now, und, "pcr", p / c, None))
            except Exception:
                pass
        try:
            n = _clean(await core.news_unified(symbol="NIFTY", limit=60, user=user))
            items = (n or {}).get("events") or (n or {}).get("items") or []
            pos = sum(1 for e in items if "pos" in str(e.get("sentiment") or "").lower())
            neg = sum(1 for e in items if "neg" in str(e.get("sentiment") or "").lower())
            if items:
                rows.append((now, "NIFTY", "news_tone", (pos - neg) / len(items), json.dumps({"n": len(items), "pos": pos, "neg": neg})))
        except Exception:
            pass
        for r in rows:
            core.db_exec("INSERT INTO ca_context_log(ts, symbol, kind, value, extra) VALUES(?,?,?,?,?)", list(r), fetch=None)
        return len(rows)

    async def _log_crude_once() -> int:
        """MCX front-month CRUDEOIL futures price (rolls 3 days before expiry), so a continuous crude series builds up."""
        user = _mcp_user()
        res = _clean(await core.instrument_search(q="CRUDEOIL FUT", user=user))
        cut = (datetime.now(timezone(timedelta(hours=5, minutes=30))) + timedelta(days=3)).date().isoformat()
        futs = sorted((i for i in (res or {}).get("items") or []
                       if i.get("exchange") == "MCX" and i.get("instrument_type") == "FUT"
                       and str(i.get("symbol") or "").upper().startswith("CRUDEOIL FUT") and str(i.get("expiry") or "") > cut),
                      key=lambda i: str(i.get("expiry")))
        if not futs:
            return 0
        f = futs[0]
        q = _clean(await core.market_quotes(instruments=f["instrument_key"], user=user))
        it = ((q or {}).get("items") or [{}])[0]
        ltp = it.get("ltp")
        if not ltp:
            return 0
        extra = {"key": f["instrument_key"], "contract": f.get("symbol"), "expiry": f.get("expiry"),
                 "prev_close": it.get("prev_close") or it.get("cp"), "volume": it.get("volume"), "oi": it.get("oi")}
        core.db_exec("INSERT INTO ca_context_log(ts, symbol, kind, value, extra) VALUES(?,?,?,?,?)",
                     [datetime.utcnow().timestamp(), "CRUDEOIL", "crude_fut", float(ltp), json.dumps(extra)], fetch=None)
        return 1

    async def _context_loop() -> None:
        _ensure_context_table()
        while True:
            try:
                if (core.market_session("NSE_EQ") or {}).get("active"):
                    n = await _log_context_once()
                    if log:
                        log.info("context log: %d rows", n)
            except Exception as exc:
                if log:
                    log.warning("context log failed: %s", exc)
            try:
                if (core.market_session("MCX") or {}).get("active"):
                    await _log_crude_once()
            except Exception as exc:
                if log:
                    log.warning("crude log failed: %s", exc)
            await asyncio.sleep(1800)

    _ctx_started = {"v": False}

    @app.middleware("http")
    async def _start_context_logger(request: Request, call_next):
        if not _ctx_started["v"] and os.getenv("CA_CONTEXT_LOG", "1") == "1":
            _ctx_started["v"] = True
            asyncio.create_task(_context_loop())
        return await call_next(request)

    secret = _resolve_secret(core, log)
    if not secret:
        if log:
            log.warning("MCP endpoint disabled: no usable secret")
        return


    async def call_tool(name: str, args: dict[str, Any]) -> dict[str, Any]:
        fn = handlers.get(name)
        if fn is None:
            return {"content": [{"type": "text", "text": f"Unknown tool: {name}"}], "isError": True}
        try:
            data = _clean(await fn(args or {}, _mcp_user()))
        except Exception as exc:  # report as a tool error, never a transport error
            msg = getattr(exc, "detail", None) or str(exc) or exc.__class__.__name__
            if log:
                log.warning("MCP tool %s failed: %s", name, msg)
            return {"content": [{"type": "text", "text": f"{name} failed: {msg}"}], "isError": True}
        is_error = isinstance(data, dict) and isinstance(data.get("error"), dict) and len(data) == 1
        structured = data if isinstance(data, dict) else {"items": data}
        return {
            "content": [{"type": "text", "text": json.dumps(structured, ensure_ascii=False, allow_nan=False)}],
            "structuredContent": structured,
            "isError": bool(is_error),
        }

    async def handle_message(msg: Any) -> dict[str, Any] | None:
        if not isinstance(msg, dict) or msg.get("jsonrpc") != "2.0":
            return _rpc_error(None, -32600, "Invalid Request")
        method = msg.get("method")
        msg_id = msg.get("id")
        if method is None:  # a client response to us; nothing to do
            return None
        if "id" not in msg:  # notification (e.g. notifications/initialized)
            return None
        params = msg.get("params") or {}
        if method == "initialize":
            requested = str(params.get("protocolVersion") or "")
            version = requested if requested in SUPPORTED_PROTOCOLS else DEFAULT_PROTOCOL
            return _rpc_result(msg_id, {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": SERVER_NAME, "title": "CA Trader", "version": SERVER_VERSION},
                "instructions": INSTRUCTIONS,
            })
        if method == "ping":
            return _rpc_result(msg_id, {})
        if method == "tools/list":
            return _rpc_result(msg_id, {"tools": TOOLS})
        if method == "tools/call":
            name = str(params.get("name") or "")
            args = params.get("arguments") or {}
            if not isinstance(args, dict):
                return _rpc_error(msg_id, -32602, "arguments must be an object")
            return _rpc_result(msg_id, await call_tool(name, args))
        if method in ("resources/list", "prompts/list"):
            key = "resources" if method == "resources/list" else "prompts"
            return _rpc_result(msg_id, {key: []})
        return _rpc_error(msg_id, -32601, f"Method not found: {method}")

    def _authorized(token: str) -> bool:
        return hmac.compare_digest(token.encode("utf-8"), secret.encode("utf-8"))

    # ------------------------------------------------------------------
    # Minimal OAuth 2.1 (PKCE + dynamic client registration) so claude.ai's
    # "Connect" flow completes. Access requires a logged-in CA Trader admin.
    # Tokens are HMAC-signed with the connector secret, so they survive
    # restarts and need no database.
    # ------------------------------------------------------------------
    ACCESS_TTL = 24 * 3600
    REFRESH_TTL = 90 * 24 * 3600
    CODE_TTL = 300
    auth_codes: dict[str, dict[str, Any]] = {}

    def _base_url(request: Request) -> str:
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc).split(",")[0].strip()
        if proto == "http" and not host.startswith(("localhost", "127.0.0.1", "testserver")):
            proto = "https"
        return f"{proto}://{host}"

    def _b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")

    def _unb64(text: str) -> bytes:
        return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))

    def _sign(kind: str, ttl: int) -> str:
        payload = _b64(json.dumps({"k": kind, "exp": int(time.time()) + ttl, "n": secrets.token_hex(8)}, separators=(",", ":")).encode())
        sig = _b64(hmac.new(secret.encode(), f"{kind}.{payload}".encode(), hashlib.sha256).digest())
        return f"{payload}.{sig}"

    def _verify(token: str, kind: str) -> bool:
        try:
            payload, sig = token.split(".", 1)
            expected = _b64(hmac.new(secret.encode(), f"{kind}.{payload}".encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(sig, expected):
                return False
            data = json.loads(_unb64(payload))
            return data.get("k") == kind and int(data.get("exp", 0)) > time.time()
        except Exception:
            return False

    def _redirect_ok(uri: str) -> bool:
        try:
            p = urllib.parse.urlparse(uri)
        except Exception:
            return False
        host = (p.hostname or "").lower()
        if p.scheme == "https" and (host in ("claude.ai", "claude.com") or host.endswith((".claude.ai", ".claude.com", ".anthropic.com"))):
            return True
        return p.scheme == "http" and host in ("localhost", "127.0.0.1")

    def _token_pair() -> dict[str, Any]:
        return {
            "access_token": _sign("access", ACCESS_TTL),
            "token_type": "Bearer",
            "expires_in": ACCESS_TTL,
            "refresh_token": _sign("refresh", REFRESH_TTL),
            "scope": "mcp",
        }

    def _html(title: str, body: str, status: int = 200) -> Response:
        page = (
            "<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{title}</title><style>body{{font-family:system-ui,sans-serif;background:#0d1117;color:#e6edf3;"
            "display:flex;min-height:100vh;align-items:center;justify-content:center;margin:0;padding:16px}"
            ".c{max-width:420px;background:#161b22;border:1px solid #30363d;border-radius:12px;padding:24px}"
            "a,button{display:inline-block;margin:8px 8px 0 0;padding:10px 16px;border-radius:8px;border:0;"
            "background:#238636;color:#fff;text-decoration:none;font-size:15px;cursor:pointer}"
            "a.s{background:#30363d}</style></head>"
            f"<body><div class=c><h2>{title}</h2>{body}</div></body></html>"
        )
        return Response(page, status_code=status, media_type="text/html", headers={"Cache-Control": "no-store"})

    async def _read_params(request: Request) -> dict[str, str]:
        raw = (await request.body()).decode("utf-8", "replace")
        ctype = request.headers.get("content-type", "")
        if "json" in ctype:
            try:
                data = json.loads(raw or "{}")
                return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}
            except Exception:
                return {}
        return {k: v[0] for k, v in urllib.parse.parse_qs(raw).items()}

    @app.get("/.well-known/oauth-protected-resource/mcp/{token}", include_in_schema=False)
    async def oauth_resource_meta(token: str, request: Request) -> Response:
        if not _authorized(token):
            return JSONResponse({"error": "not found"}, status_code=404)
        base = _base_url(request)
        return JSONResponse({
            "resource": f"{base}/mcp/{token}",
            "authorization_servers": [base],
            "bearer_methods_supported": ["header"],
            "scopes_supported": ["mcp"],
        })

    @app.get("/.well-known/oauth-authorization-server", include_in_schema=False)
    async def oauth_server_meta(request: Request) -> Response:
        base = _base_url(request)
        return JSONResponse({
            "issuer": base,
            "authorization_endpoint": f"{base}/oauth/authorize",
            "token_endpoint": f"{base}/oauth/token",
            "registration_endpoint": f"{base}/oauth/register",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code", "refresh_token"],
            "code_challenge_methods_supported": ["S256"],
            "token_endpoint_auth_methods_supported": ["none"],
            "scopes_supported": ["mcp"],
        })

    @app.post("/oauth/register", include_in_schema=False)
    @app.post("/register", include_in_schema=False)
    async def oauth_register(request: Request) -> Response:
        try:
            meta = await request.json()
            if not isinstance(meta, dict):
                meta = {}
        except Exception:
            meta = {}
        uris = [u for u in (meta.get("redirect_uris") or []) if isinstance(u, str)]
        if not uris or not all(_redirect_ok(u) for u in uris):
            return JSONResponse({"error": "invalid_redirect_uri", "error_description": "Only claude.ai redirect URIs are allowed"}, status_code=400)
        return JSONResponse({
            "client_id": "ca-" + secrets.token_urlsafe(12),
            "client_id_issued_at": int(time.time()),
            "client_name": str(meta.get("client_name") or "Claude"),
            "redirect_uris": uris,
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
        }, status_code=201)

    @app.get("/oauth/authorize", include_in_schema=False)
    async def oauth_authorize(request: Request) -> Response:
        q = request.query_params
        redirect_uri = q.get("redirect_uri") or ""
        if not _redirect_ok(redirect_uri):
            return _html("Connection refused", "<p>This sign-in request did not come from Claude.</p>", 400)
        if q.get("response_type") != "code" or not q.get("code_challenge") or (q.get("code_challenge_method") or "S256") != "S256":
            return _html("Connection refused", "<p>Unsupported sign-in request.</p>", 400)
        user = core.current_user(request)
        if not user or not core.is_admin(user):
            return _html(
                "Log in to CA Trader first",
                "<p>Claude wants read-only access to your CA Trader data. Log in to CA Trader in this browser "
                "(as admin), then come back to this tab and tap <b>Try again</b>.</p>"
                "<a href='/login' target='_blank' rel='noopener'>Open CA Trader login</a>"
                "<button onclick='location.reload()' class=s>Try again</button>",
                401,
            )
        now = time.time()
        for k in [k for k, v in auth_codes.items() if v["exp"] < now]:
            auth_codes.pop(k, None)
        code = secrets.token_urlsafe(32)
        auth_codes[code] = {"challenge": q.get("code_challenge"), "redirect_uri": redirect_uri, "exp": now + CODE_TTL}
        params = {"code": code}
        if q.get("state"):
            params["state"] = q.get("state")
        sep = "&" if "?" in redirect_uri else "?"
        return RedirectResponse(f"{redirect_uri}{sep}{urllib.parse.urlencode(params)}", status_code=302)

    @app.post("/oauth/token", include_in_schema=False)
    async def oauth_token(request: Request) -> Response:
        p = await _read_params(request)
        grant = p.get("grant_type")
        no_store = {"Cache-Control": "no-store"}
        if grant == "authorization_code":
            entry = auth_codes.pop(p.get("code") or "", None)
            if not entry or entry["exp"] < time.time():
                return JSONResponse({"error": "invalid_grant", "error_description": "Code expired or unknown"}, status_code=400, headers=no_store)
            if p.get("redirect_uri") and p.get("redirect_uri") != entry["redirect_uri"]:
                return JSONResponse({"error": "invalid_grant", "error_description": "redirect_uri mismatch"}, status_code=400, headers=no_store)
            verifier = p.get("code_verifier") or ""
            computed = _b64(hashlib.sha256(verifier.encode()).digest())
            if not verifier or not hmac.compare_digest(computed, entry["challenge"]):
                return JSONResponse({"error": "invalid_grant", "error_description": "PKCE check failed"}, status_code=400, headers=no_store)
            return JSONResponse(_token_pair(), headers=no_store)
        if grant == "refresh_token":
            if not _verify(p.get("refresh_token") or "", "refresh"):
                return JSONResponse({"error": "invalid_grant", "error_description": "Refresh token invalid or expired"}, status_code=400, headers=no_store)
            return JSONResponse(_token_pair(), headers=no_store)
        return JSONResponse({"error": "unsupported_grant_type"}, status_code=400, headers=no_store)

    @app.post("/mcp/{token}", include_in_schema=False)
    async def mcp_post(token: str, request: Request) -> Response:
        if not _authorized(token):
            return JSONResponse({"error": "not found"}, status_code=404)
        auth = request.headers.get("authorization") or ""
        if auth.lower().startswith("bearer ") and not _verify(auth[7:].strip(), "access"):
            meta = f"{_base_url(request)}/.well-known/oauth-protected-resource/mcp/{token}"
            return JSONResponse({"error": "invalid_token"}, status_code=401,
                                headers={"WWW-Authenticate": f'Bearer error="invalid_token", resource_metadata="{meta}"'})
        try:
            body = await request.json()
        except Exception:
            return JSONResponse(_rpc_error(None, -32700, "Parse error"), status_code=400)
        if isinstance(body, list):
            replies = [r for r in [await handle_message(m) for m in body] if r is not None]
            return JSONResponse(replies) if replies else Response(status_code=202)
        reply = await handle_message(body)
        if reply is None:
            return Response(status_code=202)
        return JSONResponse(reply, headers={"Cache-Control": "no-store"})

    @app.get("/mcp/{token}", include_in_schema=False)
    async def mcp_get(token: str) -> Response:
        if not _authorized(token):
            return JSONResponse({"error": "not found"}, status_code=404)
        # No server-initiated SSE stream; clients fall back to POST-only.
        return Response(status_code=405, headers={"Allow": "POST"})

    @app.delete("/mcp/{token}", include_in_schema=False)
    async def mcp_delete(token: str) -> Response:
        if not _authorized(token):
            return JSONResponse({"error": "not found"}, status_code=404)
        return Response(status_code=405, headers={"Allow": "POST"})

    @app.get("/api/admin/mcp-connector", include_in_schema=False)
    async def mcp_connector_url(request: Request) -> Response:
        """Admin-only: shows the full connector URL to paste into claude.ai."""
        user = core.current_user(request)
        if not user:
            return JSONResponse({"error": "Log in to CA Trader first, then reopen this page."}, status_code=401)
        if not core.is_admin(user):
            return JSONResponse({"error": "Admin only"}, status_code=403)
        proto = (request.headers.get("x-forwarded-proto") or request.url.scheme or "https").split(",")[0].strip()
        host = (request.headers.get("x-forwarded-host") or request.headers.get("host") or request.url.netloc).split(",")[0].strip()
        if proto == "http" and not host.startswith(("localhost", "127.0.0.1")):
            proto = "https"
        return JSONResponse({
            "connector_url": f"{proto}://{host}/mcp/{secret}",
            "how_to": "claude.ai > Settings > Connectors > Add custom connector > paste connector_url. Keep this URL private.",
            "tools": [t["name"] for t in TOOLS],
        }, headers={"Cache-Control": "no-store"})

    if log:
        log.info("MCP endpoint enabled at /mcp/<secret> with %d read-only tools", len(TOOLS))
