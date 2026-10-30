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

import contextlib
import hmac
import json
import math
import os
import secrets
from datetime import date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any, Awaitable, Callable

from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

SERVER_NAME = "ca-trader"
SERVER_VERSION = "1.0.0"
SUPPORTED_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26", "2024-11-05")
DEFAULT_PROTOCOL = "2025-06-18"
TIMEFRAMES = ["1m", "3m", "5m", "15m", "30m", "60m", "1D"]
MOVER_CATEGORIES = ["gainers", "losers", "high_volume", "unusual_volume", "turnover"]

INSTRUCTIONS = (
    "CA Trader: Santosh's Indian-market trading terminal backed by Upstox. "
    "Symbols are NSE/BSE trading symbols such as RELIANCE, TCS, NIFTY, BANKNIFTY "
    "(use search_instruments when unsure). All tools are read-only; positions and "
    "holdings are the app's paper-trading book. Prices are Upstox quotes at call time."
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
    {"name": "get_watchlists", "description": "The user's CA Trader watchlists and their symbols.", "inputSchema": _schema({})},
    {"name": "get_positions", "description": "Open paper-trading positions with live mark-to-market P&L.", "inputSchema": _schema({})},
    {"name": "get_holdings", "description": "Paper-trading holdings.", "inputSchema": _schema({})},
    {"name": "get_portfolio_snapshot", "description": "One-call snapshot of funds, positions, holdings and day P&L from the paper book.", "inputSchema": _schema({})},
]

for _t in TOOLS:
    _t["annotations"] = {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": True}


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
    secret = _resolve_secret(core, log)
    if not secret:
        if log:
            log.warning("MCP endpoint disabled: no usable secret")
        return

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
        syms = [str(s).strip().upper() for s in (args.get("symbols") or []) if str(s).strip()][:50]
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

    async def t_reco(args, user):
        return await core.analysis_overall(_sym(args), timeframe=_tf(args, "5m"), desired_profit=_num(args, "desired_profit"), bearable_loss=_num(args, "bearable_loss"), user=user)

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

    async def t_snapshot(args, user):
        return await core.portfolio_snapshot(_dummy_request(), user=user)

    handlers: dict[str, Callable[[dict[str, Any], dict[str, Any]], Awaitable[Any]]] = {
        "search_instruments": t_search,
        "get_quotes": t_quotes,
        "get_candles": t_candles,
        "get_recommendation": t_reco,
        "get_market_movers": t_movers,
        "get_market_session": t_session,
        "get_option_chain": t_options,
        "get_market_depth": t_depth,
        "get_news": t_news,
        "get_watchlists": t_watchlists,
        "get_positions": t_positions,
        "get_holdings": t_holdings,
        "get_portfolio_snapshot": t_snapshot,
    }

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

    @app.post("/mcp/{token}", include_in_schema=False)
    async def mcp_post(token: str, request: Request) -> Response:
        if not _authorized(token):
            return JSONResponse({"error": "not found"}, status_code=404)
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
