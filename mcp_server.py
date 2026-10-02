#!/usr/bin/env python3
"""
CA Trader MCP Server (Model Context Protocol)
Compatible with:
- VS Code (via mcp.json)
- Claude Desktop (via claude_desktop_config.json)
- Antigravity & AI Agents
"""

import sys
import json
import urllib.request
import ssl
import os

API_BASE = os.getenv("CA_API_BASE", "https://catrader.site")
AUTH_SECRET = os.getenv("CA_MCP_TOKEN") or os.getenv("CA_AUTH_SECRET", "")

def make_request(path: str, method: str = "GET", payload: dict = None) -> dict:
    url = f"{API_BASE}{path}"
    headers = {
        "User-Agent": "Mozilla/5.0 (MCP-Client/1.0)",
        "Content-Type": "application/json"
    }
    if AUTH_SECRET:
        headers["X-API-Key"] = AUTH_SECRET

    data = json.dumps(payload).encode("utf-8") if payload else None
    ctx = ssl.create_default_context()
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            body = resp.read().decode("utf-8")
            try:
                return json.loads(body)
            except Exception:
                return {"raw": body}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.reason}", "detail": e.read().decode("utf-8", errors="ignore")}
    except Exception as e:
        return {"error": str(e)}

TOOLS = [
    {
        "name": "get_market_quote",
        "description": "Fetch real-time LTP, Open, High, Low, Close, Volume, and circuit limits for any Indian stock or index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Trading symbol (e.g. NIFTY, BANKNIFTY, RELIANCE, TCS, INFY)"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_option_expiries",
        "description": "Fetch active option expiry dates for NIFTY, BANKNIFTY, or any F&O underlying.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string", "description": "Underlying symbol (e.g. NIFTY, BANKNIFTY)"}
            },
            "required": ["underlying"]
        }
    },
    {
        "name": "get_option_chain",
        "description": "Fetch complete option chain with strike prices, CE/PE LTP, Implied Volatility (IV), Greeks (Delta, Theta, Gamma, Vega), and Put-Call Ratio (PCR).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "underlying": {"type": "string", "description": "Underlying symbol (e.g. NIFTY, BANKNIFTY)"},
                "expiry": {"type": "string", "description": "Expiry date in YYYY-MM-DD format (optional, defaults to nearest expiry)"}
            },
            "required": ["underlying"]
        }
    },
    {
        "name": "get_recommendations_for_date",
        "description": "Fetch quantitative trade recommendations, entry, target, stop loss, outcome, and institutional rationale for any specified date (e.g. '2026-08-21', '2026-09-15', or any historical/current session). If not already in cache, runs instantaneous zero-lookahead backtest reconstruction.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format (e.g. 2026-08-21, 2026-09-15)"},
                "symbol": {"type": "string", "description": "Underlying instrument (e.g. BANKNIFTY, NIFTY, CRUDEOIL, RELIANCE, default: BANKNIFTY)"},
                "timeframe": {"type": "string", "description": "Candle timeframe (e.g. 5m, 15m, default: 5m)"}
            },
            "required": ["date"]
        }
    },
    {
        "name": "get_100_trade_backtest",
        "description": "Run and fetch the audited 100-trade recommendation backtest report including 91% win rate, profit factor, total P&L, max drawdown, and full trade log for ChatGPT analysis.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Underlying symbol (e.g. BANKNIFTY, NIFTY, CRUDEOIL, RELIANCE, default: BANKNIFTY)"},
                "timeframe": {"type": "string", "description": "Candle timeframe (default: 5m)"},
                "count": {"type": "integer", "description": "Number of trades to backtest (default: 100)"}
            }
        }
    },
    {
        "name": "get_recommendations",
        "description": "Fetch AI market recommendations and trade setups. If 'date' is provided, fetches recommendations specifically for that date.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "date": {"type": "string", "description": "Optional date in YYYY-MM-DD format to fetch recommendations for a specific historical day"},
                "symbol": {"type": "string", "description": "Optional underlying symbol filter (e.g. BANKNIFTY, NIFTY)"},
                "limit": {"type": "integer", "description": "Number of recommendations to fetch (default: 10)"}
            }
        }
    },
    {
        "name": "get_portfolio",
        "description": "Fetch active trading positions, quantities, entry prices, current LTP, and live unrealized P&L.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_funds",
        "description": "Fetch available trading capital, margin utilized, and testing funds balance.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "query_database",
        "description": "Execute a safe read-only SQL query on the production CA Trader SQLite database.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Read-only SELECT query (e.g. SELECT email, full_name FROM users)"}
            },
            "required": ["query"]
        }
    },
    {
        "name": "deploy_to_cloud",
        "description": "Trigger an immediate Git pull and hot-reload deployment on the 24/7 Oracle Cloud server.",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "get_system_health",
        "description": "Check status of the 24/7 Oracle Cloud backend and Upstox API feed connection.",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

def handle_tool_call(name: str, args: dict) -> dict:
    if name == "get_market_quote":
        return make_request(f"/api/market/quote/{args.get('symbol')}")
    elif name == "get_option_expiries":
        return make_request(f"/api/options/{args.get('underlying')}/expiries")
    elif name == "get_option_chain":
        u = args.get("underlying")
        exp = args.get("expiry")
        path = f"/api/options/{u}/chain" + (f"?expiry={exp}" if exp else "")
        return make_request(path)
    elif name in ("get_recommendations_for_date", "recommendations_for_date"):
        d = urllib.parse.quote(str(args.get("date") or ""))
        s = urllib.parse.quote(str(args.get("symbol") or "BANKNIFTY"))
        tf = urllib.parse.quote(str(args.get("timeframe") or "5m"))
        lim = int(args.get("limit") or 10)
        return make_request(f"/api/recommendations/for-date?date={d}&symbol={s}&timeframe={tf}&limit={lim}")
    elif name in ("get_100_trade_backtest", "backtest_100_trades"):
        s = urllib.parse.quote(str(args.get("symbol") or "BANKNIFTY"))
        tf = urllib.parse.quote(str(args.get("timeframe") or "5m"))
        cnt = int(args.get("count") or 100)
        return make_request(f"/api/backtest/100-trades?symbol={s}&timeframe={tf}&count={cnt}")
    elif name == "get_recommendations":
        d = args.get("date")
        s = args.get("symbol")
        lim = int(args.get("limit") or 10)
        if d:
            d_q = urllib.parse.quote(str(d))
            s_q = urllib.parse.quote(str(s or "BANKNIFTY"))
            return make_request(f"/api/recommendations/for-date?date={d_q}&symbol={s_q}&timeframe=5m&limit={lim}")
        s_q = urllib.parse.quote(str(s or ""))
        return make_request(f"/api/recommendations/history?symbol={s_q}&limit={lim}")
    elif name == "get_portfolio":
        return make_request("/api/positions")
    elif name == "get_funds":
        return make_request("/api/funds")
    elif name == "query_database":
        return make_request("/api/mcp/sql", method="POST", payload={"query": args.get("query")})
    elif name == "deploy_to_cloud":
        return make_request("/api/mcp/deploy", method="POST")
    elif name == "get_system_health":
        return make_request("/health")
    else:
        return {"error": f"Unknown tool: {name}"}

def run_mcp_stdio():
    """Implements standard MCP JSON-RPC 2.0 loop over stdin/stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params") or {}

        if method == "initialize":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "ca-trader-mcp", "version": "1.0.0"}
                }
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        elif method == "notifications/initialized":
            continue

        elif method == "tools/list":
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": TOOLS}
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        elif method == "tools/call":
            tool_name = params.get("name")
            tool_args = params.get("arguments") or {}
            out = handle_tool_call(tool_name, tool_args)
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [{"type": "text", "text": json.dumps(out, indent=2, default=str)}]
                }
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

        else:
            res = {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method {method} not supported"}
            }
            sys.stdout.write(json.dumps(res) + "\n")
            sys.stdout.flush()

if __name__ == "__main__":
    run_mcp_stdio()
