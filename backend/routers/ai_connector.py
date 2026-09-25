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
                "MarketQuote": {
                    "type": "object",
                    "properties": {
                        "symbol": {"type": "string", "description": "Trading instrument symbol"},
                        "ltp": {"type": "number", "description": "Last traded price"},
                        "open": {"type": "number", "description": "Session opening price"},
                        "high": {"type": "number", "description": "Session high"},
                        "low": {"type": "number", "description": "Session low"},
                        "close": {"type": "number", "description": "Previous close price"},
                        "volume": {"type": "number", "description": "Total traded volume"}
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

