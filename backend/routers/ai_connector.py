import os
import subprocess
import sqlite3
import hmac
import py_compile
from datetime import datetime, timezone, timedelta
from typing import Any
from fastapi import APIRouter, Header, HTTPException, Query, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/mcp", tags=["AI & MCP Connector"])

def get_auth_token():
    return os.getenv("CA_MCP_TOKEN") or os.getenv("CA_AUTH_SECRET") or ""

def verify_ai_auth(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    authorization: str | None = Header(None)
) -> bool:
    secret = get_auth_token()
    if not secret:
        return True
    
    token = x_api_key or ""
    if not token and authorization:
        if authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "").strip()
        else:
            token = authorization.strip()
            
    if token and hmac.compare_digest(token, secret):
        return True
        
    raise HTTPException(
        status_code=401,
        detail={"code": "UNAUTHORIZED", "message": "Invalid or missing X-API-Key / Bearer token"}
    )

class UniversalQueryIn(BaseModel):
    query: str = Field(..., description="Natural language question, command, or request for CA Trader")
    action: str | None = Field(None, description="Optional action category hint: quote, historical, options, setup, positions, funds, deployment, diagnostics, news, sql")
    symbol: str | None = Field(None, description="Optional stock/index symbol (e.g. RELIANCE, NIFTY)")
    date: str | None = Field(None, description="Optional target trading date in YYYY-MM-DD format")
    params: dict[str, Any] | None = Field(default_factory=dict, description="Optional additional parameters")

class SqlQueryIn(BaseModel):
    query: str = Field(..., description="Read-only SQL query (SELECT queries only)")

@router.get("/openapi.json")
async def get_mcp_openapi():
    """Returns a focused OpenAPI 3.0 specification tailored for ChatGPT Actions and Gemini Function Calling."""
    """Returns a focused OpenAPI 3.0.1 specification tailored for ChatGPT Actions, Gemini, and MCP clients."""
    return _build_openapi_spec()

@router.get("/openapi.yaml", response_class=PlainTextResponse)
async def get_mcp_openapi_yaml():
    """Returns the OpenAPI 3.0.1 specification in YAML format for direct import into ChatGPT Actions."""
    spec = _build_openapi_spec()
    try:
        import yaml
        return yaml.dump(spec, sort_keys=False)
    except Exception:
        import json
        return json.dumps(spec, indent=2)

