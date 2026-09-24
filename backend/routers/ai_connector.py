import os
import subprocess
import sqlite3
import hmac
from typing import Any
from fastapi import APIRouter, Header, HTTPException, Query, Request
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
    return {
        "openapi": "3.0.0",
        "info": {
            "title": "CA Trader AI Assistant & MCP API",
            "description": "Secure API connector for ChatGPT, Gemini, and MCP agents to inspect stock quotes, option chains, portfolios, and trigger cloud deployments.",
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
                    "responses": {"200": {"description": "Live quote data"}}
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
                    "responses": {"200": {"description": "List of active expiry dates"}}
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
                    "responses": {"200": {"description": "Complete option chain table"}}
                }
            },
            "/api/recommendations/history": {
                "get": {
                    "summary": "Get AI Trade Recommendations",
                    "description": "Returns recent AI trade setups with entry, target, stop-loss, and rationale.",
                    "operationId": "getRecommendationsHistory",
                    "responses": {"200": {"description": "Recent recommendations history"}}
                }
            },
            "/api/positions": {
                "get": {
                    "summary": "Get Active Trading Positions",
                    "description": "Returns open positions, quantity, buy price, current LTP, and unrealized P&L.",
                    "operationId": "getPositions",
                    "responses": {"200": {"description": "List of positions"}}
                }
            },
            "/api/funds": {
                "get": {
                    "summary": "Get Account Funds & Margin",
                    "description": "Returns available cash, margin used, and trading capital breakdown.",
                    "operationId": "getFunds",
                    "responses": {"200": {"description": "Account funds breakdown"}}
                }
            },
            "/health": {
                "get": {
                    "summary": "Get Server & Provider Health",
                    "description": "Checks server health and Upstox API connectivity status.",
                    "operationId": "getHealth",
                    "responses": {"200": {"description": "System health status"}}
                }
            },
            "/api/mcp/deploy": {
                "post": {
                    "summary": "Trigger Cloud Git Auto-Deploy",
                    "description": "Instructs the 24/7 Oracle Cloud server to pull latest changes from GitHub and reload in 5 seconds.",
                    "operationId": "triggerCloudDeploy",
                    "responses": {"200": {"description": "Deployment status result"}}
                }
            },
            "/api/mcp/sql": {
                "post": {
                    "summary": "Query SQLite Database",
                    "description": "Safely executes a read-only SELECT query on the production SQLite database.",
                    "operationId": "queryDatabase",
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": {"$ref": "#/components/schemas/SqlQueryIn"}}}
                    },
                    "responses": {"200": {"description": "Query results"}}
                }
            }
        },
        "components": {
            "schemas": {
                "SqlQueryIn": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "SELECT query to execute"}
                    },
                    "required": ["query"]
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