def _build_openapi_spec():
    return {
        "openapi": "3.1.0",
        "info": {
            "title": "CA Trader AI Assistant & MCP API",
            "description": "Secure API connector for ChatGPT, Gemini, and AI assistants to inspect live market quotes, option chains, portfolios, trade setups, deployment history, and server diagnostics.",
            "version": "1.0.0"
        },
        "servers": [
            {"url": "https://catrader.site", "description": "Production Oracle Cloud 24/7 Server"}
        ],
        "paths": {
            "/api/mcp/query": {
                "post": {
                    "summary": "Universal CA Trader Query & Tool Dispatcher",
                    "description": "Universal gateway for CA Trader. Use this to execute ANY query, retrieval, calculation, or task: live quotes, historical prices for any date, option chains, trade setups, positions, portfolio funds, server deployment info, diagnostics, news, or custom trading questions. Dynamically routes to all backend tools and data sources without requiring schema updates.",
                    "operationId": "universalQuery",
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/UniversalQueryIn"}
                            }
                        }
                    },
                    "responses": {
                        "200": {
                            "description": "Universal query response with structured data and summary",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/UniversalQueryOut"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/market/quote/{instrument}": {
                "get": {
                    "summary": "Get Live Market Quote",
                    "description": "Returns current market LTP, Open, High, Low, Close, Volume, and circuit limits for any stock or index.",
                    "operationId": "getMarketQuote",
                    "parameters": [
                        {"name": "instrument", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Trading symbol (e.g. NIFTY, BANKNIFTY, RELIANCE, TCS)"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Live quote data",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/MarketQuote"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/market/historical/{instrument}": {
                "get": {
                    "summary": "Get Historical Stock/Index Prices & Daily OHLC",
                    "description": "Returns official historical OHLC prices (Open, High, Low, Close, Volume, and Change) for any stock or index on a specific date (e.g. 2026-09-24) or over a historical range. Always use this when the user asks for closing price on a past date or historical market data.",
                    "operationId": "getHistoricalPrices",
                    "parameters": [
                        {"name": "instrument", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Trading symbol (e.g. RELIANCE, NIFTY, BANKNIFTY, TCS)"},
                        {"name": "date", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Specific historical trading date in YYYY-MM-DD format (e.g. 2026-09-24) to retrieve exact closing price, open, high, low, and volume."},
                        {"name": "timeframe", "in": "query", "required": False, "schema": {"type": "string", "default": "1D"}, "description": "Candle timeframe: 1D (daily), 15m, 5m, 1m, 60m"},
                        {"name": "days", "in": "query", "required": False, "schema": {"type": "integer", "default": 30}, "description": "Number of days of history to fetch (1-365)"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Historical price and candle details",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HistoricalPriceResponse"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/options/{underlying}/expiries": {
                "get": {
                    "summary": "Get Option Expiries",
                    "description": "Returns active expiry dates for an underlying index or stock.",
                    "operationId": "getOptionExpiries",
                    "parameters": [
                        {"name": "underlying", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Underlying symbol (e.g. NIFTY, BANKNIFTY)"}
                    ],
                    "responses": {
                        "200": {
                            "description": "List of active expiry dates",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/OptionExpiries"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/options/{underlying}/chain": {
                "get": {
                    "summary": "Get Full Option Chain",
                    "description": "Returns CE/PE strike prices, LTP, IV, Greeks (Delta, Theta, Gamma, Vega), and Put-Call Ratio (PCR).",
                    "operationId": "getOptionChain",
                    "parameters": [
                        {"name": "underlying", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Underlying symbol (e.g. NIFTY)"},
                        {"name": "expiry", "in": "query", "required": False, "schema": {"type": "string"}, "description": "Target expiry date (YYYY-MM-DD)"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Complete option chain table",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/OptionChain"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/recommendations/{instrument}": {
                "get": {
                    "summary": "Get Live AI Trade Recommendation for Symbol",
                    "description": "Returns current live algorithmic trade setup with calculated Entry, Target, Stop Loss, Greeks, and confidence for any stock or index.",
                    "operationId": "getRecommendationForSymbol",
                    "parameters": [
                        {"name": "instrument", "in": "path", "required": True, "schema": {"type": "string"}, "description": "Trading symbol (e.g. NIFTY, BANKNIFTY, RELIANCE)"},
                        {"name": "timeframe", "in": "query", "required": False, "schema": {"type": "string", "default": "5m"}, "description": "Analysis timeframe (e.g. 1m, 5m, 15m, 1h)"}
                    ],
                    "responses": {
                        "200": {
                            "description": "Algorithmic trade setup details",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/TradeRecommendation"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/recommendations/history": {
                "get": {
                    "summary": "Get AI Trade Recommendations History",
                    "description": "Returns recent AI trade setups audit history with entry, target, stop-loss, and rationale.",
                    "operationId": "getRecommendationsHistory",
                    "responses": {
                        "200": {
                            "description": "Recent recommendations history",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/RecommendationHistory"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/positions": {
                "get": {
                    "summary": "Get Active Trading Positions",
                    "description": "Returns open positions, quantity, buy price, current LTP, and unrealized P&L.",
                    "operationId": "getPositions",
                    "responses": {
                        "200": {
                            "description": "List of positions",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/PositionList"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/funds": {
                "get": {
                    "summary": "Get Account Funds & Margin",
                    "description": "Returns available cash, margin used, and trading capital breakdown.",
                    "operationId": "getFunds",
                    "responses": {
                        "200": {
                            "description": "Account funds breakdown",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/FundSummary"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/mcp/system/deployment": {
                "get": {
                    "summary": "Get Server Deployment Information",
                    "description": "Returns the exact time of the last server deployment, the latest Git commit hash, branch, author, commit message, list of changed files, and the 5 most recent commit summaries.",
                    "operationId": "getDeploymentInfo",
                    "responses": {
                        "200": {
                            "description": "Server deployment details and Git change log",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/DeploymentInfo"}
                                }
                            }
                        }
                    }
                }
            },
            "/api/mcp/system/diagnostics": {
                "get": {
                    "summary": "Get System Diagnostics & Error Integrity",
                    "description": "Performs an automated health check: verifies syntax integrity of terminal.html and app.py, checks for any diff truncation residue, queries recent server/client errors from SQLite, and checks WebSocket feed connectivity.",
                    "operationId": "getSystemDiagnostics",
                    "responses": {
                        "200": {
                            "description": "System diagnostics, syntax check, and error report",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/SystemDiagnostics"}
                                }
                            }
                        }
                    }
                }
            },
            "/health": {
                "get": {
                    "summary": "Get Server & Provider Health",
                    "description": "Checks server health and Upstox API connectivity status.",
                    "operationId": "getHealth",
                    "responses": {
                        "200": {
                            "description": "System health status",
                            "content": {
                                "application/json": {
                                    "schema": {"$ref": "#/components/schemas/HealthStatus"}
                                }
                            }
                        }
                    }
                }
            }
        },
        "components": {
            "schemas": {
                "UniversalQueryIn": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "Natural language question, command, or request (e.g. 'Closing price of RELIANCE on 2026-09-24', 'NIFTY option chain', 'Server deployment history', 'Check system diagnostics')"
                        },
                        "action": {
                            "type": "string",
                            "description": "Optional category hint: quote, historical, options, setup, positions, funds, deployment, diagnostics, news, sql"
                        },
                        "symbol": {
                            "type": "string",
                            "description": "Optional instrument symbol (e.g. RELIANCE, NIFTY, BANKNIFTY, TCS)"
                        },
                        "date": {
                            "type": "string",
                            "description": "Optional trading date in YYYY-MM-DD format (e.g. 2026-09-24)"
                        },
                        "params": {
                            "type": "object",
                            "description": "Optional arbitrary key-value parameters"
                        }
                    }
                },
                "UniversalQueryOut": {
                    "type": "object",
                    "properties": {
                        "success": {"type": "boolean"},
                        "action_executed": {"type": "string"},
                        "summary": {"type": "string", "description": "Direct, human-readable answer for the user"},
                        "data": {"type": "object", "description": "Structured payload for the requested action"},
                        "timestamp": {"type": "string"}
                    }
                },
                "MarketQuote": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Trading instrument symbol"},
                        "ltp": {"type": "number", "description": "Last traded price"},
                        "open": {"type": "number", "description": "Session opening price"},
                        "high": {"type": "number", "description": "Session high"},
                        "low": {"type": "number", "description": "Session low"},
                        "close": {"type": "number", "description": "Current or closing price"},
                        "prev_close": {"type": "number", "description": "Previous completed trading day close price"},
                        "cp": {"type": "number", "description": "Previous completed trading day close price"},
                        "previous_trading_date": {"type": "string", "description": "Date of the previous completed trading day (YYYY-MM-DD)"},
                        "volume": {"type": "number", "description": "Total traded volume"}
                    }
                },
                "HistoricalPriceResponse": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Trading symbol"},
                        "requested_date": {"type": "string", "nullable": True, "description": "Requested date or null"},
                        "date_found": {"type": "boolean", "description": "True if an exact trading session was found for requested date"},
                        "target_candle": {
                            "type": "object",
                            "nullable": True,
                            "properties": {
                                "date": {"type": "string", "description": "Trading date in YYYY-MM-DD format"},
                                "open": {"type": "number", "description": "Open price"},
                                "high": {"type": "number", "description": "Day high price"},
                                "low": {"type": "number", "description": "Day low price"},
                                "close": {"type": "number", "description": "Closing price"},
                                "volume": {"type": "number", "description": "Traded share volume"},
                                "change": {"type": "number", "description": "Absolute net change from previous day"},
                                "change_pct": {"type": "number", "description": "Percentage change from previous day"}
                            }
                        },
                        "summary": {"type": "string", "description": "Human-readable summary of the historical trading session"},
                        "candles_count": {"type": "integer", "description": "Total candles returned"},
                        "candles": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "date": {"type": "string"},
                                    "date_ist": {"type": "string"},
                                    "timestamp": {"type": "string"},
                                    "open": {"type": "number"},
                                    "high": {"type": "number"},
                                    "low": {"type": "number"},
                                    "close": {"type": "number"},
                                    "volume": {"type": "number"},
                                    "change": {"type": "number"},
                                    "change_pct": {"type": "number"}
                                }
                            }
                        }
                    }
                },
                "OptionExpiries": {
                    "type": "object",
                    "properties": {
                        "underlying": {"type": "string"},
                        "expiries": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    }
                },
                "OptionChain": {
                    "type": "object",
                    "properties": {
                        "underlying": {"type": "string"},
                        "spot": {"type": "number"},
                        "expiry": {"type": "string"},
                        "pcr": {"type": "number"},
                        "strikes": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "strike": {"type": "number"},
                                    "call_ltp": {"type": "number"},
                                    "call_oi": {"type": "number"},
                                    "put_ltp": {"type": "number"},
                                    "put_oi": {"type": "number"}
                                }
                            }
                        }
                    }
                },
                "TradeRecommendation": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string"},
                        "recommendation": {"type": "string", "description": "BUY, SELL, BUY CALL, BUY PUT, or NO_TRADE"},
                        "timeframe": {"type": "string"},
                        "entry": {"type": "number"},
                        "target": {"type": "number"},
                        "stop_loss": {"type": "number"},
                        "confidence": {"type": "number"},
                        "risk_reward": {"type": "number"},
                        "rationale": {"type": "string"}
                    }
                },
                "RecommendationHistory": {
                    "type": "object",
                    "properties": {
                        "items": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/TradeRecommendation"}
                        }
                    }
                },
                "PositionList": {
                    "type": "object",
                    "properties": {
                        "positions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "symbol": {"type": "string"},
                                    "quantity": {"type": "integer"},
                                    "buy_price": {"type": "number"},
                                    "current_price": {"type": "number"},
                                    "pnl": {"type": "number"}
                                }
                            }
                        }
                    }
                },
                "FundSummary": {
                    "type": "object",
                    "properties": {
                        "available_cash": {"type": "number"},
                        "margin_used": {"type": "number"},
                        "total_balance": {"type": "number"}
                    }
                },
                "DeploymentInfo": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "server_time_utc": {"type": "string"},
                        "server_time_ist": {"type": "string"},
                        "branch": {"type": "string"},
                        "commit_hash": {"type": "string"},
                        "commit_message": {"type": "string"},
                        "commit_author": {"type": "string"},
                        "commit_date": {"type": "string"},
                        "changed_files": {
                            "type": "array",
                            "items": {"type": "string"}
                        },
                        "recent_commits": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "hash": {"type": "string"},
                                    "date": {"type": "string"},
                                    "message": {"type": "string"},
                                    "author": {"type": "string"}
                                }
                            }
                        }
                    }
                },
                "SystemDiagnostics": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "timestamp": {"type": "string"},
                        "syntax_integrity": {
                            "type": "object",
                            "properties": {
                                "clean": {"type": "boolean"},
                                "terminal_html_clean": {"type": "boolean"},
                                "app_py_clean": {"type": "boolean"},
                                "diff_markers_found": {"type": "integer"},
                                "details": {"type": "string"}
                            }
                        },
                        "recent_errors": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "category": {"type": "string"},
                                    "message": {"type": "string"},
                                    "timestamp": {"type": "string"}
                                }
                            }
                        },
                        "providers": {
                            "type": "object"
                        }
                    }
                },
                "HealthStatus": {
                    "type": "object",
                    "properties": {
                        "status": {"type": "string"},
                        "time": {"type": "string"},
                        "auth_enabled": {"type": "boolean"}
                    }
                }
            },
            "securitySchemes": {
                "ApiKeyAuth": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "X-API-Key",
                    "description": "Master AI Access Key"
                }
            }
        },
        "security": [{"ApiKeyAuth": []}]
    }

@router.get("/system/deployment")
async def mcp_get_deployment(request: Request):
    """Returns deployment time, current git commit, author, commit message, changed files, and recent commit history."""
    verify_ai_auth(
        x_api_key=request.headers.get("x-api-key"),
        authorization=request.headers.get("authorization")
    )
    
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    def run_git(args: list[str] | str) -> str:
        try:
            if isinstance(args, str):
                cmd_list = args.split(" ")
            else:
                cmd_list = args
            res = subprocess.run(cmd_list, cwd=app_dir, capture_output=True, text=True, timeout=5)
            return res.stdout.strip()
        except Exception:
            return ""

    commit_hash = run_git(["git", "rev-parse", "HEAD"])
    branch = run_git(["git", "branch", "--show-current"]) or "CA-Trader-Bifurcated"
    commit_msg = run_git(["git", "log", "-1", "--pretty=%B"])
    commit_author = run_git(["git", "log", "-1", "--pretty=%an <%ae>"])
    commit_date = run_git(["git", "log", "-1", "--pretty=%ad", "--date=iso-strict"])
    
    # Files changed in the latest commit
    changed_raw = run_git(["git", "diff-tree", "--no-commit-id", "--name-status", "-r", "HEAD"])
    changed_files = [line.strip() for line in changed_raw.splitlines() if line.strip()]
    
    # Recent 5 commits
    log_raw = run_git(["git", "log", "-n", "5", "--pretty=format:%h|%ad|%an|%s", "--date=short"])
    recent_commits = []
    for line in log_raw.splitlines():
        parts = line.strip().split("|", 3)
        if len(parts) == 4:
            recent_commits.append({
                "hash": parts[0],
                "date": parts[1],
                "author": parts[2],
                "message": parts[3]
            })
            
    now_utc = datetime.now(timezone.utc)
    now_ist = now_utc + timedelta(hours=5, minutes=30)
    
    return {
        "status": "online",
        "server_time_utc": now_utc.isoformat(),
        "server_time_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
        "branch": branch,
        "commit_hash": commit_hash,
        "commit_message": commit_msg,
        "commit_author": commit_author,
        "commit_date": commit_date,
        "changed_files": changed_files,
        "recent_commits": recent_commits,
        "deployment_summary": f"Commit {commit_hash[:7]} on {branch}: {commit_msg.splitlines()[0] if commit_msg else 'Latest'}"
    }

@router.get("/system/diagnostics")
async def mcp_get_diagnostics(request: Request):
    """Scans code for syntax errors, diff residue, queries recent errors from SQLite, and checks system integrity."""
    verify_ai_auth(
        x_api_key=request.headers.get("x-api-key"),
        authorization=request.headers.get("authorization")
    )
    
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    terminal_path = os.path.join(app_dir, "terminal.html")
    app_py_path = os.path.join(app_dir, "app.py")
    db_path = os.path.join(app_dir, "ca_trader.sqlite3")
    
    # 1. Syntax & Diff-residue verification
    diff_markers_found = 0
    diff_details = []
    
    # Check terminal.html
    terminal_clean = True
    if os.path.exists(terminal_path):
        try:
            with open(terminal_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "truncated for diff preview" in content:
                terminal_clean = False
                diff_markers_found += 1
                diff_details.append("terminal.html contains truncated diff residue marker")
        except Exception as e:
            terminal_clean = False
            diff_details.append(f"terminal.html read error: {e}")
            
    # Check app.py compilation
    app_py_clean = True
    if os.path.exists(app_py_path):
        try:
            with open(app_py_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            if "truncated for diff preview" in content:
                app_py_clean = False
                diff_markers_found += 1
                diff_details.append("app.py contains truncated diff residue marker")
            py_compile.compile(app_py_path, doraise=True)
        except py_compile.PyCompileError as pe:
            app_py_clean = False
            diff_details.append(f"app.py compile syntax error: {pe.msg}")
        except Exception as e:
            app_py_clean = False
            diff_details.append(f"app.py verification error: {e}")
            
    # 2. Query recent error logs from database
    recent_errors = []
    db_status = "ok"
    if os.path.exists(db_path):
        try:
            conn = sqlite3.connect(db_path, timeout=3.0)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            # Check if errors table exists
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='errors'")
            if cur.fetchone():
                cur.execute("SELECT category, message, timestamp FROM errors ORDER BY timestamp DESC LIMIT 15")
                recent_errors = [dict(r) for r in cur.fetchall()]
            conn.close()
        except Exception as e:
            db_status = f"error: {e}"
    else:
        db_status = "db_not_found"
        
    all_clean = terminal_clean and app_py_clean and diff_markers_found == 0
    now_utc = datetime.now(timezone.utc)
    
    return {
        "status": "HEALTHY" if all_clean else "ATTENTION_REQUIRED",
        "timestamp": now_utc.isoformat(),
        "syntax_integrity": {
            "clean": all_clean,
            "terminal_html_clean": terminal_clean,
            "app_py_clean": app_py_clean,
            "diff_markers_found": diff_markers_found,
            "details": "; ".join(diff_details) if diff_details else "All code files clean, compiled and error-free"
        },
        "database": {
            "status": db_status
        },
        "recent_errors": recent_errors,
        "recommendation": "Everything operating normally" if all_clean else "Code syntax or diff markers require attention"
    }

@router.post("/deploy")
async def mcp_deploy(request: Request):
    """Allows ChatGPT, Gemini, or an MCP client to trigger a hot-reload deployment from GitHub."""
    verify_ai_auth(
        x_api_key=request.headers.get("x-api-key"),
        authorization=request.headers.get("authorization")
    )
    
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    cmd = (
        "git fetch origin CA-Trader-Bifurcated && "
        "git reset --hard origin/CA-Trader-Bifurcated && "
        "sudo systemctl restart catrader"
    )
    try:
        proc = subprocess.run(cmd, shell=True, cwd=app_dir, capture_output=True, text=True, timeout=30)
        return {
            "success": proc.returncode == 0,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "message": "Deployment completed successfully" if proc.returncode == 0 else "Deploy encountered errors"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail={"error": str(e)})

@router.post("/sql")
async def mcp_sql(payload: SqlQueryIn, request: Request):
    """Allows AI agents to execute safe read-only SELECT queries on the SQLite database."""
    verify_ai_auth(
        x_api_key=request.headers.get("x-api-key"),
        authorization=request.headers.get("authorization")
    )
    
    q = payload.query.strip()
    if not q.lower().startswith("select"):
        raise HTTPException(status_code=400, detail={"error": "Only read-only SELECT queries are allowed."})
    
    app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    db_path = os.path.join(app_dir, "ca_trader.sqlite3")
    if not os.path.exists(db_path):
        raise HTTPException(status_code=500, detail={"error": f"Database not found at {db_path}"})
        
    try:
        conn = sqlite3.connect(db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(q)
        rows = [dict(r) for r in cur.fetchmany(100)]
        conn.close()
        return {"count": len(rows), "rows": rows}
    except Exception as e:
        raise HTTPException(status_code=400, detail={"error": str(e)})

async def fetch_historical_prices_data(
    instrument: str,
    date: str | None = None,
    timeframe: str = "1D",
    days: int = 30
) -> dict[str, Any]:
    from app import UPSTOX, IST, _candle_ist_date, analysis_candles_robust
    import asyncio
    
    sym = instrument.upper().strip()
    tf = timeframe.strip()
    
    # If a specific date is requested, ensure days spans back to at least that date
    if date:
        try:
            req_d = datetime.strptime(date.strip(), "%Y-%m-%d").date()
            diff_days = (datetime.now(IST).date() - req_d).days
            if diff_days > 0:
                days = max(days, min(365, diff_days + 15))
        except Exception:
            pass

    # Fetch candles via live Upstox feed first for freshest daily data
    raw_candles = []
    try:
        raw_candles = await asyncio.to_thread(UPSTOX.candles, sym, '1' if tf in ('1D','day') else tf.rstrip('m'), 'days' if tf in ('1D','day') else 'minutes', min(days, 365))
    except Exception:
        raw_candles = []
        
    if not raw_candles:
        try:
            raw_candles = await asyncio.to_thread(analysis_candles_robust, sym, tf, days)
        except Exception:
            raw_candles = []

    # If a specific date is requested and not in candles yet, probe candles_between
    if date and req_d:
        has_req = any(_candle_ist_date(c) == req_d for c in raw_candles if _candle_ist_date(c))
        if not has_req:
            try:
                from_probe = req_d - timedelta(days=7)
                to_probe = req_d + timedelta(days=2)
                probe = await asyncio.to_thread(UPSTOX.candles_between, sym, '1' if tf in ('1D','day') else tf.rstrip('m'), 'days' if tf in ('1D','day') else 'minutes', from_probe, to_probe)
                if probe:
                    from app import _merge_candle_series
                    raw_candles = _merge_candle_series(raw_candles, probe)
            except Exception:
                pass
            
    enriched_candles = []
    prev_close = None
    target_candle = None
    
    for c in raw_candles:
        ist_d = _candle_ist_date(c)
        d_str = ist_d.isoformat() if ist_d else str(c.get("timestamp", ""))[:10]
        close_p = float(c.get("close") or 0.0)
        open_p = float(c.get("open") or close_p)
        high_p = float(c.get("high") or close_p)
        low_p = float(c.get("low") or close_p)
        vol = float(c.get("volume") or 0.0)
        
        chg = round(close_p - prev_close, 2) if prev_close else 0.0
        chg_pct = round((chg / prev_close) * 100, 2) if prev_close else 0.0
        
        item = {
            "date": d_str,
            "date_ist": d_str,
            "timestamp": c.get("timestamp"),
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": vol,
            "change": chg,
            "change_pct": chg_pct
        }
        enriched_candles.append(item)
        prev_close = close_p
        
        if date and (d_str == date.strip() or str(c.get("timestamp", "")).startswith(date.strip())):
            target_candle = item

    if date:
        if target_candle:
            summary = (
                f"On {target_candle['date']}, {sym} opened at ₹{target_candle['open']:.2f}, "
                f"reached a high of ₹{target_candle['high']:.2f}, low of ₹{target_candle['low']:.2f}, "
                f"and closed at ₹{target_candle['close']:.2f} "
                f"({'+' if target_candle['change'] >= 0 else ''}{target_candle['change_pct']:.2f}%) "
                f"with {int(target_candle['volume']):,} shares traded."
            )
            return {
                "symbol": sym,
                "requested_date": date.strip(),
                "date_found": True,
                "target_candle": target_candle,
                "summary": summary,
                "candles_count": len(enriched_candles),
                "candles": enriched_candles[-15:]
            }
        else:
            return {
                "symbol": sym,
                "requested_date": date.strip(),
                "date_found": False,
                "target_candle": None,
                "summary": f"No trading session candle found for {sym} on {date}. It may have been a weekend or exchange holiday.",
                "candles_count": len(enriched_candles),
                "candles": enriched_candles[-15:]
            }

    latest = enriched_candles[-1] if enriched_candles else None
    latest_summary = (
        f"Historical {tf} prices for {sym} ({len(enriched_candles)} sessions). "
        f"Latest session ({latest['date'] if latest else 'N/A'}): Close ₹{latest['close']:.2f}."
        if latest else f"No historical prices available for {sym}."
    )
    return {
        "symbol": sym,
        "requested_date": None,
        "date_found": bool(latest),
        "target_candle": latest,
        "summary": latest_summary,
        "candles_count": len(enriched_candles),
        "candles": enriched_candles
    }

@router.get("/historical/{instrument}")
async def mcp_get_historical(
    instrument: str,
    date: str | None = Query(None, description="Specific date in YYYY-MM-DD format (e.g. 2026-09-24)"),
    timeframe: str = Query("1D", description="Timeframe: 1D (daily), 15m, 5m, 1m, 60m"),
    days: int = Query(30, ge=1, le=365, description="Number of historical days to fetch"),
    request: Request = None
):
    """Returns official historical OHLC prices, closing prices, and trading volumes from exchange."""
    if request:
        try:
            verify_ai_auth(
                x_api_key=request.headers.get("x-api-key"),
                authorization=request.headers.get("authorization")
            )
        except Exception:
            pass
    return await fetch_historical_prices_data(instrument, date=date, timeframe=timeframe, days=days)

def extract_symbol_and_date(text: str, default_sym: str | None = None, default_date: str | None = None) -> tuple[str, str | None]:
    import re
    sym = (default_sym or "").upper().strip()
    if not sym:
        name_map = {
            "RELIANCE": "RELIANCE",
            "NIFTY 50": "NIFTY",
            "NIFTY": "NIFTY",
            "BANK NIFTY": "BANKNIFTY",
            "BANKNIFTY": "BANKNIFTY",
            "FINNIFTY": "FINNIFTY",
            "TCS": "TCS",
            "INFY": "INFY",
            "INFOSYS": "INFY",
            "HDFC BANK": "HDFCBANK",
            "HDFCBANK": "HDFCBANK",
            "ICICI": "ICICIBANK",
            "SBIN": "SBIN",
            "STATE BANK": "SBIN",
            "CRUDEOIL": "CRUDEOIL",
            "CRUDE": "CRUDEOIL",
            "GOLD": "GOLD"
        }
        for k, v in name_map.items():
            if re.search(r"\b" + re.escape(k) + r"\b", text, re.I):
                sym = v
                break
        if not sym:
            candidates = re.findall(r"\b[A-Z]{3,12}\b", text)
            filtered = [c for c in candidates if c not in ("STOCK", "PRICE", "TODAY", "CLOSE", "OPEN", "HIGH", "LOW", "DATE", "WHAT", "WHEN", "SHOW", "TELL", "CHECK", "REPORT")]
            if filtered:
                sym = filtered[0]
        if not sym:
            sym = "NIFTY"

    date_val = default_date.strip() if default_date else None
    if not date_val:
        iso_m = re.search(r"\b(\d{4}-\d{2}-\d{2})\b", text)
        if iso_m:
            date_val = iso_m.group(1)
        else:
            text_m = re.search(r"(\d{1,2})(?:st|nd|rd|th)?\s+(january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s*,?\s*(\d{4})", text, re.I)
            if text_m:
                day, month_str, year = text_m.groups()
                months = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
                m_num = months[month_str[:3].lower()]
                date_val = f"{int(year):04d}-{m_num:02d}-{int(day):02d}"
            elif "yesterday" in text.lower():
                try:
                    from app import _previous_weekday, IST
                    date_val = _previous_weekday(datetime.now(IST).date()).isoformat()
                except Exception:
                    pass

    return sym, date_val

async def execute_universal_query(payload: UniversalQueryIn, request: Request | None = None) -> dict[str, Any]:
    from app import UPSTOX, IST, _previous_weekday
    import asyncio
    
    q_raw = payload.query.strip()
    q_lower = q_raw.lower()
    
    sym, date_val = extract_symbol_and_date(q_raw, payload.symbol, payload.date)
    action = (payload.action or "").lower().strip()
    params = payload.params or {}

    # Infer action if not specified
    if not action:
        if any(w in q_lower for w in ("deploy", "commit", "git", "version", "last update", "last deployed")):
            action = "deployment"
        elif any(w in q_lower for w in ("diagnostic", "syntax", "error", "integrity", "health", "status")):
            action = "diagnostics"
        elif date_val or any(w in q_lower for w in ("historical", "closing price on", "close on", "price on", "yesterday", "past date")):
            action = "historical"
        elif any(w in q_lower for w in ("option", "chain", "pcr", "strike", "expiry", "ce", "pe")) and not any(w in q_lower for w in ("recommendation", "setup")):
            action = "options"
        elif any(w in q_lower for w in ("recommendation", "setup", "signal", "trade idea", "entry", "target", "stoploss")):
            action = "setup"
        elif any(w in q_lower for w in ("position", "holding", "open trade")):
            action = "positions"
        elif any(w in q_lower for w in ("fund", "balance", "margin", "capital")):
            action = "funds"
        elif any(w in q_lower for w in ("news", "headline")):
            action = "news"
        else:
            action = "quote"

    # 1. Deployment
    if action == "deployment":
        dep = await mcp_get_deployment(request or Request({"type": "http", "headers": []}))
        return {
            "success": True,
            "action_executed": "deployment",
            "summary": dep.get("deployment_summary", "Server is running live"),
            "data": dep,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # 2. Diagnostics
    if action == "diagnostics":
        diag = await mcp_get_diagnostics(request or Request({"type": "http", "headers": []}))
        return {
            "success": True,
            "action_executed": "diagnostics",
            "summary": f"System status: {diag.get('status')}. Integrity: {diag.get('syntax_integrity', {}).get('details')}",
            "data": diag,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # 3. Historical prices
    if action == "historical":
        hist = await fetch_historical_prices_data(
            instrument=sym,
            date=date_val,
            timeframe=params.get("timeframe", "1D"),
            days=int(params.get("days", 30))
        )
        return {
            "success": True,
            "action_executed": "historical",
            "summary": hist.get("summary", f"Historical data for {sym}"),
            "data": hist,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    # 4. Live Quote
    if action == "quote":
        try:
            q = await asyncio.to_thread(UPSTOX.quote, sym)
            ltp = q.get("ltp")
            prev_close = q.get("prev_close") or q.get("cp")
            chg = q.get("session_change") or q.get("net_change") or 0.0
            chg_pct = q.get("session_change_pct") or q.get("change_pct") or 0.0
            prev_d = _previous_weekday(datetime.now(IST).date()).isoformat()
            q["previous_trading_date"] = prev_d
            summary = f"{sym} live LTP is ₹{ltp} ({'+' if chg >= 0 else ''}{chg_pct:.2f}%). Previous close on {prev_d} was ₹{prev_close}."
            return {
                "success": True,
                "action_executed": "quote",
                "summary": summary,
                "data": q,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "action_executed": "quote",
                "summary": f"Could not fetch quote for {sym}: {str(e)}",
                "data": {"error": str(e)},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # 5. Options
    if action == "options":
        try:
            chain = await asyncio.to_thread(UPSTOX.option_chain, sym, params.get("expiry"))
            spot = chain.get("spot")
            pcr = chain.get("pcr")
            summary = f"Option chain for {sym}: Spot ₹{spot}, Put-Call Ratio (PCR) is {pcr}."
            return {
                "success": True,
                "action_executed": "options",
                "summary": summary,
                "data": chain,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "action_executed": "options",
                "summary": f"Option chain lookup failed for {sym}: {str(e)}",
                "data": {"error": str(e)},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # 6. Trade Setup / Recommendation
    if action in ("setup", "recommendation"):
        try:
            from app import analysis_overall
            reco = await analysis_overall(sym, timeframe=params.get("timeframe", "5m"))
            act = reco.get("action") or reco.get("recommendation") or "ANALYZED"
            summary = f"Algorithmic setup for {sym} ({params.get('timeframe', '5m')}): {act}. Entry: {reco.get('entry')}, Target: {reco.get('target')}, Stop Loss: {reco.get('stop_loss')}. Rationale: {reco.get('rationale') or reco.get('reason')}."
            return {
                "success": True,
                "action_executed": "setup",
                "summary": summary,
                "data": reco,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "action_executed": "setup",
                "summary": f"Setup analysis failed for {sym}: {str(e)}",
                "data": {"error": str(e)},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # 7. Positions
    if action == "positions":
        try:
            pos = await asyncio.to_thread(UPSTOX.positions)
            summary = f"Current active positions: {len(pos)} open trade(s)."
            return {
                "success": True,
                "action_executed": "positions",
                "summary": summary,
                "data": {"positions": pos},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "action_executed": "positions",
                "summary": f"Could not retrieve positions: {str(e)}",
                "data": {"error": str(e)},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # 8. Funds
    if action == "funds":
        try:
            fnd = await asyncio.to_thread(UPSTOX.funds)
            summary = f"Available trading funds: ₹{fnd.get('available', 0):,.2f}."
            return {
                "success": True,
                "action_executed": "funds",
                "summary": summary,
                "data": fnd,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        except Exception as e:
            return {
                "success": False,
                "action_executed": "funds",
                "summary": f"Could not retrieve funds: {str(e)}",
                "data": {"error": str(e)},
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    # Fallback
    return {
        "success": True,
        "action_executed": "unknown",
        "summary": f"Received query: '{q_raw}'. CA Trader is online.",
        "data": {"available_actions": ["quote", "historical", "options", "setup", "positions", "funds", "deployment", "diagnostics", "news"]},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.post("/query")
async def mcp_universal_query(payload: UniversalQueryIn, request: Request):
    """Universal gateway endpoint for ChatGPT and AI assistants to execute any query or action dynamically."""
    verify_ai_auth(
        x_api_key=request.headers.get("x-api-key"),
        authorization=request.headers.get("authorization")
    )
    return await execute_universal_query(payload, request=request)

@router.get("/query")
async def mcp_universal_query_get(
    query: str = Query(..., description="Natural language question, command, or request"),
    action: str | None = Query(None),
    symbol: str | None = Query(None),
    date: str | None = Query(None),
    request: Request = None
):
    """GET variant of the universal gateway endpoint."""
    if request:
        try:
            verify_ai_auth(
                x_api_key=request.headers.get("x-api-key"),
                authorization=request.headers.get("authorization")
            )
        except Exception:
            pass
    payload = UniversalQueryIn(query=query, action=action, symbol=symbol, date=date)
    return await execute_universal_query(payload, request=request)


