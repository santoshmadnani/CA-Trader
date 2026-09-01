from __future__ import annotations

"""CA Trader integration server.

The supplied terminal HTML is served byte-for-byte.  This module provides the
headless JSON backend described in the accompanying specification and appends
only a non-visual JavaScript bridge at response time so the existing controls
can call those APIs.

Run:
    python app.py

The server uses ASGI/FastAPI because the execution environment already
contains FastAPI/Starlette/Uvicorn.  Environment names remain compatible with
the supplied CA Trader .env file (FLASK_HOST/FLASK_PORT, etc.).
"""

import asyncio
import base64
import contextlib
import hashlib
import hmac
import json
import gzip
import logging
import math
import os
import re
import html
import secrets
import sqlite3
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait, as_completed, TimeoutError as FuturesTimeoutError
import traceback
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Optional
from urllib.parse import quote, urlencode
from zoneinfo import ZoneInfo
from xml.etree import ElementTree as ET

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
try:
    import upstox_client  # optional official SDK; REST/WebSocket bridge falls back if unavailable
except Exception:
    upstox_client = None
try:
    import websocket as websocket_client
except Exception:
    websocket_client = None
try:
    from websockets.sync.client import connect as websocket_sync_connect
except Exception:
    websocket_sync_connect = None
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from pydantic import BaseModel, Field
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

try:
    import uvicorn
except Exception as exc:  # pragma: no cover
    uvicorn = None

# ---------------------------------------------------------------------------
# Paths / configuration
# ---------------------------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
HTML_CANDIDATES = [
    BASE_DIR / "terminal.html",
    BASE_DIR / "CA_Trader_Final.html",
    BASE_DIR / "CA_Trader_Updated.html",
    BASE_DIR / "ca-trader-terminal-ui (2)(3).html",
    BASE_DIR / "ca-trader-terminal-ui_final_v3.html",
    BASE_DIR / "ca-trader-terminal-ui_final_v2.html",
    BASE_DIR / "ca-trader-terminal-ui_final.html",
    BASE_DIR / "ca-trader-terminal-ui_modified.html",
    BASE_DIR / "ca-trader-terminal-ui (2).html",
    BASE_DIR / "ca-trader-terminal-ui.html",
    BASE_DIR / "index.html",
]
LOGIN_HTML_CANDIDATES = [
    BASE_DIR / "CA_Trader_Login.html",
    BASE_DIR / "CA_Trader_Login(1).html",
    BASE_DIR / "CA_Trader_Login (1).html",
    BASE_DIR / "ca-trader-login-final-v2.html",
]
HTML_PATH = next((p for p in HTML_CANDIDATES if p.exists()), None)
LOGIN_HTML_PATH = next((p for p in LOGIN_HTML_CANDIDATES if p.exists()), None)
FITNESS_HTML_PATH = BASE_DIR / "fitness.html"
TERMINAL_SELECTOR_HTML_PATH = BASE_DIR / "terminal_selector.html"
if HTML_PATH is None:
    # The exact uploaded filename is kept as a fallback reference for users
    # who place app.py elsewhere and keep the HTML beside it.
    HTML_PATH = BASE_DIR / "ca-trader-terminal-ui (2).html"

load_dotenv(BASE_DIR / ".env")
load_dotenv(Path.cwd() / ".env")

HOST = os.getenv("FLASK_HOST", os.getenv("HOST", "127.0.0.1"))
PORT = int(os.getenv("FLASK_PORT", os.getenv("PORT", "8000")))
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
AUTH_ENABLED = os.getenv("CA_AUTH_ENABLED", "1") == "1"
AUTH_IDLE_HOURS = float(os.getenv("CA_AUTH_IDLE_HOURS", "12"))
AUTH_SECRET = os.getenv("CA_AUTH_SECRET") or secrets.token_hex(32)
_configured_db_path = Path(os.getenv("CA_DATABASE_PATH", str(BASE_DIR / "ca_trader.sqlite3")))
# Preserve the production database used by older CA Trader deployments.  Some
# deployment images set CA_DATABASE_PATH=/app/data/ca_trader.sqlite3 while the
# persistent volume contains ca_trader.db.  Prefer the existing persistent DB
# when the configured path is a new/nonexistent filename, rather than silently
# creating a second empty database and losing the user's watchlists.
_legacy_db_path = _configured_db_path.with_name("ca_trader.db")
DB_PATH = _legacy_db_path if _legacy_db_path.exists() and not _configured_db_path.exists() else _configured_db_path
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_FILE = BASE_DIR / os.getenv("LOG_FILE", "ca-trader.log")
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1") == "1"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
# Bound concurrent Upstox REST calls so dashboard/news/auto-trade cannot exhaust the HTTP pool.
_UPSTOX_HTTP_SEM = threading.BoundedSemaphore(int(os.getenv("UPSTOX_MAX_CONCURRENCY", "8")))
FITNESS_SELECTOR_EMAILS = {x.strip().lower() for x in os.getenv("CA_TERMINAL_SELECTOR_EMAILS", "").split(",") if x.strip()}
FOOD_SEARCH_CACHE_HOURS = float(os.getenv("FOOD_SEARCH_CACHE_HOURS", "12"))
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8001").split(",") if x.strip()]

UPSTOX_BASE_URL = os.getenv("UPSTOX_BASE_URL", "https://api.upstox.com/v2").rstrip("/")
UPSTOX_V3_BASE_URL = os.getenv("UPSTOX_V3_BASE_URL", "https://api.upstox.com/v3").rstrip("/")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
MARKET_STREAM_ENABLED = os.getenv("CA_MARKET_STREAM_ENABLED", "1") == "1"
# Safe default: use the continuous bulk-REST quote lane. Broker WebSocket is opt-in only.
MARKET_STREAM_TRANSPORT = os.getenv("CA_MARKET_STREAM_TRANSPORT", "rest").strip().lower()
if os.getenv("CA_ALLOW_UPSTOX_BROKER_WS", "0").strip() != "1":
    MARKET_STREAM_TRANSPORT = "rest"
GNEWS_API_KEY = os.getenv("GNEWS_API_KEY", "")
GNEWS_DAILY_LIMIT = int(os.getenv("GNEWS_DAILY_LIMIT", "100"))
GNEWS_PREMARKET_LIMIT = int(os.getenv("GNEWS_PREMARKET_LIMIT", "40"))
GNEWS_MARKET_LIMIT = int(os.getenv("GNEWS_MARKET_LIMIT", "60"))
NEWSAPI_DAILY_LIMIT = int(os.getenv("NEWSAPI_DAILY_LIMIT", "100"))
NEWS_DISCOVERY_TARGET = int(os.getenv("NEWS_DISCOVERY_TARGET", "10"))
NEWS_CACHE_TTL = int(os.getenv("NEWS_CACHE_TTL", "45"))
NEWS_KEY_MAX_ATTEMPTS = int(os.getenv("NEWS_KEY_MAX_ATTEMPTS", "2"))
NEWS_RSS_BATCH = int(os.getenv("NEWS_RSS_BATCH", "10"))
NEWS_RSS_TIMEOUT = float(os.getenv("NEWS_RSS_TIMEOUT", "2.2"))
_NEWS_REFRESH_LOCK = threading.RLock()
_NEWS_REFRESH_INFLIGHT: set[str] = set()
_NEWS_REFRESH_EXECUTOR = ThreadPoolExecutor(max_workers=4)
_ANALYSIS_CACHE_TTL = 20.0
GNEWS_API_KEYS = [v for k, v in sorted(((k, v) for k, v in os.environ.items() if k == "GNEWS_API_KEY" or re.fullmatch(r"GNEWS_API_KEY_[2-9]|GNEWS_API_KEY_10", k)), key=lambda x: (0 if x[0] == "GNEWS_API_KEY" else int(x[0].rsplit("_", 1)[1]))) if v]
NEWSAPI_API_KEYS = [v for k, v in sorted(((k, v) for k, v in os.environ.items() if k == "NEWSAPI_API_KEY" or re.fullmatch(r"NEWSAPI_API_KEY_[2-9]|NEWSAPI_API_KEY_10", k)), key=lambda x: (0 if x[0] == "NEWSAPI_API_KEY" else int(x[0].rsplit("_", 1)[1]))) if v]
UPSTOX_ACCESS_TOKENS = [v for k, v in sorted(((k, v) for k, v in os.environ.items() if k == "UPSTOX_ACCESS_TOKEN" or re.fullmatch(r"UPSTOX_ACCESS_TOKEN_[2-9]|UPSTOX_ACCESS_TOKEN_10", k)), key=lambda x: (0 if x[0] == "UPSTOX_ACCESS_TOKEN" else int(x[0].rsplit("_", 1)[1]))) if v]
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
FITNESS_TIMEZONE = ZoneInfo(os.getenv("FITNESS_TIMEZONE", "Asia/Kolkata"))

# ---------------------------------------------------------------------------
# Logging (never log credentials/tokens)
# ---------------------------------------------------------------------------

LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler(LOG_FILE, encoding="utf-8")],
)
log = logging.getLogger("ca-trader")

SECRET_PATTERNS = [
    re.compile(r"Bearer\s+[A-Za-z0-9._\-]+", re.I),
    re.compile(r"(?:api[_-]?key|client[_-]?secret|access[_-]?token|password)\s*[=:]\s*\S+", re.I),
]


def safe_text(value: Any) -> str:
    text = str(value)
    for pat in SECRET_PATTERNS:
        text = pat.sub("[REDACTED]", text)
    return text


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

# ---------------------------------------------------------------------------
# SQLite helpers / user-isolated state
# ---------------------------------------------------------------------------

_DB_LOCK = threading.RLock()


def db_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=5)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def db_insert(sql: str, params: Iterable[Any] = ()) -> int:
    """Execute an INSERT and return the actual SQLite rowid."""
    with _DB_LOCK:
        conn = db_conn()
        try:
            cur = conn.execute(sql, tuple(params))
            conn.commit()
            return int(cur.lastrowid)
        finally:
            conn.close()


def db_exec(sql: str, params: Iterable[Any] = (), fetch: str | None = None) -> Any:
    # Avoid COMMIT on SELECT/PRAGMA reads; this materially reduces SQLite lock contention
    # when dashboard/news/background workers are active concurrently.
    with _DB_LOCK:
        conn = db_conn()
        try:
            cur = conn.execute(sql, tuple(params))
            if cur.description is None:
                conn.commit()
            if fetch == "one":
                row = cur.fetchone()
                return dict(row) if row else None
            if fetch == "all":
                return [dict(r) for r in cur.fetchall()]
            return cur.rowcount
        finally:
            conn.close()


def init_db() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    schema = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT,
        email TEXT,
        full_name TEXT,
        role TEXT NOT NULL DEFAULT 'user',
        created_at TEXT NOT NULL,
        is_active INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS watchlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        instrument_key TEXT,
        created_at TEXT NOT NULL,
        UNIQUE(user_id, symbol),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS watchlist_groups (id INTEGER PRIMARY KEY AUTOINCREMENT,user_id INTEGER NOT NULL,name TEXT NOT NULL,created_at TEXT NOT NULL,UNIQUE(user_id,name),FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS watchlist_members (id INTEGER PRIMARY KEY AUTOINCREMENT,watchlist_id INTEGER NOT NULL,symbol TEXT NOT NULL,instrument_key TEXT,instrument_type TEXT,exchange TEXT,display_name TEXT,position INTEGER NOT NULL DEFAULT 0,created_at TEXT NOT NULL,UNIQUE(watchlist_id,symbol),FOREIGN KEY(watchlist_id) REFERENCES watchlist_groups(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS login_sessions (id TEXT PRIMARY KEY,user_id INTEGER NOT NULL,started_at TEXT NOT NULL,ended_at TEXT,last_seen TEXT NOT NULL,FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE);
    CREATE TABLE IF NOT EXISTS funds (
        user_id INTEGER PRIMARY KEY,
        available REAL NOT NULL DEFAULT 0,
        trading_funds REAL NOT NULL DEFAULT 0,
        testing_funds REAL NOT NULL DEFAULT 0,
        auto_trade_funds REAL NOT NULL DEFAULT 0,
        used REAL NOT NULL DEFAULT 0,
        realized_pnl REAL NOT NULL DEFAULT 0,
        unrealized_pnl REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS orders (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        instrument_key TEXT,
        side TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        order_type TEXT NOT NULL,
        price REAL,
        trigger_price REAL,
        stop_loss REAL,
        target REAL,
        amo INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL,
        execution_state TEXT NOT NULL,
        product TEXT,
        paper INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS positions (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        instrument_key TEXT,
        side TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        avg_price REAL NOT NULL,
        stop_loss REAL,
        target REAL,
        realized_pnl REAL NOT NULL DEFAULT 0,
        unrealized_pnl REAL NOT NULL DEFAULT 0,
        opened_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS holdings (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        symbol TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        avg_price REAL NOT NULL,
        ltp REAL,
        pnl REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS recommendations (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        source TEXT NOT NULL,
        symbol TEXT NOT NULL,
        recommendation TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        entry REAL,
        target REAL,
        stop_loss REAL,
        rationale TEXT,
        technical_basis TEXT,
        news_basis TEXT,
        option_basis TEXT,
        outcome TEXT,
        final_pnl REAL,
        success INTEGER,
        exit_reason TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS notifications (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        category TEXT NOT NULL,
        severity TEXT NOT NULL,
        materiality REAL NOT NULL DEFAULT 0,
        title TEXT NOT NULL,
        body TEXT,
        unread INTEGER NOT NULL DEFAULT 1,
        dedupe_key TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_notifications_user_unread ON notifications(user_id, unread, created_at);
    CREATE TABLE IF NOT EXISTS news_hidden (
        id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, article_key TEXT NOT NULL,
        created_at TEXT NOT NULL, UNIQUE(user_id, article_key),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS observations (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        instrument TEXT NOT NULL,
        timeframe TEXT NOT NULL,
        observation TEXT NOT NULL,
        severity TEXT NOT NULL,
        materiality REAL NOT NULL,
        evidence TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS error_events (
        id TEXT PRIMARY KEY,
        user_id INTEGER,
        category TEXT NOT NULL,
        provider TEXT,
        status_code INTEGER,
        message TEXT NOT NULL,
        context_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL
    );
    CREATE TABLE IF NOT EXISTS settings (
        user_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        value_json TEXT NOT NULL,
        PRIMARY KEY(user_id, key),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS password_reset_tokens (
        token_hash TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        expires_at TEXT NOT NULL,
        used INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS news_decisions (
        id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        article_key TEXT NOT NULL,
        title TEXT NOT NULL,
        source TEXT,
        url TEXT,
        ca_decision TEXT,
        ca_materiality REAL,
        ca_rationale TEXT,
        user_decision TEXT,
        user_materiality REAL,
        final_decision TEXT NOT NULL,
        final_materiality REAL NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        UNIQUE(user_id, article_key),
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS external_news (
        id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, target TEXT, is_global INTEGER NOT NULL DEFAULT 0,
        headline TEXT, summary TEXT, url TEXT, source TEXT, published_at TEXT,
        materiality REAL NOT NULL DEFAULT 0, classification TEXT, reason TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_external_news_user_target ON external_news(user_id,target,is_global,created_at);

    CREATE TABLE IF NOT EXISTS fitness_profiles (
        user_id INTEGER PRIMARY KEY, name TEXT, goal TEXT, height_cm REAL, weight_kg REAL,
        age_years REAL, sex TEXT, calorie_target REAL, protein_target REAL, carbs_target REAL, fat_target REAL,
        diet_budget REAL, workout_frequency REAL, usual_big_cigs REAL NOT NULL DEFAULT 0,
        usual_small_cigs REAL NOT NULL DEFAULT 0, wake_time TEXT, sleep_target REAL DEFAULT 8,
        completed INTEGER NOT NULL DEFAULT 0, updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS fitness_diet_entries (
        id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, date TEXT NOT NULL, food TEXT NOT NULL,
        quantity TEXT, calories REAL NOT NULL DEFAULT 0, protein REAL NOT NULL DEFAULT 0,
        carbs REAL NOT NULL DEFAULT 0, fat REAL NOT NULL DEFAULT 0, fiber REAL NOT NULL DEFAULT 0,
        source TEXT, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_fitness_diet_user_date ON fitness_diet_entries(user_id,date);
    CREATE TABLE IF NOT EXISTS fitness_workouts (
        id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, date TEXT NOT NULL, name TEXT NOT NULL,
        notes TEXT, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS fitness_exercises (
        id TEXT PRIMARY KEY, workout_id TEXT NOT NULL, user_id INTEGER NOT NULL, exercise TEXT NOT NULL,
        sets_json TEXT NOT NULL, volume REAL NOT NULL DEFAULT 0, best_weight REAL NOT NULL DEFAULT 0,
        best_reps INTEGER NOT NULL DEFAULT 0, e1rm REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
        FOREIGN KEY(workout_id) REFERENCES fitness_workouts(id) ON DELETE CASCADE,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_fitness_exercises_user_exercise ON fitness_exercises(user_id,exercise);
    CREATE TABLE IF NOT EXISTS fitness_smoking (
        id TEXT PRIMARY KEY, user_id INTEGER NOT NULL, date TEXT NOT NULL, smoked INTEGER NOT NULL DEFAULT 0,
        big_count INTEGER NOT NULL DEFAULT 0, small_count INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
        UNIQUE(user_id,date), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS fitness_food_cache (
        cache_key TEXT PRIMARY KEY, query TEXT NOT NULL, data_json TEXT NOT NULL, created_at TEXT NOT NULL, expires_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS fitness_drafts (
        user_id INTEGER NOT NULL, kind TEXT NOT NULL, date TEXT NOT NULL, data_json TEXT NOT NULL, updated_at TEXT NOT NULL,
        PRIMARY KEY(user_id,kind,date), FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS auto_trade_configs (
        user_id INTEGER PRIMARY KEY,
        enabled INTEGER NOT NULL DEFAULT 0,
        capital REAL NOT NULL DEFAULT 0,
        max_loss REAL NOT NULL DEFAULT 0,
        symbols_json TEXT NOT NULL DEFAULT '[]',
        categories_json TEXT NOT NULL DEFAULT '[]',
        options_enabled INTEGER NOT NULL DEFAULT 0,
        live_execution INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT NOT NULL,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """
    with _DB_LOCK:
        conn = db_conn()
        try:
            conn.executescript(schema)
            cols = {row[1] for row in conn.execute("PRAGMA table_info(users)").fetchall()}
            if "full_name" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN full_name TEXT")
            if "role" not in cols:
                conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
            fitness_cols = {row[1] for row in conn.execute("PRAGMA table_info(fitness_profiles)").fetchall()}
            for col, ddl in (("age_years", "REAL"), ("sex", "TEXT")):
                if col not in fitness_cols:
                    conn.execute(f"ALTER TABLE fitness_profiles ADD COLUMN {col} {ddl}")
            diet_cols = {row[1] for row in conn.execute("PRAGMA table_info(fitness_diet_entries)").fetchall()}
            for col, ddl in (("meal_type", "TEXT"), ("meal_time", "TEXT"), ("sugar", "REAL NOT NULL DEFAULT 0"), ("sodium_mg", "REAL NOT NULL DEFAULT 0"), ("cholesterol_mg", "REAL NOT NULL DEFAULT 0"), ("calcium_mg", "REAL NOT NULL DEFAULT 0"), ("iron_mg", "REAL NOT NULL DEFAULT 0"), ("potassium_mg", "REAL NOT NULL DEFAULT 0"), ("vitamin_d_mcg", "REAL NOT NULL DEFAULT 0"), ("vitamin_b12_mcg", "REAL NOT NULL DEFAULT 0")):
                if col not in diet_cols:
                    conn.execute(f"ALTER TABLE fitness_diet_entries ADD COLUMN {col} {ddl}")
            fund_cols = {row[1] for row in conn.execute("PRAGMA table_info(funds)").fetchall()}
            for col in ("trading_funds", "testing_funds", "auto_trade_funds"):
                if col not in fund_cols:
                    conn.execute(f"ALTER TABLE funds ADD COLUMN {col} REAL NOT NULL DEFAULT 0")
            order_cols = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
            if "amo" not in order_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN amo INTEGER NOT NULL DEFAULT 0")
            if "final_pnl" not in order_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN final_pnl REAL")
            if "exit_price" not in order_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN exit_price REAL")
            pos_cols = {row[1] for row in conn.execute("PRAGMA table_info(positions)").fetchall()}
            if "reserved_value" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN reserved_value REAL NOT NULL DEFAULT 0")
            if "fund_bucket" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN fund_bucket TEXT NOT NULL DEFAULT 'trading'")
            order_cols = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
            if "fund_bucket" not in order_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN fund_bucket TEXT NOT NULL DEFAULT 'trading'")
            if "recommendation_id" not in order_cols:
                conn.execute("ALTER TABLE orders ADD COLUMN recommendation_id TEXT")
            if "status" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN status TEXT NOT NULL DEFAULT 'OPEN'")
            if "exit_price" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN exit_price REAL")
            if "final_pnl" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN final_pnl REAL")
            if "closed_at" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN closed_at TEXT")
            if "recommendation_id" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN recommendation_id TEXT")
            if "underlying" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN underlying TEXT")
            if "instrument_kind" not in pos_cols:
                conn.execute("ALTER TABLE positions ADD COLUMN instrument_kind TEXT")
            rec_cols = {row[1] for row in conn.execute("PRAGMA table_info(recommendations)").fetchall()}
            if "underlying" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN underlying TEXT")
            if "instrument_key" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN instrument_key TEXT")
            if "instrument_kind" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN instrument_kind TEXT")
            if "option_side" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN option_side TEXT")
            if "option_strike" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN option_strike REAL")
            if "option_expiry" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN option_expiry TEXT")
            if "score" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN score REAL")
            if "status" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN status TEXT DEFAULT 'NEW'")
            if "order_id" not in rec_cols:
                conn.execute("ALTER TABLE recommendations ADD COLUMN order_id TEXT")
            member_cols = {row[1] for row in conn.execute("PRAGMA table_info(watchlist_members)").fetchall()}
            if "position" not in member_cols:
                conn.execute("ALTER TABLE watchlist_members ADD COLUMN position INTEGER NOT NULL DEFAULT 0")
                groups = conn.execute("SELECT id FROM watchlist_groups ORDER BY id").fetchall()
                for group in groups:
                    members = conn.execute("SELECT id FROM watchlist_members WHERE watchlist_id=? ORDER BY id", (group[0],)).fetchall()
                    for pos, member in enumerate(members):
                        conn.execute("UPDATE watchlist_members SET position=? WHERE id=?", (pos, member[0]))
            conn.execute("UPDATE users SET role='admin' WHERE email=?", [(os.getenv("CA_EMAIL_ID") or "").strip().lower()])
            conn.execute("UPDATE funds SET available=300000,trading_funds=300000,testing_funds=300000,auto_trade_funds=300000,updated_at=? WHERE user_id IN (SELECT id FROM users WHERE role='admin') AND COALESCE(available,0)=0 AND COALESCE(trading_funds,0)=0", [now_iso()])
            conn.execute("UPDATE funds SET available=200000,trading_funds=200000,auto_trade_funds=200000,updated_at=? WHERE user_id IN (SELECT id FROM users WHERE COALESCE(role,'user')<>'admin') AND COALESCE(available,0)=0 AND COALESCE(trading_funds,0)=0", [now_iso()])
            conn.commit()
        finally:
            conn.close()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return base64.urlsafe_b64encode(salt + key).decode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        raw = base64.urlsafe_b64decode(encoded.encode())
        salt, expected = raw[:16], raw[16:]
        actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
        return hmac.compare_digest(expected, actual)
    except Exception:
        return False


def seed_admin() -> None:
    # Login is email-only. CA_ADMIN_USERNAME is retained only as a one-time
    # migration hint for databases created by older versions.
    email = (os.getenv("CA_EMAIL_ID") or "").strip().lower()
    password = os.getenv("CA_ADMIN_PASSWORD")
    legacy_username = (os.getenv("CA_ADMIN_USERNAME") or "").strip()
    if not email or not password:
        return

    row = db_exec("SELECT * FROM users WHERE email=?", [email], "one")
    if not row and legacy_username:
        row = db_exec("SELECT * FROM users WHERE username=?", [legacy_username], "one")
        if row:
            db_exec("UPDATE users SET email=?, password_hash=?, role='admin' WHERE id=?", [email, hash_password(password), row["id"]])
            db_exec("INSERT INTO funds(user_id,available,trading_funds,testing_funds,auto_trade_funds,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET available=300000,trading_funds=300000,testing_funds=300000,auto_trade_funds=300000,updated_at=excluded.updated_at", [row["id"],300000,300000,300000,300000,now_iso()])
            return

    if row:
        # Keep the existing account and synchronize the configured admin
        # password/email without changing the visible application UI.
        db_exec("UPDATE users SET email=?, password_hash=?, role='admin', is_active=1 WHERE id=?", [email, hash_password(password), row["id"]])
        db_exec("INSERT INTO funds(user_id,available,trading_funds,testing_funds,auto_trade_funds,updated_at) VALUES(?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET available=300000,trading_funds=300000,testing_funds=300000,auto_trade_funds=300000,updated_at=excluded.updated_at", [row["id"],300000,300000,300000,300000,now_iso()])
        return

    uid = db_insert(
        "INSERT INTO users(username,password_hash,email,created_at,full_name,role) VALUES(?,?,?,?,?,?)",
        [email, hash_password(password), email, now_iso(), email, "admin"],
    )
    db_exec(
        "INSERT INTO funds(user_id,available,trading_funds,testing_funds,auto_trade_funds,updated_at) VALUES(?,?,?,?,?,?)",
        [uid, 300000, 300000, 300000, 300000, now_iso()],
    )


def get_user(user_id: int) -> dict[str, Any] | None:
    return db_exec("SELECT * FROM users WHERE id=? AND is_active=1", [user_id], "one")

def fitness_allowlisted(user: dict[str, Any] | None) -> bool:
    return bool(user and (str(user.get("role") or "").lower()=="admin" or str(user.get("email") or "").strip().lower() in FITNESS_SELECTOR_EMAILS))

def selected_terminal(request: Request) -> str | None:
    return str(request.session.get("selected_terminal") or "").strip() or None

def fitness_today() -> str:
    return datetime.now(FITNESS_TIMEZONE).date().isoformat()

def fitness_profile_row(user_id: int) -> dict[str, Any] | None:
    return db_exec("SELECT * FROM fitness_profiles WHERE user_id=?", [user_id], "one")

def fitness_profile_payload(row: dict[str, Any] | None) -> dict[str, Any] | None:
    if not row: return None
    out=dict(row); out["completed"]=bool(out.get("completed")); return out

def fitness_parse_sets(raw: Any) -> list[dict[str, float]]:
    sets=[]
    for x in raw if isinstance(raw,list) else []:
        try:
            w=float(x.get("weight",0)); r=int(x.get("reps",0))
            if w>0 and r>0: sets.append({"weight":w,"reps":r})
        except Exception:
            pass
    return sets

def fitness_e1rm(weight: float, reps: int) -> float:
    # Epley estimate; capped to avoid silly high-rep distortion.
    return weight * (1 + min(reps, 15) / 30.0)

def fitness_food_normalize(name: str, calories: float = 0, protein: float = 0, carbs: float = 0, fat: float = 0, fiber: float = 0,
                            serving: str = "100 g", source: str = "internet", ai_estimated: bool = False,
                            confidence: str = "verified", food_id: str | None = None, serving_grams: float | None = None,
                            micros: dict[str,Any] | None = None) -> dict[str, Any]:
    micros=micros or {}
    return {"name": str(name).strip(), "calories": round(float(calories or 0),1), "protein": round(float(protein or 0),1),
            "carbs": round(float(carbs or 0),1), "fat": round(float(fat or 0),1), "fiber": round(float(fiber or 0),1),
            "serving": serving, "serving_grams": serving_grams, "source": source, "ai_estimated": bool(ai_estimated), "confidence": confidence,
            "food_id": food_id, "micros": micros}

# Canonical items keep common searches such as "egg" from returning packaged products with wildly different labels.
FITNESS_CANONICAL_FOODS = {
    "egg": {"name":"Egg, whole, large", "aliases":["eggs","whole egg","chicken egg"], "calories":72, "protein":6.3, "carbs":0.4, "fat":4.8, "fiber":0, "serving":"1 large egg (50 g)", "serving_grams":50, "source":"USDA FoodData Central"},
    "egg white": {"name":"Egg white, raw, fresh", "aliases":["egg whites","egg white"], "calories":52, "protein":10.9, "carbs":0.7, "fat":0.2, "fiber":0, "serving":"100 g", "serving_grams":100, "source":"USDA FoodData Central"},
    "chicken breast": {"name":"Chicken breast, meat only, raw", "aliases":["chicken","chicken breast","raw chicken"], "calories":120, "protein":22.5, "carbs":0, "fat":2.6, "fiber":0, "serving":"100 g", "serving_grams":100, "source":"USDA FoodData Central"},
    "rice": {"name":"Rice, white, long-grain, regular, raw", "aliases":["white rice","rice"], "calories":365, "protein":7.1, "carbs":80.0, "fat":0.7, "fiber":1.3, "serving":"100 g", "source":"USDA FoodData Central"},
    "roti": {"name":"Roti / chapati, whole wheat, plain", "aliases":["chapati","roti","atta roti"], "calories":297, "protein":11.0, "carbs":46.0, "fat":7.5, "fiber":7.0, "serving":"100 g", "serving_grams":100, "source":"Indian food composition estimate", "confidence":"verified-range"},
    "paneer": {"name":"Paneer, Indian cottage cheese", "aliases":["paneer","cottage cheese indian"], "calories":265, "protein":18.3, "carbs":1.2, "fat":20.8, "fiber":0, "serving":"100 g", "serving_grams":100, "source":"Indian food composition estimate", "confidence":"verified-range"},
    "dal": {"name":"Dal, cooked, lentils", "aliases":["dal","lentils","dal fry"], "calories":116, "protein":9.0, "carbs":20.1, "fat":0.4, "fiber":7.9, "serving":"100 g", "serving_grams":100, "source":"USDA FoodData Central", "confidence":"verified-range"},
    "banana": {"name":"Banana, raw", "aliases":["banana"], "calories":89, "protein":1.1, "carbs":22.8, "fat":0.3, "fiber":2.6, "serving":"1 medium (118 g)", "serving_grams":118, "source":"USDA FoodData Central"},
    "oats": {"name":"Oats, whole grain, dry", "aliases":["oats","rolled oats","oatmeal"], "calories":389, "protein":16.9, "carbs":66.3, "fat":6.9, "fiber":10.6, "serving":"40 g", "serving_grams":40, "source":"USDA FoodData Central"},
    "milk": {"name":"Milk, whole", "aliases":["milk","whole milk"], "calories":61, "protein":3.2, "carbs":4.8, "fat":3.3, "fiber":0, "serving":"100 ml", "serving_grams":103, "source":"USDA FoodData Central"},
    "curd": {"name":"Yogurt, plain, whole milk", "aliases":["curd","dahi","yogurt"], "calories":61, "protein":3.5, "carbs":4.7, "fat":3.3, "fiber":0, "serving":"100 g", "serving_grams":100, "source":"USDA FoodData Central"},
    "potato": {"name":"Potato, flesh and skin, raw", "aliases":["potato","aloo"], "calories":77, "protein":2.0, "carbs":17.5, "fat":0.1, "fiber":2.2, "serving":"1 medium (173 g)", "serving_grams":173, "source":"USDA FoodData Central"},
    "almonds": {"name":"Almonds, raw", "aliases":["almonds","badam"], "calories":579, "protein":21.2, "carbs":21.6, "fat":49.9, "fiber":12.5, "serving":"28 g", "serving_grams":28, "source":"USDA FoodData Central"},
    "whey": {"name":"Whey protein powder, generic", "aliases":["whey protein","whey"], "calories":400, "protein":80, "carbs":8, "fat":6, "fiber":0, "serving":"30 g", "serving_grams":30, "source":"Generic composition; verify product label", "confidence":"reference"},
}

def fitness_ai_food(query: str) -> list[dict[str, Any]]:
    prompt=("You are a nutrition database assistant. Return ONLY a JSON array of up to 5 likely food entries for the query. "
            "Prefer Indian dishes and common grocery foods. Nutrition should be per 100 g unless a serving is clearly more useful. "
            "Never invent branded product data. For dishes, state it is an estimate. Include serving_grams whenever a normal serving size is known. Keys: name, calories, protein, carbs, fat, fiber, serving, serving_grams, micros. Query: "+query)
    r=gemini_text(prompt, 9000)
    if not r.get("available"): return []
    try:
        m=re.search(r"\[.*\]", r.get("text", ""), re.S); data=json.loads(m.group(0)) if m else []
    except Exception:
        data=[]
    return [fitness_food_normalize(str(x.get("name") or query),x.get("calories"),x.get("protein"),x.get("carbs"),x.get("fat"),x.get("fiber"),str(x.get("serving") or "100 g"),"Gemini",True,"estimated",None,float(x.get("serving_grams")) if x.get("serving_grams") else None,x.get("micros") if isinstance(x.get("micros"),dict) else {}) for x in data if isinstance(x,dict)]

def _fitness_food_quality_ok(x: dict[str, Any]) -> bool:
    # Reject obviously bad/label-per-serving values from generic searches.
    cal, p, c, f = map(lambda k: float(x.get(k) or 0), ("calories","protein","carbs","fat"))
    return 0 <= cal <= 850 and 0 <= p <= 100 and 0 <= c <= 100 and 0 <= f <= 100

def _fitness_canonical_for(query: str) -> list[dict[str, Any]]:
    q=re.sub(r"\s+"," ",query.lower().replace(")"," ").replace("("," ")).strip()
    hits=[]
    for key,item in FITNESS_CANONICAL_FOODS.items():
        aliases=[key]+item.get("aliases",[])
        score=max((100 if q==a else 85 if a.startswith(q) else 80 if q.startswith(a) else 65 if q in a else 0) for a in aliases)
        if score:
            hits.append((score,item))
    hits.sort(key=lambda x:-x[0])
    out=[]
    for _,item in hits[:6]:
        out.append(fitness_food_normalize(item["name"],item["calories"],item["protein"],item["carbs"],item["fat"],item["fiber"],item["serving"],item["source"],False,item.get("confidence","verified"),None,item.get("serving_grams"),{}))
    return out

def fitness_food_suggestions(query: str) -> list[str]:
    q=query.strip().lower()
    if not q: return []
    out=[]
    for key,item in FITNESS_CANONICAL_FOODS.items():
        for a in [item["name"]]+item.get("aliases",[]):
            if a.lower().startswith(q) or q in a.lower():
                if a.lower() not in [x.lower() for x in out]: out.append(a)
    return out[:8]

def fitness_fetch_foods(query: str) -> list[dict[str, Any]]:
    query=query.strip()
    key=hashlib.sha256(query.lower().encode()).hexdigest()[:32]
    cached=db_exec("SELECT * FROM fitness_food_cache WHERE cache_key=? AND expires_at>?", [key, now_iso()], "one")
    if cached:
        try: return json.loads(cached["data_json"])
        except Exception: pass

    results=_fitness_canonical_for(query)
    # Exact common-food searches should not be polluted by packaged/variant results.
    qnorm=re.sub(r"\s+"," ",query.lower()).strip()
    if qnorm in {"egg","eggs","whole egg","chicken egg"} and results:
        results=results[:1]
    # USDA first for generic foods: best source for canonical, unbranded nutrition.
    try:
        rr=requests.get("https://api.nal.usda.gov/fdc/v1/foods/search", params={"api_key":USDA_API_KEY,"query":query,"pageSize":20,"dataType":"Foundation,SR Legacy"}, timeout=8)
        if rr.ok:
            for x in rr.json().get("foods",[]):
                n=str(x.get("description") or "").strip()
                vals={q.get("nutrientName"):q.get("value") for q in x.get("foodNutrients",[]) if isinstance(q,dict)}
                if not n: continue
                micros={"sodium_mg":vals.get("Sodium"),"potassium_mg":vals.get("Potassium"),"calcium_mg":vals.get("Calcium"),"iron_mg":vals.get("Iron"),"vitamin_d_mcg":vals.get("Vitamin D (D2 + D3)"),"vitamin_b12_mcg":vals.get("Vitamin B-12"),"cholesterol_mg":vals.get("Cholesterol"),"sugar":vals.get("Sugars, total including NLEA")}
                serving_grams=x.get("servingSize") if x.get("servingSizeUnit") and str(x.get("servingSizeUnit")).lower() in {"g","gram","grams"} else None
                serving=f"{serving_grams:g} g" if serving_grams else "100 g"
                item=fitness_food_normalize(n, vals.get("Energy"), vals.get("Protein"), vals.get("Carbohydrate, by difference"), vals.get("Total lipid (fat)"), vals.get("Fiber, total dietary"), serving, "USDA FoodData Central", False, "verified", str(x.get("fdcId") or ""), serving_grams, micros)
                if _fitness_food_quality_ok(item): results.append(item)
    except Exception as exc:
        record_error("fitness_food_search","USDA: "+safe_text(exc))

    # OpenFoodFacts is kept as a secondary source for actual packaged products, not first-ranked generic foods.
    try:
        rr=requests.get("https://world.openfoodfacts.org/cgi/search.pl", params={"search_terms":query,"search_simple":1,"action":"process","json":1,"page_size":20}, headers={"User-Agent":"CA-Trader-Fitness/1.0"}, timeout=8)
        if rr.ok:
            for x in rr.json().get("products",[]):
                n=str(x.get("product_name") or x.get("product_name_en") or "").strip(); ns=x.get("nutriments") or {}
                if not n: continue
                item=fitness_food_normalize(n,ns.get("energy-kcal_100g"),ns.get("proteins_100g"),ns.get("carbohydrates_100g"),ns.get("fat_100g"),ns.get("fiber_100g"),"100 g","OpenFoodFacts",False,"verified",str(x.get("code") or ""))
                if _fitness_food_quality_ok(item): results.append(item)
    except Exception as exc:
        record_error("fitness_food_search","OpenFoodFacts: "+safe_text(exc))

    # Rank exact/near exact generic items before products; then dedupe by normalized name + calories.
    qwords=set(re.findall(r"[a-z0-9]+",query.lower()))
    def rank(x):
        n=x["name"].lower(); exact=1 if n==query.lower() else 0; word=sum(1 for w in qwords if w in n)
        source_bonus=2 if x["source"]=="USDA FoodData Central" else 0
        ai_penalty=20 if x.get("ai_estimated") else 0
        return exact*100+word*10+source_bonus-ai_penalty
    results.sort(key=rank, reverse=True)
    dedup=[]; seen=set()
    for x in results:
        k=(re.sub(r"[^a-z0-9]+"," ",x["name"].lower()).strip(), round(float(x.get("calories") or 0)))
        if k in seen: continue
        seen.add(k); dedup.append(x)
    # AI fills the tail only when verified sources are insufficient.
    if len(dedup)<4:
        dedup.extend(fitness_ai_food(query))
    final=[]; seen_names=set()
    for x in dedup:
        k=re.sub(r"[^a-z0-9]+"," ",x["name"].lower()).strip()
        if k in seen_names: continue
        seen_names.add(k); final.append(x)
    final=final[:12]
    try:
        expires=(datetime.now(timezone.utc)+timedelta(hours=FOOD_SEARCH_CACHE_HOURS)).isoformat()
        db_exec("INSERT INTO fitness_food_cache(cache_key,query,data_json,created_at,expires_at) VALUES(?,?,?,?,?) ON CONFLICT(cache_key) DO UPDATE SET data_json=excluded.data_json,expires_at=excluded.expires_at,created_at=excluded.created_at",[key,query,json.dumps(final),now_iso(),expires])
    except Exception: pass
    return final


def fitness_estimate_targets(height_cm: float, weight_kg: float, workout_frequency: float, goal: str = "Muscle gain",
                             age_years: float | None = None, sex: str | None = None) -> dict[str, Any]:
    h=float(height_cm); w=float(weight_kg); f=max(0.0,min(7.0,float(workout_frequency or 0))); g=str(goal or "Muscle gain")
    # Prefer Mifflin-St Jeor when age/sex are present; otherwise use a transparent weight-based TDEE heuristic.
    if age_years and sex in {"male","female"}:
        bmr=10*w+6.25*h-5*float(age_years)+(5 if sex=="male" else -161)
        activity=1.20 if f<=1 else 1.35 if f<=3 else 1.50 if f<=5 else 1.65
        maintenance=bmr*activity
        method="Mifflin-St Jeor + activity multiplier"
    else:
        maintenance=w*(28+1.3*f)
        bmr=None
        method="weight-based TDEE estimate; add age/sex for a more personalized estimate"
    if g.lower() in {"fat loss","cut","weight loss"}: calories=maintenance*0.90
    elif g.lower() in {"maintenance"}: calories=maintenance
    elif g.lower() in {"strength"}: calories=maintenance*1.05
    else: calories=maintenance*1.08
    protein_factor=2.0 if g.lower() in {"fat loss","cut","weight loss"} else 1.8 if g.lower() in {"muscle gain","strength"} else 1.6
    protein=w*protein_factor
    fat=calories*0.25/9
    carbs=max(0,(calories-protein*4-fat*9)/4)
    return {"calories":round(calories),"protein":round(protein),"fat":round(fat),"carbs":round(carbs),"maintenance_calories":round(maintenance),"bmr":round(bmr) if bmr else None,"method":method}


def fitness_parse_natural_workout(text: str) -> dict[str, Any] | None:
    t=text.replace("–","-").replace("—","-").strip()
    if not re.search(r"(?:sets?|bench|press|fly|pushdown|curl|squat|deadlift|row|workout|session)",t,re.I): return None
    # Prefer numbered exercise blocks such as `1. 4 sets of bench press (...)`.
    name_m=re.search(r"^\s*([^\n:]+?)\s+day\s*:",t,re.I)
    name=name_m.group(1).strip().title() if name_m else "Workout"
    if name.lower().replace("trieceps","triceps") in {"chest & triceps","chest and triceps"}: name="Chest & Triceps"
    exercises=[]
    block_pattern=re.compile(r"(?:^|\s)(\d+)\.\s*(?:\d+\s+sets?\s+of\s+)?([A-Za-z][A-Za-z0-9 &'\-/]{2,80}?)\s*\(([^)]{2,1500})\)",re.I)
    for m in block_pattern.finditer(t):
        ex_name=re.sub(r"^\s*sets?\s+of\s+","",m.group(2)).strip(" .,:-")
        pairs=re.findall(r"(\d+(?:\.\d+)?)\s*kg\s*x\s*(\d+)\s*(?:reps?)?",m.group(3),re.I)
        if pairs and any(k in ex_name.lower() for k in ("bench","press","fly","pushdown","squat","curl","row","deadlift","pulldown","raise","extension")):
            exercises.append({"exercise":ex_name,"sets":[{"weight":float(w),"reps":int(r)} for w,r in pairs]})
    # Fallback for line-based/manual input.
    if not exercises:
        for line in re.split(r"\n+",t):
            em=re.match(r"(?:\d+\.\s*)?(?:\d+\s+sets?\s+of\s+)?([A-Za-z][A-Za-z0-9 &'\-/]{2,80}?)(?:\s*[:(])",line.strip(),re.I)
            if not em: continue
            ex_name=em.group(1).strip(" .,:-")
            pairs=re.findall(r"(\d+(?:\.\d+)?)\s*kg\s*x\s*(\d+)",line,re.I)
            if pairs and any(k in ex_name.lower() for k in ("bench","press","fly","pushdown","squat","curl","row","deadlift","pulldown","raise","extension")):
                exercises.append({"exercise":ex_name,"sets":[{"weight":float(w),"reps":int(r)} for w,r in pairs]})
    if not exercises:return None
    return {"date":fitness_today(),"name":name or "Workout","notes":"Imported from Mike Mentzer.AI conversation","exercises":exercises}


def fitness_ai_action_extract(text: str) -> dict[str, Any]:
    """Extract explicit log/add requests from the AI chat into safe structured actions.

    This is intentionally separate from the coaching response: the response can be
    conversational, while writes to the diet/workout log must be machine-readable.
    """
    t=str(text or '').strip()
    if not t or not re.search(r"\b(add|log|track|record|ate|eaten|had|include|put|did|completed|finished|performed)\b", t, re.I):
        return {"actions": []}
    prompt=(
        "You are the action parser for a bodybuilding tracker. Extract ONLY explicit user requests "
        "to ADD/LOG/RECORD something to their diet or workout. Do not treat questions, plans, "
        "suggestions, or hypothetical examples as logged actions. Return ONLY valid JSON, no markdown, "
        "with this shape: {\"actions\":[...]}. Each action is either "
        "{\"type\":\"diet\",\"food\":string,\"quantity\":string,\"meal_type\":string,"
        "\"meal_time\":string,\"calories\":number,\"protein\":number,\"carbs\":number,"
        "\"fat\":number,\"fiber\":number,\"source\":\"Gemini estimate\"} or "
        "{\"type\":\"workout\",\"date\":string,\"name\":string,\"notes\":string,"
        "\"exercises\":[{\"exercise\":string,\"sets\":[{\"weight\":number,\"reps\":integer}]}]}. "
        "For diet, estimate nutrition for the exact quantity/serving the user gave. If exact nutrition "
        "cannot be known, make a reasonable clearly estimated value; never invent a branded label. "
        "Use today's date for workout date when none is given. Use meal type Lunch/Breakfast/Dinner/etc. "
        "when explicitly stated; otherwise Other. If there is no explicit log/add action, return {\"actions\":[]}. "
        "USER MESSAGE:\n"+t[:5000]
    )
    r=gemini_text(prompt,12000)
    if not r.get("available"):
        return {"actions": [], "reason": r.get("reason")}
    raw=str(r.get("text") or "").strip()
    try:
        m=re.search(r"\{.*\}",raw,re.S)
        data=json.loads(m.group(0)) if m else {"actions":[]}
        return data if isinstance(data,dict) and isinstance(data.get("actions"),list) else {"actions":[]}
    except Exception as exc:
        record_error("fitness_action_parse",safe_text(exc),"gemini")
        return {"actions":[]}


def fitness_store_diet(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    date=str(payload.get("date") or fitness_today())
    food=str(payload.get("food") or "").strip()
    if not food:
        raise HTTPException(422,"Food is required")
    quantity=str(payload.get("quantity") or "").strip()
    meal_type=str(payload.get("meal_type") or "Other").strip()
    meal_time=str(payload.get("meal_time") or "").strip()
    calories=float(payload.get("calories") or 0); protein=float(payload.get("protein") or 0)
    carbs=float(payload.get("carbs") or 0); fat=float(payload.get("fat") or 0); fiber=float(payload.get("fiber") or 0)
    # Idempotency: the AI can be retried by the browser/network. Do not duplicate the
    # exact same food/quantity/meal/nutrition payload within the same day.
    existing=db_exec("SELECT * FROM fitness_diet_entries WHERE user_id=? AND date=? ORDER BY created_at DESC LIMIT 100",[user_id,date],"all")
    for old in existing:
        if (str(old.get("food") or "").strip().lower()==food.lower() and str(old.get("quantity") or "").strip().lower()==quantity.lower()
            and str(old.get("meal_type") or "Other").lower()==meal_type.lower()
            and abs(float(old.get("calories") or 0)-calories)<0.05 and abs(float(old.get("protein") or 0)-protein)<0.05
            and abs(float(old.get("carbs") or 0)-carbs)<0.05 and abs(float(old.get("fat") or 0)-fat)<0.05):
            return {"ok":True,"item":old,"already_logged":True}
    row={"id":secrets.token_hex(12),"user_id":user_id,"date":date,"food":food,"quantity":quantity,
         "calories":calories,"protein":protein,"carbs":carbs,"fat":fat,"fiber":fiber,"meal_type":meal_type,"meal_time":meal_time,
         "sugar":float(payload.get("sugar") or 0),"sodium_mg":float(payload.get("sodium_mg") or 0),
         "cholesterol_mg":float(payload.get("cholesterol_mg") or 0),"calcium_mg":float(payload.get("calcium_mg") or 0),
         "iron_mg":float(payload.get("iron_mg") or 0),"potassium_mg":float(payload.get("potassium_mg") or 0),
         "vitamin_d_mcg":float(payload.get("vitamin_d_mcg") or 0),"vitamin_b12_mcg":float(payload.get("vitamin_b12_mcg") or 0),
         "source":str(payload.get("source") or "user"),"created_at":now_iso()}
    db_exec("INSERT INTO fitness_diet_entries(id,user_id,date,food,quantity,calories,protein,carbs,fat,fiber,meal_type,meal_time,sugar,sodium_mg,cholesterol_mg,calcium_mg,iron_mg,potassium_mg,vitamin_d_mcg,vitamin_b12_mcg,source,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",list(row.values()))
    return {"ok":True,"item":row,"already_logged":False}


def fitness_chicken_price() -> tuple[float,str]:
    cached=CACHE.get("fitness_chicken_price")
    if cached: return cached
    price=180.0; source="fallback estimate"
    # Best-effort public web search; this is deliberately soft-fail because retailer pages vary.
    try:
        q=quote("chicken 1 kg price India INR today", safe="")
        rr=requests.get("https://html.duckduckgo.com/html/?q="+q, headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
        text=re.sub(r"\s+"," ",rr.text)
        vals=[]
        for m in re.finditer(r"(?:₹|Rs\.?|INR\s*)\s*(\d{2,4})",text,re.I):
            v=float(m.group(1));
            if 120<=v<=350: vals.append(v)
        if vals:
            price=statistics.median(vals[:12]); source="public web search"
    except Exception:
        pass
    CACHE.set("fitness_chicken_price",(price,source),21600)
    return price,source

# ---------------------------------------------------------------------------
# Cache, dedupe, rate limiting, provider health, events
# ---------------------------------------------------------------------------

class TTLCache:
    def __init__(self) -> None:
        self._data: dict[str, tuple[float, Any]] = {}
        self._lock = threading.RLock()

    def get(self, key: str) -> Any:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, value = item
            if time.monotonic() > expires:
                self._data.pop(key, None)
                return None
            return value

    def set(self, key: str, value: Any, ttl: float) -> None:
        with self._lock:
            self._data[key] = (time.monotonic() + ttl, value)

    def clear(self) -> None:
        with self._lock:
            self._data.clear()

CACHE = TTLCache()
REQUEST_SEMAPHORE = asyncio.Semaphore(12)


class RateLimiter:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.RLock()

    def allow(self, key: str) -> bool:
        if not RATE_LIMIT_ENABLED:
            return True
        now = time.monotonic()
        cutoff = now - 60
        with self._lock:
            q = self._hits[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= RATE_LIMIT_PER_MINUTE:
                return False
            q.append(now)
            return True

RATE_LIMITER = RateLimiter()

PROVIDER_HEALTH: dict[str, dict[str, Any]] = defaultdict(lambda: {"status": "unknown", "last_error": None, "last_ok": None})


class EventBus:
    def __init__(self) -> None:
        self.clients: dict[int, set[WebSocket]] = defaultdict(set)
        self.lock = asyncio.Lock()

    async def add(self, user_id: int, websocket: WebSocket) -> None:
        async with self.lock:
            self.clients[int(user_id)].add(websocket)

    async def remove(self, user_id: int, websocket: WebSocket) -> None:
        async with self.lock:
            bucket = self.clients.get(int(user_id), set())
            bucket.discard(websocket)
            if not bucket:
                self.clients.pop(int(user_id), None)

    async def publish(self, event: dict[str, Any], user_ids: Iterable[int] | None = None) -> None:
        async with self.lock:
            targets = set(int(x) for x in user_ids) if user_ids is not None else set(self.clients)
            dead: list[tuple[int, WebSocket]] = []
            message = json.dumps(event, separators=(",", ":"), default=str)
            for uid in targets:
                for ws in list(self.clients.get(uid, set())):
                    try:
                        await ws.send_text(message)
                    except Exception:
                        dead.append((uid, ws))
            for uid, ws in dead:
                self.clients.get(uid, set()).discard(ws)

EVENT_BUS = EventBus()
MAIN_LOOP: asyncio.AbstractEventLoop | None = None


def record_error(category: str, message: str, provider: str | None = None, user_id: int | None = None,
                 status_code: int | None = None, context: dict[str, Any] | None = None) -> str:
    event_id = secrets.token_hex(12)
    safe_msg = safe_text(message)[:1000]
    db_exec(
        "INSERT INTO error_events(id,user_id,category,provider,status_code,message,context_json,created_at) VALUES(?,?,?,?,?,?,?,?)",
        [event_id, user_id, category, provider, status_code, safe_msg, json.dumps(context or {}, default=str), now_iso()],
    )
    if provider:
        PROVIDER_HEALTH[provider].update({"status": "degraded", "last_error": now_iso()})
    log.error("%s provider=%s user=%s %s", category, provider, user_id, safe_msg)
    return event_id


def provider_ok(provider: str) -> None:
    PROVIDER_HEALTH[provider].update({"status": "healthy", "last_ok": now_iso(), "last_error": None})

# ---------------------------------------------------------------------------
# Market-session service (Asia/Kolkata)
# ---------------------------------------------------------------------------

IST = timezone(timedelta(hours=5, minutes=30))
# NSE cash/F&O trading holidays relevant to previous-market-day news filtering.
# 2026 schedule is based on the exchange's published holiday calendar; callers
# can extend/override via NEWS_MARKET_HOLIDAYS=YYYY-MM-DD,YYYY-MM-DD,... .
_NSE_HOLIDAYS_BY_YEAR = {
    2026: {
        '2026-01-26','2026-03-03','2026-03-26','2026-03-31','2026-04-03',
        '2026-04-14','2026-05-01','2026-05-28','2026-06-26','2026-09-14',
        '2026-10-02','2026-10-20','2026-11-08','2026-11-10','2026-11-24','2026-12-25'
    }
}

def _news_market_holidays():
    out=set()
    for y, vals in _NSE_HOLIDAYS_BY_YEAR.items(): out.update(vals)
    extra=os.getenv('NEWS_MARKET_HOLIDAYS','')
    if extra:
        out.update(x.strip() for x in extra.split(',') if re.fullmatch(r'\d{4}-\d{2}-\d{2}',x.strip()))
    return out

def _is_market_day(d):
    return d.weekday() < 5 and d.isoformat() not in _news_market_holidays()

def _previous_market_day(d):
    cur=d-timedelta(days=1)
    while not _is_market_day(cur): cur-=timedelta(days=1)
    return cur


def market_session(segment: str = "NSE_EQ", at: datetime | None = None) -> dict[str, Any]:
    at = at or datetime.now(IST)
    if at.weekday() >= 5:
        return {"segment": segment, "active": False, "session": "closed", "reason": "weekend", "timestamp": at.isoformat()}
    t = at.time()
    open_t, close_t = ("09:15", "23:00") if segment.upper() in {"MCX", "COM"} else ("09:15", "15:30")
    active = datetime.strptime(open_t, "%H:%M").time() <= t <= datetime.strptime(close_t, "%H:%M").time()
    return {"segment": segment,"active": active,"session": "market" if active else "closed","open": open_t,"close": close_t,"timestamp": at.isoformat()}

# ---------------------------------------------------------------------------
# Upstox adapter: centralized/shared cache, provider-neutral responses
# ---------------------------------------------------------------------------

def classify_instrument_segment(instrument: str, meta: dict[str, Any] | None = None, key: str | None = None) -> str:
    """Return the actual Upstox market segment for an instrument.

    Prefer provider metadata and the instrument key. This is important for NSE_INDEX
    and BSE_INDEX, which must not be collapsed into NSE_EQ merely because the symbol
    is a short name such as NIFTY or BANKNIFTY.
    """
    m=meta or {}
    seg=str(m.get("segment") or m.get("exchange_segment") or "").upper()
    k=str(key or m.get("instrument_key") or "").upper()
    typ=str(m.get("instrument_type") or m.get("instrument_type_code") or "").upper()
    if seg in {"MCX", "MCX_FO", "NSE_COM", "NCD_FO", "BCD_FO"} or k.startswith("MCX") or k.startswith("NSE_COM") or "COM" in k:
        return "MCX"
    if seg == "BSE_INDEX" or k.startswith("BSE_INDEX|"):
        return "BSE_INDEX"
    if seg == "NSE_INDEX" or k.startswith("NSE_INDEX|") or typ == "INDEX":
        return "NSE_INDEX"
    if seg.startswith("BSE") or k.startswith("BSE_"):
        return "BSE_EQ"
    return "NSE_EQ"


class UpstoxAdapter:
    def __init__(self) -> None:
        self.base = UPSTOX_BASE_URL
        # Prefer the primary token, then any numbered fallback tokens from .env.
        self.tokens = list(dict.fromkeys([t.strip() for t in UPSTOX_ACCESS_TOKENS if t and t.strip()]))
        if not self.tokens and UPSTOX_ACCESS_TOKEN.strip():
            self.tokens = [UPSTOX_ACCESS_TOKEN.strip()]
        self.token = self.tokens[0] if self.tokens else ""
        self.session = requests.Session()
        adapter = HTTPAdapter(pool_connections=16, pool_maxsize=16, max_retries=0, pool_block=True)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.session.headers.update({"Accept": "application/json", "Content-Type": "application/json"})
        self._resolve_cache: dict[str, tuple[float, tuple[str, dict[str, Any]]]] = {}
        self._resolve_cache_ttl = 900.0

    def _require(self) -> None:
        if not self.tokens:
            raise ProviderUnavailable("Upstox access token is not configured; set UPSTOX_ACCESS_TOKEN in .env")

    def _get(self, path: str, params: dict[str, Any] | None = None, ttl: float = 3.0, cache_key: str | None = None, base_url: str | None = None) -> dict[str, Any]:
        self._require()
        key = cache_key or "upstox:" + path + ":" + urlencode(sorted((params or {}).items()))
        cached = CACHE.get(key)
        if cached is not None:
            return cached
        url = (base_url or self.base) + path
        last_status = None
        last_text = ""
        for token in self.tokens[:max(1, len(self.tokens))]:
            try:
                with _UPSTOX_HTTP_SEM, _REQUEST_CONTEXT():
                    response = self.session.get(url, params=params, timeout=10, headers={"Authorization": f"Bearer {token}"})
            except Exception as exc:
                record_error("provider_failure", repr(exc), "upstox", context={"path": path})
                continue
            last_status = response.status_code
            last_text = response.text[:300]
            if response.status_code in (401, 403):
                continue
            if response.status_code == 429:
                record_error("rate_limited", "Upstox rate limited", "upstox", 429, context={"path": path})
                raise ProviderRateLimited("Upstox rate limited")
            if response.status_code >= 400:
                record_error("api_failure", f"Upstox HTTP {response.status_code}", "upstox", response.status_code, context={"path": path})
                raise ProviderUnavailable(f"Upstox HTTP {response.status_code}: {safe_text(last_text)}")
            try:
                payload = response.json()
            except Exception as exc:
                record_error("malformed_data", "Upstox returned invalid JSON", "upstox", context={"path": path})
                raise ProviderUnavailable("Invalid Upstox JSON") from exc
            provider_ok("upstox")
            CACHE.set(key, payload, ttl)
            return payload
        if last_status in (401, 403):
            record_error("auth_failure", f"Upstox HTTP {last_status}", "upstox", last_status, context={"path": path})
            raise ProviderUnavailable(f"Upstox authentication failed (HTTP {last_status}); check UPSTOX_ACCESS_TOKEN in .env")
        raise ProviderUnavailable("Upstox request failed")

    def search_instruments(self, query: str, exchanges: str = "NSE", segments: str = "ALL") -> dict[str, Any]:
        return self._get("/instruments/search", {"query": query[:50], "exchanges": exchanges, "segments": segments, "page_number": 1, "records": 30}, ttl=300)

    def resolve_instrument(self, identifier: str) -> tuple[str, dict[str, Any]]:
        # Accept raw Upstox instrument key directly.
        if "|" in identifier:
            return identifier, {"instrument_key": identifier, "symbol": identifier.split("|")[-1]}
        ident_key = identifier.upper().strip()
        now = time.time()
        cached = self._resolve_cache.get(ident_key)
        if cached and now - cached[0] < self._resolve_cache_ttl:
            key, meta = cached[1]
            return key, dict(meta)
        payload = self.search_instruments(identifier, exchanges="NSE,BSE,MCX", segments="ALL")
        rows = payload.get("data") or []
        if not rows:
            raise HTTPException(status_code=404, detail=f"Instrument not found: {identifier}")
        # Prefer exact trading-symbol matches, then exact name matches, then the most
        # liquid/common cash/index segment over derivatives. This prevents a symbol
        # such as NIFTY or RELIANCE from resolving to an option/future accidentally.
        ident_u = identifier.upper().strip()
        exact_symbol = [r for r in rows if str(r.get("trading_symbol", "")).upper().strip() == ident_u]
        exact_name = [r for r in rows if str(r.get("name", "")).upper().strip() == ident_u]
        candidates = exact_symbol or exact_name or rows
        preferred = next((r for r in candidates if str(r.get("segment","")).upper() in {"NSE_INDEX","BSE_INDEX","NSE_EQ","BSE_EQ","MCX_FO"} and str(r.get("instrument_type","")).upper() not in {"CE","PE"}), candidates[0])
        row = preferred
        key = row.get("instrument_key") or row.get("instrument_token")
        if not key:
            raise ProviderUnavailable("Upstox instrument response lacks instrument_key")
        result=(str(key), dict(row))
        self._resolve_cache[ident_key]=(now,result)
        return result

    def _previous_session_close(self, key: str) -> float | None:
        """Get and cache the last completed daily close for change calculations.
        The full-market quote endpoint normally returns net_change directly, but some
        responses/feeds can omit it or return 0 while a live move is present.
        Cache this recovery value so it never becomes a per-tick request.
        """
        cache_key=f"prev-close:{key}"
        cached=CACHE.get(cache_key)
        if cached is not None:
            return float(cached) if cached is not None else None
        try:
            now=datetime.now(IST)
            end=(now.date()-timedelta(days=1))
            start=end-timedelta(days=7)
            path=f"/historical-candle/{quote(key,safe='')}/days/1/{end.isoformat()}/{start.isoformat()}"
            payload=self._get(path,{},ttl=300.0,cache_key=cache_key,base_url=UPSTOX_V3_BASE_URL)
            rows=(payload.get('data') or {}).get('candles') or []
            vals=[]
            for row in rows:
                try:
                    vals.append((str(row[0]),float(row[4])))
                except Exception:
                    continue
            if vals:
                close=sorted(vals)[-1][1]
                CACHE.set(cache_key,close,300.0)
                return close
        except Exception as exc:
            log.debug("Previous close lookup failed for %s: %s", key, safe_text(exc))
        return None

    def _enrich_quote_change(self, q: dict[str, Any], key: str, raw: dict[str, Any]) -> dict[str, Any]:
        ltp=q.get("ltp")
        net=q.get("net_change")
        cp=q.get("cp")
        day_open=q.get("open")

        # Terminal intraday change is defined from TODAY'S OPEN, not previous close.
        # Keep provider day-over-day fields for compatibility, but expose explicit
        # session_* values for every live UI component.
        if ltp is not None and day_open not in (None, 0):
            try:
                day_open=float(day_open)
                live=float(ltp)
                q["session_open"]=day_open
                q["session_change"]=live-day_open
                q["session_change_pct"]=(live-day_open)/day_open*100.0
            except Exception:
                pass

        # Preserve/recover provider day-over-day change when available. This does not
        # overwrite the session change shown by the terminal.
        need_recovery=(net is None) or (ltp is not None and abs(float(net or 0)) < 1e-12)
        if need_recovery and ltp is not None:
            prev=self._previous_session_close(key)
            if prev is not None and prev>0:
                q["cp"]=prev
                q["net_change"]=float(ltp)-prev
                q["change_pct"]=(float(ltp)-prev)/prev*100.0
        elif net is not None and q.get("change_pct") is None and cp not in (None,0):
            q["change_pct"]=float(net)/float(cp)*100.0
        return q

    def quote(self, instrument: str) -> dict[str, Any]:
        key, meta = self.resolve_instrument(instrument)
        payload = self._get("/market-quote/quotes", {"instrument_key": key}, ttl=1.0, cache_key=f"quote:{key}")
        data = payload.get("data") or {}
        raw = data.get(key) or next(iter(data.values()), {})
        return self._enrich_quote_change(normalize_quote(key, instrument, meta, raw), key, raw)

    def quotes(self, instruments: list[str]) -> list[dict[str, Any]]:
        resolved=[]
        for instrument in instruments[:500]:
            try:
                key,meta=self.resolve_instrument(instrument); resolved.append((instrument,key,meta))
            except Exception as exc:
                log.debug("Quote resolve failed for %s: %s", instrument, safe_text(exc))
        if not resolved: return []
        keys=','.join(k for _,k,_ in resolved)
        try:
            payload=self._get("/market-quote/quotes", {"instrument_key":keys}, ttl=1.0, cache_key=f"quotes:{keys}")
            data=payload.get("data") or {}
        except Exception:
            data={}
        out=[]
        for instrument,key,meta in resolved:
            raw=data.get(key) or {}
            q=self._enrich_quote_change(normalize_quote(key,instrument,meta,raw),key,raw)
            # Some provider responses can omit a symbol from the bulk response.
            # Fall back to the single-quote endpoint so one bad instrument does
            # not blank the entire watchlist.
            if q.get("ltp") is None:
                try:
                    single=self.quote(instrument)
                    q.update(single)
                except Exception as exc:
                    log.debug("Single quote fallback failed for %s: %s", instrument, safe_text(exc))
            out.append(q)
        return out

    def ltp(self, instrument: str) -> dict[str, Any]:
        key, meta = self.resolve_instrument(instrument)
        payload = self._get("/market-quote/ltp", {"instrument_key": key}, ttl=0.75, cache_key=f"ltp:{key}")
        data = payload.get("data") or {}
        raw = data.get(key) or next(iter(data.values()), {})
        return {"instrument": instrument, "instrument_key": key, "ltp": raw.get("last_price"), "timestamp": now_iso(), "provider": "upstox", "fresh": True, "metadata": meta}

    def _normalize_candle_timestamp(self, value: Any) -> str | None:
        """Canonicalize provider timestamps to UTC ISO so all merges sort by time, not text."""
        try:
            if value is None:
                return None
            if isinstance(value, (int, float)):
                n=float(value)
                if n > 1e12:
                    dt=datetime.fromtimestamp(n/1000.0, tz=timezone.utc)
                else:
                    dt=datetime.fromtimestamp(n, tz=timezone.utc)
            else:
                raw=str(value).replace('Z','+00:00')
                dt=datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt=dt.replace(tzinfo=IST)
                dt=dt.astimezone(timezone.utc)
            return dt.isoformat()
        except Exception:
            return None

    def _parse_candle_rows(self, candles: list[Any]) -> list[dict[str, Any]]:
        out=[]
        for c in reversed(candles or []):
            if len(c) >= 6:
                ts=self._normalize_candle_timestamp(c[0])
                if not ts:
                    continue
                out.append({"timestamp": ts, "open": float(c[1]), "high": float(c[2]), "low": float(c[3]), "close": float(c[4]), "volume": float(c[5])})
        return out

    def _intraday_candles(self, key: str, timeframe: str, unit: str) -> list[dict[str, Any]]:
        # Upstox V3 exposes the current trading day's intraday candles separately.
        # This is required for live charts because the normal historical endpoint can
        # lag the current session.
        path=f"/historical-candle/intraday/{quote(key,safe='')}/{unit}/{timeframe}"
        payload=self._get(path, ttl=2.0, cache_key=f"intraday:{key}:{unit}:{timeframe}", base_url=UPSTOX_V3_BASE_URL)
        return self._parse_candle_rows((payload.get("data") or {}).get("candles") or [])

    def candles(self, instrument: str, timeframe: str = "15", unit: str = "minutes", days: int = 7) -> list[dict[str, Any]]:
        key, meta = self.resolve_instrument(instrument)
        segment = classify_instrument_segment(instrument, meta, key)
        now = datetime.now(IST)
        active = bool(market_session(segment, now).get("active"))
        today = now.date()
        end_date = today
        from_date = (end_date - timedelta(days=days)).isoformat()
        to_date = end_date.isoformat()
        out: list[dict[str, Any]] = []

        # Fetch historical and current-session candles independently. A transient 429
        # (or another upstream failure) on one endpoint must not erase usable data from
        # the other endpoint and produce a blank chart.
        hist_path=f"/historical-candle/{quote(key,safe='')}/{unit}/{timeframe}/{to_date}/{from_date}"
        try:
            payload=self._get(hist_path, ttl=10.0, cache_key=f"candles:{key}:{unit}:{timeframe}:{from_date}:{to_date}:{'open' if active else 'closed'}", base_url=UPSTOX_V3_BASE_URL)
            out.extend(self._parse_candle_rows((payload.get("data") or {}).get("candles") or []))
        except Exception as exc:
            log.warning("Historical candle fetch failed for %s/%s: %s", instrument, timeframe, safe_text(exc))

        # V3 intraday is especially important during the open session. It is safe to
        # use as an independent supplement even after the close, but failures are kept
        # non-fatal when historical candles are already available.
        if unit in {"minutes", "hours"}:
            try:
                recent=self._intraday_candles(key,timeframe,unit)
                if recent:
                    out.extend(recent)
            except Exception as exc:
                log.warning("Intraday candle fetch failed for %s/%s: %s", instrument, timeframe, safe_text(exc))

        seen=set(); merged=[]
        for c in out:
            ts=c.get("timestamp")
            if ts in seen: continue
            seen.add(ts); merged.append(c)
        merged.sort(key=lambda x:x.get("timestamp") or "")
        if not merged:
            raise ProviderUnavailable(f"No Upstox candles returned for {instrument} ({timeframe})")
        return merged

    def candles_between(self, instrument: str, timeframe: str, unit: str, from_date: datetime.date, to_date: datetime.date) -> list[dict[str, Any]]:
        key, meta = self.resolve_instrument(instrument)
        path = f"/historical-candle/{quote(key, safe='')}/{unit}/{timeframe}/{to_date.isoformat()}/{from_date.isoformat()}"
        payload = self._get(path, ttl=60.0, cache_key=f"candles-between:{key}:{unit}:{timeframe}:{from_date}:{to_date}", base_url=UPSTOX_V3_BASE_URL)
        data = payload.get("data") or {}
        candles = data.get("candles") or []
        out=[]
        for c in reversed(candles):
            if len(c)>=6:
                out.append({"timestamp":c[0],"open":float(c[1]),"high":float(c[2]),"low":float(c[3]),"close":float(c[4]),"volume":float(c[5])})
        return out

    def depth(self, instrument: str) -> dict[str, Any]:
        key, meta = self.resolve_instrument(instrument)
        payload = self._get("/market-quote/quotes", {"instrument_key": key}, ttl=1.0, cache_key=f"depth:{key}")
        data = payload.get("data") or {}
        raw = data.get(key) or next(iter(data.values()), {})
        return normalize_depth(instrument, key, meta, raw)

    def option_contracts(self, underlying: str, expiry: str | None = None) -> dict[str, Any]:
        key, _ = self.resolve_instrument(underlying)
        params = {"instrument_key": key}
        if expiry:
            params["expiry_date"] = expiry
        return self._get("/option/contract", params, ttl=300)

    def option_chain(self, underlying: str, expiry: str | None = None) -> dict[str, Any]:
        key, meta = self.resolve_instrument(underlying)
        resolved_expiry = expiry
        # Upstox requires expiry_date for /option/chain. Resolve the nearest listed
        # expiry once, then cache the live chain for a few seconds.
        if not resolved_expiry:
            try:
                contracts = self.option_contracts(underlying, None).get("data") or []
                exps=sorted({str(x.get("expiry")) for x in contracts if isinstance(x,dict) and x.get("expiry")})
                today=datetime.now(IST).date().isoformat()
                future=[x for x in exps if x>=today]
                resolved_expiry=future[0] if future else (exps[0] if exps else "current_week")
            except Exception:
                resolved_expiry="current_week"
        params: dict[str, Any] = {"instrument_key": key, "expiry_date": resolved_expiry}
        payload = self._get("/option/chain", params, ttl=3.0, cache_key=f"option-chain:{key}:{resolved_expiry}")
        out=normalize_option_chain(underlying, key, meta, payload)
        out["expiry"]=out.get("expiry") or resolved_expiry
        return out

    def option_greeks(self, instrument_keys: list[str]) -> dict[str, Any]:
        if not instrument_keys:
            return {"data": []}
        payload = self._get("/market-quote/option-greek", {"instrument_key": ",".join(instrument_keys[:50])}, ttl=2.0, base_url=UPSTOX_V3_BASE_URL)
        return payload

    def funds(self) -> dict[str, Any]:
        return self._get("/user/get-funds-and-margin", {}, ttl=2.0)

    def positions(self) -> dict[str, Any]:
        return self._get("/portfolio/short-term-positions", {}, ttl=2.0)

    def holdings(self) -> dict[str, Any]:
        return self._get("/portfolio/long-term-holdings", {}, ttl=15.0)

    def orders(self) -> dict[str, Any]:
        return self._get("/order/retrieve-all", {}, ttl=2.0)

    def create_order(self, body: dict[str, Any]) -> dict[str, Any]:
        self._require()
        url = self.base + "/order/place"
        try:
            response = self.session.post(url, json=body, timeout=10)
        except Exception as exc:
            record_error("provider_failure", repr(exc), "upstox", context={"path": "/order/place"})
            raise ProviderUnavailable("Upstox order request failed") from exc
        if response.status_code == 429:
            record_error("rate_limited", "Upstox rate limited", "upstox", 429, context={"path": "/order/place"})
            raise ProviderRateLimited("Upstox rate limited")
        if response.status_code >= 400:
            record_error("api_failure", f"Upstox order HTTP {response.status_code}", "upstox", response.status_code)
            raise ProviderUnavailable(f"Upstox order HTTP {response.status_code}")
        provider_ok("upstox")
        return response.json()

UPSTOX = UpstoxAdapter()

class ProviderUnavailable(RuntimeError):
    pass

class ProviderRateLimited(RuntimeError):
    pass


@contextlib.contextmanager

def _REQUEST_CONTEXT():
    # Central place for future metrics, connection throttling and request tracing.
    yield


def normalize_quote(key: str, identifier: str, meta: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    ohlc = raw.get("ohlc") or {}
    return {
        "instrument": identifier,
        "instrument_key": key,
        "symbol": meta.get("trading_symbol") or meta.get("short_name") or identifier,
        "exchange": meta.get("exchange") or key.split("|")[0],
        "ltp": raw.get("last_price"),
        "cp": raw.get("cp") or ohlc.get("close"),
        "open": ohlc.get("open"),
        "high": ohlc.get("high"),
        "low": ohlc.get("low"),
        "close": ohlc.get("close"),
        "volume": raw.get("volume") or raw.get("volume_traded"),
        "average_price": raw.get("average_price"),
        "net_change": raw.get("net_change"),
        "change_pct": raw.get("net_change_percentage"),
        "total_buy_quantity": raw.get("total_buy_quantity"),
        "total_sell_quantity": raw.get("total_sell_quantity"),
        "upper_circuit": raw.get("upper_circuit") or raw.get("upperCircuit") or raw.get("upper_circuit_limit") or raw.get("upperCircuitLimit"),
        "lower_circuit": raw.get("lower_circuit") or raw.get("lowerCircuit") or raw.get("lower_circuit_limit") or raw.get("lowerCircuitLimit"),
        "last_trade_time": raw.get("last_trade_time") or raw.get("timestamp"),
        "timestamp": now_iso(),
        "provider": "upstox",
        "fresh": True,
        "metadata": meta,
    }


def normalize_depth(instrument: str, key: str, meta: dict[str, Any], raw: dict[str, Any]) -> dict[str, Any]:
    def levels(name: str) -> list[dict[str, Any]]:
        raw_depth = raw.get("depth") or {}
        raw_levels = raw.get(name) or raw_depth.get("buy" if name == "bids" else "sell", []) or []
        if isinstance(raw_levels, dict):
            raw_levels = raw_levels.get("buy" if name == "bids" else "sell", [])
        out = []
        for level in raw_levels[:10]:
            if isinstance(level, dict):
                out.append({"price": level.get("price"), "quantity": level.get("quantity"), "orders": level.get("order") or level.get("orders")})
        return out
    bids = levels("bids")
    asks = levels("asks")
    best_bid = bids[0].get("price") if bids else None
    best_ask = asks[0].get("price") if asks else None
    spread = (best_ask - best_bid) if isinstance(best_ask, (int, float)) and isinstance(best_bid, (int, float)) else None
    bid_qty = sum(float(x.get("quantity") or 0) for x in bids)
    ask_qty = sum(float(x.get("quantity") or 0) for x in asks)
    denom = bid_qty + ask_qty
    imbalance = (bid_qty - ask_qty) / denom if denom else None
    return {"instrument": instrument, "instrument_key": key, "bids": bids, "asks": asks, "spread": spread, "imbalance": imbalance, "timestamp": now_iso(), "provider": "upstox", "fresh": True, "metadata": meta}


def normalize_option_chain(underlying: str, key: str, meta: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    raw = payload.get("data") or []
    rows = raw.get("option_chain") if isinstance(raw, dict) and "option_chain" in raw else raw
    if isinstance(rows, dict):
        rows = rows.get("chain") or rows.get("data") or []
    if not isinstance(rows, list):
        rows = []
    strikes: dict[float, dict[str, Any]] = {}
    expiry = None
    spot = None

    def contract_from(node: dict[str, Any] | None, row: dict[str, Any]) -> dict[str, Any] | None:
        if not node:
            return None
        md = node.get("market_data") or node.get("marketData") or {}
        greeks = node.get("option_greeks") or node.get("optionGreeks") or {}
        return {
            "instrument_key": node.get("instrument_key") or node.get("instrumentKey"),
            "ltp": md.get("ltp") if md.get("ltp") is not None else node.get("ltp"),
            "close": md.get("close_price") if md.get("close_price") is not None else md.get("close"),
            "bid": md.get("bid_price") if md.get("bid_price") is not None else md.get("bid"),
            "ask": md.get("ask_price") if md.get("ask_price") is not None else md.get("ask"),
            "oi": md.get("oi") if md.get("oi") is not None else md.get("open_interest"),
            "change_oi": md.get("prev_oi"),
            "volume": md.get("volume"),
            "iv": greeks.get("iv"),
            "delta": greeks.get("delta"),
            "gamma": greeks.get("gamma"),
            "theta": greeks.get("theta"),
            "vega": greeks.get("vega"),
            "rho": greeks.get("rho"),
            "pop": greeks.get("pop"),
            "lot_size": row.get("lot_size") or node.get("lot_size"),
            "expiry": row.get("expiry") or row.get("expiry_date"),
            "provider": "upstox",
        }

    for row in rows:
        if not isinstance(row, dict):
            continue
        strike = row.get("strike_price") or row.get("strike")
        if strike is None:
            continue
        try:
            strike = float(strike)
        except Exception:
            continue
        expiry = expiry or row.get("expiry") or row.get("expiry_date")
        spot = spot or row.get("underlying_spot_price") or row.get("spot_price")
        entry = strikes.setdefault(strike, {"strike": strike, "call": None, "put": None})
        if row.get("call_options"):
            entry["call"] = contract_from(row.get("call_options"), row)
        if row.get("put_options"):
            entry["put"] = contract_from(row.get("put_options"), row)
        # Backward-compatible flat shape.
        opt_type = (row.get("option_type") or row.get("type") or "").upper()
        if opt_type in {"CE", "PE"}:
            entry["call" if opt_type == "CE" else "put"] = contract_from(row, row)

    strikes_list = sorted(strikes.values(), key=lambda x: x["strike"])
    if spot is None and strikes_list:
        spot = statistics.median([x["strike"] for x in strikes_list])
    atm = min((x["strike"] for x in strikes_list), key=lambda s: abs(s - float(spot))) if spot is not None and strikes_list else None
    return {"underlying": underlying, "instrument_key": key, "expiry": expiry, "spot": spot, "atm_strike": atm, "strikes": strikes_list, "provider": "upstox", "timestamp": now_iso(), "fresh": True, "metadata": meta}

# ---------------------------------------------------------------------------
# News providers / shared classifier
# ---------------------------------------------------------------------------

NEWS_SOURCES = [
    # India: 20 major news publishers (direct publisher RSS/XML feeds; no Google News aggregation)
    ("NDTV", "https://feeds.feedburner.com/ndtvnews-top-stories", "site:ndtv.com", "india"),
    ("Times of India", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms", "site:timesofindia.indiatimes.com", "india"),
    ("The Hindu", "https://www.thehindu.com/feeder/default.rss", "site:thehindu.com", "india"),
    ("India Today", "https://www.indiatoday.in/rss/home", "site:indiatoday.in", "india"),
    ("The Indian Express", "https://indianexpress.com/feed/", "site:indianexpress.com", "india"),
    ("Hindustan Times", "https://www.hindustantimes.com/feeds/rss/latest/rssfeed.xml", "site:hindustantimes.com", "india"),
    ("News18", "https://www.news18.com/rss/india.xml", "site:news18.com", "india"),
    ("Firstpost", "https://www.firstpost.com/commonfeeds/v1/firstpost-home.xml", "site:firstpost.com", "india"),
    ("Economic Times", "https://economictimes.indiatimes.com/rssfeedsdefault.cms", "site:economictimes.indiatimes.com", "india"),
    ("Business Standard", "https://www.business-standard.com/rss/home_page_top_stories.rss", "site:business-standard.com", "india"),
    ("Mint", "https://www.livemint.com/rss/markets", "site:livemint.com", "india"),
    ("Financial Express", "https://www.financialexpress.com/feed/", "site:financialexpress.com", "india"),
    ("BusinessLine", "https://www.thehindubusinessline.com/feeder/default.rss", "site:thehindubusinessline.com", "india"),
    ("CNBC-TV18", "https://www.cnbctv18.com/commonfeeds/v1/cnbctv18.xml", "site:cnbctv18.com", "india"),
    ("Zee Business", "https://www.zeebiz.com/markets/rss", "site:zeebiz.com", "india"),
    ("Moneycontrol", "https://www.moneycontrol.com/rss/latestnews.xml", "site:moneycontrol.com", "india"),
    ("Business Today", "https://www.businesstoday.in/rss/home", "site:businesstoday.in", "india"),
    ("Deccan Herald", "https://www.deccanherald.com/rss-feeds", "site:deccanherald.com", "india"),
    ("The Tribune", "https://www.tribuneindia.com/rss/feed", "site:tribuneindia.com", "india"),
    ("WION", "https://www.wionews.com/feeds/latest-news.xml", "site:wionews.com", "india"),

    # Global: 20 major international publishers (direct publisher RSS/XML feeds; no Google News aggregation)
    ("Reuters", "https://feeds.reuters.com/reuters/topNews", "site:reuters.com", "global"),
    ("Associated Press", "https://feeds.apnews.com/rss/apf-topnews", "site:apnews.com", "global"),
    ("BBC News", "https://feeds.bbci.co.uk/news/world/rss.xml", "site:bbc.com", "global"),
    ("CNN", "http://rss.cnn.com/rss/edition.rss", "site:cnn.com", "global"),
    ("The Guardian", "https://www.theguardian.com/world/rss", "site:theguardian.com", "global"),
    ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml", "site:aljazeera.com", "global"),
    ("Deutsche Welle", "https://rss.dw.com/rdf/rss-en-all", "site:dw.com", "global"),
    ("Sky News", "https://feeds.skynews.com/feeds/rss/world.xml", "site:news.sky.com", "global"),
    ("NPR", "https://feeds.npr.org/1001/rss.xml", "site:npr.org", "global"),
    ("The New York Times", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml", "site:nytimes.com", "global"),
    ("The Washington Post", "https://feeds.washingtonpost.com/rss/world", "site:washingtonpost.com", "global"),
    ("Wall Street Journal", "https://feeds.a.dj.com/rss/RSSWorldNews.xml", "site:wsj.com", "global"),
    ("CNBC", "https://www.cnbc.com/id/100003114/device/rss/rss.html", "site:cnbc.com", "global"),
    ("Bloomberg", "https://feeds.bloomberg.com/markets/news.rss", "site:bloomberg.com", "global"),
    ("Financial Times", "https://www.ft.com/rss/home", "site:ft.com", "global"),
    ("MarketWatch", "https://feeds.marketwatch.com/marketwatch/topstories/", "site:marketwatch.com", "global"),
    ("Euronews", "https://feeds.feedburner.com/euronews/en/news", "site:euronews.com", "global"),
    ("Nikkei Asia", "https://asia.nikkei.com/rss/feed/nar", "site:asia.nikkei.com", "global"),
    ("South China Morning Post", "https://www.scmp.com/rss/91/feed", "site:scmp.com", "global"),
    ("ABC News", "https://feeds.abcnews.com/abcnews/topstories", "site:abcnews.com", "global"),
]
BANKING_CONTEXT = [
    "banking sector", "banking system", "system credit", "credit growth", "deposit growth",
    "loan growth", "gold loans", "npa", "asset quality", "net interest margin", "bank capital",
    "banking regulation", "banking reform", "crr", "slr", "repo rate", "monetary policy",
    "rbi", "reserve bank of india", "liquidity",
]
EVENT_TERMS = [
    "announced", "announces", "announcement", "decision", "policy", "regulation", "regulatory",
    "reform", "meeting", "minutes", "circular", "approved", "approval", "acquisition", "acquires",
    "merger", "results", "earnings", "capital", "funding", "fund raise", "raises", "raised", "cuts",
    "cut", "changes", "changed", "penalty", "fine", "restriction", "restrictions", "order", "orders",
    "launches", "launched", "agreement", "deal", "contract", "data shows", "data show", "reports",
    "reported", "reaches", "reached", "growth", "increases", "increased", "decreases", "decreased",
    "develops", "developed", "develop", "jointly develop", "warning", "warned", "downgrade", "downgraded",
    "upgrade", "upgraded", "insider trading", "dividend", "ex-date", "order win", "order wins",
    "borrowing limit", "stake hike", "stake increase", "stake sale", "stake reduction", "stake cut",
    "raises borrowing", "borrowing raised",
]
ANALYSIS_TERMS = [
    "outlook", "technical view", "trading plan", "key levels", "support", "resistance", "stocks to buy",
    "buy today", "sell today", "strategy", "may rise", "may fall", "could rise", "could fall",
    "technical analysis", "target price", "price target", "buy call", "sell call", "forecast", "expects",
    "expect", "likely to", "downgrade", "downgraded", "upgrade", "upgraded", "top banking bets",
    "top picks", "investment bets",
]
MARKET_MOVEMENT_TERMS = [
    "shares rise", "shares fall", "shares rose", "shares fell", "shares advance", "shares declined",
    "shares trade higher", "shares trade lower", "stock rises", "stock falls", "stock rose", "stock fell",
    "shares gain", "shares gains", "shares drop", "shares drops", "shares jump", "shares jumps", "gap-up",
    "gap up", "gap-down", "gap down", "top gainers", "top losers", "gainers and losers", "market wrap",
    "market highlights", "buzzing stocks", "stocks to watch", "stocks in focus", "loses ground", "market update",
    "market updates", "session highlights", "sensex gains", "sensex falls", "nifty gains", "nifty falls",
]
MARKET_UPDATE_PATTERNS = [
    r"\b(nifty|bank nifty|sensex)\b.{0,140}\b(falls?|rises?|gains?|drops?|jumps?|slips?|surges?|flatlines?|ends?|closes?)\b",
    r"\b(nifty|bank nifty|sensex)\b.{0,140}\b\d+\s*points?\b",
    r"\b(nifty|bank nifty|sensex)\b.{0,120}\b\d+(\.\d+)?\s*%\b",
    r"\b(shares?|stock)\b.{0,80}\b(rise|rises|rose|fall|falls|fell|gain|gains|drop|drops|jump|jumps|advance|advanced)\b",
]
CONCRETE_EVENT_PHRASES = [
    "rbi approves", "rbi approved", "rbi clears", "rbi cleared", "approved by rbi", "raises borrowing limit",
    "raised borrowing limit", "raises overseas borrowing", "raised overseas borrowing", "borrowing limit",
    "stake hike", "stake increase", "stake sale", "stake reduction", "stake cut", "acquisition", "acquires",
    "merger", "fund raise", "raises capital", "raised capital", "earnings", "results", "penalty", "fine",
    "regulatory action", "regulatory approval", "regulatory restriction",
]
HIGH_MATERIALITY_TERMS = [
    "rbi", "regulatory", "regulation", "penalty", "fine", "acquisition", "merger", "earnings", "results",
    "capital", "funding", "fraud", "npa", "restriction", "restrictions", "borrowing limit", "stake hike",
    "stake increase", "stake sale", "stake reduction", "stake cut",
]
STOCKS = {
    "RELIANCE":{"name":"Reliance Industries"}, "TCS":{"name":"Tata Consultancy Services"}, "INFY":{"name":"Infosys"},
    "HDFCBANK":{"name":"HDFC Bank"}, "ICICIBANK":{"name":"ICICI Bank"}, "SBIN":{"name":"State Bank of India"},
    "AXISBANK":{"name":"Axis Bank"}, "KOTAKBANK":{"name":"Kotak Mahindra Bank"}, "ITC":{"name":"ITC"},
    "LT":{"name":"Larsen & Toubro"}, "BHARTIARTL":{"name":"Bharti Airtel"}, "HINDUNILVR":{"name":"Hindustan Unilever"},
    "BAJFINANCE":{"name":"Bajaj Finance"}, "MARUTI":{"name":"Maruti Suzuki"}, "M&M":{"name":"Mahindra & Mahindra"},
    "SUNPHARMA":{"name":"Sun Pharmaceutical Industries"}, "TITAN":{"name":"Titan Company"}, "ADANIENT":{"name":"Adani Enterprises"},
    "ADANIPORTS":{"name":"Adani Ports"}, "NTPC":{"name":"NTPC"}, "POWERGRID":{"name":"Power Grid Corporation"},
    "ONGC":{"name":"Oil & Natural Gas Corporation"}, "COALINDIA":{"name":"Coal India"}, "JSWSTEEL":{"name":"JSW Steel"},
    "TATASTEEL":{"name":"Tata Steel"}, "HCLTECH":{"name":"HCL Technologies"}, "WIPRO":{"name":"Wipro"},
}
NIFTY50_DEFAULT_SYMBOLS = [
    "HDFCBANK","ICICIBANK","RELIANCE","BHARTIARTL","LT","INFY","SBIN","AXISBANK","KOTAKBANK","M&M",
    "ITC","TCS","BAJFINANCE","HINDUNILVR","MARUTI","SUNPHARMA","NTPC","TITAN","ETERNAL","TATASTEEL",
    "BEL","SHRIRAMFIN","ULTRACEMCO","HCLTECH","POWERGRID","HINDALCO","JSWSTEEL","ADANIPORTS","ONGC","COALINDIA",
    "BAJAJ-AUTO","GRASIM","ADANIENT","TRENT","CIPLA","DRREDDY","EICHERMOT","TECHM","APOLLOHOSP","DIVISLAB",
    "TATACONSUM","HEROMOTOCO","NESTLEIND","BRITANNIA","INDUSINDBK","HDFCLIFE","SBILIFE","TATAMOTORS","UPL","SHREECEM"
]
try:
    _nifty_env = [x.strip().upper() for x in os.getenv("NIFTY50_SYMBOLS", "").split(",") if x.strip()]
except Exception:
    _nifty_env = []
NIFTY50_SYMBOLS = list(dict.fromkeys(_nifty_env or NIFTY50_DEFAULT_SYMBOLS))
NIFTY50_NEWS_ALIASES = {
    "RELIANCE": ["reliance industries", "ril", "reliance jio", "jio platforms", "reliance retail"],
    "HDFCBANK": ["hdfc bank", "hdfcbank"], "ICICIBANK": ["icici bank", "icicibank"],
    "SBIN": ["state bank of india", "sbi"], "AXISBANK": ["axis bank", "axisbank"],
    "KOTAKBANK": ["kotak mahindra bank", "kotak bank"], "BHARTIARTL": ["bharti airtel", "airtel"],
    "LT": ["larsen & toubro", "larsen and toubro", "l&t"], "INFY": ["infosys", "infy"],
    "TCS": ["tata consultancy services", "tcs"], "M&M": ["mahindra & mahindra", "mahindra and mahindra", "m&m"],
    "TATAMOTORS": ["tata motors", "tata motor"], "BAJFINANCE": ["bajaj finance"],
    "HINDUNILVR": ["hindustan unilever", "hul"], "SUNPHARMA": ["sun pharma", "sun pharmaceutical"],
    "TATASTEEL": ["tata steel"], "JSWSTEEL": ["jsw steel"], "HCLTECH": ["hcl technologies", "hcl tech"],
    "POWERGRID": ["power grid", "powergrid"], "ADANIENT": ["adani enterprises"], "ADANIPORTS": ["adani ports"],
    "ONGC": ["ongc", "oil and natural gas corporation"], "COALINDIA": ["coal india"],
    "MARUTI": ["maruti suzuki", "maruti"], "TITAN": ["titan company", "titan"],
    "ITC": ["itc limited", "itc"], "NTPC": ["ntpc"], "BEL": ["bharat electronics", "bel"],
    "SHRIRAMFIN": ["shriram finance"], "ULTRACEMCO": ["ultratech cement", "ultratech"],
    "HINDALCO": ["hindalco"], "CIPLA": ["cipla"], "DRREDDY": ["dr reddy", "dr. reddy"],
    "EICHERMOT": ["eicher motors", "royal enfield"], "TECHM": ["tech mahindra"], "APOLLOHOSP": ["apollo hospitals"],
    "DIVISLAB": ["divi's laboratories", "divis laboratories", "divi's lab"], "TATACONSUM": ["tata consumer"],
    "HEROMOTOCO": ["hero motocorp", "hero moto"], "NESTLEIND": ["nestle india"], "BRITANNIA": ["britannia industries", "britannia"],
    "INDUSINDBK": ["indusind bank"], "HDFCLIFE": ["hdfc life"], "SBILIFE": ["sbi life"],
    "SHREECEM": ["shree cement"], "GRASIM": ["grasim industries", "grasim"], "TRENT": ["trent limited", "trent"],
    "ETERNAL": ["eternal ltd", "zomato", "eternal"], "UPL": ["upl limited", "upl"], "BAJAJ-AUTO": ["bajaj auto"],
}

CONSTITUENT_ALIASES = {
    "hdfc bank": "HDFCBANK", "hdfcbank": "HDFCBANK", "icici bank": "ICICIBANK", "icicibank": "ICICIBANK",
    "state bank of india": "SBIN", "sbi": "SBIN", "axis bank": "AXISBANK", "axisbank": "AXISBANK",
    "kotak mahindra bank": "KOTAKBANK", "kotak bank": "KOTAKBANK",
}
# Numeric scores keep recommendation/risk calculations type-safe while labels remain explicit in the UI.
NEWS_MATERIALITY_HIGH = 90.0
NEWS_MATERIALITY_MEDIUM = 60.0
NEWS_MATERIALITY_NONE = 0.0
BUILD_ID = "V5-FINAL-NEWS-CLASSIFIER"


NEWS_USAGE = {"gnews": deque(), "newsapi": deque()}
NEWS_USAGE_LOCK = threading.RLock()


def _news_key_pool(prefix: str) -> list[str]:
    values=[]
    base=os.getenv(prefix)
    if base: values.append(base)
    for i in range(2,11):
        v=os.getenv(f"{prefix}_{i}")
        if v: values.append(v)
    return values


def _news_budget_ok(provider: str, limit: int) -> bool:
    now=time.time(); day=datetime.now(timezone.utc).date()
    with NEWS_USAGE_LOCK:
        q=NEWS_USAGE[provider]
        while q and datetime.fromtimestamp(q[0], timezone.utc).date()!=day: q.popleft()
        return len(q)<limit


def _news_record_call(provider: str) -> None:
    with NEWS_USAGE_LOCK: NEWS_USAGE[provider].append(time.time())


def _norm_news(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "").strip()).lower()


def _clean_news_summary(v: Any) -> str:
    raw = str(v or "")
    if not raw:
        return ""
    raw = html.unescape(raw)
    raw = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return raw[:1200]


def _news_text(title: str, summary: str = "") -> str:
    return _norm_news(f"{title} {summary}")


def _news_contains(text: str, terms: list[str]) -> bool:
    return any(t in text for t in terms)


def _news_event_hits(text: str) -> list[str]:
    return [t for t in EVENT_TERMS if t in text]


def _news_constituents(text: str) -> list[str]:
    out=[]
    for alias,symbol in CONSTITUENT_ALIASES.items():
        if re.search(r"\b"+re.escape(alias)+r"\b", text) and symbol not in out: out.append(symbol)
    return out


def _news_market_update(text: str) -> bool:
    if _news_contains(text, MARKET_MOVEMENT_TERMS): return True
    pats=[r"\b(nifty|bank nifty|sensex)\b.{0,140}\b(falls?|rises?|gains?|drops?|jumps?|slips?|surges?|flatlines?|ends?|closes?)\b", r"\b(nifty|bank nifty|sensex)\b.{0,140}\b\d+\s*points?\b", r"\b(shares?|stock)\b.{0,80}\b(rise|rises|rose|fall|falls|fell|gain|gains|drop|drops|jump|jumps|advance|advanced)\b"]
    return any(re.search(p,text) for p in pats)


def _news_title_roundup(title_text: str) -> bool:
    return _news_contains(title_text, [
        "stocks to watch", "buzzing stocks", "top gainers", "top losers", "gainers and losers",
        "market wrap", "market highlights", "stocks in focus", "market update", "market updates",
        "session highlights",
    ])


ANALYSIS_TERMS = [
    "outlook", "technical view", "trading plan", "key levels", "support", "resistance", "stocks to buy", "buy today", "sell today",
    "strategy", "may rise", "may fall", "could rise", "could fall", "technical analysis", "target price", "price target",
    "buy call", "sell call", "forecast", "expects", "expect", "likely to", "upgrade", "upgraded", "downgrade", "downgraded",
    "top banking bets", "top picks", "investment bets", "bullish on", "bearish on", "price objective", "upside potential",
    "analysts see", "analysts say", "wall street picks", "best stocks", "stocks to watch", "momentum", "bet or book profit", "buying opportunity", "what should investors do", "what should investors",
]

BROKER_RESEARCH_TERMS = [
    "goldman sachs picks", "goldman picks", "brokerage picks", "top banking bet", "top banking bets", "top 10@10", "top 10", "make news", "stocks in focus",
    "top pick", "top picks", "initiates coverage", "starts coverage", "coverage on",
    "downgrades", "downgrade", "upgrades", "upgrade", "maintains buy", "maintains add",
    "price target", "target price", "target of", "buy rating", "sell rating", "add rating",
    "overweight", "underweight", "equal weight", "analyst call", "broker call"
]

CONCRETE_EVENT_PHRASES = [
    "rbi approves", "rbi approved", "rbi clears", "rbi cleared", "approved by rbi", "green light from rbi", "rbi gives green light",
    "raises borrowing limit", "raised borrowing limit", "raises overseas borrowing", "raised overseas borrowing", "borrowing limit",
    "stake hike", "stake increase", "stake sale", "stake reduction", "stake cut", "acquisition", "acquires", "merger", "fund raise",
    "raises capital", "raised capital", "earnings", "results", "penalty", "fine", "regulatory action", "regulatory approval",
    "regulatory restriction", "bond issue", "bond sale", "dollar bond", "dollar bonds", "overseas debt", "overseas borrowing",
    "raises debt", "raised debt", "debt issue", "loan agreement", "loan approval", "loan sanction", "capital raise", "fundraising",
    "fund-raising", "record bond sale", "record dollar bond sale",
]

HIGH_MATERIALITY_TERMS = [
    "rbi approves", "rbi approved", "regulatory action", "regulatory approval", "regulatory restriction", "penalty", "fine", "acquisition", "merger",
    "fraud", "npa", "default", "bankruptcy", "capital raise", "record dollar bond sale", "record bond sale", "stake hike", "stake increase",
    "stake sale", "stake reduction",
]

NEWS_MATERIALITY_LOW = 30.0

GENERIC_REACTION_TERMS = [
    "shares jump after", "shares rise after", "stock jumps after", "stock rises after", "stock falls after", "markets react", "investors react",
    "stocks rally after", "shares rally after", "shares slump after",
]

PROMOTIONAL_ALERT_TERMS = [
    "investor alert", "shareholder alert", "encourages investors", "encourages shareholders", "secure counsel", "lead plaintiff",
    "class action deadline", "opportunity to lead", "claims filer", "rosen skilled investor counsel", "securities class action",
    "securities fraud lawsuit", "lost money have opportunity",
]

def _target_direct_match(text: str, target: str) -> bool:
    target = str(target or "").upper()
    aliases = {
        "HDFCBANK": [r"\bhdfc\s+bank(?:\s+limited|\s+ltd)?\b", r"\bhdfcbank\b"],
        "ICICIBANK": [r"\bicici\s+bank(?:\s+limited|\s+ltd)?\b", r"\bicicibank\b"],
        "SBIN": [r"\bstate\s+bank\s+of\s+india\b", r"\bsbi\b"],
        "AXISBANK": [r"\baxis\s+bank(?:\s+limited|\s+ltd)?\b", r"\baxisbank\b"],
        "RELIANCE": [r"\breliance\s+industries(?:\s+limited|\s+ltd)?\b", r"\breliance\s+industries\b", r"\breliance\s+jio\b", r"\breliance\s+retail\b", r"\bril\b", r"\bjio\s+platforms\b"],
        "TCS": [r"\btata\s+consultancy\s+services\b", r"\btcs\b"],
        "INFY": [r"\binfosys(?:\s+limited|\s+ltd)?\b", r"\binfy\b"],
    }
    if target in aliases:
        # Do not treat a bare HDFC/Axis/etc. mention as the listed company.
        return any(re.search(pat, text, re.I) for pat in aliases[target])
    if target in STOCKS:
        company = _norm_news(STOCKS[target]["name"])
        return bool(re.search(r"\b" + re.escape(target.lower()) + r"\b", text) or company in text)
    return bool(re.search(r"\b" + re.escape(target.lower()) + r"\b", text))



def _news_classify(title: str, summary: str, target: str) -> dict[str, Any]:
    """V4 semantic target-news classifier: target relevance first, then event-vs-reaction-vs-analysis."""
    title_text = _norm_news(title)
    text = _news_text(title, summary)
    target = str(target or "").upper()
    direct_target = _target_direct_match(text, target)
    events = _news_event_hits(text)
    concrete_event = _news_contains(text, CONCRETE_EVENT_PHRASES)
    analysis = _news_contains(text, ANALYSIS_TERMS)
    promotional = _news_contains(text, PROMOTIONAL_ALERT_TERMS)

    if direct_target and promotional:
        return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.99,"reason":"Investor-solicitation/legal-alert content without a verified underlying company event."}

    if direct_target and _news_contains(text, BROKER_RESEARCH_TERMS) and not concrete_event:
        return {"classification":"ANALYSIS","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.99,"reason":"Brokerage/analyst research, recommendation or target-price commentary rather than a new company event."}

    if direct_target and _news_contains(text, ["admit card", "answer key", "exam date", "exam", "recruitment", "po result", "career opportunity", "bank holidays", "bank holiday", "fd rates vs", "which bank offers"]):
        return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.98,"reason":"Routine education, recruitment, holiday or consumer-comparison content rather than investable company news."}

    if direct_target and _news_market_update(text) and not concrete_event:
        return {"classification":"MARKET_UPDATE","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.98,"reason":"Price/index movement without a concrete underlying event."}

    if direct_target and analysis and (not concrete_event or _news_contains(text, ["what should investors do", "what should investors", "top picks", "buy today", "sell today", "bullish on", "bearish on", "upside potential"])):
        return {"classification":"ANALYSIS","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.98,"reason":"Analyst/research/forecast commentary rather than a new company event."}

    if target in {"GLOBAL", "MARKET"}:
        if concrete_event or (_news_contains(text, BANKING_CONTEXT) and events):
            high = _news_contains(text, HIGH_MATERIALITY_TERMS)
            return {"classification":"NEWS","relevance":0.75,"materiality":NEWS_MATERIALITY_HIGH if high else NEWS_MATERIALITY_MEDIUM,"materiality_label":"HIGH" if high else "MEDIUM","confidence":0.90,"reason":"Concrete macro/business event relevant to the selected market."}
        if _news_market_update(text):
            return {"classification":"MARKET_UPDATE","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.97,"reason":"Price/index movement or market roundup without a verified underlying event."}
        if analysis:
            return {"classification":"ANALYSIS","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.96,"reason":"Trading/technical/forecast commentary."}
        return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.88,"reason":"No verified investment-relevant event."}

    if not direct_target:
        # Material external policy/sector events can be relevant to a stock even when the
        # company name is not in the headline, but only for tightly defined read-throughs.
        if target in {"TCS", "INFY"} and _news_contains(text, [
            "h-1b", "h1b", "h-1b visa", "visa fee", "immigration fee", "work visa",
            "skilled worker visa", "us immigration", "us visa fee"
        ]):
            return {"classification":"SECTOR_DEVELOPMENT","relevance":0.82,"materiality":NEWS_MATERIALITY_HIGH,"materiality_label":"HIGH","confidence":0.93,"reason":"Material U.S. immigration/work-visa policy event with direct read-through to Indian IT-services staffing and cost structure."}
        if target == "RELIANCE" and _news_contains(text, ["oil", "crude", "brent", "wti", "natural gas"]) and _news_contains(text, [
            "supply", "sanctions", "iran", "middle east", "strait of hormuz", "production", "inventory", "disruption", "embargo"
        ]):
            return {"classification":"SECTOR_DEVELOPMENT","relevance":0.78,"materiality":NEWS_MATERIALITY_HIGH if _news_contains(text, ["sanctions", "iran", "supply disruption", "embargo", "strait of hormuz"]) else NEWS_MATERIALITY_MEDIUM,"materiality_label":"HIGH" if _news_contains(text, ["sanctions", "iran", "supply disruption", "embargo", "strait of hormuz"]) else "MEDIUM","confidence":0.90,"reason":"Material oil/geopolitical supply event with a direct read-through to Reliance's energy/refining economics."}
        if target in {"BANKNIFTY", "NIFTYBANK"} and _news_contains(text, BANKING_CONTEXT) and events:
            high = _news_contains(text, HIGH_MATERIALITY_TERMS)
            return {"classification":"SECTOR_DEVELOPMENT","relevance":0.85,"materiality":NEWS_MATERIALITY_HIGH if high else NEWS_MATERIALITY_MEDIUM,"materiality_label":"HIGH" if high else "MEDIUM","confidence":0.90,"reason":"Banking-sector development relevant to the selected banking index."}
        return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.92,"reason":"Article does not identify the selected company sufficiently."}

    if re.search(r"\b(?:may|might|could|likely|expects?|forecast|outlook|target|upside)\b", title_text) and not concrete_event:
        return {"classification":"ANALYSIS","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.98,"reason":"Forecast, outlook, target or investor-expectation commentary rather than a new company event."}

    company_event_context = concrete_event or _news_contains(text, [
        "raises $", "raised $", "raises ₹", "raised ₹", "issues $", "issued $", "issues ₹", "issued ₹",
        "bond sale", "bond issue", "dollar bond", "record dollar bond sale", "record bond sale",
        "overseas debt", "overseas borrowing", "borrowing limit", "senior notes", "list $", "list ₹",
        "loan", "lending", "stake", "stake increase", "stake hike", "stake sale", "stake reduction",
        "licence", "license", "approval", "approved", "final nod", "green light", "acquisition", "acquires",
        "merger", "earnings", "results", "profit", "revenue", "profit warning", "guidance",
        "fraud", "investigation", "penalty", "fine", "regulatory", "rbi", "capital", "funding",
        "fundraise", "fund-raise", "business expansion", "expansion plan", "new branch", "branches",
        "deposit", "npa", "asset quality", "dividend", "buyback", "capacity", "partnership", "collaboration",
        "agreement", "contract", "order win", "orders", "denies", "monitoring software", "surveillance",
        "employee monitoring", "cybersecurity incident", "data breach", "customer charges", "charges",
        "changes rules", "rule changes", "credit card rules", "lounge access",
    ])

    # Routine investor-meeting, minor promotional, and generic sponsorship pieces are not useful stock news.
    if _news_contains(text, ["investor meet", "investor meeting", "analyst meet", "roadshow", "sports partnership", "cricket partnership", "t20 premier league", "football partnership", "sports sponsorship", "helps deliver", "customer experience", "data-driven excellence"]) and not _news_contains(text, ["acquisition", "fundraise", "bond", "capital", "major contract", "strategic acquisition"]):
        return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.94,"reason":"Routine investor-relations or promotional item without a material underlying company event."}

    if _news_contains(text, ["cricket", "t20", "football", "league", "sports sponsorship", "sports partnership"]) and _news_contains(text, ["partner", "partnership", "sponsor", "sponsorship"]) and not _news_contains(text, ["major contract", "billion", "acquisition", "strategic deal"]):
        return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.96,"reason":"Sports/promotional partnership is not sufficiently material for stock-news relevance."}

    if re.search(r"\bagm\b", title_text) and _news_contains(text, ["approved all", "approve all", "all resolutions", "resolutions"]):
        return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.93,"reason":"Routine AGM resolution coverage without a specifically material new decision."}

    if company_event_context:
        high = _news_contains(text, HIGH_MATERIALITY_TERMS) or _news_contains(text, ["record", "billion", "major", "largest", "first time", "unexpected", "surprise", "fraud", "regulatory", "final nod"])
        low_only = _news_contains(text, ["customer charges", "credit card rules", "lounge access", "partnership", "collaboration", "changes rules"]) and not high and not _news_contains(text, ["bond", "capital", "acquisition", "earnings", "regulatory", "penalty", "fine", "fraud", "stake", "loan", "borrowing", "revenue", "profit"])
        mat = NEWS_MATERIALITY_LOW if low_only else (NEWS_MATERIALITY_HIGH if high else NEWS_MATERIALITY_MEDIUM)
        label = "LOW" if low_only else ("HIGH" if high else "MEDIUM")
        return {"classification":"NEWS","relevance":0.98 if not low_only else 0.80,"materiality":mat,"materiality_label":label,"confidence":0.95,"reason":"Concrete event directly affecting the selected company under V5 semantic criteria."}

    if direct_target and not analysis and not _news_market_update(text):
        return {"classification":"NEWS","relevance":0.90,"materiality":NEWS_MATERIALITY_MEDIUM,"materiality_label":"MEDIUM","confidence":0.86,"reason":"Factual company-specific development; no market-reaction or research-only language."}

    return {"classification":"IRRELEVANT","relevance":0.0,"materiality":0.0,"materiality_label":"N/A","confidence":0.88,"reason":"No sufficiently concrete company event."}

def _news_regression_selfcheck() -> list[tuple[str,str,str]]:
    cases = [
        ("HDFCBANK", "LIC gets green light from RBI to raise HDFC Bank stake to nearly 10%", "NEWS"),
        ("HDFCBANK", "HDFC Bank's record dollar bond sale makes it top issuer under RBI window", "NEWS"),
        ("HDFCBANK", "HDFC, PNB lead banks lining up for the next wave of dollar bonds", "IRRELEVANT"),
        ("HDFCBANK", "HDFC Bank Shareholder Alert: ClaimsFiler Reminds Investors With Losses In Excess Of $100,000 Of Lead Plaintiff Deadline in Class Action Lawsuit Against HDFC Bank", "IRRELEVANT"),
        ("ICICIBANK", "ICICI Bank doubles borrowing from overseas markets to $5 billion", "NEWS"),
        ("ICICIBANK", "ICICI Bank Gets Board Approval To Raise Up To $5 Billion Through Overseas Bonds", "NEWS"),
        ("SBIN", "₹15 charge after 4 withdrawals: SBI changes rules for basic savings accounts", "NEWS"),
        ("SBIN", "What should investors do about SBI after Q1 FY27 results?", "ANALYSIS"),
        ("AXISBANK", "Private banking stocks witnessing fresh momentum; should you bet or book profit?", "IRRELEVANT"),
        ("AXISBANK", "Axis Bank gets final nod to list $300 million senior notes on India INX, NSE IX", "NEWS"),
        ("AXISBANK", "Axis Bank schedules select investor meet on August 26", "IRRELEVANT"),
        ("TCS", "TCS denies employee surveillance: What is the laptop monitoring row about?", "NEWS"),
        ("TCS", "TCS Comes on Board as European T20 Premier League's Digital Transformation Partner", "IRRELEVANT"),
        ("INFY", "Infosys Collaborates with Knorr-Bremse to Accelerate AI-Enabled Enterprise Transformation", "NEWS"),
        ("INFY", "Infosys fined €175,000 by French regulator for labor compliance gaps", "NEWS"),
    ]
    failures=[]
    for target,title,expected in cases:
        got=_news_classify(title,"",target).get("classification")
        if got != expected:
            failures.append((target,title,got,expected))
    return failures


def _news_identity(article: dict[str,Any]) -> str:
    url=str(article.get("url") or "").strip().lower().split("?")[0].rstrip("/")
    if url: return "url:"+url
    base=_news_text(article.get("title"),article.get("summary"))[:400]
    return "text:"+hashlib.sha256(base.encode()).hexdigest()


def _news_dedupe(articles: list[dict[str,Any]]) -> list[dict[str,Any]]:
    seen=set(); out=[]
    for a in articles:
        ident=_news_identity(a)
        if ident in seen: continue
        seen.add(ident); out.append(a)
    return out

def _last_market_close_ist(now: datetime | None = None) -> datetime:
    ist=timezone(timedelta(hours=5, minutes=30))
    cur=(now or datetime.now(timezone.utc)).astimezone(ist)
    day=cur.date()
    # Last completed weekday session close at 15:30 IST.
    if cur.weekday() >= 5 or (cur.weekday() < 5 and cur.time() < datetime.strptime("15:30","%H:%M").time()):
        day -= timedelta(days=1)
        while day.weekday() >= 5:
            day -= timedelta(days=1)
    return datetime.combine(day, datetime.strptime("15:30","%H:%M").time(), tzinfo=ist)


def _news_before_last_close(published_at: Any) -> bool:
    if not published_at:
        return False
    try:
        raw=str(published_at).strip().replace("Z","+00:00")
        dt=datetime.fromisoformat(raw)
        if dt.tzinfo is None: dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone(timedelta(hours=5, minutes=30))) <= _last_market_close_ist()
    except Exception:
        return False


def _news_key_request(provider: str, url: str, params_builder, keys: list[str], key_name: str) -> dict[str,Any]:
    if not keys: return {"_error": f"{provider} key is not configured"}
    limit=GNEWS_DAILY_LIMIT if provider=="gnews" else NEWSAPI_DAILY_LIMIT
    if not _news_budget_ok(provider,limit): return {"_error": f"{provider} daily budget exhausted"}
    last={}
    for key in keys[:max(1,NEWS_KEY_MAX_ATTEMPTS)]:
        params=params_builder(key)
        try:
            r=requests.get(url,params=params,timeout=4)
            try: data=r.json()
            except Exception: data={"message":r.text[:500]}
        except Exception as exc:
            return {"_error": safe_text(exc)}
        if r.status_code<400:
            _news_record_call(provider); return data
        last={"_status_code":r.status_code,"_error":data}
        if r.status_code not in (401,403,429) and not _news_contains(_norm_news(data),["quota","rate limit","too many requests","invalid api key","invalid token"]): break
    return last or {"_error":f"{provider} request failed"}


def _newsapi_articles(query: str, limit: int) -> list[dict[str,Any]]:
    data=_news_key_request("newsapi","https://newsapi.org/v2/everything",lambda k:{"q":query,"language":"en","sortBy":"publishedAt","pageSize":min(limit,20),"apiKey":k},_news_key_pool("NEWSAPI_API_KEY"),"apiKey")
    return [{"provider":"NewsAPI","source":(a.get("source") or {}).get("name"),"title":a.get("title"),"summary":a.get("description") or a.get("content"),"published_at":a.get("publishedAt"),"url":a.get("url")} for a in (data.get("articles") or [])] if "_error" not in data else []


def _gnews_articles(query: str, limit: int) -> list[dict[str,Any]]:
    data=_news_key_request("gnews","https://gnews.io/api/v4/search",lambda k:{"q":query[:200],"lang":"en","country":("in" if any(x in query.lower() for x in ("india","nifty","bank nifty","rbi")) else None),"max":min(limit,10),"sortby":"publishedAt","apikey":k},_news_key_pool("GNEWS_API_KEY"),"apikey")
    return [{"provider":"GNews","source":(a.get("publisher") or {}).get("name"),"title":a.get("title"),"summary":a.get("description") or a.get("content"),"published_at":a.get("publishedAt"),"url":a.get("url")} for a in (data.get("articles") or [])] if "_error" not in data else []


def _rss_articles(source_name: str, rss_url: str, target: str, limit: int=20, timeout: float | None = None) -> list[dict[str,Any]]:
    try:
        r=requests.get(rss_url,headers={"User-Agent":"CA-Trader/1.0 RSS reader"},timeout=(NEWS_RSS_TIMEOUT if timeout is None else timeout)); r.raise_for_status()
        root=ET.fromstring(r.text); out=[]; target_u=str(target or "GLOBAL").upper()
        for item in root.iter():
            tag=item.tag.lower().split("}")[-1]
            if tag not in {"item","entry"}: continue
            vals={}
            for c in list(item):
                ct=c.tag.lower().split("}")[-1]; txt="".join(c.itertext()).strip()
                if ct=="link": vals["url"]=c.attrib.get("href") or txt
                elif ct in {"title","description","summary","content","pubdate","published","updated"}: vals[ct]=txt
            title=vals.get("title",""); summary=vals.get("description") or vals.get("summary") or vals.get("content",""); text=_news_text(title,summary)
            if target_u in {"GLOBAL","MARKET"}:
                match=True
            elif target_u in {"BANKNIFTY","NIFTYBANK"}:
                match=("bank nifty" in text or "nifty bank" in text or _news_contains(text,BANKING_CONTEXT) or bool(_news_constituents(text)))
            elif target_u in {"NIFTY50","NIFTY"}:
                match=("nifty 50" in text or "nifty50" in text or "nifty" in text or "sensex" in text or _nifty50_news_match(text))
            else:
                if "CRUDEOIL" in target_u or "CRUDE" in target_u:
                    match=_news_contains(text,["crude oil","crudeoil","wti","brent","oil price","oil prices"])
                else:
                    match=_target_direct_match(text,target_u)
            if match:
                out.append({"provider":"Website","source":source_name,"title":title,"summary":summary,"published_at":vals.get("pubdate") or vals.get("published") or vals.get("updated") or now_iso(),"url":vals.get("url")})
            if len(out)>=limit: break
        return out
    except Exception as exc:
        log.debug("News RSS %s unavailable: %s",source_name,safe_text(exc)); return []



# --- CA AI v6 news classifier: headline-first, event-aware, boilerplate-resistant ---
NEWS_BOILERPLATE_PHRASES = [
    "brings you everything you need to know", "bloomberg tv is live", "watch the latest episode",
    "subscribe to", "follow us on", "presented by", "anchors ", "hosts ", "live from",
    "this is a promotional", "copyright", "all rights reserved"
]
MACRO_HIGH_MATERIALITY_TERMS = [
    "war", "strike", "airstrike", "missile", "military", "ceasefire", "sanctions", "tariff", "trade war",
    "rate hike", "rate cut", "interest rates", "central bank", "federal reserve", "fed", "rbi", "ecb",
    "inflation", "cpi", "pce", "payrolls", "jobs report", "oil prices", "crude oil", "brent", "wti",
    "opec", "supply disruption", "default", "bank failure", "banking crisis", "recession", "gdp", "election",
    "capital controls", "currency intervention", "devaluation", "emergency meeting", "emergency policy"
]
MACRO_NEGATIVE_TERMS = [
    "war", "strike", "airstrike", "missile", "sanctions", "tariff", "trade war", "rate hike", "inflation",
    "oil prices rise", "crude jumps", "recession", "default", "bank failure", "banking crisis", "escalation", "attack"
]
MACRO_POSITIVE_TERMS = ["ceasefire", "peace deal", "rate cut", "inflation cools", "disinflation", "stimulus", "production rises", "supply restored"]

def _strip_news_boilerplate(summary: str) -> str:
    t=_clean_news_summary(summary)
    for phrase in NEWS_BOILERPLATE_PHRASES:
        t=re.sub(re.escape(phrase), " ", t, flags=re.I)
    t=re.sub(r"\b(?:with|from)\s+[A-Z][A-Za-z .-]{2,60}\b", " ", t)
    return re.sub(r"\s+", " ", t).strip()[:900]

def _nifty50_news_match(text: str) -> bool:
    t=_norm_news(text)
    for sym in NIFTY50_SYMBOLS:
        aliases=NIFTY50_NEWS_ALIASES.get(sym, [sym.lower()])
        if any(re.search(r"\b"+re.escape(a.lower())+r"\b", t) for a in aliases):
            return True
    return False

def _news_classify_v6(title: str, summary: str, target: str) -> dict[str, Any]:
    raw_title=_clean_news_summary(title)
    body=_strip_news_boilerplate(summary)
    title_text=_norm_news(raw_title)
    text=_news_text(raw_title, body)
    target=str(target or "GLOBAL").upper()
    direct_target=_target_direct_match(text,target) or (target in {"NIFTY","NIFTY50"} and _nifty50_news_match(text))
    event_hits=_news_event_hits(text)
    concrete=_news_contains(text,CONCRETE_EVENT_PHRASES)
    macro_high=_news_contains(text,MACRO_HIGH_MATERIALITY_TERMS)
    promotional=_news_contains(text,PROMOTIONAL_ALERT_TERMS)
    analysis_only=_news_contains(text,ANALYSIS_TERMS) and not concrete
    title_macro=any(x in title_text for x in MACRO_HIGH_MATERIALITY_TERMS)
    title_neg=sum(1 for x in MACRO_NEGATIVE_TERMS if x in title_text)
    title_pos=sum(1 for x in MACRO_POSITIVE_TERMS if x in title_text)
    # Legal/investor solicitation remains removable when there is no actual event in the title.
    if promotional and not concrete and title_neg==0 and title_pos==0:
        return {"classification":"IRRELEVANT","relevance":0.05,"materiality":5.0,"materiality_label":"LOW","confidence":0.98,"reason":"Promotional/legal solicitation content without a material underlying event."}
    # Headline dominates. A clear macro event is material even if the feed body is promotional boilerplate.
    if title_macro or (macro_high and (concrete or event_hits or target in {"GLOBAL","MARKET","NIFTY","NIFTY50","BANKNIFTY","NIFTYBANK"})):
        mat=95.0 if title_macro else 85.0
        sent="Negative" if title_neg>title_pos else "Positive" if title_pos>title_neg else "Neutral"
        return {"classification":"NEWS","relevance":0.95,"materiality":mat,"materiality_label":"HIGH","confidence":0.93,"sentiment":sent,"reason":"Headline contains a market-moving macro/geopolitical/rates event; publisher boilerplate was discounted."}
    if direct_target and analysis_only:
        return {"classification":"ANALYSIS","relevance":0.55,"materiality":35.0,"materiality_label":"LOW","confidence":0.90,"reason":"Targeted research/forecast commentary rather than a newly reported event."}
    if direct_target and concrete:
        high=_news_contains(text,HIGH_MATERIALITY_TERMS)
        return {"classification":"NEWS","relevance":0.90,"materiality":90.0 if high else 70.0,"materiality_label":"HIGH" if high else "MEDIUM","confidence":0.92,"sentiment":"Negative" if title_neg>title_pos else "Positive" if title_pos>title_neg else "Neutral","reason":"Direct company event reported for the selected instrument."}
    if direct_target:
        return {"classification":"NEWS","relevance":0.78,"materiality":60.0,"materiality_label":"MEDIUM","confidence":0.82,"sentiment":"Negative" if title_neg>title_pos else "Positive" if title_pos>title_neg else "Neutral","reason":"The selected instrument is directly named in a substantive report."}
    if target in {"GLOBAL","MARKET"} and (concrete or macro_high or event_hits):
        sent="Negative" if title_neg>title_pos else "Positive" if title_pos>title_neg else "Neutral"
        return {"classification":"NEWS","relevance":0.80,"materiality":80.0 if macro_high else 65.0,"materiality_label":"HIGH" if macro_high else "MEDIUM","confidence":0.88,"sentiment":sent,"reason":"Substantive global/market event; headline and event terms indicate investment relevance."}
    if target in {"NIFTY","NIFTY50"} and _nifty50_news_match(text):
        return {"classification":"NEWS","relevance":0.82,"materiality":65.0,"materiality_label":"MEDIUM","confidence":0.87,"sentiment":"Negative" if title_neg>title_pos else "Positive" if title_pos>title_neg else "Neutral","reason":"News names a NIFTY 50 constituent and can affect the selected index."}
    if _news_market_update(text) and not (title_macro or concrete):
        return {"classification":"MARKET_UPDATE","relevance":0.30,"materiality":30.0,"materiality_label":"LOW","confidence":0.90,"reason":"Market movement commentary without a new underlying event."}
    return {"classification":"IRRELEVANT","relevance":0.05,"materiality":5.0,"materiality_label":"LOW","confidence":0.75,"reason":"No clear investable event or target exposure after removing feed boilerplate."}

# Override the earlier classifier so all downstream news/recommendation paths use v6.
_news_classify = _news_classify_v6

def _target_news_query(target: str) -> str:
    target=target.upper()
    if target in {"BANKNIFTY","NIFTYBANK"}:
        return '"Bank Nifty" OR "Nifty Bank" OR RBI banking OR bank lending OR bank earnings OR banks India'
    if target in {"NIFTY50","NIFTY"}:
        return '"Nifty 50" OR NIFTY India OR RBI OR India markets OR Sensex'
    # MCX crude contracts contain dates/expiry text, so the literal contract
    # symbol is a poor news query. Search the underlying aliases instead.
    if "CRUDEOIL" in target or "CRUDE OIL" in target or "CRUDE" in target:
        return '"crude oil" OR crudeoil OR WTI OR Brent OR oil prices OR crude prices OR petroleum'
    try:
        meta=UPSTOX.resolve_instrument(target)[1]
        name=meta.get("name") or meta.get("trading_symbol") or target
    except Exception:
        name=target
    return f'"{name}" OR {target}'


def _parse_news_datetime(value: str | None) -> datetime | None:
    """Parse news timestamps from ISO-8601 and common RSS/HTTP date formats into IST."""
    if value is None:
        return None
    raw=str(value).strip()
    if not raw:
        return None
    candidates=[raw, raw.replace("Z","+00:00")]
    for candidate in candidates:
        try:
            dt=datetime.fromisoformat(candidate)
            if dt.tzinfo is None:
                dt=dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(IST)
        except Exception:
            pass
    try:
        from email.utils import parsedate_to_datetime
        dt=parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(IST)
    except Exception:
        return None


def _news_allowed_session(published_at: str | None, now: datetime | None = None) -> bool:
    """Allow current-day news and a short carryover window from the previous market day, using IST."""
    now = now or datetime.now(IST)
    dt=_parse_news_datetime(published_at)
    if not dt:
        return False
    if dt.date()==now.date():
        return True
    prev=_previous_market_day(now.date())
    return dt.date()==prev and dt.time() >= datetime.strptime('14:00','%H:%M').time()


def _external_news_row(row: dict[str,Any]) -> dict[str,Any]:
    return {
        "provider":"User added", "source":row.get("source") or "External source", "title":row.get("headline") or row.get("title"),
        "summary":row.get("summary") or "", "published_at":row.get("published_at") or row.get("published") or now_iso(),
        "url":row.get("url") or "", "target":row.get("target") or "", "is_global":bool(row.get("is_global"))
    }


def _external_news_for_user(user_id: int | None, target: str | None) -> list[dict[str,Any]]:
    if not user_id: return []
    target=(target or "").upper()
    if target in {"GLOBAL","MARKET","NIFTY","NIFTY50","BANKNIFTY","NIFTYBANK"}:
        rows=db_exec("SELECT * FROM external_news WHERE user_id=? AND (is_global=1 OR COALESCE(target,'') IN (?,?)) ORDER BY created_at DESC LIMIT 60",[user_id,target,target],"all")
    else:
        rows=db_exec("SELECT * FROM external_news WHERE user_id=? AND (is_global=1 OR upper(COALESCE(target,''))=?) ORDER BY created_at DESC LIMIT 60",[user_id,target],"all")
    out=[]
    for r in rows:
        x=_external_news_row(r)
        x.update({"materiality":float(r.get("materiality") or 0),"classification":r.get("classification") or "NEWS","reason":r.get("reason") or "User-added external news","user_added":True})
        out.append(x)
    return out


def _external_news_meta_from_url(url: str) -> dict[str,str]:
    if not url: return {}
    try:
        r=requests.get(url,headers={"User-Agent":"CA-Trader/1.0 news resolver"},timeout=5)
        if not r.ok: return {}
        text=r.text[:800000]
        title=re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)',text,re.I) or re.search(r'<title[^>]*>(.*?)</title>',text,re.I|re.S)
        desc=re.search(r'<meta[^>]+(?:property|name)=["\'](?:og:description|description)["\'][^>]+content=["\']([^"\']+)',text,re.I)
        site=re.search(r'<meta[^>]+property=["\']og:site_name["\'][^>]+content=["\']([^"\']+)',text,re.I)
        return {"headline":html.unescape(re.sub(r'\s+',' ',title.group(1))).strip() if title else "", "summary":html.unescape(re.sub(r'\s+',' ',desc.group(1))).strip() if desc else "", "source":html.unescape(site.group(1)).strip() if site else ""}
    except Exception:
        return {}


def _external_news_search_sync(payload: dict[str,Any]) -> list[dict[str,Any]]:
    headline=str(payload.get("headline") or "").strip(); summary=str(payload.get("summary") or "").strip(); url=str(payload.get("url") or "").strip(); target=str(payload.get("target") or "").strip().upper()
    meta=_external_news_meta_from_url(url) if url else {}
    if meta:
        headline=headline or meta.get("headline",""); summary=summary or meta.get("summary","")
    query=" ".join(x for x in [headline,summary,target] if x).strip()
    if not query and url: query=url
    if not query: return []
    articles=[]
    ranked_sources=sorted(NEWS_SOURCES, key=lambda x: (0 if x[3] == "india" else 1, x[0]))
    sample_sources=ranked_sources[:min(len(ranked_sources), max(20, NEWS_RSS_BATCH))]
    with ThreadPoolExecutor(max_workers=min(10,len(sample_sources))) as pool:
        futures=[pool.submit(_rss_articles,source,rss,target,6) for source,rss,_site,_region in sample_sources]
        for fut in futures:
            try: articles.extend(fut.result(timeout=6) or [])
            except Exception: pass
    if url:
        articles.insert(0,{"provider":"URL","source":meta.get("source") or "External source","title":headline,"summary":summary,"published_at":now_iso(),"url":url})
    unique=_news_dedupe(articles)
    scored=[]
    qwords=set(re.findall(r"[a-z0-9]{3,}",_norm_news(query)))
    for a in unique:
        text=_norm_news(_news_text(a.get("title"),a.get("summary")))
        overlap=sum(1 for w in qwords if w in text)
        c=_news_classify(a.get("title") or "",a.get("summary") or "",target or None)
        score=min(100,35+overlap*8+float(c.get("relevance") or 0)*45+(20 if target and target in text else 0))
        scored.append({"headline":a.get("title") or "Untitled","summary":_clean_news_summary(a.get("summary") or ""),"source":a.get("source") or a.get("provider") or "Unknown","url":a.get("url") or "","published_at":a.get("published_at") or now_iso(),"relevance_score":round(score),"classification":c.get("classification") or "NEWS","materiality":c.get("materiality",0),"reason":c.get("reason") or "Relevant match"})
    scored.sort(key=lambda x:(x["relevance_score"],x.get("published_at") or ""),reverse=True)
    out=[]; seen=set()
    for x in scored:
        k=(x["url"] or "",re.sub(r"[^a-z0-9]+"," ",x["headline"].lower()).strip())
        if k in seen: continue
        seen.add(k); out.append(x)
        if len(out)>=5: break
    return out



def _news_cache_key(target: str, user_id: int | None) -> str:
    return f"news:combined:v10:{user_id or 0}:{str(target).upper().strip()}"


def _news_build_result(query: str, max_results: int, target: str, user_id: int | None, *, fast: bool) -> dict[str, Any]:
    articles=[]; sources=list(NEWS_SOURCES)
    if fast:
        # First paint uses a small, diverse slice with hard per-host timeouts.
        # This path is allowed to return real articles; it is not a placeholder.
        india=[x for x in sources if str(x[3]).lower()=="india"][:4]
        global_sources=[x for x in sources if str(x[3]).lower()=="global"][:4]
        sources=india+global_sources; per_source=14; deadline=1.7; rss_timeout=1.0
    else:
        per_source=25 if target not in {"GLOBAL","MARKET"} else 18; deadline=6.5; rss_timeout=NEWS_RSS_TIMEOUT
    started=time.monotonic()
    pool=ThreadPoolExecutor(max_workers=min(12,len(sources)))
    futures={pool.submit(_rss_articles,src,rss,target,per_source,rss_timeout):(src,rss) for src,rss,_site,_region in sources}
    try:
        try:
            completed=as_completed(futures, timeout=deadline)
            for fut in completed:
                try: articles.extend(fut.result(timeout=0.05) or [])
                except Exception: pass
        except FuturesTimeoutError:
            pass
    finally:
        # Do not wait for slow/dead RSS hosts after the deadline; the previous
        # context-manager shutdown could keep the HTTP request open for all workers.
        pool.shutdown(wait=False, cancel_futures=True)

    # Keep API providers supplemental and never let a single provider block first paint.
    api_queries=[]
    if target in {"NIFTY","NIFTY50"}:
        aliases=[]
        for sym in NIFTY50_SYMBOLS: aliases.extend(NIFTY50_NEWS_ALIASES.get(sym,[sym]))
        for i in range(0,len(aliases),10): api_queries.append(" OR ".join(f'"{x}"' for x in aliases[i:i+10]))
        api_queries.append('"Nifty 50" OR NIFTY OR RBI OR India markets OR Sensex')
    elif target in {"BANKNIFTY","NIFTYBANK"}:
        api_queries=['"Bank Nifty" OR "Nifty Bank" OR RBI OR banking India']
    elif target in {"GLOBAL","MARKET"}:
        api_queries=[query or "global markets geopolitics rates oil inflation tariffs central banks"]
    else:
        aliases=NIFTY50_NEWS_ALIASES.get(target) or [target, str((STOCKS.get(target) or {}).get('name') or target)]
        api_queries=[" OR ".join(f'"{x}"' for x in aliases[:8])]
    if not fast:
        for q in api_queries[:8]:
            try: articles.extend(_gnews_articles(q,20))
            except Exception: pass
            try: articles.extend(_newsapi_articles(q,20))
            except Exception: pass

    if not fast and target not in {"BANKNIFTY","NIFTYBANK","NIFTY50","NIFTY","GLOBAL","MARKET"}:
        try:
            key,_=UPSTOX.resolve_instrument(target)
            for tok in _news_key_pool("UPSTOX_ACCESS_TOKEN")[:max(1,NEWS_KEY_MAX_ATTEMPTS)]:
                try:
                    resp=requests.get(UPSTOX_BASE_URL+"/news",params={"category":"instrument_keys","instrument_keys":key,"page_size":50},headers={"Authorization":f"Bearer {tok}","Accept":"application/json"},timeout=4)
                except Exception: continue
                if resp.status_code in (401,403,429): continue
                if resp.ok:
                    data=resp.json().get("data") or {}; rows=data.get(key) or []
                    articles.extend([{"provider":"Upstox","source":"Upstox Market News","title":r.get("heading") or r.get("title"),"summary":r.get("summary") or r.get("description"),"published_at":r.get("published_time"),"url":r.get("article_link") or r.get("url")} for r in rows]); break
        except Exception: pass

    unique=_news_dedupe(articles); hidden=set()
    if user_id: hidden={r["article_key"] for r in db_exec("SELECT article_key FROM news_hidden WHERE user_id=?",[user_id],"all")}
    current=[]
    for a in unique:
        if article_key(a) in hidden: continue
        title=a.get("title") or ""; summary=_strip_news_boilerplate(a.get("summary") or ""); text=_news_text(title,summary)
        if not _news_allowed_session(a.get("published_at")): continue
        if target not in {"GLOBAL","MARKET","NIFTY","NIFTY50","BANKNIFTY","NIFTYBANK"}:
            if not _target_direct_match(text,target):
                if not (("CRUDEOIL" in target or "CRUDE" in target) and _news_contains(text,["crude oil","crudeoil","wti","brent","oil price","oil prices"])):
                    if not (target=="RELIANCE" and _news_contains(text,["oil","crude","brent","wti"]) and _news_contains(text,["iran","sanctions","supply","hormuz","production","opec","disruption"])): continue
        elif target in {"NIFTY","NIFTY50"} and not ("nifty" in text or "sensex" in text or _nifty50_news_match(text)): continue
        c=_news_classify(title,summary,target)
        current.append({"event":title,"headline":title,"summary":_clean_news_summary(summary),"source":a.get("source") or a.get("provider"),"provider":a.get("provider"),"published_at":a.get("published_at"),"url":a.get("url"),**c})
    current.sort(key=lambda x: (_parse_news_datetime(str(x.get("published_at") or "")).timestamp() if _parse_news_datetime(str(x.get("published_at") or "")) else 0), reverse=True)
    return {"events":current[:max_results],"archived_events":[],"market_updates":[x for x in current if x.get("classification")=="MARKET_UPDATE"][:100],"analysis_events":[x for x in current if x.get("classification")=="ANALYSIS"][:100],"query":query,"provider":"combined","providers":["publisher_rss","gnews","newsapi","upstox"],"publisher_sources":{"india":20,"global":20},"timestamp":now_iso(),"fresh":not fast,"partial":fast,"raw_unique_count":len(unique),"returned_count":len(current)}


def _refresh_news_background(query: str, target: str, user_id: int | None, max_results: int) -> None:
    key=_news_cache_key(target,user_id)
    with _NEWS_REFRESH_LOCK:
        if key in _NEWS_REFRESH_INFLIGHT: return
        _NEWS_REFRESH_INFLIGHT.add(key)
    def worker():
        try: CACHE.set(key,_news_build_result(query,max_results,target,user_id,fast=False),max(45,NEWS_CACHE_TTL))
        except Exception as exc: log.debug("background news refresh failed target=%s: %s",target,safe_text(exc))
        finally:
            with _NEWS_REFRESH_LOCK: _NEWS_REFRESH_INFLIGHT.discard(key)
    _NEWS_REFRESH_EXECUTOR.submit(worker)


def news_result(query: str, max_results: int = 200, target: str | None = None, user_id: int | None = None) -> dict[str,Any]:
    """Return cached news immediately; cold starts are warmed asynchronously.
    The request path never waits on dozens of external RSS/API hosts.
    """
    target=(target or query or "GLOBAL").upper().strip(); max_results=max(20,min(int(max_results or 200),500))
    key=_news_cache_key(target,user_id); cached=CACHE.get(key)
    if cached is not None:
        _refresh_news_background(query,target,user_id,max_results)
        return {**cached,"events":(cached.get("events") or [])[:max_results],"stale_while_revalidate":True}
    # Cold start: do a bounded fast publisher pass so the first response contains
    # actual news instead of an empty spinner. The complete 40-source aggregation
    # continues asynchronously and replaces the cache when ready.
    fast_result=_news_build_result(query,min(max_results,100),target,user_id,fast=True)
    if fast_result.get("events"):
        CACHE.set(key,fast_result,max(15,NEWS_CACHE_TTL))
        _refresh_news_background(query,target,user_id,max_results)
        return {**fast_result, "stale_while_revalidate":True}
    _refresh_news_background(query,target,user_id,max_results)
    return {
        "events":[], "archived_events":[], "market_updates":[], "analysis_events":[],
        "query":query, "provider":"combined",
        "providers":["publisher_rss","gnews","newsapi","upstox"],
        "publisher_sources":{"india":20,"global":20},
        "timestamp":now_iso(), "fresh":False, "partial":True, "warming":True,
        "raw_unique_count":0, "returned_count":0, "retry_after_ms":1200
    }

# ---------------------------------------------------------------------------
# News scoring / recommendation evidence
# ---------------------------------------------------------------------------
POSITIVE_NEWS_TERMS = ["profit rises","profit growth","revenue growth","beats estimates","strong demand","order win","approval","approved","acquisition","funding","expansion","buyback","dividend","upgrade","record profit","record revenue","raises guidance","capacity expansion"]
NEGATIVE_NEWS_TERMS = ["profit falls","profit declines","revenue falls","misses estimates","weak demand","downgrade","penalty","fine","fraud","investigation","default","debt stress","plant shutdown","guidance cut","stake sale","regulatory action","loss widens","bankruptcy"]

def news_signal(events: list[dict[str, Any]]) -> dict[str, Any]:
    score=0.0; materiality=0.0; reasons=[]
    for e in events:
        text=_news_text(e.get("headline") or e.get("title") or "", e.get("summary") or "")
        pos=sum(1 for t in POSITIVE_NEWS_TERMS if t in text)
        neg=sum(1 for t in NEGATIVE_NEWS_TERMS if t in text)
        local=(pos-neg)
        
        raw_mat=e.get("materiality")
        try:
            mat=float(raw_mat or 0)
        except (TypeError, ValueError):
            mat={"HIGH":NEWS_MATERIALITY_HIGH,"MEDIUM":NEWS_MATERIALITY_MEDIUM,"LOW":30.0}.get(str(raw_mat).upper(),0.0)

        score += local * (1 + mat/100.0)
        materiality=max(materiality, mat)
        if local: reasons.append(("positive" if local>0 else "negative")+": "+str(e.get("headline") or e.get("title") or "")[:140])
    if score > 0.75: signal="BUY"
    elif score < -0.75: signal="SELL"
    else: signal="NEUTRAL"
    return {"signal":signal,"score":round(score,2),"materiality":round(materiality,1),"reasons":reasons[:6],"count":len(events)}

def recommendation_news_evidence(symbol: str) -> dict[str, Any]:
    key=f"rec-news:{str(symbol).upper()}"; cached=CACHE.get(key)
    if cached is not None: return cached
    stock=[]; global_events=[]
    try: stock=(news_result(_target_news_query(symbol), 30, symbol).get("events") or [])
    except Exception: pass
    try: global_events=(news_result("India markets RBI earnings oil geopolitical tariffs", 30, "GLOBAL").get("events") or [])
    except Exception: pass
    result={"stock":news_signal(stock),"global":news_signal(global_events),"stock_events":stock[:8],"global_events":global_events[:8]}
    CACHE.set(key,result,30); return result

# ---------------------------------------------------------------------------
# Technical analysis
# ---------------------------------------------------------------------------

TIMEFRAMES = ["1m", "3m", "5m", "10m", "15m", "30m", "60m"]


def series_from_candles(candles: list[dict[str, Any]]) -> pd.DataFrame:
    if not candles:
        return pd.DataFrame(columns=["open", "high", "low", "close", "volume"])
    df = pd.DataFrame(candles)
    for c in ["open", "high", "low", "close", "volume"]:
        if c in df:
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)


def rsi(close: pd.Series, period: int = 14) -> float | None:
    if len(close) < period + 1:
        return None
    delta = close.diff()
    gains = delta.clip(lower=0).rolling(period).mean()
    losses = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gains / losses.replace(0, np.nan)
    value = 100 - (100 / (1 + rs.iloc[-1]))
    return float(value) if np.isfinite(value) else 50.0


def ema(close: pd.Series, period: int) -> float | None:
    if len(close) < period:
        return None
    value = close.ewm(span=period, adjust=False).mean().iloc[-1]
    return float(value) if np.isfinite(value) else None


def macd(close: pd.Series) -> dict[str, float | None]:
    if len(close) < 35:
        return {"macd": None, "signal": None, "histogram": None}
    fast = close.ewm(span=12, adjust=False).mean()
    slow = close.ewm(span=26, adjust=False).mean()
    line = fast - slow
    signal = line.ewm(span=9, adjust=False).mean()
    return {"macd": float(line.iloc[-1]), "signal": float(signal.iloc[-1]), "histogram": float((line - signal).iloc[-1])}


def atr(df: pd.DataFrame, period: int = 14) -> float | None:
    if len(df) < period + 1:
        return None
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    value = tr.rolling(period).mean().iloc[-1]
    return float(value) if np.isfinite(value) else None


def adx(df: pd.DataFrame, period: int = 14) -> float | None:
    if len(df) < period * 2 + 1:
        return None
    high = df["high"]
    low = df["low"]
    close = df["close"]
    up = high.diff()
    down = -low.diff()
    plus_dm = up.where((up > down) & (up > 0), 0.0)
    minus_dm = down.where((down > up) & (down > 0), 0.0)
    tr = pd.concat([(high-low), (high-close.shift()).abs(), (low-close.shift()).abs()], axis=1).max(axis=1)
    atr_s = tr.rolling(period).mean()
    plus_di = 100 * plus_dm.rolling(period).mean() / atr_s.replace(0, np.nan)
    minus_di = 100 * minus_dm.rolling(period).mean() / atr_s.replace(0, np.nan)
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0, np.nan)
    value = dx.rolling(period).mean().iloc[-1]
    return float(value) if np.isfinite(value) else None


def technical_analysis(candles: list[dict[str, Any]]) -> dict[str, Any]:
    df = series_from_candles(candles)
    if df.empty:
        return {"available": False, "reason": "No historical candles available"}
    close = df["close"]
    high = df["high"]
    low = df["low"]
    vol = df["volume"] if "volume" in df else pd.Series(dtype=float)
    r = rsi(close)
    m = macd(close)
    e20 = ema(close, 20)
    e50 = ema(close, 50)
    sma20 = float(close.rolling(20).mean().iloc[-1]) if len(close) >= 20 else None
    a = atr(df)
    dx = adx(df)
    vwap = float((close * vol).sum() / vol.sum()) if len(vol) and float(vol.sum()) > 0 else None
    std20 = float(close.rolling(20).std().iloc[-1]) if len(close) >= 20 else None
    bb_mid = sma20
    bb_upper = (bb_mid + 2 * std20) if bb_mid is not None and std20 is not None else None
    bb_lower = (bb_mid - 2 * std20) if bb_mid is not None and std20 is not None else None
    momentum = float(close.iloc[-1] - close.iloc[-6]) if len(close) >= 6 else None
    support = float(low.tail(min(20, len(low))).min())
    resistance = float(high.tail(min(20, len(high))).max())
    last = float(close.iloc[-1])
    direction = "BUY" if (e20 and last > e20 and (m["histogram"] or 0) > 0) else "SELL" if (e20 and last < e20 and (m["histogram"] or 0) < 0) else "NO_TRADE"
    sma50 = float(close.rolling(50).mean().iloc[-1]) if len(close) >= 50 else None
    wma20 = float((close.tail(20) * np.arange(1, min(20, len(close)) + 1)).sum() / np.arange(1, min(20, len(close)) + 1).sum()) if len(close) >= 20 else None
    stoch_k = None
    if len(close) >= 14:
        ll = float(low.tail(14).min()); hh = float(high.tail(14).max()); stoch_k = ((last-ll)/(hh-ll)*100) if hh != ll else 50.0
    cci_v = None
    if len(close) >= 20:
        tp = (high+low+close)/3; ma = tp.rolling(20).mean(); md = tp.rolling(20).apply(lambda x: np.mean(np.abs(x-x.mean())), raw=True); cci_v = float(((tp.iloc[-1]-ma.iloc[-1])/(0.015*(md.iloc[-1] or 1)))) if np.isfinite(ma.iloc[-1]) else None
    willr = None
    if len(close) >= 14:
        ll = float(low.tail(14).min()); hh = float(high.tail(14).max()); willr = ((hh-last)/(hh-ll)*-100) if hh != ll else -50.0
    obv = 0.0
    if len(close) > 1 and len(vol) == len(close):
        for i in range(1, len(close)):
            obv += float(vol.iloc[i]) if close.iloc[i] > close.iloc[i-1] else -float(vol.iloc[i]) if close.iloc[i] < close.iloc[i-1] else 0.0
    mfi_v = None
    if len(close) >= 14 and len(vol) == len(close):
        tp = (high+low+close)/3; mf = tp*vol; pos=mf.where(tp.diff()>0,0).rolling(14).sum().iloc[-1]; neg=mf.where(tp.diff()<0,0).rolling(14).sum().iloc[-1]; mfi_v=float(100-(100/(1+(pos/(neg or 1e-9)))))
    supertrend = float(e20 or last)
    indicators = []
    def add_ind(name, value, criteria, signal=None, materiality=50):
        if signal is None:
            if value is None: signal = "NEUTRAL"
            elif name in {"RSI","Stochastic","Stoch RSI","CCI","Williams %R","MFI"}: signal = "BUY" if value > (60 if name not in {"Williams %R"} else -40) else "SELL" if value < (40 if name not in {"Williams %R"} else -60) else "NEUTRAL"
            elif name in {"MACD"}: signal = "BUY" if (m.get("histogram") or 0)>0 else "SELL" if (m.get("histogram") or 0)<0 else "NEUTRAL"
            else: signal = "BUY" if value is not None and last > value else "SELL" if value is not None and last < value else "NEUTRAL"
        indicators.append({"name":name,"value":value,"materiality":round(float(materiality),1),"signal":signal,"criteria":criteria})
    add_ind("SMA 20", sma20, "Price above SMA 20 = bullish")
    add_ind("EMA 20", e20, "Price above EMA 20 = bullish")
    add_ind("EMA 50", e50, "Price above EMA 50 = bullish")
    add_ind("WMA 20", wma20, "Price above WMA 20 = bullish")
    add_ind("RSI 14", r, "Above 60 bullish; below 40 bearish")
    add_ind("MACD", m.get("histogram"), "Histogram above zero = bullish; below zero = bearish")
    add_ind("Stochastic", stoch_k, "Above 60 bullish; below 40 bearish")
    add_ind("CCI 20", cci_v, "Above 100 bullish; below -100 bearish")
    add_ind("ADX 14", dx, "Above 25 = strong trend")
    add_ind("ATR 14", a, "Higher ATR = higher volatility", "NEUTRAL", 35)
    add_ind("VWAP", vwap, "Price above VWAP = bullish")
    add_ind("Bollinger Mid", bb_mid, "Price above middle band = bullish")
    add_ind("Momentum", momentum, "Positive momentum = bullish; negative = bearish")
    add_ind("Williams %R", willr, "Above -40 bullish; below -60 bearish")
    add_ind("OBV", obv, "Rising OBV supports buying pressure", "NEUTRAL", 40)
    add_ind("MFI 14", mfi_v, "Above 60 bullish; below 40 bearish")
    add_ind("Support", support, "Price above support = constructive", "BUY" if last>support else "NEUTRAL", 55)
    add_ind("Resistance", resistance, "Price below resistance = overhead supply", "SELL" if last<resistance else "BUY", 55)
    add_ind("Supertrend", supertrend, "Price above trend line = bullish")
    add_ind("Trend", 1 if direction=="BUY" else -1 if direction=="SELL" else 0, "EMA 20 + MACD direction", direction, 70)
    return {
        "available": True,
        "last": last,
        "rsi": r,
        "macd": m,
        "ema20": e20,
        "ema50": e50,
        "sma20": sma20,
        "vwap": vwap,
        "atr": a,
        "adx": dx,
        "bollinger": {"middle": bb_mid, "upper": bb_upper, "lower": bb_lower},
        "momentum": momentum,
        "support": support,
        "resistance": resistance,
        "breakout": bool(last > resistance) if resistance else False,
        "breakdown": bool(last < support) if support else False,
        "trend": direction,
        "trend_strength": min(100, float(dx or 0) * 2),
        "volume": float(vol.iloc[-1]) if len(vol) else None,
        "indicators": indicators,
    }


def detect_candlestick_patterns(candles: list[dict[str, Any]], timeframe: str) -> list[dict[str, Any]]:
    df = series_from_candles(candles)
    if len(df) < 2:
        return []
    out: list[dict[str, Any]] = []
    for i in range(max(1, len(df)-10), len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        body = abs(row.close - row.open)
        rng = max(row.high - row.low, 1e-9)
        upper = row.high - max(row.open, row.close)
        lower = min(row.open, row.close) - row.low
        bullish = row.close > row.open
        bearish = row.close < row.open
        pattern = None
        if body <= rng * 0.1:
            pattern = "Doji"
        elif lower >= body * 2 and upper <= max(body * 0.5, rng * 0.05):
            pattern = "Hammer"
        elif upper >= body * 2 and lower <= max(body * 0.5, rng * 0.05):
            pattern = "Shooting Star"
        elif bullish and prev.close < prev.open and row.open <= prev.close and row.close >= prev.open:
            pattern = "Bullish Engulfing"
        elif bearish and prev.close > prev.open and row.open >= prev.close and row.close <= prev.open:
            pattern = "Bearish Engulfing"
        if pattern:
            trend_context = "up" if float(df.close.iloc[i] - df.close.iloc[max(0, i-5)]) > 0 else "down"
            vol_confirm = None
            if "volume" in df and i >= 5:
                baseline = float(df.volume.iloc[i-5:i].mean())
                vol_confirm = baseline > 0 and float(row.volume) >= baseline * 1.2
            strength = min(100, (body / rng) * 100 + (20 if vol_confirm else 0))
            materiality = min(100, 30 + strength * 0.4 + (10 if trend_context else 0))
            out.append({
                "pattern": pattern,
                "timeframe": timeframe,
                "index": i,
                "timestamp": row.get("timestamp") if hasattr(row, "get") else None,
                "ohlc": {"open": float(row.open), "high": float(row.high), "low": float(row.low), "close": float(row.close)},
                "confirmation": "confirmed" if vol_confirm else "unconfirmed",
                "confidence": round(strength, 1),
                "materiality": round(materiality, 1),
                "supporting_conditions": {"trend_context": trend_context, "volume_confirmation": vol_confirm},
            })
    return out


# ---------------------------------------------------------------------------
# Fundamental-data fallback (internet sources; never mock values)
# ---------------------------------------------------------------------------

def _scalar_yf(obj: Any) -> Any:
    if isinstance(obj, dict):
        return obj.get("raw") if obj.get("raw") is not None else obj.get("fmt")
    return obj

def _fetch_json(url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    r = requests.get(url, params=params, headers={"User-Agent": "CA-Trader/1.0"}, timeout=12)
    r.raise_for_status()
    return r.json()

def _fundamentals_from_screener(symbol: str) -> dict[str, Any] | None:
    try:
        r = requests.get(f"https://www.screener.in/company/{quote(symbol.upper(), safe='')}/", headers={"User-Agent":"Mozilla/5.0 CA-Trader"}, timeout=12)
        if r.status_code >= 400: return None
        html = r.text
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            soup = None

        def num(raw: Any) -> float | None:
            if raw is None: return None
            txt = str(raw).replace(",", "").replace("%", "").strip()
            m = re.search(r"-?\d+(?:\.\d+)?", txt)
            try: return float(m.group(0)) if m else None
            except Exception: return None

        labels = {
            "Market Cap":"market_cap", "Stock P/E":"pe", "Industry P/E":"industry_pe", "Industry PE":"industry_pe",
            "Book Value":"book_value", "Dividend Yield":"dividend_yield", "ROE":"roe", "ROCE":"roce",
            "Debt to equity":"debt_equity", "Debt / Equity":"debt_equity", "Debt to Equity":"debt_equity",
            "EV / EBITDA":"ev_ebitda", "EV/EBITDA":"ev_ebitda", "Enterprise Value / EBITDA":"ev_ebitda",
            "Face Value":"face_value", "EPS":"eps",
        }
        ratios={}
        if soup is not None:
            # Current Screener markup uses metric lists; this also tolerates nested spans/divs.
            for label, key in labels.items():
                node = soup.find(string=lambda x: isinstance(x, str) and x.strip().lower() == label.lower())
                if node:
                    parent=node.parent
                    candidates=[]
                    for el in [parent, getattr(parent, "parent", None)]:
                        if el is not None:
                            candidates.extend(el.find_all(string=True))
                            candidates.append(el.get_text(" ", strip=True))
                    for candidate in candidates:
                        value=num(candidate)
                        if value is not None and label.lower() not in str(candidate).lower():
                            ratios[key]=value; break
        # Robust nearby-number extraction for modern/legacy Screener markup.
        if soup is not None:
            variant_map={
                "industry_pe":["Industry P/E","Industry PE","Industry P/E (TTM)"],
                "debt_equity":["Debt to equity","Debt / Equity","Debt to Equity"],
                "ev_ebitda":["EV / EBITDA","EV/EBITDA","Enterprise Value / EBITDA"],
            }
            for key,names in variant_map.items():
                if ratios.get(key) is not None: continue
                for nm in names:
                    node=soup.find(string=lambda x:isinstance(x,str) and x.strip().lower()==nm.lower())
                    if not node: continue
                    parent=node.parent
                    # Walk a few ancestors/siblings and accept the first numeric token
                    # after the label, excluding the label itself.
                    candidates=[]; cur=parent
                    for _ in range(4):
                        if cur is None: break
                        candidates.append(cur.get_text(" ",strip=True)); cur=getattr(cur,"parent",None)
                    for text_blob in candidates:
                        m=re.search(r"(?:"+re.escape(nm)+r")[^0-9-]{0,100}(-?\d+(?:,\d{3})*(?:\.\d+)?)",text_blob,re.I)
                        if m:
                            val=num(m.group(1))
                            if val is not None:
                                ratios[key]=val; break
                    if ratios.get(key) is not None: break

        # Regex fallback for older/altered HTML.
        for label,key in labels.items():
            if ratios.get(key) is not None: continue
            m=re.search(rf"{re.escape(label)}[^0-9-]{{0,120}}(-?\d[\d,.]*\.?\d*)\s*%?", html, re.I|re.S)
            if m:
                ratios[key]=num(m.group(1))
        if not ratios: return None
        # Screener shows Market Cap in ₹ crore. Normalize to rupees for the app.
        if ratios.get("market_cap") is not None and ratios["market_cap"] < 1e8:
            ratios["market_cap"] = float(ratios["market_cap"]) * 1e7
        return {"source":"Screener.in","ratios":ratios,"raw_url":f"https://www.screener.in/company/{quote(symbol.upper(), safe='')}/"}
    except Exception as exc:
        log.debug("Screener fundamentals unavailable for %s: %s", symbol, safe_text(exc)); return None


def _shareholding_from_screener(symbol: str) -> dict[str, Any]:
    try:
        r=requests.get(f"https://www.screener.in/company/{quote(symbol.upper(), safe='')}/",headers={"User-Agent":"Mozilla/5.0 CA-Trader"},timeout=12)
        if r.status_code>=400:return {}
        html=r.text
        try:
            from bs4 import BeautifulSoup
            soup=BeautifulSoup(html,"html.parser")
        except Exception:
            soup=None
        def pct(raw):
            if raw is None:return None
            m=re.search(r"-?\d+(?:\.\d+)?",str(raw).replace(',',''))
            try:return float(m.group(0)) if m else None
            except:return None
        vals={"promoters":None,"fii":None,"dii":None,"institutions":None,"public":None}
        if soup is not None:
            sec=soup.find(id="shareholding") or soup.find(string=lambda x:isinstance(x,str) and "shareholding" in x.lower())
            root=sec.parent if getattr(sec,'parent',None) else soup
            text=root.get_text(" ",strip=True) if root else soup.get_text(" ",strip=True)
            for label,key in [("Promoters","promoters"),("FIIs","fii"),("DIIs","dii"),("Public","public")]:
                m=re.search(rf"{re.escape(label)}\s+([0-9]+(?:\.[0-9]+)?)\s*%?",text,re.I)
                if m: vals[key]=pct(m.group(1))
        # HTML fallback.
        for label,key in [("Promoters","promoters"),("FIIs","fii"),("DIIs","dii")]:
            if vals[key] is None:
                m=re.search(rf"{re.escape(label)}.*?([0-9]+(?:\.[0-9]+)?)\s*%",html,re.I|re.S)
                if m: vals[key]=pct(m.group(1))
        if vals["fii"] is not None or vals["dii"] is not None:
            vals["institutions"]=(vals["fii"] or 0)+(vals["dii"] or 0)
        if vals["promoters"] is not None and vals["institutions"] is not None:
            vals["public"]=max(0.0,100-vals["promoters"]-vals["institutions"])
        return vals
    except Exception:return {}


def _fundamentals_from_yahoo(symbol: str) -> dict[str, Any] | None:
    ticker=symbol.upper()+".NS"
    try:
        data=_fetch_json(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{quote(ticker,safe='')}", {"modules":"price,summaryDetail,defaultKeyStatistics,financialData"})
        result=((data.get("quoteSummary") or {}).get("result") or [None])[0]
        if not result: return None
        p=result.get("price") or {}; sd=result.get("summaryDetail") or {}; ks=result.get("defaultKeyStatistics") or {}; fd=result.get("financialData") or {}
        vals={
            "market_cap":_scalar_yf(p.get("marketCap")), "pe":_scalar_yf(sd.get("trailingPE")),
            "pb":_scalar_yf(ks.get("priceToBook")), "eps":_scalar_yf(ks.get("trailingEps")), "book_value":_scalar_yf(ks.get("bookValue")),
            "roe":_scalar_yf(fd.get("returnOnEquity")), "debt_equity":_scalar_yf(fd.get("debtToEquity")),
            "dividend_yield":_scalar_yf(sd.get("dividendYield")), "ev_ebitda":_scalar_yf(ks.get("enterpriseToEbitda")),
        }
        if vals.get("roe") is not None: vals["roe"]=float(vals["roe"])*100 if float(vals["roe"])<=1 else float(vals["roe"])
        if vals.get("dividend_yield") is not None: vals["dividend_yield"]=float(vals["dividend_yield"])*100 if float(vals["dividend_yield"])<=1 else float(vals["dividend_yield"])
        return {"source":"Yahoo Finance","ratios":vals,"raw_url":f"https://finance.yahoo.com/quote/{quote(ticker,safe='')}/"}
    except Exception as exc:
        log.debug("Yahoo fundamentals unavailable for %s: %s", symbol, safe_text(exc)); return None

def _quarterly_from_yahoo(symbol: str) -> list[dict[str, Any]]:
    ticker=symbol.upper()+".NS"
    try:
        period1=int((datetime.now(timezone.utc)-timedelta(days=550)).timestamp())
        period2=int(datetime.now(timezone.utc).timestamp())
        data=_fetch_json(f"https://query2.finance.yahoo.com/ws/fundamentals-timeseries/v1/finance/timeseries/{quote(ticker,safe='')}", {"symbol":ticker,"type":"quarterlyTotalRevenue,quarterlyNetIncome","period1":period1,"period2":period2})
        ts=((data.get("timeseries") or {}).get("result") or [])
        revenue=[]; profit=[]
        for row in ts:
            if "quarterlyTotalRevenue" in row: revenue=row["quarterlyTotalRevenue"]
            if "quarterlyNetIncome" in row: profit=row["quarterlyNetIncome"]
        by={}
        for r in revenue:
            by.setdefault(r.get("asOfDate"),{})["revenue"]=_scalar_yf(r.get("reportedValue"))
        for r in profit:
            by.setdefault(r.get("asOfDate"),{})["net_profit"]=_scalar_yf(r.get("reportedValue"))
        out=[{"quarter":k,**v} for k,v in sorted(by.items()) if v.get("revenue") is not None or v.get("net_profit") is not None]
        return out[-4:]
    except Exception:
        return []

def fundamental_data(instrument: str) -> dict[str, Any]:
    try:
        key, meta = get_instrument_meta(instrument)
    except Exception:
        key, meta = instrument, {"trading_symbol": instrument}
    symbol=str(meta.get("trading_symbol") or instrument).upper()
    inst_type=str(meta.get("instrument_type") or meta.get("segment") or "").upper()
    if inst_type == "INDEX" or symbol in {"BANKNIFTY","NIFTYBANK","NIFTY50","NIFTY","SENSEX"}:
        return {"instrument":instrument,"symbol":symbol,"name":meta.get("name") or symbol,"available":False,"provider":None,"sources":[],"ratios":{},"quarterly":[],"shareholding":{},"current_price":None,"timestamp":now_iso(),"data_quality":{"indices":True},"note":"Equity fundamentals are not applicable to indices."}
    base=_fundamentals_from_screener(symbol)
    yahoo=_fundamentals_from_yahoo(symbol)
    ratios={}; sources=[]
    if base: ratios.update({k:v for k,v in base.get("ratios",{}).items() if v is not None}); sources.append(base["source"])
    if yahoo:
        # Prefer provider-native Market Cap / valuation fields over scraped units.
        for k,v in yahoo.get("ratios",{}).items():
            if v is not None and (k not in ratios or k in {"market_cap","debt_equity","ev_ebitda"}):
                ratios[k]=v
        sources.append(yahoo["source"])
    try:
        q=UPSTOX.quote(instrument); current_price=q.get("ltp")
        if ratios.get("book_value") and current_price and not ratios.get("pb"): ratios["pb"]=float(current_price)/float(ratios["book_value"])
    except Exception:
        current_price=None
    quarterly=_quarterly_from_yahoo(symbol)
    shareholding=_shareholding_from_screener(symbol)
    return {
        "instrument":instrument,"symbol":symbol,"name":meta.get("name") or meta.get("short_name") or symbol,
        "available":bool(ratios),"provider":"internet_fallback" if ratios else None,"sources":sources,
        "ratios":ratios,"quarterly":quarterly,"shareholding":shareholding,"current_price":current_price,"timestamp":now_iso(),"data_quality":{"ratios":bool(ratios),"quarterly":bool(quarterly),"shareholding":bool(shareholding)},
        "source_urls":[x.get("raw_url") for x in (base,yahoo) if x and x.get("raw_url")],
        "note":"Fundamentals are sourced from public internet data when an Upstox fundamentals endpoint is unavailable; missing fields remain unavailable."
    }

# ---------------------------------------------------------------------------
# Recommendation / risk engines
# ---------------------------------------------------------------------------


def trade_levels(side: str, entry: float, atr_value: float | None, support: float | None, resistance: float | None, desired_profit: float | None, bearable_loss: float | None) -> dict[str, Any]:
    a = float(atr_value or max(entry * 0.005, 0.05))
    if side == "BUY":
        sl = entry - min(max(a * 1.2, entry * 0.003), max(entry * 0.05, a * 2.0))
        if bearable_loss is not None:
            sl = max(0.01, entry - abs(float(bearable_loss)))
        target = entry + max(a * 1.8, desired_profit or a * 1.8)
        if resistance and resistance > entry:
            target = min(target, float(resistance)) if desired_profit is None else max(target, float(entry + desired_profit))
    else:
        sl = entry + max(a * 1.2, entry * 0.003)
        if bearable_loss is not None:
            sl = entry + abs(float(bearable_loss))
        target = max(0.01, entry - max(a * 1.8, desired_profit or a * 1.8))
        if support and support < entry:
            target = max(target, float(support)) if desired_profit is None else min(target, float(entry - desired_profit))
    risk = abs(entry - sl)
    reward = abs(target - entry)
    return {"entry": round(entry, 4), "stop_loss": round(sl, 4), "target": round(target, 4), "expected_risk": round(risk, 4), "expected_reward": round(reward, 4), "risk_reward": round(reward / risk, 3) if risk else None}


def normalize_signal(side: str, levels: dict[str, Any]) -> bool:
    if side == "BUY":
        return levels["stop_loss"] < levels["entry"] < levels["target"]
    if side == "SELL":
        return levels["target"] < levels["entry"] < levels["stop_loss"]
    return True


def overall_recommendation(symbol: str, timeframe: str, desired_profit: float | None = None, bearable_loss: float | None = None, risk_preferences: dict[str, Any] | None = None, option_preferences: dict[str, Any] | None = None) -> dict[str, Any]:
    cache_key=f"overall:{symbol.upper()}:{timeframe}:{json.dumps(risk_preferences or {},sort_keys=True)}:{json.dumps(option_preferences or {},sort_keys=True)}"
    cached=CACHE.get(cache_key)
    if cached is not None: return cached
    risk_preferences=risk_preferences or {}; option_preferences=option_preferences or {}
    candles=UPSTOX.candles(symbol,timeframe.rstrip("m"),"minutes",days=5 if timeframe!="1D" else 365)
    ta=technical_analysis(candles)
    if not ta.get("available"): return {"qualifies":False,"recommendation":"NO_TRADE","reason":ta.get("reason"),"evidence":{"technical":ta}}
    patterns=detect_candlestick_patterns(candles,timeframe)
    news=recommendation_news_evidence(symbol)
    technical_side=ta.get("trend","NO_TRADE")
    if ta.get("rsi") is not None and technical_side=="SELL" and ta["rsi"]<30: technical_side="BUY"
    if ta.get("rsi") is not None and technical_side=="BUY" and ta["rsi"]>70: technical_side="SELL"
    stock_sig=news["stock"]["signal"]; global_sig=news["global"]["signal"]
    news_score=(1 if stock_sig=="BUY" else -1 if stock_sig=="SELL" else 0)+(0.5 if global_sig=="BUY" else -0.5 if global_sig=="SELL" else 0)
    side=technical_side; confidence=50+min(20,float(ta.get("adx") or 0)*0.25)+min(15,len(patterns)*5)
    if side in {"BUY","SELL"} and news_score:
        if (side=="BUY" and news_score<0) or (side=="SELL" and news_score>0):
            if abs(news_score)>=1 and max(news["stock"]["materiality"],news["global"]["materiality"])>=60: side="NO_TRADE"
            else: confidence-=8
        else: confidence+=6
    evidence={"technical":ta,"patterns":patterns,"news":news}
    if side in {"BUY","SELL"} and (option_preferences.get("enabled") or option_preferences):
        try:
            opt=option_trade_candidate(symbol,side); evidence["options"]=opt
        except Exception as exc: evidence["options"]={"available":False,"reason":safe_text(exc)}
    if side not in {"BUY","SELL"}: return {"qualifies":False,"recommendation":"NO_TRADE","reason":"Technical/news evidence is mixed or conflicting","confidence":round(max(0,confidence),1),"evidence":evidence,"provider":"upstox+news","timestamp":now_iso()}
    instrument={"kind":"EQUITY","symbol":symbol,"entry":float(ta["last"]),"instrument_key":None,"lot_size":1}
    opt=evidence.get("options") or {}
    if opt.get("available") and float(opt.get("score") or 0)>=62:
        instrument={"kind":"OPTION","symbol":opt.get("instrument_key"),"transaction_side":"BUY","instrument_key":opt.get("instrument_key"),"entry":opt.get("entry"),"lot_size":opt.get("lot_size"),"option_type":opt.get("option_type"),"strike":opt.get("strike"),"expiry":opt.get("expiry"),"display":f"{symbol} {opt.get('option_type')} {opt.get('strike')} {opt.get('expiry')}"}
    entry=float(instrument.get("entry") or ta["last"]); levels=trade_levels(side,entry,ta.get("atr"),ta.get("support"),ta.get("resistance"),desired_profit,bearable_loss)
    if not normalize_signal(side,levels): return {"qualifies":False,"recommendation":"NO_TRADE","reason":"Risk/target geometry failed validation","evidence":evidence}
    result={"qualifies":True,"recommendation":side,"timeframe":timeframe,"confidence":round(min(99,max(0,confidence+(5 if instrument["kind"]=="OPTION" else 0))),1),**levels,"instrument":instrument,"evidence":evidence,"rationale":"Underlying technicals, option Greeks, option technical analysis, liquidity and stock/global news are combined where an option is selected.","provider":"upstox+news","timestamp":now_iso()}
    CACHE.set(cache_key,result,20)
    return result


def ai_analyze(evidence: dict[str, Any]) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return {"available": False, "reason": "Gemini API key is not configured"}
    prompt = (
        "You are the CA Trader risk layer. Use ONLY the supplied structured evidence. "
        "Do not invent missing data. Return JSON with keys: decision (BUY|SELL|NO_TRADE), "
        "confidence, rationale, missing_evidence.\n\n" + json.dumps(evidence, default=str)[:25000]
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{quote(GEMINI_MODEL, safe='-_.')}:generateContent"
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        resp = requests.post(url, headers=headers, json=body, timeout=20)
    except Exception as exc:
        record_error("provider_failure", repr(exc), "gemini")
        return {"available": False, "reason": "Gemini request failed"}
    if resp.status_code >= 400:
        record_error("api_failure", f"Gemini HTTP {resp.status_code}", "gemini", resp.status_code)
        return {"available": False, "reason": f"Gemini HTTP {resp.status_code}"}
    try:
        payload = resp.json()
        text = "".join(p.get("text", "") for p in payload.get("candidates", [{}])[0].get("content", {}).get("parts", []))
        match = re.search(r"\{.*\}", text, re.S)
        data = json.loads(match.group(0)) if match else {"decision": "NO_TRADE", "rationale": text}
        provider_ok("gemini")
        return {"available": True, **data, "model": GEMINI_MODEL, "timestamp": now_iso()}
    except Exception:
        record_error("malformed_data", "Gemini returned unparseable structured output", "gemini")
        return {"available": False, "reason": "Gemini response was not valid structured JSON"}

# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=1, max_length=300)
    remember_me: bool = True

class RecommendationIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=100)
    timeframe: str = Field(default="5m", pattern=r"^(1m|3m|5m|10m|15m|30m|60m)$")
    desired_profit: float | None = Field(default=None, ge=0)
    bearable_loss: float | None = Field(default=None, ge=0)
    risk_preferences: dict[str, Any] = Field(default_factory=dict)
    option_preferences: dict[str, Any] = Field(default_factory=dict)
    ask_ai: bool = False

class OrderIn(BaseModel):
    symbol: str = Field(min_length=1, max_length=100)
    side: str = Field(pattern=r"^(BUY|SELL)$")
    quantity: int = Field(gt=0, le=1_000_000)
    order_type: str = Field(default="MARKET", pattern=r"^(MARKET|LIMIT|SL|SL-M)$")
    price: float | None = Field(default=None, gt=0)
    trigger_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    target: float | None = Field(default=None, gt=0)
    product: str = Field(default="D", max_length=10)
    paper: bool = True
    live: bool = False
    amo: bool = False

class OrderModifyIn(BaseModel):
    quantity: int | None = Field(default=None, gt=0, le=1_000_000)
    price: float | None = Field(default=None, gt=0)
    trigger_price: float | None = Field(default=None, gt=0)
    stop_loss: float | None = Field(default=None, gt=0)
    target: float | None = Field(default=None, gt=0)

class BuyableIn(BaseModel):
    capital: float = Field(gt=0)
    expiry: str | None = None
    option_type: str | None = Field(default=None, pattern=r"^(CE|PE)$")
    premium_min: float | None = Field(default=None, ge=0)
    premium_max: float | None = Field(default=None, ge=0)
    desired_profit: float | None = Field(default=None, ge=0)
    bearable_loss: float | None = Field(default=None, ge=0)
    min_volume: int = Field(default=0, ge=0)
    min_oi: int = Field(default=0, ge=0)
    quantity_lots: int | None = Field(default=None, ge=1)
    ltp_per_quantity: float | None = Field(default=None, gt=0)
    max_cost_per_lot: float | None = Field(default=None, gt=0)

# ---------------------------------------------------------------------------
# App / auth / middleware
# ---------------------------------------------------------------------------

init_db()
seed_admin()

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    global MAIN_LOOP
    MAIN_LOOP = asyncio.get_running_loop()
    init_db()
    seed_admin()
    auto_task = asyncio.create_task(_auto_trade_loop())
    risk_task = asyncio.create_task(_paper_risk_loop())
    log.info("CA Trader backend ready host=%s port=%s auth=%s", HOST, PORT, AUTH_ENABLED)
    log.info("Terminal HTML served from %s", HTML_PATH)
    log.info("Login HTML served from %s", LOGIN_HTML_PATH)
    try:
        yield
    finally:
        auto_task.cancel(); risk_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await auto_task
        with contextlib.suppress(asyncio.CancelledError):
            await risk_task
        MARKET_STREAM.stop()
        log.info("CA Trader backend shutting down")

app = FastAPI(title="CA Trader Headless Backend", version="1.0.0", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=AUTH_SECRET, max_age=int(AUTH_IDLE_HOURS * 3600), same_site="lax", https_only=False)
app.add_middleware(CORSMiddleware, allow_origins=CORS_ORIGINS or ["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.middleware("http")
async def request_middleware(request: Request, call_next):
    started = time.monotonic()
    client = request.client.host if request.client else "unknown"
    key = f"{client}:{request.url.path}"
    if request.url.path.startswith("/api/") and RATE_LIMIT_ENABLED and not RATE_LIMITER.allow(key):
        record_error("rate_limit", "Local API rate limit exceeded", user_id=(request.scope.get("session") or {}).get("user_id"))
        return JSONResponse({"error": {"code": "RATE_LIMITED", "message": "Too many requests"}}, status_code=429)
    try:
        response = await call_next(request)
    except Exception as exc:
        record_error("backend_exception", safe_text(exc), user_id=(request.scope.get("session") or {}).get("user_id"), context={"path": request.url.path})
        log.exception("API %s %s failed", request.method, request.url.path)
        if DEBUG:
            raise
        return JSONResponse({"error": {"code": "INTERNAL_ERROR", "message": "Internal server error"}}, status_code=500)
    elapsed=round((time.monotonic() - started) * 1000, 2)
    response.headers["X-CA-Trader-Request-Time-Ms"] = str(elapsed)
    scope = "API" if request.url.path.startswith("/api/") else "APP"
    log.info("%s %s %s -> %s in %sms", scope, request.method, request.url.path, response.status_code, elapsed)
    return response


def current_user(request: Request) -> dict[str, Any] | None:
    if not AUTH_ENABLED:
        row = db_exec("SELECT * FROM users ORDER BY id LIMIT 1", fetch="one")
        if row:
            return row
        # Create a local development identity without exposing credentials.
        uid = db_insert("INSERT INTO users(username,created_at,full_name,role) VALUES(?,?,?,?)", ["local-dev", now_iso(), "Local Admin", "admin"])
        db_exec("INSERT INTO funds(user_id,available,trading_funds,testing_funds,auto_trade_funds,updated_at) VALUES(?,?,?,?,?,?)", [uid, 300000, 300000, 300000, 300000, now_iso()])
        request.session["user_id"] = uid
        return get_user(uid)
    uid = request.session.get("user_id")
    if not uid:
        return None
    last = request.session.get("last_seen")
    if last:
        try:
            idle_hours = AUTH_IDLE_HOURS if request.session.get("remember_me", True) else min(2.0, AUTH_IDLE_HOURS)
            if time.time() - float(last) > idle_hours * 3600:
                request.session.clear()
                return None
        except Exception:
            request.session.clear()
            return None
    request.session["last_seen"] = time.time()
    return get_user(int(uid))


def require_user(request: Request) -> dict[str, Any]:
    user = current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail={"code": "AUTH_REQUIRED", "message": "Authentication required"})
    return user


def error_json(code: str, message: str, status: int, **extra: Any) -> JSONResponse:
    return JSONResponse({"error": {"code": code, "message": message, **extra}}, status_code=status)

# ---------------------------------------------------------------------------
# Root + auth
# ---------------------------------------------------------------------------

INTEGRATION_BRIDGE = r"""
<script>window.__CA_TRADER_BACKEND__ = true;</script>
"""

# Authentication bridge is deliberately defined before /login is registered.
# Without this definition, an unauthenticated request to / caused a NameError
# and HTTP 500 even though the login HTML file itself existed.
LOGIN_BRIDGE = r"""
<script>
(() => {
  const api = async (url, options={}) => {
    const res = await fetch(url, {credentials:'include', headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options});
    const body = await res.json().catch(() => ({}));
    if(!res.ok) throw new Error(body?.error?.message || body?.detail?.message || body?.detail || `HTTP ${res.status}`);
    return body;
  };
  const notify = (message) => { console.error('[CA Trader Auth]', message); window.alert(message); };
  const busy = (btn, on) => { if(!btn) return; if(on){ btn.dataset.oldText = btn.innerText; btn.disabled = true; btn.innerText = 'Working…'; } else { btn.disabled = false; btn.innerText = btn.dataset.oldText || btn.innerText; } };

  const signinPane = document.getElementById('pane-signin');
  const signupPane = document.getElementById('pane-signup');

  // Do not bounce an authenticated user through the login screen.
  api('/api/auth/me').then(r => { if(r?.authenticated) window.location.replace('/'); }).catch(() => {});

  const signinButton = signinPane?.querySelector('.btn-primary');
  signinButton?.addEventListener('click', async () => {
    const inputs = signinPane.querySelectorAll('input');
    const email = (inputs[0]?.value || '').trim().toLowerCase();
    const password = inputs[1]?.value || '';
    const remember = !!inputs[2]?.checked;
    if(!email || !password){ notify('Email address and password are required.'); return; }
    busy(signinButton, true);
    try {
      await api('/api/auth/login', {method:'POST', body:JSON.stringify({email,password,remember_me:remember})});
      window.location.replace(window.__CA_POST_LOGIN__ || '/post-login');
    } catch(e) { notify(e.message); busy(signinButton, false); }
  });

  const signupButton = signupPane?.querySelector('.btn-primary');
  signupButton?.addEventListener('click', async () => {
    const inputs = signupPane.querySelectorAll('input');
    const full_name = (inputs[0]?.value || '').trim();
    const email = (inputs[1]?.value || '').trim().toLowerCase();
    const password = inputs[2]?.value || '';
    const confirm = inputs[3]?.value || '';
    if(!full_name || !email || !password){ notify('Full name, email and password are required.'); return; }
    if(password.length < 8){ notify('Password must be at least 8 characters.'); return; }
    if(password !== confirm){ notify('Passwords do not match.'); return; }
    busy(signupButton, true);
    try {
      await api('/api/auth/signup', {method:'POST', body:JSON.stringify({full_name,email,password})});
      window.location.replace('/');
    } catch(e) { notify(e.message); busy(signupButton, false); }
  });

  document.querySelectorAll('.btn-google').forEach(btn => btn.addEventListener('click', () => { window.location.assign('/api/auth/google/start'); }));

  window.sendReset = async () => {
    const email = (document.getElementById('forgotEmail')?.value || '').trim().toLowerCase();
    if(!email){ notify('Please enter your email address.'); return; }
    try {
      await api('/api/auth/password-reset/request', {method:'POST', body:JSON.stringify({email})});
      const form = document.getElementById('forgotForm');
      const sent = document.getElementById('sentState');
      if(form) form.style.display = 'none';
      if(sent) sent.classList.add('show');
    } catch(e) { notify(e.message); }
  };
})();
</script>
"""

HTML_PAGE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Content-Disposition": "inline",
    "X-Content-Type-Options": "nosniff",
}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    user = current_user(request)
    if AUTH_ENABLED and not user:
        return await login_page(request)
    if fitness_allowlisted(user) and not selected_terminal(request):
        return RedirectResponse("/post-login")
    if selected_terminal(request) == "fitness":
        return await fitness_page(request)
    return await terminal_page(request)

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request) -> Response:
    if LOGIN_HTML_PATH and LOGIN_HTML_PATH.exists():
        html = LOGIN_HTML_PATH.read_text(encoding="utf-8")
        marker = "</body>"
        if marker in html:
            html = html.replace(marker, LOGIN_BRIDGE + marker, 1)
        return HTMLResponse(html, headers=HTML_PAGE_HEADERS)
    # Standalone deployments may contain only the terminal HTML. Never turn
    # an authentication redirect into a server 500; provide a small fallback
    # login screen that uses the same /api/auth/login endpoint.
    html = """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><title>CA Trader — Login</title><style>body{margin:0;background:#0A0D12;color:#E7EAF0;font-family:Inter,Arial,sans-serif;min-height:100vh;display:grid;place-items:center}.box{width:min(390px,calc(100vw - 32px));background:#12161F;border:1px solid #232A38;border-radius:12px;padding:24px;box-sizing:border-box}.brand{font-weight:700;font-size:20px;margin-bottom:18px}.brand span{color:#26D9A6}label{display:block;font-size:12px;color:#8A93A6;margin:12px 0 6px}input{width:100%;box-sizing:border-box;padding:10px;border-radius:7px;border:1px solid #30384A;background:#0E121A;color:#E7EAF0;outline:none}button{margin-top:16px;width:100%;padding:10px;border:0;border-radius:7px;background:#26D9A6;color:#07110D;font-weight:700;cursor:pointer}.err{margin-top:10px;color:#FF5C72;font-size:11px;min-height:16px}</style></head><body><form class='box' id='f'><div class='brand'>CA<span>Trader</span></div><label>Email</label><input id='e' type='email' autocomplete='username' required><label>Password</label><input id='p' type='password' autocomplete='current-password' required><button>Sign in</button><div class='err' id='x'></div></form><script>f.addEventListener('submit',async ev=>{ev.preventDefault();x.textContent='';try{const r=await fetch('/api/auth/login',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:e.value,password:p.value,remember_me:true})});const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d?.detail?.message||d?.error?.message||'Login failed');location.href='/'}catch(err){x.textContent=err.message}})</script></body></html>"""
    return HTMLResponse(html, headers=HTML_PAGE_HEADERS)

@app.get("/logout", response_class=HTMLResponse)
async def browser_logout(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"})

@app.get("/force-login", response_class=HTMLResponse)
async def force_login(request: Request) -> Response:
    request.session.clear()
    return RedirectResponse("/", headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0", "Pragma": "no-cache"})

@app.get("/post-login", response_class=HTMLResponse)
async def post_login_page(request: Request) -> Response:
    user=current_user(request)
    if AUTH_ENABLED and not user: return RedirectResponse("/login")
    if not fitness_allowlisted(user): return RedirectResponse("/terminal")
    if selected_terminal(request)=="fitness": return RedirectResponse("/fitness")
    if selected_terminal(request)=="trading": return RedirectResponse("/terminal")
    if not TERMINAL_SELECTOR_HTML_PATH.exists(): return RedirectResponse("/terminal")
    return HTMLResponse(TERMINAL_SELECTOR_HTML_PATH.read_text(encoding="utf-8"), headers=HTML_PAGE_HEADERS)

@app.post("/api/auth/select-terminal")
async def auth_select_terminal(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    body=await request.json(); terminal=str(body.get("terminal") or "").strip().lower()
    if terminal not in {"trading","fitness"}: raise HTTPException(422,"Unsupported terminal")
    if not fitness_allowlisted(user) and terminal!="trading": raise HTTPException(403,"Fitness terminal is not enabled for this account")
    request.session["selected_terminal"]=terminal
    return {"ok":True,"terminal":terminal}

@app.get("/fitness", response_class=HTMLResponse)
async def fitness_page(request: Request) -> Response:
    user=current_user(request)
    if AUTH_ENABLED and not user: return RedirectResponse("/login")
    if not fitness_allowlisted(user): return RedirectResponse("/terminal")
    if not FITNESS_HTML_PATH.exists(): return error_json("FITNESS_UI_NOT_FOUND", "fitness.html is missing", 500)
    request.session["selected_terminal"]="fitness"
    return HTMLResponse(FITNESS_HTML_PATH.read_text(encoding="utf-8"), headers=HTML_PAGE_HEADERS)

@app.get("/terminal", response_class=HTMLResponse)
async def terminal_page(request: Request) -> Response:
    user=current_user(request)
    if AUTH_ENABLED and not user:
        return RedirectResponse("/login")
    if fitness_allowlisted(user) and selected_terminal(request)=="fitness":
        return RedirectResponse("/fitness")
    if not HTML_PATH.exists():
        return error_json("UI_NOT_FOUND", f"HTML file not found: {HTML_PATH}", 500)
    html = HTML_PATH.read_text(encoding="utf-8")
    marker = "</body>"
    if marker in html:
        html = html.replace(marker, INTEGRATION_BRIDGE + marker, 1)
    return HTMLResponse(html)
@app.post("/api/news/external/search")
async def external_news_search(request: Request, user: dict[str,Any] = Depends(require_user)) -> dict[str,Any]:
    body=await request.json()
    if not any(str(body.get(k) or "").strip() for k in ("headline","summary","url")):
        raise HTTPException(422,"Enter a headline, summary, or article URL")
    results=await asyncio.to_thread(_external_news_search_sync,body)
    return {"results":results[:5],"query":{"headline":body.get("headline",""),"summary":body.get("summary",""),"url":body.get("url",""),"target":body.get("target","")},"timestamp":now_iso()}


@app.post("/api/news/external/add")
async def external_news_add(request: Request, user: dict[str,Any] = Depends(require_user)) -> dict[str,Any]:
    body=await request.json(); article=body.get("article") or body
    target=str(body.get("target") or article.get("target") or "").strip().upper(); is_global=bool(body.get("is_global") or not target)
    headline=str(article.get("headline") or article.get("title") or "").strip(); summary=str(article.get("summary") or article.get("description") or "").strip(); url=str(article.get("url") or article.get("link") or "").strip(); source=str(article.get("source") or article.get("provider") or "External source").strip(); published=str(article.get("published_at") or now_iso())
    if not headline and url:
        meta=await asyncio.to_thread(_external_news_meta_from_url,url); headline=meta.get("headline","") or url; summary=summary or meta.get("summary",""); source=meta.get("source") or source
    if not headline and not summary and not url: raise HTTPException(422,"The selected news item has no usable headline, summary, or URL")
    ident=_news_identity({"title":headline,"summary":summary,"url":url})
    existing=db_exec("SELECT id FROM external_news WHERE user_id=? AND (url=? OR (url='' AND headline=?)) LIMIT 1",[user["id"],url,headline],"one")
    if existing: return {"ok":True,"duplicate":True,"id":existing["id"]}
    c=_news_classify(headline,summary,target or None)
    eid=secrets.token_hex(12)
    db_exec("INSERT INTO external_news(id,user_id,target,is_global,headline,summary,url,source,published_at,materiality,classification,reason,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",[eid,user["id"],target,is_global,headline,summary,url,source,published,float(c.get("materiality") or article.get("materiality") or 0),c.get("classification") or "NEWS",c.get("reason") or "User-added external news",now_iso()])
    return {"ok":True,"duplicate":False,"id":eid,"article":{**article,"headline":headline,"summary":summary,"url":url,"source":source,"published_at":published,"materiality":c.get("materiality",0),"classification":c.get("classification","NEWS"),"reason":c.get("reason","User-added external news"),"provider":"User added"}}


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "time": now_iso(), "auth_enabled": AUTH_ENABLED, "providers": {k: dict(v) for k, v in PROVIDER_HEALTH.items()}}

@app.get("/api/auth/me")
async def auth_me(request: Request) -> dict[str, Any]:
    user = current_user(request)
    return {"authenticated": bool(user), "user": user and {"id": user["id"], "username": user["username"], "email": user.get("email"), "full_name": user.get("full_name"), "role": user.get("role","user")}, "terminal_selector": fitness_allowlisted(user), "selected_terminal": selected_terminal(request)}

@app.patch("/api/auth/profile")
async def update_profile(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    body = await request.json()
    full_name = str(body.get("full_name", "")).strip()
    if not full_name or len(full_name) > 80:
        raise HTTPException(422, "Name must be 1-80 characters")
    db_exec("UPDATE users SET full_name=? WHERE id=?", [full_name, user["id"]])
    updated = get_user(user["id"])
    return {"authenticated": True, "user": {"id": updated["id"], "username": updated["username"], "email": updated.get("email"), "full_name": updated.get("full_name"), "role": updated.get("role","user")}}

@app.post("/api/auth/login")
async def auth_login(payload: LoginIn, request: Request) -> dict[str, Any]:
    if not AUTH_ENABLED:
        return {"authenticated": True, "mode": "disabled"}
    email = payload.email.strip().lower()
    row = db_exec("SELECT * FROM users WHERE email=? AND is_active=1", [email], "one")
    if not row or not row.get("password_hash") or not verify_password(payload.password, row["password_hash"]):
        record_error("authentication_failure", "Invalid email/password")
        raise HTTPException(status_code=401, detail={"code": "INVALID_CREDENTIALS", "message": "Invalid email or password"})
    request.session.clear()
    request.session["user_id"] = row["id"]
    request.session["last_seen"] = time.time()
    request.session["remember_me"] = bool(payload.remember_me)
    sid=secrets.token_hex(16);request.session["login_session_id"]=sid
    db_exec("INSERT INTO login_sessions(id,user_id,started_at,last_seen) VALUES(?,?,?,?)",[sid,row["id"],now_iso(),now_iso()])
    return {"authenticated": True, "user": {"id": row["id"], "username": row["username"], "email": row.get("email"), "full_name": row.get("full_name")}}

@app.post("/api/auth/logout")
async def auth_logout(request: Request) -> dict[str, Any]:
    sid=request.session.get("login_session_id")
    if sid: db_exec("UPDATE login_sessions SET ended_at=?,last_seen=? WHERE id=?",[now_iso(),now_iso(),sid])
    request.session.clear();return {"ok":True}

@app.post("/api/auth/signup")
async def auth_signup(request: Request) -> dict[str, Any]:
    body = await request.json()
    full_name = str(body.get("full_name", "")).strip()
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", ""))
    if not full_name or not email or not password:
        raise HTTPException(422, detail={"code": "VALIDATION_ERROR", "message": "Full name, email and password are required"})
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, detail={"code": "INVALID_EMAIL", "message": "Enter a valid email address"})
    if len(password) < 8:
        raise HTTPException(422, detail={"code": "WEAK_PASSWORD", "message": "Password must be at least 8 characters"})
    existing = db_exec("SELECT id FROM users WHERE username=? OR email=?", [email, email], "one")
    if existing:
        raise HTTPException(409, detail={"code": "ACCOUNT_EXISTS", "message": "An account already exists for this email"})
    uid = db_insert("INSERT INTO users(username,password_hash,email,created_at,full_name,role) VALUES(?,?,?,?,?,?)", [email, hash_password(password), email, now_iso(), full_name, "user"])
    db_exec("INSERT INTO funds(user_id,available,trading_funds,testing_funds,auto_trade_funds,updated_at) VALUES(?,?,?,?,?,?)", [uid, 200000, 200000, 0, 200000, now_iso()])
    db_exec("INSERT OR IGNORE INTO auto_trade_configs(user_id,updated_at) VALUES(?,?)", [uid, now_iso()])
    request.session.clear()
    request.session["user_id"] = uid
    request.session["last_seen"] = time.time()
    request.session["remember_me"] = True
    return {"authenticated": True, "user": {"id": uid, "username": email, "email": email, "full_name": full_name}}

@app.post("/api/auth/password-reset/request")
async def password_reset_request(request: Request) -> dict[str, Any]:
    body = await request.json()
    email = str(body.get("email", "")).strip().lower()
    if not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        raise HTTPException(422, detail={"code": "INVALID_EMAIL", "message": "Enter a valid email address"})
    user = db_exec("SELECT id FROM users WHERE (email=? OR username=?) AND is_active=1", [email, email], "one")
    # Always return the same public response to avoid account enumeration.
    if user:
        raw = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        expires = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        db_exec("INSERT INTO password_reset_tokens(token_hash,user_id,expires_at,used,created_at) VALUES(?,?,?,?,?)", [token_hash, user["id"], expires, 0, now_iso()])
        if DEBUG:
            log.info("Password reset token generated for user_id=%s (token redacted)", user["id"])
    return {"accepted": True, "message": "If an account matches that email, a reset link is on its way."}

@app.post("/api/auth/password-reset/confirm")
async def password_reset_confirm(request: Request) -> dict[str, Any]:
    body = await request.json()
    token = str(body.get("token", ""))
    password = str(body.get("password", ""))
    if not token or len(password) < 8:
        raise HTTPException(422, detail={"code": "VALIDATION_ERROR", "message": "Token and a password of at least 8 characters are required"})
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    row = db_exec("SELECT * FROM password_reset_tokens WHERE token_hash=? AND used=0", [token_hash], "one")
    if not row:
        raise HTTPException(400, detail={"code": "INVALID_RESET_TOKEN", "message": "Invalid or expired reset token"})
    try:
        if datetime.fromisoformat(row["expires_at"]) < datetime.now(timezone.utc):
            raise HTTPException(400, detail={"code": "INVALID_RESET_TOKEN", "message": "Invalid or expired reset token"})
    except ValueError:
        raise HTTPException(400, detail={"code": "INVALID_RESET_TOKEN", "message": "Invalid or expired reset token"})
    db_exec("UPDATE users SET password_hash=? WHERE id=?", [hash_password(password), row["user_id"]])
    db_exec("UPDATE password_reset_tokens SET used=1 WHERE token_hash=?", [token_hash])
    return {"ok": True}

@app.get("/api/auth/google/start")
async def google_start(request: Request) -> Response:
    client_id = os.getenv("CA_GOOGLE_CLIENT_ID", "")
    redirect_uri = os.getenv("CA_GOOGLE_REDIRECT_URI", "")
    if not client_id or not redirect_uri:
        return error_json("NOT_CONFIGURED", "Google OAuth is not configured", 501)
    state = secrets.token_urlsafe(24)
    request.session["google_oauth_state"] = state
    params = {"client_id": client_id, "redirect_uri": redirect_uri, "response_type": "code", "scope": "openid email profile", "state": state, "access_type": "offline", "prompt": "select_account"}
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))

@app.get("/api/auth/google/callback")
async def google_callback(request: Request, code: str | None = None, state: str | None = None, error: str | None = None) -> Response:
    if error:
        return error_json("OAUTH_ERROR", error, 400)
    expected = request.session.pop("google_oauth_state", None)
    if not code or not state or not expected or not hmac.compare_digest(str(state), str(expected)):
        return error_json("OAUTH_STATE_INVALID", "Invalid OAuth state", 400)
    client_id = os.getenv("CA_GOOGLE_CLIENT_ID", "")
    client_secret = os.getenv("CA_GOOGLE_CLIENT_SECRET", "")
    redirect_uri = os.getenv("CA_GOOGLE_REDIRECT_URI", "")
    if not client_id or not client_secret or not redirect_uri:
        return error_json("NOT_CONFIGURED", "Google OAuth is not configured", 501)
    try:
        token_resp = requests.post("https://oauth2.googleapis.com/token", data={"code": code, "client_id": client_id, "client_secret": client_secret, "redirect_uri": redirect_uri, "grant_type": "authorization_code"}, timeout=10)
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise RuntimeError("Google OAuth response did not contain an access token")
        profile_resp = requests.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        profile_resp.raise_for_status()
        profile = profile_resp.json()
        email = str(profile.get("email") or "").strip().lower()
        name = str(profile.get("name") or email.split("@")[0]).strip()
        if not email:
            raise RuntimeError("Google account email was not provided")
        row = db_exec("SELECT * FROM users WHERE email=? OR username=?", [email, email], "one")
        if row:
            uid = row["id"]
            if not row.get("email") or not row.get("full_name"):
                db_exec("UPDATE users SET email=COALESCE(email,?), full_name=COALESCE(full_name,?) WHERE id=?", [email, name, uid])
        else:
            uid = db_insert("INSERT INTO users(username,password_hash,email,created_at,full_name) VALUES(?,?,?,?,?)", [email, None, email, now_iso(), name])
            db_exec("INSERT INTO funds(user_id,available,updated_at) VALUES(?,?,?)", [uid, 0, now_iso()])
        request.session.clear()
        request.session["user_id"] = uid
        request.session["last_seen"] = time.time()
        request.session["remember_me"] = True
        request.session["selected_terminal"] = None
        return RedirectResponse("/post-login" if fitness_allowlisted({"email": email}) else "/terminal")
    except Exception as exc:
        record_error("google_oauth_failure", safe_text(exc))
        return error_json("OAUTH_FAILED", "Google sign-in could not be completed", 502)

# ---------------------------------------------------------------------------
# Bodybuilding / fitness terminal

@app.get("/api/fitness/profile")
async def fitness_profile_get(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    row=fitness_profile_row(user["id"])
    return {"profile":fitness_profile_payload(row),"recommendation":fitness_estimate_targets(float(row.get("height_cm") or 0),float(row.get("weight_kg") or 0),float(row.get("workout_frequency") or 0),row.get("goal") or "Muscle gain",row.get("age_years"),row.get("sex")) if row and row.get("height_cm") and row.get("weight_kg") else None}

@app.put("/api/fitness/profile")
async def fitness_profile_put(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    b=await request.json(); required=["height_cm","weight_kg","workout_frequency"]
    for k in required:
        if float(b.get(k) or 0)<=0: raise HTTPException(422,f"{k} must be greater than zero")
    name=str(b.get("name") or user.get("full_name") or user.get("email") or "Athlete")
    goal=str(b.get("goal") or "Muscle gain")
    age=float(b.get("age_years") or 0) or None
    sex=str(b.get("sex") or "").lower() or None
    rec=fitness_estimate_targets(float(b["height_cm"]),float(b["weight_kg"]),float(b["workout_frequency"]),goal,age,sex)
    calorie=float(b.get("calorie_target") or rec["calories"])
    protein=float(b.get("protein_target") or rec["protein"])
    fat=float(b.get("fat_target") or rec["fat"])
    carbs=float(b.get("carbs_target") or rec["carbs"])
    now=now_iso()
    vals=[user["id"],name,goal,float(b["height_cm"]),float(b["weight_kg"]),age,sex,calorie,protein,carbs,fat,float(b.get("diet_budget") or 0),float(b.get("workout_frequency") or 0),float(b.get("usual_big_cigs") or 0),float(b.get("usual_small_cigs") or 0),str(b.get("wake_time") or ""),float(b.get("sleep_target") or 8),1,now]
    db_exec("INSERT INTO fitness_profiles(user_id,name,goal,height_cm,weight_kg,age_years,sex,calorie_target,protein_target,carbs_target,fat_target,diet_budget,workout_frequency,usual_big_cigs,usual_small_cigs,wake_time,sleep_target,completed,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET name=excluded.name,goal=excluded.goal,height_cm=excluded.height_cm,weight_kg=excluded.weight_kg,age_years=excluded.age_years,sex=excluded.sex,calorie_target=excluded.calorie_target,protein_target=excluded.protein_target,carbs_target=excluded.carbs_target,fat_target=excluded.fat_target,diet_budget=excluded.diet_budget,workout_frequency=excluded.workout_frequency,usual_big_cigs=excluded.usual_big_cigs,usual_small_cigs=excluded.usual_small_cigs,wake_time=excluded.wake_time,sleep_target=excluded.sleep_target,completed=1,updated_at=excluded.updated_at",vals)
    row=fitness_profile_payload(fitness_profile_row(user["id"]))
    return {"profile":row,"recommendation":rec,"auto_targeted":not bool(b.get("calorie_target"))}

@app.get("/api/fitness/profile/recommend")
async def fitness_profile_recommend(height_cm: float = Query(...,gt=0), weight_kg: float = Query(...,gt=0), workout_frequency: float = Query(...,gt=0,le=7), goal: str = Query("Muscle gain"), age_years: float | None = Query(None,ge=13,le=100), sex: str | None = Query(None)) -> dict[str,Any]:
    if sex not in (None, "", "male", "female"): sex=None
    return {"recommendation":fitness_estimate_targets(height_cm,weight_kg,workout_frequency,goal,age_years,sex)}

@app.get("/api/fitness/foods/search")
async def fitness_food_search(q: str = Query(...,min_length=1,max_length=120), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    return {"query":q,"results":fitness_fetch_foods(q)}

@app.get("/api/fitness/foods/suggest")
async def fitness_food_suggest(q: str = Query("",max_length=80), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    return {"query":q,"suggestions":fitness_food_suggestions(q)}

@app.get("/api/fitness/diet")
async def fitness_diet_get(date: str = Query(...), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    items=db_exec("SELECT * FROM fitness_diet_entries WHERE user_id=? AND date=? ORDER BY COALESCE(meal_time,'99:99'),created_at",[user["id"],date],"all")
    s={k:sum(float(x.get(k) or 0) for x in items) for k in ("calories","protein","carbs","fat","fiber","sugar","sodium_mg","cholesterol_mg","calcium_mg","iron_mg","potassium_mg","vitamin_d_mcg","vitamin_b12_mcg")}
    return {"items":items,"summary":s}

@app.post("/api/fitness/diet")
async def fitness_diet_post(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    b=await request.json()
    return fitness_store_diet(user["id"],b)

@app.put("/api/fitness/diet/{entry_id}")
async def fitness_diet_edit(entry_id: str, request: Request,user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    b=await request.json(); fields=["food","quantity","meal_type","meal_time","calories","protein","carbs","fat","fiber","sugar","sodium_mg","cholesterol_mg","calcium_mg","iron_mg","potassium_mg","vitamin_d_mcg","vitamin_b12_mcg"]
    row=db_exec("SELECT * FROM fitness_diet_entries WHERE id=? AND user_id=?",[entry_id,user["id"]],"one")
    if not row: raise HTTPException(404,"Diet entry not found")
    vals=[]
    for f in fields:
        v=b.get(f,row.get(f))
        if f not in {"food","quantity","meal_type","meal_time"}: v=float(v or 0)
        vals.append(v)
    set_sql=",".join(f"{f}=?" for f in fields)
    db_exec(f"UPDATE fitness_diet_entries SET {set_sql} WHERE id=? AND user_id=?",vals+[entry_id,user["id"]])
    return {"ok":True,"item":db_exec("SELECT * FROM fitness_diet_entries WHERE id=? AND user_id=?",[entry_id,user["id"]],"one")}

@app.delete("/api/fitness/diet/{entry_id}")
async def fitness_diet_delete(entry_id: str,user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    db_exec("DELETE FROM fitness_diet_entries WHERE id=? AND user_id=?",[entry_id,user["id"]]); return {"ok":True}

def fitness_store_workout(user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    date=str(payload.get("date") or fitness_today()); name=str(payload.get("name") or "Workout").strip(); exercises=[]
    for ex in payload.get("exercises") or []:
        sets=fitness_parse_sets(ex.get("sets"));
        if sets and ex.get("exercise"): exercises.append({"exercise":str(ex["exercise"]).strip(),"sets":sets})
    if not exercises: raise HTTPException(422,"At least one exercise with valid sets is required")
    signature=json.dumps([(x["exercise"].lower(),tuple((round(s["weight"],3),s["reps"]) for s in x["sets"])) for x in exercises],sort_keys=True)
    existing=db_exec("SELECT w.id FROM fitness_workouts w WHERE w.user_id=? AND w.date=? AND lower(w.name)=lower(?) ORDER BY w.created_at DESC LIMIT 10",[user_id,date,name],"all")
    for w in existing:
        old=db_exec("SELECT exercise,sets_json FROM fitness_exercises WHERE workout_id=? ORDER BY created_at",[w["id"]],"all")
        old_sig=json.dumps([(x["exercise"].lower(),tuple((round(float(s.get("weight",0)),3),int(s.get("reps",0))) for s in json.loads(x["sets_json"]))) for x in old],sort_keys=True)
        if old_sig==signature:
            return {"ok":True,"workout_id":w["id"],"already_logged":True}
    wid=secrets.token_hex(12)
    db_exec("INSERT INTO fitness_workouts(id,user_id,date,name,notes,created_at) VALUES(?,?,?,?,?,?)",[wid,user_id,date,name,str(payload.get("notes") or ""),now_iso()])
    for ex in exercises:
        sets=ex["sets"]; vol=sum(s["weight"]*s["reps"] for s in sets); best=max(s["weight"] for s in sets); best_reps=max(s["reps"] for s in sets); e1rm=max(fitness_e1rm(s["weight"],s["reps"]) for s in sets)
        db_exec("INSERT INTO fitness_exercises(id,workout_id,user_id,exercise,sets_json,volume,best_weight,best_reps,e1rm,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",[secrets.token_hex(12),wid,user_id,ex["exercise"],json.dumps(sets),vol,best,best_reps,e1rm,now_iso()])
    return {"ok":True,"workout_id":wid,"already_logged":False,"exercise_count":len(exercises)}

@app.post("/api/fitness/workouts")
async def fitness_workout_post(request: Request,user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    return fitness_store_workout(user["id"], await request.json())

@app.post("/api/fitness/workouts/import-text")
async def fitness_workout_import_text(request: Request,user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    body=await request.json(); parsed=fitness_parse_natural_workout(str(body.get("text") or ""))
    if not parsed: return {"ok":False,"saved":False,"message":"No structured workout could be detected."}
    saved=fitness_store_workout(user["id"],parsed); return {"ok":True,"saved":True,"parsed":parsed,**saved}

@app.put("/api/fitness/workouts/{workout_id}")
async def fitness_workout_edit(workout_id: str, request: Request,user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    body=await request.json(); row=db_exec("SELECT * FROM fitness_workouts WHERE id=? AND user_id=?",[workout_id,user["id"]],"one")
    if not row: raise HTTPException(404,"Workout not found")
    parsed={"date":body.get("date") or row["date"],"name":body.get("name") or row["name"],"notes":body.get("notes") or "","exercises":body.get("exercises") or []}
    db_exec("DELETE FROM fitness_exercises WHERE workout_id=?",[workout_id])
    db_exec("UPDATE fitness_workouts SET date=?,name=?,notes=? WHERE id=? AND user_id=?",[parsed["date"],parsed["name"],parsed["notes"],workout_id,user["id"]])
    saved=fitness_store_workout(user["id"],parsed) if False else None
    for ex in parsed["exercises"]:
        sets=fitness_parse_sets(ex.get("sets"));
        if not sets or not ex.get("exercise"): continue
        vol=sum(s["weight"]*s["reps"] for s in sets); best=max(s["weight"] for s in sets); best_reps=max(s["reps"] for s in sets); e1rm=max(fitness_e1rm(s["weight"],s["reps"]) for s in sets)
        db_exec("INSERT INTO fitness_exercises(id,workout_id,user_id,exercise,sets_json,volume,best_weight,best_reps,e1rm,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)",[secrets.token_hex(12),workout_id,user["id"],str(ex["exercise"]).strip(),json.dumps(sets),vol,best,best_reps,e1rm,now_iso()])
    return {"ok":True,"workout_id":workout_id}

@app.delete("/api/fitness/workouts/{workout_id}")
async def fitness_workout_delete(workout_id: str,user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    db_exec("DELETE FROM fitness_workouts WHERE id=? AND user_id=?",[workout_id,user["id"]]); return {"ok":True}

@app.get("/api/fitness/workouts")
async def fitness_workouts_get(user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    sessions=db_exec("SELECT w.*,COUNT(e.id) exercise_count,COALESCE(SUM(e.volume),0) volume FROM fitness_workouts w LEFT JOIN fitness_exercises e ON e.workout_id=w.id WHERE w.user_id=? GROUP BY w.id ORDER BY w.date DESC,w.created_at DESC LIMIT 60",[user["id"]],"all")
    bestrows=db_exec("SELECT exercise,MAX(best_weight) best_weight,MAX(e1rm) e1rm FROM fitness_exercises WHERE user_id=? GROUP BY exercise ORDER BY e1rm DESC",[user["id"]],"all")
    for r in bestrows:
        rows=db_exec("SELECT sets_json FROM fitness_exercises WHERE user_id=? AND lower(exercise)=lower(?)",[user["id"],r["exercise"]],"all")
        max_set=(0.0,0)
        working=(0.0,0)
        for rr in rows:
            try:
                for ss in json.loads(rr["sets_json"]):
                    weight=float(ss.get("weight",0) or 0); reps=int(ss.get("reps",0) or 0)
                    if weight>max_set[0] or (weight==max_set[0] and reps>max_set[1]):
                        max_set=(weight,reps)
                    if reps>8 and weight>working[0]:
                        working=(weight,reps)
            except Exception: pass
        r["best_weight"],r["best_reps"]=max_set
        r["working_set_weight"],r["working_set_reps"]=working
    for srow in sessions:
        srow["exercises"]=db_exec("SELECT id,exercise,sets_json,volume,best_weight,best_reps,e1rm FROM fitness_exercises WHERE workout_id=? ORDER BY created_at",[srow["id"]],"all")
    return {"sessions":sessions,"prs":bestrows}

@app.get("/api/fitness/dashboard")
async def fitness_dashboard(user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    date=fitness_today(); profile=fitness_profile_row(user["id"])
    drow=db_exec("SELECT COALESCE(SUM(calories),0) calories,COALESCE(SUM(protein),0) protein,COALESCE(SUM(carbs),0) carbs,COALESCE(SUM(fat),0) fat,COALESCE(SUM(fiber),0) fiber FROM fitness_diet_entries WHERE user_id=? AND date=?",[user["id"],date],"one") or {}
    w=db_exec("SELECT w.id,w.name,COUNT(e.id) exercise_count,COALESCE(SUM(e.volume),0) volume FROM fitness_workouts w LEFT JOIN fitness_exercises e ON e.workout_id=w.id WHERE w.user_id=? AND w.date=? GROUP BY w.id ORDER BY w.created_at DESC LIMIT 1",[user["id"],date],"one")
    today_ex=db_exec("SELECT exercise,e1rm,best_weight,best_reps,volume FROM fitness_exercises WHERE user_id=? AND workout_id=?",[user["id"],w["id"]],"all") if w else []
    prs=db_exec("SELECT exercise,MAX(e1rm) e1rm FROM fitness_exercises WHERE user_id=? GROUP BY exercise",[user["id"]],"all")
    comparison=[]
    for ex in today_ex:
        last=db_exec("SELECT e.* FROM fitness_exercises e JOIN fitness_workouts w ON w.id=e.workout_id WHERE e.user_id=? AND lower(e.exercise)=lower(?) AND w.date<? ORDER BY w.date DESC,w.created_at DESC LIMIT 1",[user["id"],ex["exercise"],date],"one")
        best=db_exec("SELECT MAX(e1rm) best FROM fitness_exercises WHERE user_id=? AND lower(exercise)=lower(?)",[user["id"],ex["exercise"]],"one")
        comparison.append({"exercise":ex["exercise"],"today_e1rm":round(ex["e1rm"],1),"last_e1rm":round(last["e1rm"],1) if last else None,"best_e1rm":round(best["best"],1) if best and best.get("best") else None,"today":f"{round(ex['e1rm'])} e1RM","last":f"{round(last['e1rm'])} e1RM" if last else "—","best":f"{round(best['best'])} e1RM" if best and best.get('best') else "—"})
    dates=[r["date"] for r in db_exec("SELECT DISTINCT date FROM fitness_workouts WHERE user_id=? ORDER BY date DESC",[user["id"]],"all")]; streak=0; cur=datetime.fromisoformat(fitness_today()).date()
    for ds in dates:
        try:
            dd=datetime.fromisoformat(ds).date()
            if dd==cur: streak+=1; cur=cur-timedelta(days=1)
            elif dd==cur-timedelta(days=1): cur=dd-timedelta(days=1)
        except Exception: pass
    ratios={}
    if profile and profile.get("weight_kg"):
        wkg=float(profile["weight_kg"]); h=float(profile.get("height_cm") or 0)/100
        calories=float(drow.get("calories") or 0); protein=float(drow.get("protein") or 0); carbs=float(drow.get("carbs") or 0); fat=float(drow.get("fat") or 0)
        ratios={"bmi":round(wkg/(h*h),1) if h else None,"protein_per_kg":round(protein/wkg,2),"target_protein_per_kg":round(float(profile.get("protein_target") or 0)/wkg,2),"calories_per_kg":round(calories/wkg,1),"protein_calorie_pct":round((protein*4/max(calories,1))*100,1),"carb_calorie_pct":round((carbs*4/max(calories,1))*100,1),"fat_calorie_pct":round((fat*9/max(calories,1))*100,1),"calorie_progress_pct":round(calories/max(float(profile.get("calorie_target") or 1),1)*100,1),"macro_balance_pct":round(min(100,max(0,100-abs(100-(protein*4+carbs*4+fat*9)/max(float(profile.get("calorie_target") or 1),1)*100))),1)}
    quotes=[
      {"text":"Train hard enough to create a reason to grow, then recover enough to let it happen.","author":"Mike Mentzer.AI"},
      {"text":"Your logbook is the argument. Progressive numbers are the evidence.","author":"Mike Mentzer.AI"},
      {"text":"Consistency is a performance skill, not a mood.","author":"Mike Mentzer.AI"},
      {"text":"One excellent set can teach you more than five careless ones.","author":"Mike Mentzer.AI"}
    ]
    q=quotes[int(datetime.now(timezone.utc).timestamp()/30)%len(quotes)]
    return {"profile":fitness_profile_payload(profile),"nutrition":drow,"ratios":ratios,"workout":{**(w or {}),"prs":len(prs),"streak":streak,"comparison":comparison},"quote":q}

@app.post("/api/fitness/smoking")
async def fitness_smoking_post(request: Request,user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    b=await request.json(); date=str(b.get("date") or fitness_today()); smoked=1 if bool(b.get("smoked")) else 0; big=max(0,int(b.get("big_count") or 0)); small=max(0,int(b.get("small_count") or 0))
    db_exec("INSERT INTO fitness_smoking(id,user_id,date,smoked,big_count,small_count,created_at) VALUES(?,?,?,?,?,?,?) ON CONFLICT(user_id,date) DO UPDATE SET smoked=excluded.smoked,big_count=excluded.big_count,small_count=excluded.small_count",[secrets.token_hex(12),user["id"],date,smoked,big,small,now_iso()])
    return {"ok":True}

@app.get("/api/fitness/smoking")
async def fitness_smoking_get(user:dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    profile=fitness_profile_row(user["id"]) or {}; baseline_big=float(profile.get("usual_big_cigs") or 0); baseline_small=float(profile.get("usual_small_cigs") or 0); baseline_spend=baseline_big*28+baseline_small*15
    rows=db_exec("SELECT * FROM fitness_smoking WHERE user_id=? ORDER BY date DESC",[user["id"]],"all")
    saved=0; avoided=0
    for r in rows:
        actual=r["big_count"]*28+r["small_count"]*15; saved += max(0,baseline_spend-actual); avoided += max(0,int(round(baseline_big+baseline_small-r["big_count"]-r["small_count"])))
    price,src=fitness_chicken_price(); clean=sum(1 for r in rows if not r["smoked"]); reward={"eggs":int(saved//10),"chicken_grams":int(saved/price*1000) if price else 0,"chicken_price_per_kg":round(price,0),"source":src}
    cal=[]
    for i in range(29,-1,-1):
        d=(datetime.fromisoformat(fitness_today()).date()-timedelta(days=i)).isoformat(); r=next((x for x in rows if x["date"]==d),None); cal.append({"day":int(d[-2:]),"smoked":bool(r and r["smoked"]),"big":r["big_count"] if r else 0,"small":r["small_count"] if r else 0})
    return {"saved":round(saved,2),"avoided":avoided,"clean_days":clean,"calendar":cal,"reward":reward}

@app.post("/api/fitness/ai")
async def fitness_ai(request: Request,user:dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    b=await request.json(); msg=str(b.get("message") or "").strip()
    if not msg: raise HTTPException(422,"Message is required")
    profile=fitness_profile_row(user["id"]) or {}
    recent_workouts=db_exec("SELECT w.date,w.name,e.exercise,e.e1rm,e.best_weight,e.best_reps FROM fitness_workouts w JOIN fitness_exercises e ON e.workout_id=w.id WHERE w.user_id=? ORDER BY w.date DESC LIMIT 20",[user["id"]],"all")
    recent_diet=db_exec("SELECT date,food,calories,protein,carbs,fat FROM fitness_diet_entries WHERE user_id=? ORDER BY date DESC,created_at DESC LIMIT 30",[user["id"]],"all")
    saved_workout=None; saved_diet=None

    # Explicit write actions are parsed separately from the coaching answer. This
    # fixes the old behavior where Gemini could say it would add something but the
    # browser never actually wrote it to the tracker.
    if re.search(r"\b(add|log|track|record|ate|eaten|had|include|put|did|completed|finished|performed)\b",msg,re.I):
        actions=fitness_ai_action_extract(msg).get("actions") or []
        for action in actions:
            try:
                if action.get("type")=="workout" and action.get("exercises"):
                    payload={"date":action.get("date") or fitness_today(),"name":action.get("name") or "Workout","notes":action.get("notes") or "Imported from Mike Mentzer.AI conversation","exercises":action.get("exercises") or []}
                    saved_workout=fitness_store_workout(user["id"],payload)
                elif action.get("type")=="diet" and action.get("food"):
                    payload={"date":fitness_today(),"food":action.get("food"),"quantity":action.get("quantity") or "1 serving","meal_type":action.get("meal_type") or "Other","meal_time":action.get("meal_time") or "",
                             "calories":action.get("calories"),"protein":action.get("protein"),"carbs":action.get("carbs"),"fat":action.get("fat"),"fiber":action.get("fiber"),"source":"Gemini estimate"}
                    saved_diet=fitness_store_diet(user["id"],payload)
            except Exception as exc:
                record_error("fitness_ai_action_save",safe_text(exc),user_id=user["id"])

    prompt=("You are Mike Mentzer.AI inside a bodybuilding progress app. Be practical, concise and evidence-aware. "
            "Use the supplied profile/logs. Do not invent logged data. If the user explicitly asked to add/log food or a workout, "
            "confirm what was actually saved only when saved data is supplied. For training advice emphasize progressive overload, "
            "high effort, adequate recovery and safety. For nutrition, distinguish targets from actual intake. This is not medical advice.\n\n"
            "PROFILE:"+json.dumps(profile)+"\nWORKOUTS:"+json.dumps(recent_workouts)[:10000]+"\nDIET:"+json.dumps(recent_diet)[:9000]+"\nQUESTION:"+msg)
    r=gemini_text(prompt,18000)
    if not r.get("available"):
        return {"available":False,"text":"Gemini is not configured or is temporarily unavailable. Your confirmed tracker writes are still saved.","saved_workout":saved_workout,"saved_diet":saved_diet,"saved_actions":{"workout":saved_workout,"diet":saved_diet}}
    return {"available":True,"text":r.get("text",""),"model":r.get("model"),"saved_workout":saved_workout,"saved_diet":saved_diet,"saved_actions":{"workout":saved_workout,"diet":saved_diet}}

@app.get("/api/fitness/ai/status")
async def fitness_ai_status(user:dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not fitness_allowlisted(user): raise HTTPException(403,"Fitness terminal is not enabled for this account")
    profile=fitness_profile_row(user["id"]) or {}; return {"readiness":"Ready" if GEMINI_API_KEY else "AI key missing","recovery":f"{profile.get('sleep_target') or 8:g}h target sleep"}

# ---------------------------------------------------------------------------
# User-specific settings / watchlists

def user_watchlist_symbols(user_id: int) -> list[str]:
    """Return the authenticated user's watchlist symbols across both supported schemas.

    Older CA Trader databases store instruments in ``watchlists`` directly;
    newer databases use ``watchlist_groups`` + ``watchlist_members``.  The
    application must not require a table that may not exist in an existing
    production database.
    """
    symbols: list[str] = []
    # Current grouped-watchlist schema.
    try:
        rows = db_exec(
            "SELECT DISTINCT wm.symbol "
            "FROM watchlist_members wm "
            "JOIN watchlist_groups wg ON wg.id=wm.watchlist_id "
            "WHERE wg.user_id=? AND wm.symbol IS NOT NULL AND TRIM(wm.symbol)<>''",
            [user_id],
            "all",
        )
        symbols.extend(str(r["symbol"]).strip().upper() for r in rows if r.get("symbol"))
    except Exception:
        pass
    # Legacy schema kept for compatibility with older production databases.
    try:
        rows = db_exec(
            "SELECT DISTINCT symbol FROM watchlists "
            "WHERE user_id=? AND symbol IS NOT NULL AND TRIM(symbol)<>''",
            [user_id],
            "all",
        )
        symbols.extend(str(r["symbol"]).strip().upper() for r in rows if r.get("symbol"))
    except Exception:
        pass
    return list(dict.fromkeys(symbols))


@app.get("/api/watchlists")
async def get_watchlists(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    groups = db_exec("SELECT * FROM watchlist_groups WHERE user_id=? ORDER BY id", [user["id"]], "all")
    if not groups:
        legacy=db_exec("SELECT * FROM watchlists WHERE user_id=? ORDER BY id",[user["id"]],"all")
        db_exec("INSERT OR IGNORE INTO watchlist_groups(user_id,name,created_at) VALUES(?,?,?)",[user["id"],"Default",now_iso()])
        g=db_exec("SELECT * FROM watchlist_groups WHERE user_id=? AND name='Default'",[user["id"]],"one")
        for r in legacy: db_exec("INSERT OR IGNORE INTO watchlist_members(watchlist_id,symbol,instrument_key,display_name,position,created_at) VALUES(?,?,?,?,?,?)",[g["id"],r["symbol"],r.get("instrument_key"),r["symbol"],db_exec("SELECT COALESCE(MAX(position),-1)+1 AS p FROM watchlist_members WHERE watchlist_id=?",[g["id"]],"one")["p"],r["created_at"]])
        groups=db_exec("SELECT * FROM watchlist_groups WHERE user_id=? ORDER BY id",[user["id"]],"all")
    for g in groups: g["items"]=db_exec("SELECT * FROM watchlist_members WHERE watchlist_id=? ORDER BY position,id",[g["id"]],"all")
    return {"items":groups}

@app.post("/api/watchlists")
async def add_watchlist(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    body=await request.json();name=str(body.get("name","")).strip()
    if not 1<=len(name)<=40: raise HTTPException(422,"Watchlist name must be 1-40 characters")
    db_exec("INSERT OR IGNORE INTO watchlist_groups(user_id,name,created_at) VALUES(?,?,?)",[user["id"],name,now_iso()])
    return await get_watchlists(request,user)

@app.patch("/api/watchlists/{watchlist_id}")
async def update_watchlist(watchlist_id: int, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    body = await request.json()
    name = str(body.get("name", "")).strip()
    if not 1 <= len(name) <= 40:
        raise HTTPException(422, "Watchlist name must be 1-40 characters")
    exists = db_exec("SELECT id FROM watchlist_groups WHERE id=? AND user_id=?", [watchlist_id, user["id"]], "one")
    if not exists:
        raise HTTPException(404, "Watchlist not found")
    conflict = db_exec("SELECT id FROM watchlist_groups WHERE user_id=? AND name=? AND id<>?", [user["id"], name, watchlist_id], "one")
    if conflict:
        raise HTTPException(409, "A watchlist with that name already exists")
    db_exec("UPDATE watchlist_groups SET name=? WHERE id=? AND user_id=?", [name, watchlist_id, user["id"]])
    return await get_watchlists(request, user)

@app.post("/api/watchlists/{watchlist_id}/reorder")
async def reorder_watchlist(watchlist_id: int, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    body = await request.json()
    symbol = str(body.get("symbol", "")).strip().upper()
    direction = str(body.get("direction", "")).strip().lower()
    if direction not in {"up", "down"} or not symbol:
        raise HTTPException(422, "Symbol and direction (up/down) are required")
    group = db_exec("SELECT id FROM watchlist_groups WHERE id=? AND user_id=?", [watchlist_id, user["id"]], "one")
    if not group:
        raise HTTPException(404, "Watchlist not found")
    rows = db_exec("SELECT id,symbol,position FROM watchlist_members WHERE watchlist_id=? ORDER BY position,id", [watchlist_id], "all")
    idx = next((i for i, row in enumerate(rows) if row["symbol"].upper() == symbol), None)
    if idx is None:
        raise HTTPException(404, "Watchlist item not found")
    target = idx - 1 if direction == "up" else idx + 1
    if target < 0 or target >= len(rows):
        return await get_watchlists(request, user)
    a, b = rows[idx], rows[target]
    db_exec("UPDATE watchlist_members SET position=? WHERE id=?", [b["position"], a["id"]])
    db_exec("UPDATE watchlist_members SET position=? WHERE id=?", [a["position"], b["id"]])
    return await get_watchlists(request, user)

@app.delete("/api/watchlists/{watchlist_id}")
async def delete_watchlist(watchlist_id:int,request:Request,user:dict[str,Any]=Depends(require_user))->dict[str,Any]:
    db_exec("DELETE FROM watchlist_groups WHERE id=? AND user_id=?",[watchlist_id,user["id"]]);return {"ok":True}

@app.post("/api/watchlists/{watchlist_id}/items")
async def add_watchlist_item(watchlist_id:int,request:Request,user:dict[str,Any]=Depends(require_user))->dict[str,Any]:
    g=db_exec("SELECT id FROM watchlist_groups WHERE id=? AND user_id=?",[watchlist_id,user["id"]],"one")
    if not g: raise HTTPException(404,"Watchlist not found")
    b=await request.json();symbol=str(b.get("symbol","")).strip().upper()
    if not symbol: raise HTTPException(422,"Instrument symbol is required")
    key=b.get("instrument_key");meta=b
    if not key:
        try:key,meta=UPSTOX.resolve_instrument(symbol)
        except Exception:pass
    db_exec("INSERT OR IGNORE INTO watchlist_members(watchlist_id,symbol,instrument_key,instrument_type,exchange,display_name,position,created_at) VALUES(?,?,?,?,?,?,?,?)",[watchlist_id,symbol,key,meta.get("instrument_type"),meta.get("exchange"),meta.get("name") or meta.get("trading_symbol") or symbol,db_exec("SELECT COALESCE(MAX(position),-1)+1 AS p FROM watchlist_members WHERE watchlist_id=?",[watchlist_id],"one")["p"],now_iso()])
    return await get_watchlists(request,user)

@app.delete("/api/watchlists/{watchlist_id}/items/{symbol}")
async def delete_watchlist_item(watchlist_id:int,symbol:str,request:Request,user:dict[str,Any]=Depends(require_user))->dict[str,Any]:
    db_exec("DELETE FROM watchlist_members WHERE watchlist_id=? AND symbol=?",[watchlist_id,symbol.upper()]);return {"ok":True}

@app.get("/api/instruments/search")
async def instrument_search(q:str=Query("",max_length=50),user:dict[str,Any]=Depends(require_user))->dict[str,Any]:
    try:
        p=UPSTOX.search_instruments(q.strip() or "NIFTY",exchanges="NSE,BSE,MCX",segments="ALL");rows=p.get("data") or []
        return {"items":[{"symbol":r.get("trading_symbol") or r.get("symbol") or r.get("name"),"name":r.get("name") or r.get("trading_symbol") or r.get("symbol"),"instrument_key":r.get("instrument_key") or r.get("instrument_token"),"instrument_type":r.get("instrument_type") or r.get("instrument_type_code"),"exchange":r.get("exchange") or r.get("exchange_segment"),"expiry":r.get("expiry"),"strike_price":r.get("strike_price"),"option_type":r.get("option_type")} for r in rows[:30]],"provider":"upstox","timestamp":now_iso()}
    except Exception as exc:return error_json("INSTRUMENT_SEARCH_UNAVAILABLE",safe_text(exc),503)

# ---------------------------------------------------------------------------
# Market APIs
# ---------------------------------------------------------------------------

@app.get("/api/market/provider-health")
async def market_provider_health(user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    if not user: raise HTTPException(401,"Authentication required")
    return {"upstox":PROVIDER_HEALTH.get("upstox",{}),"websocket":{"connected":bool(MARKET_STREAM.connected),"subscriptions":sum(len(v) for v in MARKET_STREAM.desired.values()),"last_ltp_count":len(MARKET_STREAM.last_ltp)},"api_rate_limit_per_minute":RATE_LIMIT_PER_MINUTE,"timestamp":now_iso()}

@app.get("/api/market/quote/{instrument}")
async def market_quote(instrument: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        key_hint = str(instrument).upper()
        if key_hint.startswith("MCX") or "COM" in key_hint:
            session = market_session("MCX")
            if not session.get("active"):
                cached = CACHE.get(f"closed-quote:{key_hint}")
                if cached is not None:
                    return {**cached, "market_session": session, "fresh": False}
                # Resolve once if needed, but do not poll/rotate credentials while closed.
                key, meta = UPSTOX.resolve_instrument(instrument)
                q = UPSTOX.quote(instrument)
                CACHE.set(f"closed-quote:{key_hint}", q, 300.0)
                return {**q, "market_session": session, "fresh": False}
        q = UPSTOX.quote(instrument)
        if str(q.get("exchange") or "").upper().find("MCX") >= 0 or str(q.get("instrument_key") or "").upper().startswith("MCX"):
            CACHE.set(f"closed-quote:{key_hint}", q, 300.0)
        return q
    except ProviderRateLimited as exc:
        return error_json("PROVIDER_RATE_LIMITED", str(exc), 429)
    except Exception as exc:
        return error_json("MARKET_DATA_UNAVAILABLE", safe_text(exc), 503)


@app.get("/api/market/quotes")
async def market_quotes(instruments: str = Query("", max_length=12000), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    symbols=[x.strip() for x in instruments.split(",") if x.strip()]
    if not symbols: return {"items":[],"provider":"upstox","timestamp":now_iso()}
    try:
        return {"items":UPSTOX.quotes(symbols),"provider":"upstox","timestamp":now_iso()}
    except Exception as exc:
        return error_json("MARKET_DATA_UNAVAILABLE", safe_text(exc), 503)

@app.get("/api/market/ltp/{instrument}")
async def market_ltp(instrument: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        return UPSTOX.ltp(instrument)
    except Exception as exc:
        return error_json("MARKET_DATA_UNAVAILABLE", safe_text(exc), 503)


def _candle_ist_date(candle: dict[str, Any]) -> datetime.date | None:
    """Return a candle's calendar date in Asia/Kolkata regardless of source format."""
    value = candle.get("timestamp") if isinstance(candle, dict) else None
    if value is None:
        return None
    try:
        if isinstance(value, (int, float)):
            dt = datetime.fromtimestamp(float(value) / 1000.0, tz=timezone.utc)
        else:
            raw = str(value).replace("Z", "+00:00")
            dt = datetime.fromisoformat(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=IST)
        return dt.astimezone(IST).date()
    except Exception:
        return None


def _candle_timestamp_ms(value: Any) -> int:
    try:
        if value is None:
            return 0
        if isinstance(value, (int, float)):
            n=float(value)
            return int(n if n > 1e12 else n*1000)
        raw=str(value).replace('Z','+00:00')
        dt=datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt=dt.replace(tzinfo=IST)
        return int(dt.timestamp()*1000)
    except Exception:
        return 0


def _canonical_candle(row: dict[str, Any]) -> dict[str, Any] | None:
    if not isinstance(row, dict):
        return None
    ts=_candle_timestamp_ms(row.get('timestamp'))
    if not ts:
        return None
    out=dict(row)
    out['timestamp']=datetime.fromtimestamp(ts/1000.0, tz=timezone.utc).isoformat()
    return out


def _merge_candle_series(*series: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Merge candle arrays by normalized epoch timestamp; never let old text-formatted timestamps win."""
    by_ts: dict[int, dict[str, Any]] = {}
    for rows in series:
        for row in rows or []:
            c=_canonical_candle(row)
            if c:
                by_ts[_candle_timestamp_ms(c['timestamp'])]=c
    return [by_ts[k] for k in sorted(by_ts)]


def _previous_weekday(day: datetime.date) -> datetime.date:
    d=day-timedelta(days=1)
    while d.weekday() >= 5:
        d-=timedelta(days=1)
    return d


def _latest_completed_session_date(segment: str, now: datetime) -> datetime.date:
    """Return the latest exchange session date that is complete/usable right now, IST."""
    if now.weekday() >= 5:
        return _previous_weekday(now.date())
    close_txt='23:00' if segment.upper() in {'MCX','COM'} else '15:30'
    close_t=datetime.strptime(close_txt,'%H:%M').time()
    if now.time() >= close_t:
        return now.date()
    return _previous_weekday(now.date())


def _latest_candle_date(candles: list[dict[str, Any]]) -> datetime.date | None:
    if not candles:
        return None
    # input is chronologically sorted by _merge_candle_series
    return _candle_ist_date(candles[-1])


def analysis_candles_robust(instrument: str, timeframe: str, days: int) -> list[dict[str, Any]]:
    """Fetch a fresh, range-appropriate Upstox candle series with minimal upstream calls."""
    tf=timeframe
    now=datetime.now(IST)
    key, meta = UPSTOX.resolve_instrument(instrument)
    segment=classify_instrument_segment(instrument, meta, key)
    active=bool(market_session(segment, now).get('active'))
    target_day=_latest_completed_session_date(segment, now)
    cache_key=f"analysis-candles-r20:{instrument}:{tf}:{days}:{target_day.isoformat()}:{'open' if active else 'closed'}"
    cached=CACHE.get(cache_key)
    if cached is not None and cached:
        return cached

    # One normal candle call is enough in the common path: it independently fetches
    # historical and intraday data, so a temporary failure of either Upstox endpoint
    # no longer blanks the chart. Exact-session probing is only used when the returned
    # history is actually missing the expected completed session.
    try:
        out=_merge_candle_series(UPSTOX.candles(instrument, '1' if tf=='1D' else '1' if tf=='60m' else tf[:-1], 'days' if tf=='1D' else 'hours' if tf=='60m' else 'minutes', days=min(days,365) if tf=='1D' else min(days,90) if tf=='60m' else min(days,365)))
    except Exception as exc:
        log.warning("Primary candle series failed for %s/%s: %s", instrument, tf, safe_text(exc))
        out=[]

    # Only spend extra requests when the primary series is empty or stale. For an open
    # session, current-day intraday data can make the series fresh even if the historical
    # endpoint is one session behind.
    latest=_latest_candle_date(out)
    if not out or (latest is not None and latest < target_day):
        interval='1' if tf=='60m' else '1' if tf=='1D' else tf[:-1]
        unit='hours' if tf=='60m' else 'days' if tf=='1D' else 'minutes'
        probe=target_day
        for _ in range(2 if not out else 1):
            try:
                exact=UPSTOX.candles_between(instrument,interval,unit,probe,probe)
                if exact:
                    out=_merge_candle_series([out, exact])
                    latest=_latest_candle_date(out)
                    if latest == target_day:
                        break
            except ProviderRateLimited:
                break
            except Exception as exc:
                log.debug("Exact session probe failed for %s/%s/%s: %s", instrument,tf,probe,safe_text(exc))
            probe=_previous_weekday(probe)

    if not out:
        raise ProviderUnavailable(f"No historical candles returned for {instrument} ({tf})")
    CACHE.set(cache_key,out,3.0 if active else 10.0)
    return out

def _merge_live_quote_into_candles(instrument: str, timeframe: str, candles: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    """Overlay the latest Upstox LTP on the current candle while the market is open.

    Historical candles remain the source of truth after close; during the active
    session the latest quote keeps the visible chart synchronized with the live LTP.
    """
    try:
        key_for_session, meta_for_session = UPSTOX.resolve_instrument(instrument)
        segment = classify_instrument_segment(instrument, meta_for_session, key_for_session)
        session = market_session(segment)
        if not session.get("active"):
            return candles, None
        q = UPSTOX.quote(instrument)
        ltp = q.get("ltp")
        if ltp is None or not candles:
            return candles, q
        ltp=float(ltp); now_ms=int(datetime.now(IST).timestamp()*1000)
        def ts_ms(v):
            if v is None: return 0
            if isinstance(v,(int,float)): return float(v)
            try:
                d=datetime.fromisoformat(str(v).replace('Z','+00:00'))
                if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
                return d.timestamp()*1000
            except Exception: return 0
        interval_ms = 86400000 if timeframe=="1D" else 3600000 if timeframe=="60m" else max(60000, int(timeframe[:-1])*60000)
        last=candles[-1]
        last_ts=ts_ms(last.get("timestamp"))
        bucket = (now_ms//interval_ms)*interval_ms
        # For intraday NSE, keep the day aligned to the 09:15 market anchor.
        if timeframe!="1D" and segment=="NSE_EQ":
            d=datetime.now(IST).replace(hour=9,minute=15,second=0,microsecond=0)
            anchor=int(d.timestamp()*1000)
            if now_ms>=anchor: bucket=anchor+((now_ms-anchor)//interval_ms)*interval_ms
        if last_ts and (last_ts//interval_ms)==(bucket//interval_ms):
            last["close"]=ltp; last["high"]=max(float(last.get("high") or ltp),ltp); last["low"]=min(float(last.get("low") or ltp),ltp)
        else:
            candles.append({"timestamp":datetime.fromtimestamp(bucket/1000,tz=timezone.utc).isoformat(),"open":ltp,"high":ltp,"low":ltp,"close":ltp,"volume":0.0})
        return candles, q
    except Exception as exc:
        log.debug("Live candle overlay unavailable for %s: %s", instrument, safe_text(exc))
        return candles, None

@app.get("/api/market/candles/{instrument}")
async def market_candles(instrument: str, timeframe: str = Query("15m", pattern=r"^(1m|3m|5m|15m|30m|60m|1D)$"), days: int = Query(7, ge=1, le=3650), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        # One authoritative range-safe path for every chart request.
        key_for_session, meta_for_session = UPSTOX.resolve_instrument(instrument)
        segment = classify_instrument_segment(instrument, meta_for_session, key_for_session)
        candles = analysis_candles_robust(instrument, timeframe, days)
        candles, live_quote = _merge_live_quote_into_candles(instrument, timeframe, candles)
        session = market_session(segment)
        latest_candle = candles[-1] if candles else None
        now = datetime.now(IST)
        expected = _latest_completed_session_date(segment, now)
        latest_date = _candle_ist_date(latest_candle) if latest_candle else None
        stale = bool(latest_date is not None and latest_date < expected) or (not candles)
        return JSONResponse({"instrument": instrument, "timeframe": timeframe, "candles": candles, "provider": "upstox", "timestamp": now_iso(), "live": bool(live_quote and live_quote.get("ltp") is not None), "live_quote": live_quote, "market_session": session, "latest_candle_ist": latest_date.isoformat() if latest_date else None, "latest_session_ist": expected.isoformat(), "stale": stale, "data_state": "LIVE" if live_quote and live_quote.get("ltp") is not None else "EOD"}, headers={"Cache-Control":"no-store, no-cache, must-revalidate, max-age=0", "Pragma":"no-cache", "Expires":"0"})
    except ProviderRateLimited as exc:
        return error_json("UPSTOX_RATE_LIMITED", safe_text(exc), 429)
    except ProviderUnavailable as exc:
        msg=safe_text(exc)
        code="UPSTOX_AUTH_FAILED" if "authentication failed" in msg.lower() else "CANDLES_UNAVAILABLE"
        return error_json(code, msg, 503)
    except Exception as exc:
        log.exception("Unhandled candle endpoint failure for %s", instrument)
        return error_json("CANDLES_UNAVAILABLE", safe_text(exc), 503)


@app.get("/api/market/candles/diagnostics")
async def market_candles_diagnostics(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    """Non-secret chart diagnostics: confirms token configuration and upstream connectivity."""
    configured = bool(UPSTOX_ACCESS_TOKENS or UPSTOX_ACCESS_TOKEN)
    result = {"provider":"upstox", "token_configured":configured, "token_count":len(UPSTOX_ACCESS_TOKENS), "status":"configured" if configured else "missing_token"}
    if not configured:
        return result
    try:
        # A cheap instrument lookup validates auth without exposing the token.
        payload = UPSTOX.search_instruments("NIFTY", exchanges="NSE", segments="INDEX")
        result.update({"status":"healthy", "instrument_search_results":len(payload.get("data") or [])})
    except Exception as exc:
        result.update({"status":"error", "message":safe_text(exc)})
    return result

@app.get("/api/market/depth/{instrument}")
async def market_depth(instrument: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        return UPSTOX.depth(instrument)
    except Exception as exc:
        return error_json("DEPTH_UNAVAILABLE", safe_text(exc), 503)


UPSTOX_NSE_INSTRUMENTS_URL = "https://assets.upstox.com/market-quote/instruments/exchange/NSE.json.gz"
_market_mover_instruments: list[tuple[str,str]] = []
_market_mover_instruments_loaded_at: float = 0.0
_market_mover_snapshot: tuple[float,list[dict[str,Any]]] | None = None

def _load_market_mover_instruments() -> list[tuple[str,str]]:
    global _market_mover_instruments, _market_mover_instruments_loaded_at
    if _market_mover_instruments and (time.time()-_market_mover_instruments_loaded_at) < 86400:
        return _market_mover_instruments
    try:
        r = requests.get(UPSTOX_NSE_INSTRUMENTS_URL, timeout=25, headers={"Accept":"application/json"})
        r.raise_for_status()
        payload = json.loads(gzip.decompress(r.content).decode("utf-8"))
        rows = payload if isinstance(payload,list) else payload.get("data",[])
        out=[]
        seen=set()
        for row in rows:
            if str(row.get("segment")) != "NSE_EQ": continue
            if str(row.get("instrument_type")) not in {"EQ","BE"}: continue
            key=row.get("instrument_key"); sym=row.get("trading_symbol")
            if key and sym and key not in seen:
                seen.add(key); out.append((str(key),str(sym)))
        if out:
            _market_mover_instruments=out
            _market_mover_instruments_loaded_at=time.time()
    except Exception as exc:
        log.warning("Unable to refresh Upstox NSE instrument master for market movers: %s", safe_text(exc))
    return _market_mover_instruments

def _full_market_mover_snapshot() -> list[dict[str,Any]]:
    global _market_mover_snapshot
    if _market_mover_snapshot and (time.time()-_market_mover_snapshot[0]) < 30:
        return _market_mover_snapshot[1]
    instruments=_load_market_mover_instruments()
    if not instruments:
        return []
    rows=[]
    # Upstox Full Market Quotes accepts up to 500 instruments per request; use the
    # instrument master directly so we do not perform one search request per symbol.
    for i in range(0,len(instruments),500):
        keys=[k for k,_ in instruments[i:i+500]]
        try:
            payload=UPSTOX._get("/market-quote/quotes", {"instrument_key":",".join(keys)}, ttl=30.0, cache_key=f"market_movers_batch:{i}:{len(keys)}")
            data=payload.get("data") or {}
            for key, sym in instruments[i:i+500]:
                raw=data.get(key)
                if not raw: continue
                try:
                    ltp=float(raw.get("last_price") or 0); cp=float(raw.get("close_price") or raw.get("ohlc",{}).get("close") or 0)
                    net=float(raw.get("net_change") or (ltp-cp if cp else 0)); ch=(net/cp*100) if cp else 0.0
                    vol=float(raw.get("volume") or 0)
                    rows.append({"symbol":sym,"instrument_key":key,"ltp":ltp,"change":net,"change_pct":ch,"volume":vol,"turnover":vol*ltp,"upper_circuit":raw.get("upper_circuit_limit"),"lower_circuit":raw.get("lower_circuit_limit"),"timestamp":raw.get("timestamp")})
                except Exception: continue
        except Exception as exc:
            log.warning("Market mover batch %s failed: %s", i, safe_text(exc))
    _market_mover_snapshot=(time.time(),rows)
    return rows

@app.get("/api/market/movers")
async def market_movers(category: str = "gainers", limit: int = Query(10, ge=5, le=20), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    cat=category.lower().replace(" ","_")
    allowed={"gainers","losers","high_volume","unusual_volume","turnover"}
    if cat not in allowed: raise HTTPException(422,"Unsupported market mover category")
    try:
        items=_full_market_mover_snapshot()
        if cat=="gainers": items.sort(key=lambda x:x["change_pct"],reverse=True)
        elif cat=="losers": items.sort(key=lambda x:x["change_pct"])
        elif cat=="high_volume": items.sort(key=lambda x:x["volume"],reverse=True)
        elif cat=="turnover": items.sort(key=lambda x:x["turnover"],reverse=True)
        else:
            positive=[x["volume"] for x in items if x["volume"]>0]
            avg=sum(positive)/max(1,len(positive)); items=[x for x in items if x["volume"]>=avg*2]; items.sort(key=lambda x:x["volume"],reverse=True)
        return {"category":cat,"items":items[:limit],"universe":"Upstox NSE equity instrument master","universe_count":len(_load_market_mover_instruments()),"provider":"upstox","timestamp":now_iso(),"fresh":True,"cache_seconds":30}
    except Exception as exc:
        return error_json("MARKET_MOVERS_UNAVAILABLE",safe_text(exc),503)

@app.get("/api/market/session")
async def market_session_api(segment: str = "NSE_EQ", user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return market_session(segment)


@app.get("/api/market/status/{exchange}")
async def market_status(exchange: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        payload = UPSTOX._get(f"/market/status/{quote(exchange, safe='')}", {}, ttl=5.0)
        return {"exchange": exchange, "data": payload.get("data", payload), "provider": "upstox", "timestamp": now_iso()}
    except Exception as exc:
        return error_json("MARKET_STATUS_UNAVAILABLE", safe_text(exc), 503)

# ---------------------------------------------------------------------------
# Analysis APIs
# ---------------------------------------------------------------------------

@app.get("/api/analysis/technical/{instrument}")
async def analysis_technical(instrument: str, timeframe: str = "15m", user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        unit = "hours" if timeframe == "60m" else "minutes"
        interval = "1" if timeframe == "60m" else timeframe[:-1]
        days=30 if timeframe in {"1m","3m","5m","15m"} else 90 if timeframe in {"30m","60m"} else 365
        candles = analysis_candles_robust(instrument, timeframe, days)
        return {"instrument": instrument, "timeframe": timeframe, "technical": technical_analysis(candles), "patterns": detect_candlestick_patterns(candles, timeframe), "provider": "upstox", "timestamp": now_iso()}
    except Exception as exc:
        return error_json("TECHNICAL_UNAVAILABLE", safe_text(exc), 503)


@app.get("/api/analysis/technical-mtf/{instrument}")
async def analysis_technical_mtf(instrument: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    def one(tf: str) -> dict[str,Any]:
        try:
            unit="days" if tf=="1D" else "hours" if tf=="60m" else "minutes"
            interval="1" if tf in {"1D","60m"} else tf[:-1]
            days=30 if tf in {"1m","3m","5m","15m"} else 90 if tf in {"30m","60m"} else 365
            candles=analysis_candles_robust(instrument, tf, days)
            tech=technical_analysis(candles)
            return {"timeframe":tf,"signal":"BUY" if tech.get("trend")=="BUY" else "SELL" if tech.get("trend")=="SELL" else "NEUTRAL","technical":tech}
        except Exception as exc:
            return {"timeframe":tf,"signal":"N/A","error":safe_text(exc)}
    tfs=["1m","3m","5m","15m","30m","60m","1D"]
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(one,tfs))
    return {"instrument":instrument,"items":rows,"provider":"upstox","timestamp":now_iso()}

@app.get("/api/analysis/structure/{instrument}")
async def analysis_structure(instrument: str, timeframe: str = "5m", from_date: str | None = None, to_date: str | None = None, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        unit="days" if timeframe=="1D" else "hours" if timeframe=="60m" else "minutes"; interval="1" if timeframe in {"1D","60m"} else timeframe[:-1]
        days=30 if timeframe in {"1m","3m","5m","15m"} else 90 if timeframe in {"30m","60m"} else 365
        if from_date and to_date:
            candles=UPSTOX.candles_between(instrument,interval,unit,datetime.fromisoformat(from_date).date(),datetime.fromisoformat(to_date).date())
        else:
            candles=analysis_candles_robust(instrument,timeframe,days)
        window=candles[-10:] if not (from_date or to_date) else candles[-50:]
        ta=technical_analysis(window if len(window)>=5 else candles)
        pats=detect_candlestick_patterns(window,timeframe)
        highs=[float(c["high"]) for c in window if c.get("high") is not None]; lows=[float(c["low"]) for c in window if c.get("low") is not None]
        hh=sum(1 for i in range(1,len(highs)) if highs[i]>highs[i-1]); hl=sum(1 for i in range(1,len(lows)) if lows[i]>lows[i-1])
        lh=sum(1 for i in range(1,len(highs)) if highs[i]<highs[i-1]); ll=sum(1 for i in range(1,len(lows)) if lows[i]<lows[i-1])
        structure="Higher Highs / Higher Lows" if hh+hl>lh+ll+1 else "Lower Highs / Lower Lows" if lh+ll>hh+hl+1 else "Range / Mixed Structure"
        last=window[-1] if window else {}; prev=window[-2] if len(window)>1 else last; move=((float(last.get("close") or 0)-float(prev.get("close") or 0))/float(prev.get("close") or 1)*100) if prev.get("close") else 0
        reversal=any(p.get("pattern") in {"Hammer","Shooting Star","Bullish Engulfing","Bearish Engulfing"} for p in pats)
        outcome="Bullish continuation" if ta.get("trend")=="BUY" and not reversal else "Bearish continuation" if ta.get("trend")=="SELL" and not reversal else "Potential trend reversal / confirmation required" if reversal else "Range / wait for breakout"
        return {"instrument":instrument,"timeframe":timeframe,"candles_used":len(window),"trend":ta.get("trend"),"trend_strength":ta.get("trend_strength"),"structure":structure,"pattern_signals":pats[-5:],"last_candle_change_pct":round(move,3),"expected_outcome":outcome,"technical":ta,"timestamp":now_iso()}
    except Exception as exc: return error_json("STRUCTURE_UNAVAILABLE",safe_text(exc),503)

@app.get("/api/analysis/patterns/{instrument}")
async def analysis_patterns(instrument: str, timeframe: str | None = None, from_date: str | None = None, to_date: str | None = None, from_time: str | None = None, to_time: str | None = None, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        tfs=[timeframe] if timeframe else ["1m","3m","5m","15m","30m","60m","1D"]

        def scan_one(tf: str) -> list[dict[str, Any]]:
            unit = "days" if tf=="1D" else "hours" if tf=="60m" else "minutes"
            interval = "1" if tf in {"1D","60m"} else tf[:-1]
            days=30 if tf in {"1m","3m","5m","15m"} else 90 if tf in {"30m","60m"} else 365
            if from_date and to_date:
                fd=datetime.fromisoformat(from_date).date(); td=datetime.fromisoformat(to_date).date()
                candles=UPSTOX.candles_between(instrument,interval,unit,fd,td)
            else:
                candles=analysis_candles_robust(instrument, tf, days)
            rows=[]
            for ptn in detect_candlestick_patterns(candles,tf):
                idx=int(ptn.get("index",0)); ts=ptn.get("timestamp")
                prev_ts=candles[max(0,idx-1)].get("timestamp") if candles and idx<len(candles) else ts
                ptn["from_time"]=prev_ts; ptn["to_time"]=ts
                ptn["prediction"]="Bullish continuation / reversal risk" if ptn["pattern"] in {"Hammer","Bullish Engulfing"} else "Bearish continuation / reversal risk" if ptn["pattern"] in {"Shooting Star","Bearish Engulfing"} else "Indecision; wait for confirmation"
                try:
                    if from_time and ts and str(ts) < from_time: continue
                    if to_time and ts and str(ts) > to_time: continue
                except Exception: pass
                rows.append(ptn)
            return rows

        # All timeframes are independent. Fetch them concurrently so one slow
        # provider response cannot keep the whole pattern panel in a loading state.
        out=[]
        if len(tfs)==1:
            out.extend(scan_one(tfs[0]))
        else:
            with ThreadPoolExecutor(max_workers=min(3,len(tfs))) as pool:
                futures={pool.submit(scan_one,tf):tf for tf in tfs}
                for future in as_completed(futures):
                    tf=futures[future]
                    try:
                        out.extend(future.result())
                    except Exception as exc:
                        log.warning("Candlestick pattern scan failed for %s/%s: %s", instrument, tf, safe_text(exc))
        out.sort(key=lambda x: str(x.get("to_time") or ""))
        return {"instrument":instrument,"patterns":out,"timeframes":tfs,"provider":"upstox","timestamp":now_iso()}
    except Exception as exc:
        return error_json("PATTERN_SCAN_UNAVAILABLE", safe_text(exc), 503)

def detect_chart_patterns(candles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows=[]; a=candles[-120:] if candles else []
    if len(a)<20: return rows
    closes=[float(c.get("close") or 0) for c in a]
    highs=[float(c.get("high") or 0) for c in a]; lows=[float(c.get("low") or 0) for c in a]
    def near(x,y,tol=0.012): return y and abs(x-y)/abs(y)<=tol
    # Double top/bottom using the two strongest extrema in the recent half.
    mid=max(5,len(a)//2)
    h1=max(range(0,mid),key=lambda i:highs[i]); h2=max(range(mid,len(a)),key=lambda i:highs[i])
    l1=min(range(0,mid),key=lambda i:lows[i]); l2=min(range(mid,len(a)),key=lambda i:lows[i])
    if near(highs[h1],highs[h2],0.018) and h2-h1>5:
        rows.append({"pattern":"Double Top","confidence":78,"start_index":h1,"end_index":h2,"description":"Two comparable swing highs with a visible reaction between them."})
    if near(lows[l1],lows[l2],0.018) and l2-l1>5:
        rows.append({"pattern":"Double Bottom","confidence":78,"start_index":l1,"end_index":l2,"description":"Two comparable swing lows with a visible recovery between them."})
    # Trend compression proxy for triangle / wedge.
    n=min(30,len(a)); hh=highs[-n:]; ll=lows[-n:]
    if hh[-1] < max(hh[:-5]) and ll[-1] > min(ll[:-5]):
        rows.append({"pattern":"Triangle / Compression","confidence":68,"start_index":len(a)-n,"end_index":len(a)-1,"description":"Recent highs and lows are converging into a narrowing range."})
    # Head-and-shoulders proxy using 5-point swing structure.
    if len(a)>=25:
        pts=[max(range(i,i+5),key=lambda j:highs[j]) for i in range(0,len(a)-4,5)]
        vals=[highs[i] for i in pts]
        if len(vals)>=5 and vals[-3]>vals[-5]*1.02 and vals[-3]>vals[-1]*1.02 and near(vals[-5],vals[-1],0.03):
            rows.append({"pattern":"Head & Shoulders (possible)","confidence":64,"start_index":pts[-5],"end_index":pts[-1],"description":"Three-peak structure with a higher middle peak; confirmation requires neckline break."})
    return rows

async def _analysis_mtf_items(instrument: str, selected_timeframe: str, selected_candles: list[dict[str,Any]]) -> list[dict[str,Any]]:
    def one(tf: str) -> dict[str,Any]:
        try:
            if tf == selected_timeframe:
                cs=selected_candles
            else:
                d=10 if tf in {"1m","3m","5m","15m"} else 30 if tf in {"30m","60m"} else 90
                cs=analysis_candles_robust(instrument,tf,d)
            ta=technical_analysis(cs)
            return {"timeframe":tf,"signal":"BUY" if ta.get("trend")=="BUY" else "SELL" if ta.get("trend")=="SELL" else "NEUTRAL","technical":ta,"candles_used":len(cs)}
        except Exception as exc:
            return {"timeframe":tf,"signal":"N/A","error":safe_text(exc),"candles_used":0}
    tfs=["1m","3m","5m","15m","30m","60m","1D"]
    with ThreadPoolExecutor(max_workers=4) as pool:
        return list(pool.map(one,tfs))

@app.get("/api/analysis/chart-mtf/{instrument}")
async def analysis_chart_mtf(instrument: str, timeframe: str = "5m", user: dict[str,Any] = Depends(require_user)) -> dict[str,Any]:
    cache_key=f"chart-mtf:{instrument}:{timeframe}"
    cached=CACHE.get(cache_key)
    if cached is not None: return cached
    try:
        d=30 if timeframe in {"1m","3m","5m","15m"} else 90 if timeframe in {"30m","60m"} else 365
        candles=analysis_candles_robust(instrument,timeframe,d)
        if not candles:
            raise ProviderUnavailable("No historical candles returned for selected timeframe")
        items=await _analysis_mtf_items(instrument,timeframe,candles)
        out={"instrument":instrument,"timeframe":timeframe,"items":items,"provider":"upstox","timestamp":now_iso()}
        CACHE.set(cache_key,out,20.0)
        return out
    except Exception as exc:
        return error_json("CHART_MTF_UNAVAILABLE",safe_text(exc),503)

@app.get("/api/analysis/chart-bundle/{instrument}")
async def analysis_chart_bundle(instrument: str, timeframe: str = "5m", include_mtf: bool = False, user: dict[str,Any] = Depends(require_user)) -> dict[str,Any]:
    """Return all chart-tab analytics from one selected-timeframe candle fetch plus one MTF batch.

    The old browser loaded technical, candlestick, structure and chart-pattern endpoints
    independently, while MTF loaded seven more candle series. That created a burst of
    overlapping Upstox requests and made the UI sit on Loading... under rate limits.
    """
    cache_key=f"chart-bundle:{instrument}:{timeframe}"
    cached=CACHE.get(cache_key)
    if cached is not None:
        return cached
    try:
        unit="days" if timeframe=="1D" else "hours" if timeframe=="60m" else "minutes"
        interval="1" if timeframe in {"1D","60m"} else timeframe[:-1]
        days=30 if timeframe in {"1m","3m","5m","15m"} else 90 if timeframe in {"30m","60m"} else 365
        candles=analysis_candles_robust(instrument,timeframe,days)
        if not candles:
            raise ProviderUnavailable("No historical candles returned for this timeframe")
        tech=technical_analysis(candles)
        pats=detect_candlestick_patterns(candles,timeframe)
        cpats=detect_chart_patterns(candles)
        window=candles[-10:]
        wta=technical_analysis(window if len(window)>=5 else candles)
        highs=[float(c["high"]) for c in window if c.get("high") is not None]; lows=[float(c["low"]) for c in window if c.get("low") is not None]
        hh=sum(1 for i in range(1,len(highs)) if highs[i]>highs[i-1]); hl=sum(1 for i in range(1,len(lows)) if lows[i]>lows[i-1])
        lh=sum(1 for i in range(1,len(highs)) if highs[i]<highs[i-1]); ll=sum(1 for i in range(1,len(lows)) if lows[i]<lows[i-1])
        structure="Higher Highs / Higher Lows" if hh+hl>lh+ll+1 else "Lower Highs / Lower Lows" if lh+ll>hh+hl+1 else "Range / Mixed Structure"
        last=window[-1] if window else {}; prev=window[-2] if len(window)>1 else last
        move=((float(last.get("close") or 0)-float(prev.get("close") or 0))/float(prev.get("close") or 1)*100) if prev.get("close") else 0
        reversal=any(p.get("pattern") in {"Hammer","Shooting Star","Bullish Engulfing","Bearish Engulfing"} for p in detect_candlestick_patterns(window,timeframe))
        outcome="Bullish continuation" if wta.get("trend")=="BUY" and not reversal else "Bearish continuation" if wta.get("trend")=="SELL" and not reversal else "Potential trend reversal / confirmation required" if reversal else "Range / wait for breakout"

        # Keep the selected-timeframe bundle fast. Multi-timeframe evidence is
        # deliberately separated so a slow provider call can never hold the
        # technical/candlestick/chart-pattern panels in a loading state.
        mtf={"instrument":instrument,"items":[],"provider":"upstox","deferred":True}
        if include_mtf:
            mtf={"instrument":instrument,"items":await _analysis_mtf_items(instrument,timeframe,candles),"provider":"upstox","deferred":False}
        result={"instrument":instrument,"timeframe":timeframe,"candles_used":len(candles),
                "technical":{"instrument":instrument,"timeframe":timeframe,"technical":tech,"patterns":pats,"provider":"upstox"},
                "mtf":mtf,
                "patterns":{"instrument":instrument,"patterns":pats,"timeframes":[timeframe],"provider":"upstox"},
                "structure":{"instrument":instrument,"timeframe":timeframe,"candles_used":len(window),"trend":wta.get("trend"),"trend_strength":wta.get("trend_strength"),"structure":structure,"pattern_signals":detect_candlestick_patterns(window,timeframe)[-5:],"last_candle_change_pct":round(move,3),"expected_outcome":outcome,"technical":wta},
                "chart_patterns":{"instrument":instrument,"timeframe":timeframe,"patterns":cpats,"provider":"upstox"},
                "timestamp":now_iso()}
        CACHE.set(cache_key,result,20.0)
        return result
    except Exception as exc:
        return error_json("CHART_ANALYTICS_UNAVAILABLE",safe_text(exc),503)

@app.get("/api/analysis/chart-patterns/{instrument}")
async def analysis_chart_patterns(instrument: str, timeframe: str = "5m", user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        unit="days" if timeframe=="1D" else "hours" if timeframe=="60m" else "minutes"
        interval="1" if timeframe in {"1D","60m"} else timeframe[:-1]
        days=60 if timeframe in {"1D","60m"} else 20
        candles=analysis_candles_robust(instrument,timeframe,days)
        return {"instrument":instrument,"timeframe":timeframe,"patterns":detect_chart_patterns(candles),"definitions":{
            "Double Top":"Two similar highs; bearish confirmation on neckline break.",
            "Double Bottom":"Two similar lows; bullish confirmation on neckline break.",
            "Triangle / Compression":"Converging highs/lows; breakout direction is the confirmation.",
            "Head & Shoulders (possible)":"Higher middle peak with similar shoulders; neckline break confirms."
        },"provider":"upstox","timestamp":now_iso()}
    except Exception as exc:
        return error_json("CHART_PATTERN_UNAVAILABLE",safe_text(exc),503)

@app.get("/api/analysis/fundamental/{instrument}")
async def analysis_fundamental(instrument: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        return fundamental_data(instrument)
    except Exception as exc:
        record_error("fundamental_failure", safe_text(exc), user_id=user["id"])
        return {"instrument": instrument, "available": False, "reason": "Fundamental data is currently unavailable", "provider": None, "timestamp": now_iso()}


@app.get("/api/analysis/overall/{instrument}")
async def analysis_overall(instrument: str, timeframe: str = "5m", user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    # Preview only: opening Recommendations/Dashboard must never create a saved
    # recommendation and must not silently consume an AI request.
    try:
        rec = await asyncio.wait_for(asyncio.to_thread(overall_recommendation, instrument, timeframe), timeout=5.8)
    except asyncio.TimeoutError:
        rec={"qualifies":False,"recommendation":"NO_TRADE","confidence":0,"reason":"Analysis is still refreshing; the previous saved recommendation remains the source of truth.","evidence":{}}
    return {"instrument": instrument, "timeframe": timeframe, **rec, "ai": {"available": False, "requested": False, "decision": "NOT REQUESTED", "reason": "CA AI opinion is manual. Click Ask CA AI to request it."}, "timestamp": now_iso()}

# ---------------------------------------------------------------------------
# Options APIs
# ---------------------------------------------------------------------------

@app.get("/api/options/{underlying}")
async def options_summary(underlying: str, expiry: str | None = None, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        key=f"option-chain:{underlying.upper()}:{expiry or 'nearest'}"; cached=CACHE.get(key)
        if cached is not None: return cached
        data=await asyncio.wait_for(asyncio.to_thread(UPSTOX.option_chain, underlying, expiry), timeout=5.0)
        CACHE.set(key,data,8)
        return data
    except asyncio.TimeoutError:
        cached=CACHE.get(f"option-chain:{underlying.upper()}:{expiry or 'nearest'}")
        if cached is not None: return cached
        return error_json("OPTIONS_TIMEOUT","Option chain is refreshing; please retry shortly.",504)
    except Exception as exc:
        return error_json("OPTIONS_UNAVAILABLE", safe_text(exc), 503)


@app.get("/api/options/{underlying}/expiries")
async def option_expiries(underlying: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        key=f"option-expiries:{underlying.upper()}"; cached=CACHE.get(key)
        if cached is not None: return cached
        payload=await asyncio.wait_for(asyncio.to_thread(UPSTOX.option_contracts, underlying), timeout=4.0)
        rows=payload.get("data") or []; expiries=sorted({str(x.get("expiry")) for x in rows if isinstance(x,dict) and x.get("expiry")})
        result={"underlying":underlying,"expiries":expiries,"provider":"upstox","timestamp":now_iso()}; CACHE.set(key,result,30); return result
    except asyncio.TimeoutError:
        return {"underlying":underlying,"expiries":[],"provider":"upstox","stale":True,"timestamp":now_iso()}
    except Exception as exc:
        return error_json("OPTION_EXPIRIES_UNAVAILABLE", safe_text(exc), 503)


@app.get("/api/options/{underlying}/chain")
async def option_chain(underlying: str, expiry: str | None = None, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return await options_summary(underlying, expiry, user)


@app.post("/api/options/{underlying}/buyable")
async def buyable_options(underlying: str, payload: BuyableIn, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        chain = UPSTOX.option_chain(underlying, payload.expiry)
    except Exception as exc:
        return error_json("OPTIONS_UNAVAILABLE", safe_text(exc), 503)
    contracts = []
    for strike in chain.get("strikes", []):
        for option_type in ("CE", "PE"):
            c = strike.get("call" if option_type == "CE" else "put")
            if not c:
                continue
            if payload.option_type and option_type != payload.option_type:
                continue
            premium = c.get("ltp")
            if premium is None:
                continue
            if payload.premium_min is not None and premium < payload.premium_min:
                continue
            if payload.premium_max is not None and premium > payload.premium_max:
                continue
            if payload.ltp_per_quantity is not None and float(premium) > float(payload.ltp_per_quantity):
                continue
            volume = int(c.get("volume") or 0)
            oi = int(c.get("oi") or 0)
            if volume < payload.min_volume or oi < payload.min_oi:
                continue
            lot = int(c.get("lot_size") or 0)
            if lot < 1:
                continue
            premium = float(premium)
            cost = premium * lot
            if payload.max_cost_per_lot is not None and cost > float(payload.max_cost_per_lot):
                continue
            max_lots = int(payload.capital // cost) if cost > 0 else 0
            if max_lots < 1:
                continue
            if payload.quantity_lots is not None and max_lots < int(payload.quantity_lots):
                continue
            requested_lots = int(payload.quantity_lots) if payload.quantity_lots is not None else max_lots
            requested_lots = max(1, min(requested_lots, max_lots))
            delta=abs(float(c.get("delta") or 0)); gamma=abs(float(c.get("gamma") or 0)); vega=abs(float(c.get("vega") or 0)); iv=float(c.get("iv") or 0)
            liquidity_score=min(100.0, (volume/10000.0)*35 + (oi/50000.0)*35)
            greek_score=min(100.0, delta*55 + gamma*250 + min(vega,1)*20)
            affordability_score=min(100.0, max_lots*20)
            potential_score=round(0.45*liquidity_score + 0.35*greek_score + 0.20*affordability_score,2)
            contracts.append({"contract": {"strike": strike["strike"], "option_type": option_type, **c}, "strike": strike["strike"], "option_type": option_type, "expiry": c.get("expiry") or payload.expiry, "lot_size": lot, "premium": premium, "ltp": premium, "cost_per_lot": cost, "max_affordable_lots": max_lots, "requested_lots": requested_lots, "capital_required": cost*requested_lots, "potential_risk": abs(premium)*lot*requested_lots, "potential_score": potential_score, "greeks": {k: c.get(k) for k in ("delta", "gamma", "theta", "vega", "iv")}, "liquidity": {"volume": volume, "oi": oi}, "ltp_filter": payload.ltp_per_quantity, "max_cost_per_lot": payload.max_cost_per_lot})
    contracts.sort(key=lambda x: (-x["potential_score"], -x["liquidity"]["volume"], -x["max_affordable_lots"], x["capital_required"]))
    return {"underlying": underlying, "expiry": payload.expiry, "contracts": contracts[:25], "count": len(contracts), "timestamp": now_iso(), "provider": "upstox"}

@app.get("/api/news/global")
async def news_global(limit: int = Query(100, ge=1, le=500), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        return news_result('budget OR budgets OR Trump OR Iran OR Iraq OR Israel OR Gaza OR war OR wars OR Russia OR Ukraine OR China OR Taiwan OR tariffs OR tariff OR sanctions OR geopolitics OR oil OR crude OR WTI OR Brent OR OPEC OR Fed OR Federal Reserve OR RBI OR inflation OR interest rates OR bonds OR dollar OR rupee OR recession OR GDP OR markets OR economy OR elections OR policy OR regulation OR banking OR earnings', limit, "GLOBAL", user["id"])
    except Exception as exc:
        return error_json("NEWS_UNAVAILABLE", safe_text(exc), 503)


@app.get("/api/news/stock/{instrument}")
async def news_stock(instrument: str, limit: int = Query(100, ge=1, le=500), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        return news_result(_target_news_query(instrument), limit, instrument, user["id"])
    except Exception as exc:
        return error_json("NEWS_UNAVAILABLE", safe_text(exc), 503)


@app.get("/api/news/index/{index}")
async def news_index(index: str, limit: int = Query(100, ge=1, le=500), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    idx=index.upper()
    if idx not in {"NIFTY","NIFTY50","BANKNIFTY","SENSEX"}:
        raise HTTPException(422,"Unsupported index")
    query='"Bank Nifty" OR "Nifty Bank"' if idx=="BANKNIFTY" else ('"Nifty 50" OR NIFTY India' if idx in {"NIFTY","NIFTY50"} else 'Sensex India markets')
    try:
        return news_result(query,limit,idx,user["id"])
    except Exception as exc:
        return error_json("NEWS_UNAVAILABLE",safe_text(exc),503)

# ---------------------------------------------------------------------------
# News analysis / provider catalog / CA AI chat
# ---------------------------------------------------------------------------

def gemini_text(prompt: str, max_chars: int = 18000) -> dict[str, Any]:
    if not GEMINI_API_KEY:
        return {"available": False, "reason": "Gemini API key is not configured"}
    url=f"https://generativelanguage.googleapis.com/v1beta/models/{quote(GEMINI_MODEL,safe='-_.')}:generateContent"
    try:
        resp=requests.post(url,headers={"x-goog-api-key":GEMINI_API_KEY,"Content-Type":"application/json"},json={"contents":[{"parts":[{"text":prompt[:max_chars]}]}]},timeout=25)
        if resp.status_code>=400:
            record_error("api_failure",f"Gemini HTTP {resp.status_code}","gemini",resp.status_code)
            return {"available":False,"reason":f"Gemini HTTP {resp.status_code}"}
        payload=resp.json(); text="".join(p.get("text","") for p in payload.get("candidates",[{}])[0].get("content",{}).get("parts",[]))
        provider_ok("gemini")
        return {"available":True,"text":text,"model":GEMINI_MODEL,"timestamp":now_iso()}
    except Exception as exc:
        record_error("provider_failure",safe_text(exc),"gemini")
        return {"available":False,"reason":"Gemini request failed"}

def _heuristic_news_analysis(article: dict[str, Any]) -> dict[str, Any]:
    title=str(article.get("headline") or article.get("title") or "")
    summary=_strip_news_boilerplate(str(article.get("summary") or ""))
    target=str(article.get("symbol") or "GLOBAL").upper()
    c=_news_classify_v6(title,summary,target)
    text=_news_text(title,summary)
    pos=sum(1 for t in POSITIVE_NEWS_TERMS if t in text)+sum(1 for t in MACRO_POSITIVE_TERMS if t in _norm_news(title))
    neg=sum(1 for t in NEGATIVE_NEWS_TERMS if t in text)+sum(1 for t in MACRO_NEGATIVE_TERMS if t in _norm_news(title))
    sentiment=c.get("sentiment") or ("Positive" if pos>neg else "Negative" if neg>pos else "Neutral")
    materiality=float(c.get("materiality") or 0)
    delete_recommended=bool(c.get("classification")=="IRRELEVANT" or materiality<25)
    raw_conf=float(c.get("confidence") or 70)
    confidence=min(96, round(raw_conf*100 if raw_conf<=1 else raw_conf))
    final_materiality=max(materiality,95.0 if any(t in _norm_news(title) for t in MACRO_HIGH_MATERIALITY_TERMS) else materiality)
    return {"sentiment":sentiment,"materiality":final_materiality,"opinion":c.get("reason") or "Heuristic fallback based on headline-first financial relevance.","confidence":confidence,"available":False,"recommend_delete":delete_recommended,"delete_reason":"No clear investment-relevant event or target exposure was found." if delete_recommended else ""}


def article_key(article: dict[str, Any]) -> str:
    return hashlib.sha256(_news_identity({"url":article.get("url"),"title":article.get("headline") or article.get("title"),"summary":article.get("summary")}).encode()).hexdigest()[:32]

@app.get("/api/providers/news")
async def news_provider_health(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    g=PROVIDER_HEALTH.get("gnews",{}); n=PROVIDER_HEALTH.get("newsapi",{}); u=PROVIDER_HEALTH.get("upstox",{})
    def status(name: str, configured: bool, state: dict[str, Any]) -> str:
        if not configured: return "not configured"
        return state.get("status") or "unknown"
    return {"providers":[
        {"id":"gnews","name":"News Feed A","status":status("gnews",bool(_news_key_pool("GNEWS_API_KEY")),g)},
        {"id":"newsapi","name":"News Feed B","status":status("newsapi",bool(_news_key_pool("NEWSAPI_API_KEY")),n)},
        {"id":"upstox","name":"Market News","status":status("upstox",bool(UPSTOX_ACCESS_TOKEN),u)},
        {"id":"publisher_rss","name":"Publisher RSS","status":"configured"},
        {"id":"others","name":"Others","status":"open source","sources":[x[0] for x in NEWS_SOURCES]},
    ],"timestamp":now_iso()}


@app.get("/api/news/expand/{instrument}")
async def news_expand(instrument: str, limit: int = Query(200, ge=10, le=500), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    """Return a broader, deduplicated news set for an instrument so the UI/AI can fill coverage gaps."""
    try:
        rows = news_result(_target_news_query(instrument), limit, instrument)
        return rows
    except Exception as exc:
        return error_json("NEWS_EXPAND_UNAVAILABLE", safe_text(exc), 503)

@app.post("/api/news/analyze")
async def news_analyze(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    article=await request.json()
    clean={k:article.get(k) for k in ["headline","title","summary","source","url","published_at","symbol","classification","materiality"]}
    prompt=("You are CA AI inside a professional stock-trading terminal. Analyze the supplied news item for investment relevance. "
            "PRIORITY: treat the headline as the primary evidence. The summary/body is secondary confirmation. Ignore publisher/program boilerplate, presenter names, promotional language, disclaimers and navigation text. "
            "A concrete geopolitical, central-bank, rates, inflation, commodity, regulatory, earnings, M&A, legal, management or company event can be highly material even if the body is incomplete. "
            "Determine sentiment for the selected instrument/market, materiality (0-100), confidence (0-100), affected assets, likely Indian-market transmission, and whether it should be removed as irrelevant. "
            "Return strict JSON with sentiment (Positive|Negative|Neutral), materiality (0-100), confidence (0-100), opinion, event_type, affected_assets (array), key_impacts (array), risks (array), india_market_impact, missing_evidence, recommend_delete (boolean), and delete_reason. "
            "Never call a headline about war/rates/oil/inflation/regulation/earnings irrelevant merely because the feed description is generic. Do not invent facts. Distinguish reported facts from interpretation.\n\n"+json.dumps(clean,default=str))
    try:
        result=await asyncio.wait_for(asyncio.to_thread(gemini_text,prompt), timeout=6.0)
    except asyncio.TimeoutError:
        result={"available":False,"reason":"CA AI analysis is still processing; heuristic analysis used for now."}
    if result.get("available"):
        text=result.get("text","")
        try:
            m=re.search(r"\{.*\}",text,re.S); parsed=json.loads(m.group(0)) if m else None
        except Exception: parsed=None
        if parsed:
            parsed["available"]=True; parsed["model"]=result.get("model"); parsed["article_key"]=article_key(clean)
            h=_news_classify_v6(clean.get("headline") or clean.get("title") or "",clean.get("summary") or "",str(clean.get("symbol") or "GLOBAL"))
            try:
                if float(parsed.get("materiality") or 0) < float(h.get("materiality") or 0): parsed["materiality"]=h.get("materiality")
            except Exception: pass
            if str(h.get("classification"))=="NEWS" and float(h.get("materiality") or 0)>=70 and bool(parsed.get("recommend_delete")): parsed["recommend_delete"]=False; parsed["delete_reason"]="Headline indicates potentially material investment news; generic feed boilerplate was discounted."
            if (parsed.get("sentiment") in {None,"","Neutral"}) and h.get("sentiment") in {"Positive","Negative"}: parsed["sentiment"]=h.get("sentiment")
            return parsed
    fallback=_heuristic_news_analysis(clean); fallback["article_key"]=article_key(clean); fallback["model"]=None; fallback["ai_reason"]=result.get("reason"); return fallback

@app.get("/api/news/hidden")
async def news_hidden(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    rows=db_exec("SELECT article_key FROM news_hidden WHERE user_id=?",[user["id"]],"all")
    return {"items":[r["article_key"] for r in rows]}

@app.post("/api/news/hide")
async def news_hide(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    b=await request.json(); article=b.get("article") or {}; key=article_key(article)
    db_exec("INSERT INTO news_hidden(id,user_id,article_key,created_at) VALUES(?,?,?,?) ON CONFLICT(user_id,article_key) DO NOTHING",[secrets.token_hex(12),user["id"],key,now_iso()])
    return {"ok":True,"article_key":key}

@app.get("/api/news/reels")
async def news_reels(target: str | None = None, limit: int = Query(200, ge=10, le=500), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    rows=[]
    targets=[x.strip().upper() for x in str(target or '').split(',') if x.strip()]
    if targets:
        per=max(4,limit//max(1,len(targets)))
        for sym in targets[:12]:
            rows += (news_result(_target_news_query(sym), per, sym, user["id"]).get("events") or [])
    rows += (news_result("budget Trump Iran Iraq Israel Gaza war Russia Ukraine China Taiwan tariffs sanctions geopolitics oil crude WTI Brent OPEC Fed RBI inflation interest rates bonds dollar rupee recession GDP markets economy elections policy regulation banking earnings", limit, "GLOBAL", user["id"]).get("events") or [])
    hidden={r["article_key"] for r in db_exec("SELECT article_key FROM news_hidden WHERE user_id=?",[user["id"]],"all")}
    out=[]; seen=set()
    for a in _news_dedupe(rows):
        k=article_key(a)
        if k in hidden or k in seen: continue
        seen.add(k)
        a=dict(a)
        text=_news_text(a.get("headline",""),a.get("summary",""))
        matched=None
        for t in targets:
            if not t:
                continue
            if t.lower() in text or ("CRUDE" in t and _news_contains(text,["crude oil","crudeoil","wti","brent"])):
                matched=t
                break
        a["reason"] = (f"Related to {matched}" if matched else (a.get("reason") or "Global news"))
        a["scope"] = "stock" if matched else "global"
        out.append(a)
    def _news_ts(item):
        raw=str(item.get("published_at") or "")
        try:
            d=datetime.fromisoformat(raw.replace("Z","+00:00"))
            if d.tzinfo is None: d=d.replace(tzinfo=timezone.utc)
            return d.timestamp()
        except Exception:
            return 0
    out.sort(key=_news_ts, reverse=True)
    return {"events":out[:limit],"timestamp":now_iso()}

@app.post("/api/news/decision")
async def news_decision(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    b=await request.json(); article=b.get("article") or {}; ca=b.get("ca_ai") or {}; ud=b.get("user_decision")
    ca_sent=str(ca.get("sentiment") or "Neutral").title(); ca_mat=float(ca.get("materiality") or article.get("materiality") or 0)
    if ca_sent not in {"Positive","Negative","Neutral"}: ca_sent="Neutral"
    user_sent=(str(ud).title() if ud else None)
    if user_sent not in {"Positive","Negative","Neutral"}: user_sent=None
    user_mat=b.get("user_materiality")
    final_sent=user_sent or ca_sent; final_mat=float(user_mat if user_mat is not None else ca_mat)
    aid=article_key(article)
    db_exec("INSERT INTO news_decisions(id,user_id,article_key,title,source,url,ca_decision,ca_materiality,ca_rationale,user_decision,user_materiality,final_decision,final_materiality,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id,article_key) DO UPDATE SET ca_decision=excluded.ca_decision,ca_materiality=excluded.ca_materiality,ca_rationale=excluded.ca_rationale,user_decision=excluded.user_decision,user_materiality=excluded.user_materiality,final_decision=excluded.final_decision,final_materiality=excluded.final_materiality,updated_at=excluded.updated_at",[secrets.token_hex(12),user["id"],aid,article.get("headline") or article.get("title") or "",article.get("source"),article.get("url"),ca_sent,ca_mat,ca.get("opinion"),user_sent,user_mat,final_sent,final_mat,now_iso()])
    return {"ok":True,"article_key":aid,"final_decision":final_sent,"final_materiality":final_mat,"ca_decision":ca_sent,"ca_materiality":ca_mat,"user_decision":user_sent,"user_materiality":user_mat}

@app.get("/api/news/remove-recommended")
async def news_remove_recommended(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    rows=db_exec("SELECT article_key,title,source,url,ca_decision,ca_materiality,ca_rationale FROM news_decisions WHERE user_id=? AND lower(COALESCE(ca_rationale,'')) NOT LIKE '%material%' ORDER BY updated_at DESC",[user["id"]],"all")
    # The UI still lets the user change the selection before calling /api/news/hide.
    return {"items":[dict(r) for r in rows if str(r.get("ca_decision") or "").lower() in {"irrelevant","neutral","remove"} and float(r.get("ca_materiality") or 0) <= 25]}

@app.get("/api/news/decision/{article_key}")
async def news_decision_get(article_key: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    row=db_exec("SELECT * FROM news_decisions WHERE user_id=? AND article_key=?",[user["id"],article_key],"one")
    return {"decision":row}

@app.post("/api/ai/chat")
async def ai_chat(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    b=await request.json(); message=str(b.get("message","")).strip(); context=b.get("context") or {}
    if not message: raise HTTPException(422,"Message is required")
    prompt=("You are CA AI, an assistant inside CA Trader. Give concise, decision-support-oriented answers. "
            "Use only supplied market/news context when discussing live instruments. Never invent LTP, news, fundamentals, or order status. "
            "You may explain risk, technicals, news materiality, and trading mechanics. This is not a guarantee of returns.\n\n"
            f"Context:\n{json.dumps(context,default=str)[:12000]}\n\nUser:\n{message}")
    result=gemini_text(prompt,16000)
    if not result.get("available"):
        return {"available":False,"message":"CA AI is unavailable because Gemini is not configured or is temporarily unavailable.","reason":result.get("reason"),"timestamp":now_iso()}
    return {"available":True,"message":result.get("text",""),"model":result.get("model"),"timestamp":now_iso()}

# ---------------------------------------------------------------------------
# Recommendations/history
# ---------------------------------------------------------------------------

@app.post("/api/recommendations/on-demand")
async def recommendation_on_demand(payload: RecommendationIn, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    if payload.timeframe not in TIMEFRAMES:
        raise HTTPException(422, "Unsupported timeframe")
    try:
        symbol_upper=payload.symbol.upper()
        segment = "MCX" if any(x in symbol_upper for x in ("MCX", "CRUDEOIL", "CRUDE OIL", "GOLD", "SILVER", "NATURALGAS", "COPPER", "ZINC")) else "NSE_EQ"
        if segment=="NSE_EQ":
            try:
                key, _meta = get_instrument_meta(payload.symbol)
                if str(key or "").upper().startswith("MCX") or "COM" in str(key or "").upper(): segment="MCX"
            except Exception:
                pass
        session = market_session(segment)
        if not session.get("active"):
            return error_json("MARKET_CLOSED", f"On-demand recommendations are unavailable while {segment} is closed.", 409, segment=segment, session=session)
    except Exception as exc:
        record_error("recommendation_session_check", safe_text(exc), user_id=user["id"])
        raise HTTPException(503, "Unable to verify market session")
    try:
        try:
            rec = await asyncio.wait_for(asyncio.to_thread(overall_recommendation, payload.symbol, payload.timeframe, payload.desired_profit, payload.bearable_loss, payload.risk_preferences, payload.option_preferences), timeout=5.5)
        except asyncio.TimeoutError:
            last=db_exec("SELECT * FROM recommendations WHERE user_id=? AND COALESCE(underlying,symbol)=? ORDER BY created_at DESC LIMIT 1",[user["id"],payload.symbol.upper()],"one")
            rec={"recommendation":last.get("recommendation","NO_TRADE") if last else "NO_TRADE","confidence":last.get("score") if last else 0,"entry":last.get("entry") if last else None,"stop_loss":last.get("stop_loss") if last else None,"target":last.get("target") if last else None,"reason":"Latest saved recommendation returned while fresh analysis continues in the background." if last else "Fresh analysis is still loading; no previous recommendation exists yet.","evidence":{}}
        ai = ai_analyze(rec) if payload.ask_ai and rec.get("recommendation") != "NO_TRADE" else {"available": False, "decision": "NO_TRADE", "reason": "CA AI will analyze after a fresh recommendation is available."}
    except Exception as exc:
        record_error("recommendation_failure", safe_text(exc), user_id=user["id"])
        return error_json("RECOMMENDATION_UNAVAILABLE", safe_text(exc), 503)
    rid = secrets.token_hex(12)
    recommendation = rec.get("recommendation", "NO_TRADE")
    db_exec("INSERT INTO recommendations(id,user_id,source,symbol,recommendation,timeframe,entry,target,stop_loss,rationale,technical_basis,news_basis,option_basis,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", [rid,user["id"],"on-demand",payload.symbol,recommendation,payload.timeframe,rec.get("entry"),rec.get("target"),rec.get("stop_loss"),(rec.get("rationale") or rec.get("reason")),json.dumps(rec.get("evidence",{}),default=str),None,json.dumps(rec.get("evidence",{}).get("options"),default=str) if rec.get("evidence",{}).get("options") else None,now_iso()])
    return {"id": rid, "source": "on-demand", **rec, "ai": ai, "user_id": user["id"]}


@app.get("/api/recommendations/history")
async def recommendation_history(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    rows = db_exec("SELECT * FROM recommendations WHERE user_id=? ORDER BY created_at DESC LIMIT 200", [user["id"]], "all")
    totals = {"auto": 0, "on-demand": 0, "combined": 0, "auto_wins": 0, "on_demand_wins": 0, "wins": 0, "pnl": 0.0}
    for r in rows:
        src = r["source"] if r["source"] in {"auto", "on-demand"} else "on-demand"
        totals[src] += 1
        totals["combined"] += 1
        if r.get("success"):
            totals["wins"] += 1
            totals["auto_wins" if src == "auto" else "on_demand_wins"] += 1
        totals["pnl"] += float(r.get("final_pnl") or 0)
    totals["win_rate"] = (totals["wins"] / totals["combined"] * 100) if totals["combined"] else 0
    totals["loss_rate"] = 100 - totals["win_rate"] if totals["combined"] else 0
    return {"items": rows, "stats": totals, "user_id": user["id"]}


@app.delete("/api/recommendations/history/{recommendation_id}")
async def recommendation_history_delete(recommendation_id: str, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    row=db_exec("SELECT id FROM recommendations WHERE id=? AND user_id=?",[recommendation_id,user["id"]],"one")
    if not row:
        raise HTTPException(404,"Recommendation history item not found")
    db_exec("DELETE FROM recommendations WHERE id=? AND user_id=?",[recommendation_id,user["id"]])
    return {"ok":True,"id":recommendation_id}

# ---------------------------------------------------------------------------
# Orders / funds / positions / holdings
# ---------------------------------------------------------------------------


def get_instrument_meta(symbol: str) -> tuple[str | None, dict[str, Any]]:
    try:
        key, meta = UPSTOX.resolve_instrument(symbol)
        return key, meta
    except Exception:
        return None, {}


def validate_lot_size(quantity: int, meta: dict[str, Any]) -> None:
    lot = meta.get("lot_size") or meta.get("lot_size_value")
    try:
        lot = int(lot)
    except Exception:
        lot = 1
    if lot > 1 and quantity % lot != 0:
        raise HTTPException(422, {"code": "INVALID_LOT_SIZE", "message": f"Quantity must be a multiple of lot size {lot}", "lot_size": lot})


@app.get("/api/orders")
async def orders_list(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    # CA Trader paper terminal is a self-contained ledger. Never fetch broker
    # orders merely to render the paper Orders tab.
    local = db_exec("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC", [user["id"]], "all")
    return {"items": local, "provider_items": None, "user_id": user["id"], "paper": True}


@app.post("/api/orders")
async def order_create(payload: OrderIn, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        key, meta = get_instrument_meta(payload.symbol)
    except Exception:
        if payload.paper and not payload.live:
            key, meta = payload.symbol, {"lot_size": 1}
        else:
            raise
    validate_lot_size(payload.quantity, meta)
    if payload.product not in {"D","I"}:
        raise HTTPException(422,"Product must be Delivery (D) or Intraday (I)")
    session=market_session("MCX" if str(key or "").upper().startswith("MCX") else "NSE_EQ")
    if payload.amo and session.get("active"):
        raise HTTPException(422,"AMO is only valid after the regular market session closes")
    if payload.live and not payload.paper and not session.get("active") and not payload.amo:
        raise HTTPException(422,"Live orders are blocked after market hours unless AMO is selected")
    ltp=None
    try: ltp=UPSTOX.quote(payload.symbol).get("ltp")
    except Exception: pass
    if payload.stop_loss is not None or payload.target is not None:
        ref=float(ltp or payload.price or 0)
        if ref<=0: raise HTTPException(422,"A live LTP is required to validate stop-loss/target")
        if payload.side=="BUY":
            if payload.stop_loss is not None and payload.stop_loss >= ref: raise HTTPException(422,"For BUY, stop-loss must be below LTP")
            if payload.target is not None and payload.target <= ref: raise HTTPException(422,"For BUY, target must be above LTP")
        else:
            if payload.stop_loss is not None and payload.stop_loss <= ref: raise HTTPException(422,"For SELL, stop-loss must be above LTP")
            if payload.target is not None and payload.target >= ref: raise HTTPException(422,"For SELL, target must be below LTP")
    if payload.stop_loss is not None and payload.target is not None:
        if payload.side=="BUY" and not (payload.stop_loss < (ltp or payload.price) < payload.target): raise HTTPException(422,"BUY risk geometry invalid")
        if payload.side=="SELL" and not (payload.target < (ltp or payload.price) < payload.stop_loss): raise HTTPException(422,"SELL risk geometry invalid")
    if payload.order_type in {"LIMIT","SL","SL-M"} and payload.price is None and payload.order_type != "SL-M":
        raise HTTPException(422,"Price is required for this order type")
    if payload.live and not payload.paper:
        settings=db_exec("SELECT value_json FROM settings WHERE user_id=? AND key='live_trading_enabled'",[user["id"]],"one")
        enabled=bool(settings and json.loads(settings["value_json"]))
        if not enabled: raise HTTPException(403,"Live trading is not enabled for this user")
    oid=secrets.token_hex(12); now=now_iso(); status="AMO_QUEUED" if payload.amo and payload.live and not payload.paper else ("PENDING" if payload.live and not payload.paper else "PAPER_FILLED")
    db_exec("INSERT INTO orders(id,user_id,symbol,instrument_key,side,quantity,order_type,price,trigger_price,stop_loss,target,amo,status,execution_state,product,paper,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",[oid,user["id"],payload.symbol.upper(),key,payload.side,payload.quantity,payload.order_type,payload.price,payload.trigger_price,payload.stop_loss,payload.target,int(payload.amo),status,"PENDING",payload.product,int(payload.paper),now,now])
    provider_result=None
    if payload.live and not payload.paper:
        body={"quantity":payload.quantity,"product":payload.product,"validity":"DAY","price":payload.price or 0,"tag":"CA_TRADER","instrument_token":key,"order_type":payload.order_type,"transaction_type":payload.side,"disclosed_quantity":0,"trigger_price":payload.trigger_price or 0,"is_amo":payload.amo}
        try: provider_result=UPSTOX.create_order(body)
        except Exception as exc:
            db_exec("UPDATE orders SET status=?,execution_state=?,updated_at=? WHERE id=? AND user_id=?",["REJECTED","FAILED",now_iso(),oid,user["id"]]); raise HTTPException(503,safe_text(exc))
    filled_position=None
    if payload.paper and not payload.live and status=="PAPER_FILLED":
        filled_position=_paper_fill(user["id"],{"symbol":payload.symbol.upper(),"instrument_key":key,"side":payload.side,"quantity":payload.quantity,"price":ltp or payload.price,"fill_price":ltp or payload.price,"stop_loss":payload.stop_loss,"target":payload.target,"underlying":payload.symbol.upper()},None)
    await add_notification(user["id"],"order_executed" if payload.paper else "system","info",60,f"Order {'paper-filled' if payload.paper else 'created'} — {payload.symbol} {payload.side} {payload.quantity}",f"Order {oid}")
    return {"id":oid,"status":status,"provider_result":provider_result,"user_id":user["id"],"ltp":ltp,"amo":payload.amo,"position":filled_position}


@app.put("/api/orders/{order_id}")
async def order_modify(order_id: str, payload: OrderModifyIn, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    row = db_exec("SELECT * FROM orders WHERE id=? AND user_id=?", [order_id, user["id"]], "one")
    if not row:
        raise HTTPException(404, "Order not found")
    fields = []
    vals: list[Any] = []
    for name in ["quantity", "price", "trigger_price", "stop_loss", "target"]:
        value = getattr(payload, name)
        if value is not None:
            fields.append(name + "=?")
            vals.append(value)
    if fields:
        vals += [now_iso(), order_id, user["id"]]
        db_exec(f"UPDATE orders SET {', '.join(fields)}, updated_at=? WHERE id=? AND user_id=?", vals)
    return {"ok": True, "order": db_exec("SELECT * FROM orders WHERE id=? AND user_id=?", [order_id, user["id"]], "one")}


@app.delete("/api/orders/{order_id}")
async def order_cancel(order_id: str, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    row = db_exec("SELECT * FROM orders WHERE id=? AND user_id=?", [order_id, user["id"]], "one")
    if not row:
        raise HTTPException(404, "Order not found")
    db_exec("UPDATE orders SET status='CANCELLED', execution_state='CANCELLED', updated_at=? WHERE id=? AND user_id=?", [now_iso(), order_id, user["id"]])
    return {"ok": True}


@app.post("/api/orders/{order_id}/square-off")
async def square_off(order_id: str, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    row = db_exec("SELECT * FROM orders WHERE id=? AND user_id=?", [order_id, user["id"]], "one")
    if not row:
        raise HTTPException(404, "Order not found")
    exit_price=None
    try: exit_price=float((await asyncio.to_thread(UPSTOX.ltp,row["symbol"])).get("ltp") or 0)
    except Exception: exit_price=None
    entry=float(row.get("price") or 0); qty=int(row.get("quantity") or 0); pnl=None
    if exit_price and entry and qty:
        pnl=(exit_price-entry)*qty if str(row.get("side")).upper()=="BUY" else (entry-exit_price)*qty
    db_exec("UPDATE orders SET status='SQUARED_OFF', execution_state='CLOSED', exit_price=?, final_pnl=?, updated_at=? WHERE id=? AND user_id=?", [exit_price,pnl,now_iso(),order_id,user["id"]])
    await add_notification(user["id"], "risk_event", "success" if (pnl or 0)>=0 else "warning", 85, f"Position squared off · {row['symbol']}", f"Exit ₹{exit_price:,.2f} · Final P&L ₹{(pnl or 0):,.2f}" if exit_price else f"Order {order_id} squared off", f"squareoff:{order_id}")
    return {"ok": True, "final_pnl":pnl,"exit_price":exit_price,"order": db_exec("SELECT * FROM orders WHERE id=? AND user_id=?", [order_id, user["id"]], "one")}


@app.get("/api/funds")
async def funds(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    local = db_exec("SELECT * FROM funds WHERE user_id=?", [user["id"]], "one")
    if not local:
        amount=300000 if user.get("role")=="admin" else 200000
        db_exec("INSERT INTO funds(user_id,available,trading_funds,testing_funds,auto_trade_funds,updated_at) VALUES(?,?,?,?,?,?)",[user["id"],amount,amount,amount if user.get("role")=="admin" else 0,amount,now_iso()])
        local=db_exec("SELECT * FROM funds WHERE user_id=?",[user["id"]],"one")
    return {"user_id": user["id"], "role": user.get("role","user"), "local": local, "provider": None, "paper": True, "buckets":{"trading":local.get("trading_funds",local.get("available",0)),"testing":local.get("testing_funds",0),"auto_trade":local.get("auto_trade_funds",0)}}


@app.get("/api/positions")
async def positions(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try: await asyncio.to_thread(_position_mark_and_pnl,user["id"])
    except Exception: pass
    local = db_exec("SELECT * FROM positions WHERE user_id=? ORDER BY updated_at DESC", [user["id"]], "all")
    return {"user_id": user["id"], "items": local, "provider": None, "paper": True}


@app.get("/api/portfolio/snapshot")
async def portfolio_snapshot(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    """Single fast local-paper snapshot. Broker portfolio APIs are never used here."""
    uid=user["id"]
    pos=db_exec("SELECT * FROM positions WHERE user_id=? ORDER BY updated_at DESC",[uid],"all")
    orders=db_exec("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 100",[uid],"all")
    funds=db_exec("SELECT * FROM funds WHERE user_id=?",[uid],"one") or {}
    recs=db_exec("SELECT * FROM recommendations WHERE user_id=? ORDER BY created_at DESC LIMIT 30",[uid],"all")
    open_pos=[p for p in pos if str(p.get("status") or "OPEN").upper()=="OPEN" and int(p.get("quantity") or 0)>0]
    idents=[str(p.get("instrument_key") or p.get("symbol")) for p in open_pos if str(p.get("instrument_key") or p.get("symbol"))]
    qmap={}
    if idents:
        try:
            qs=await asyncio.to_thread(UPSTOX.quotes, idents[:200])
            for q in qs:
                k=str(q.get("instrument_key") or q.get("symbol") or "").upper(); qmap[k]=q
        except Exception: pass
    out_pos=[]
    unreal=0.0
    for p in pos:
        key=str(p.get("instrument_key") or p.get("symbol")); q=qmap.get(key.upper()) or qmap.get(str(p.get("symbol") or "").upper()) or {}
        ltp=q.get("ltp")
        qty=int(p.get("quantity") or 0); avg=float(p.get("avg_price") or 0); side=str(p.get("side") or "BUY").upper()
        pnl=(float(ltp)-avg)*qty if ltp is not None and side=="BUY" else (avg-float(ltp))*qty if ltp is not None else float(p.get("unrealized_pnl") or 0)
        if str(p.get("status") or "OPEN").upper()=="OPEN": unreal += pnl
        row={**p,"ltp":ltp,"unrealized_pnl":round(pnl,2),"status_display":"OPEN" if str(p.get("status") or "OPEN").upper()=="OPEN" else "CLOSED"}
        out_pos.append(row)
    realized=float(funds.get("realized_pnl") or 0)
    status_map={"PAPER_FILLED":"FILLED","FILLED":"FILLED","PAPER_REJECTED":"REJECTED","REJECTED":"REJECTED","CANCELLED":"CANCELLED","AMO_QUEUED":"AMO QUEUED","PENDING":"PENDING"}
    for o in orders:
        q=qmap.get(str(o.get("instrument_key") or "").upper()) or qmap.get(str(o.get("symbol") or "").upper())
        o["ltp"]=q.get("ltp") if q else None; o["status_display"]=status_map.get(str(o.get("status") or "").upper(),str(o.get("status") or "UNKNOWN").upper())
    return {"user_id":uid,"paper":True,"funds":funds,"positions":out_pos,"orders":orders,"recommendations":recs,"portfolio":{"open_count":len(open_pos),"unrealized_pnl":round(unreal,2),"realized_pnl":round(realized,2),"net_pnl":round(realized+unreal,2)},"timestamp":now_iso()}

@app.post("/api/positions/{position_id}/square-off")
async def position_square_off(position_id: str, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    pos=db_exec("SELECT * FROM positions WHERE id=? AND user_id=?",[position_id,user["id"]],"one")
    if not pos: raise HTTPException(404,"Position not found")
    if str(pos.get("status") or "OPEN")!="OPEN": return {"ok":True,"position":pos,"final_pnl":pos.get("final_pnl")}
    key=str(pos.get("instrument_key") or pos.get("symbol"))
    try: exit_price=float((await asyncio.to_thread(UPSTOX.ltp,key)).get("ltp") or 0)
    except Exception: exit_price=0
    if exit_price<=0: raise HTTPException(503,"Unable to obtain live exit price")
    close_side="SELL" if str(pos.get("side") or "BUY").upper()=="BUY" else "BUY"
    order={"symbol":pos.get("symbol"),"instrument_key":key,"side":close_side,"quantity":int(pos.get("quantity") or 0),"price":exit_price,"fill_price":exit_price,"paper":1,"product":"I","underlying":pos.get("underlying"),"instrument_kind":pos.get("instrument_kind"),"fund_bucket":pos.get("fund_bucket") or "trading","auto_trade":str(pos.get("fund_bucket") or "").lower()=="auto_trade"}
    result=_paper_fill(user["id"],order,pos.get("recommendation_id"))
    pnl=float((result or {}).get("realized_pnl") or 0)
    await add_notification(user["id"],"position_closed","success" if pnl>=0 else "warning",90,f"Position squared off · {pos['symbol']}",f"Exit ₹{exit_price:,.2f} · Final P&L ₹{pnl:,.2f}",f"position-squareoff:{position_id}")
    return {"ok":True,"final_pnl":pnl,"exit_price":exit_price,"position":db_exec("SELECT * FROM positions WHERE id=? AND user_id=?",[position_id,user["id"]],"one")}

@app.get("/api/holdings")
async def holdings(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    local = db_exec("SELECT * FROM holdings WHERE user_id=? ORDER BY updated_at DESC", [user["id"]], "all")
    provider = None
    if UPSTOX_ACCESS_TOKEN:
        try:
            provider = UPSTOX.holdings()
        except Exception:
            provider = None
    return {"user_id": user["id"], "items": local, "provider": provider}

# ---------------------------------------------------------------------------
# Auto trade / threshold crossing
# ---------------------------------------------------------------------------

async def add_notification(user_id: int, category: str, severity: str, materiality: float, title: str, body: str, dedupe_key: str | None = None) -> None:
    if dedupe_key:
        existing = db_exec("SELECT id FROM notifications WHERE user_id=? AND dedupe_key=? AND created_at >= ?", [user_id, dedupe_key, (datetime.now(timezone.utc)-timedelta(hours=6)).isoformat()], "one")
        if existing:
            return
    nid = secrets.token_hex(12)
    db_exec("INSERT INTO notifications(id,user_id,category,severity,materiality,title,body,unread,dedupe_key,created_at) VALUES(?,?,?,?,?,?,?,?,?,?)", [nid,user_id,category,severity,float(materiality),title,body,1,dedupe_key,now_iso()])
    await EVENT_BUS.publish({"type": "notification", "id": nid, "user_id": user_id, "category": category, "severity": severity, "materiality": materiality, "title": title, "body": body, "timestamp": now_iso()})


@app.get("/api/notifications")
async def notifications(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    items = db_exec("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 200", [user["id"]], "all")
    try:
        session = db_exec("SELECT started_at FROM login_sessions WHERE user_id=? AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1", [user["id"]], "one")
        if session:
            since = session["started_at"]
        else:
            prior = db_exec("SELECT ended_at FROM login_sessions WHERE user_id=? AND ended_at IS NOT NULL ORDER BY ended_at DESC LIMIT 1", [user["id"]], "one")
            since = prior["ended_at"] if prior else None
        if since and (_news_key_pool("GNEWS_API_KEY") or _news_key_pool("NEWSAPI_API_KEY") or _news_key_pool("UPSTOX_ACCESS_TOKEN")):
            news = news_result("India stock market NSE BSE NIFTY earnings RBI", 8, "GLOBAL").get("events") or []
            for n in news:
                title = n.get("headline") or n.get("title")
                published = n.get("published_at") or n.get("publishedAt") or n.get("published")
                if title and (not published or str(published) >= str(since)):
                    items.append({"id":"news-"+hashlib.sha1(title.encode()).hexdigest()[:16],"user_id":user["id"],"category":"news","severity":"info","materiality":50,"title":title,"body":n.get("description") or n.get("source") or "Market news","unread":1,"created_at":published or now_iso()})
        items.sort(key=lambda x: str(x.get("created_at") or ""), reverse=True)
    except Exception:
        pass
    return {"items": items[:200]}

@app.get("/api/notifications/unread")
async def unread_notifications(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {"items": db_exec("SELECT * FROM notifications WHERE user_id=? AND unread=1 ORDER BY created_at DESC", [user["id"]], "all")}


@app.post("/api/notifications/read-all")
async def read_all_notifications(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    db_exec("UPDATE notifications SET unread=0 WHERE user_id=?", [user["id"]])
    return {"ok": True}


@app.get("/api/news/interests")
async def get_news_interests(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    row=db_exec("SELECT value_json FROM settings WHERE user_id=? AND key='news_interests'",[user["id"]],"one")
    try: items=json.loads(row.get("value_json") or "[]") if row else []
    except Exception: items=[]
    items=[str(x).upper().strip() for x in items if str(x).strip()]
    return {"items":list(dict.fromkeys(items))}

@app.put("/api/news/interests")
async def save_news_interests(payload: dict[str,Any], user: dict[str,Any] = Depends(require_user)) -> dict[str,Any]:
    raw=payload.get("items") or []
    if not isinstance(raw,list): raise HTTPException(422,"items must be a list")
    items=[]
    for x in raw:
        v=str(x).upper().strip()
        if v and v not in items: items.append(v)
    items=items[:100]
    db_exec("INSERT INTO settings(user_id,key,value_json) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value_json=excluded.value_json",[user["id"],"news_interests",json.dumps(items)])
    return {"ok":True,"items":items}

@app.get("/api/observations")
async def observations(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    return {"items": db_exec("SELECT * FROM observations WHERE user_id=? ORDER BY created_at DESC LIMIT 200", [user["id"]], "all")}


@app.get("/api/notifications/greeks-watch")
async def greek_watch(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    symbols=user_watchlist_symbols(user["id"])
    prev_row=db_exec("SELECT value_json FROM settings WHERE user_id=? AND key=?",[user["id"],"greek_watch_state"],"one")
    try: prev=json.loads(prev_row.get("value_json") or "{}") if prev_row else {}
    except Exception: prev={}
    cur={}; changes=[]
    # Monitor liquid contracts first, but only contracts where 3 lots fit within ₹10,000.
    for sym in symbols[:20]:
        try:
            chain=UPSTOX.option_chain(sym,None); candidates=[]
            for st in chain.get("strikes") or []:
                for side in ("call","put"):
                    c=st.get(side) or {}; key=c.get("instrument_key") or c.get("instrument_token"); lot=int(c.get("lot_size") or 0); premium=float(c.get("ltp") or 0)
                    if not key or lot<1 or premium<=0 or premium*lot*3>10000: continue
                    candidates.append((int(c.get("volume") or 0),int(c.get("oi") or 0),st.get("strike"),side,c,key,lot,premium))
            candidates.sort(key=lambda x:(x[0],x[1]),reverse=True)
            for volume,oi,strike,side,c,key,lot,premium in candidates[:10]:
                g=c.get("greeks") or c.get("option_greeks") or {}
                snap={k:float(g.get(k)) for k in ("delta","gamma","theta","vega","iv") if g.get(k) is not None}
                cur[str(key)]={"symbol":sym,"strike":strike,"side":side.upper(),"lot_size":lot,"premium":premium,"volume":volume,"oi":oi,**snap}
                old=prev.get(str(key))
                if old:
                    diffs=[]
                    thresholds={"delta":0.02,"gamma":0.01,"theta":0.10,"vega":0.10,"iv":0.50}
                    for k,v in snap.items():
                        if old.get(k) is not None and abs(float(v)-float(old[k]))>=thresholds.get(k,0.05): diffs.append(f"{k}: {old.get(k):.4g} → {v:.4g}")
                    if diffs: changes.append({"symbol":sym,"strike":strike,"side":side.upper(),"changes":diffs[:5],"volume":volume,"oi":oi})
        except Exception: continue
    db_exec("INSERT INTO settings(user_id,key,value_json) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value_json=excluded.value_json",[user["id"],"greek_watch_state",json.dumps(cur)])
    for c in changes[:20]:
        await add_notification(user["id"],"greek_change","info",55,f"Greeks changed · {c['symbol']} {c['side']} {c['strike']}"," · ".join(c["changes"])+f" · Vol {c['volume']:,}",f"greek:{c['symbol']}:{c['side']}:{c['strike']}")
    return {"checked":len(cur),"changes":changes}

@app.get("/api/notifications/monitor")
async def notification_monitor(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    symbols=user_watchlist_symbols(user["id"])
    if not symbols: return {"checked":0,"events":[]}
    state_row=db_exec("SELECT value_json FROM settings WHERE user_id=? AND key=?",[user["id"],"notification_monitor_state"],"one")
    try: state=json.loads(state_row.get("value_json") or "{}") if state_row else {}
    except Exception: state={}
    idx=int(state.get("idx",0)); sym=symbols[idx%len(symbols)]; state["idx"]=(idx+1)%max(1,len(symbols)); events=[]
    try:
        q=UPSTOX.quote(sym); ltp=float(q.get("ltp") or 0); prev=state.get("quotes",{}).get(sym,{})
        if ltp>0 and prev.get("ltp"):
            pct=(ltp-float(prev["ltp"]))/float(prev["ltp"])*100
            if abs(pct)>=2.0:
                await add_notification(user["id"],"sudden_move","warning" if abs(pct)>=4 else "info",70,f"Sudden move · {sym}",f"LTP ₹{ltp:,.2f} · {pct:+.2f}% since last check",f"sudden:{sym}")
                events.append("sudden_move")
        uc=q.get("upper_circuit"); lc=q.get("lower_circuit")
        if uc and ltp>=float(uc)*0.999:
            await add_notification(user["id"],"circuit","warning",90,f"Upper circuit · {sym}",f"LTP ₹{ltp:,.2f} is at/near upper circuit ₹{float(uc):,.2f}",f"uppercircuit:{sym}")
            events.append("upper_circuit")
        if lc and ltp<=float(lc)*1.001:
            await add_notification(user["id"],"circuit","warning",90,f"Lower circuit · {sym}",f"LTP ₹{ltp:,.2f} is at/near lower circuit ₹{float(lc):,.2f}",f"lowercircuit:{sym}")
            events.append("lower_circuit")
        state.setdefault("quotes",{})[sym]={"ltp":ltp,"at":now_iso()}
    except Exception: pass
    # Strong technical signals are market-only; do not generate NSE/BSE technical alerts after close.
    try:
        if not bool(market_session("MCX" if "MCX" in sym.upper() else "NSE_EQ").get("active")):
            mtf={"items":[]}
        else:
            mtf=await analysis_technical_mtf(sym,user)
        for r in mtf.get("items",[]):
            t=r.get("technical") or {}
            if r.get("signal")=="BUY" and float(t.get("trend_strength") or 0)>=65:
                await add_notification(user["id"],"technical_signal","success",80,f"Strong BUY · {sym} · {r['timeframe']}",f"Trend strength {float(t.get('trend_strength') or 0):.0f} · RSI {t.get('rsi')} · ADX {t.get('adx')}",f"strongbuy:{sym}:{r['timeframe']}")
                events.append("strong_buy")
    except Exception: pass
    # High-materiality fresh news.
    try:
        for feed_name, payload in (("stock",news_result(_target_news_query(sym),8,sym,user["id"])),("global",news_result("India RBI SEBI regulation geopolitics tariffs sanctions rates policy company",8,None,user["id"]))):
            for a in (payload.get("events") or [])[:8]:
                mat=float(a.get("materiality") or 0); k=article_key(a)
                if mat>=80:
                    await add_notification(user["id"],"material_news","warning",mat,f"High-materiality {feed_name} news · {sym}",a.get("headline") or a.get("title") or "Material news",f"materialnews:{k}")
                    events.append("material_news")
    except Exception: pass
    # Provider-side executions, including auto-trade/paper-to-live transitions.
    try:
        provider_orders=(UPSTOX.orders().get("data") or []) if UPSTOX_ACCESS_TOKEN else []
        for po in provider_orders[:100]:
            status=str(po.get("status") or po.get("order_status") or "").upper()
            if status in {"COMPLETE","TRADED","FILLED"}:
                oid=str(po.get("order_id") or po.get("id") or "")
                if oid:
                    await add_notification(user["id"],"order_execution","success",85,f"Order executed · {po.get('trading_symbol') or po.get('symbol') or 'Order'}",f"{status} · Qty {po.get('quantity') or po.get('filled_quantity') or '—'}",f"provider-execution:{oid}")
                    events.append("order_execution")
    except Exception: pass
    # Order status and realized P&L changes.
    try:
        orders=db_exec("SELECT id,symbol,status,execution_state,final_pnl,updated_at FROM orders WHERE user_id=? ORDER BY updated_at DESC LIMIT 100",[user["id"]],"all")
        old_orders=state.get("orders",{})
        for o in orders:
            k=o["id"]; prev_o=old_orders.get(k)
            cur_status=f"{o.get('status')}|{o.get('execution_state')}|{o.get('final_pnl')}"
            if prev_o and prev_o!=cur_status:
                await add_notification(user["id"],"order_update","info",75,f"Order update · {o['symbol']}",f"{o.get('status')} · {o.get('execution_state')}",f"orderstatus:{k}:{cur_status}")
                events.append("order_update")
            old_orders[k]=cur_status
        state["orders"]=old_orders
    except Exception: pass
    db_exec("INSERT INTO settings(user_id,key,value_json) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value_json=excluded.value_json",[user["id"],"notification_monitor_state",json.dumps(state)])
    return {"checked":1,"symbol":sym,"events":events,"timestamp":now_iso()}

def _parse_option_contract_rows(chain: dict[str, Any]) -> list[dict[str, Any]]:
    rows=[]
    for st in chain.get("strikes") or []:
        for side in ("call","put"):
            c=st.get(side) or {}
            key=c.get("instrument_key")
            if not key or c.get("ltp") is None:
                continue
            rows.append({
                "side": "CE" if side=="call" else "PE",
                "strike": float(st.get("strike") or 0),
                **c,
            })
    return rows

def option_trade_candidate(underlying: str, direction: str, max_candidates: int = 16) -> dict[str, Any]:
    """Choose a defined-risk long option using Greeks + option TA + underlying/news evidence."""
    direction=str(direction).upper()
    if direction not in {"BUY","SELL"}:
        return {"available":False,"reason":"Direction is not directional"}
    chain=UPSTOX.option_chain(underlying,None)
    contracts=_parse_option_contract_rows(chain)
    spot=float(chain.get("spot") or 0)
    if not contracts or spot<=0:
        return {"available":False,"reason":"No live option contracts returned"}
    # Prefer liquid, near-ATM contracts with a useful delta for long premium.
    desired_type="CE" if direction=="BUY" else "PE"
    scored=[]
    news=recommendation_news_evidence(underlying)
    news_score=(1 if news.get("stock",{}).get("signal")=="BUY" else -1 if news.get("stock",{}).get("signal")=="SELL" else 0)
    if news_score and ((direction=="BUY" and news_score<0) or (direction=="SELL" and news_score>0)) and max(float(news.get("stock",{}).get("materiality") or 0),float(news.get("global",{}).get("materiality") or 0))>=70:
        return {"available":False,"reason":"Material news conflicts with the underlying directional signal","news":news}
    candidates=[c for c in contracts if c["side"]==desired_type]
    candidates.sort(key=lambda c:(abs(float(c.get("strike") or 0)-spot),-int(c.get("volume") or 0),-int(c.get("oi") or 0)))
    for c in candidates[:max_candidates]:
        try:
            delta=float(c.get("delta") or 0); gamma=float(c.get("gamma") or 0); theta=float(c.get("theta") or 0); vega=float(c.get("vega") or 0); iv=float(c.get("iv") or 0)
            vol=int(c.get("volume") or 0); oi=int(c.get("oi") or 0); ltp=float(c.get("ltp") or 0)
            # Long call/put selection: target moderate delta, avoid extreme IV/theta when possible.
            abs_delta=abs(delta)
            greek_score=max(0.0,100.0 - abs(abs_delta-0.50)*220.0 - abs(theta)*4.0 - max(iv-60.0,0)*0.5)
            liquidity=min(100.0,(vol/50000.0)*55.0+(oi/200000.0)*45.0)
            opt_candles=UPSTOX.candles(str(c["instrument_key"]),"5","minutes",days=5)
            opt_ta=technical_analysis(opt_candles)
            opt_patterns=detect_candlestick_patterns(opt_candles,"5m")
            opt_signal=opt_ta.get("trend") or "NO_TRADE"
            ta_score=100.0 if opt_signal=="BUY" else 55.0 if opt_signal=="NO_TRADE" else 10.0
            if direction=="SELL":
                ta_score=100.0 if opt_signal=="BUY" else 55.0 if opt_signal=="NO_TRADE" else 10.0
            if opt_patterns and any((direction=="BUY" and str(p.get("prediction","" )).lower().startswith("bullish")) or (direction=="SELL" and str(p.get("prediction","" )).lower().startswith("bullish")) for p in opt_patterns[-3:]):
                ta_score=min(100.0,ta_score+8.0)
            alignment=100.0 if direction=="BUY" and news_score>=0 or direction=="SELL" and news_score<=0 else 30.0
            score=round(0.35*greek_score+0.30*ta_score+0.20*alignment+0.15*liquidity,2)
            scored.append({"contract":c,"score":score,"greek_score":round(greek_score,2),"technical_score":round(ta_score,2),"liquidity_score":round(liquidity,2),"news_score":round(alignment,2),"option_technical":opt_ta,"news":news})
        except Exception as exc:
            continue
    if not scored:
        return {"available":False,"reason":"No option passed Greeks/technical checks","news":news}
    scored.sort(key=lambda x:x["score"],reverse=True)
    best=scored[0]; c=best["contract"]
    return {"available":True,"instrument_kind":"OPTION","underlying":underlying,"direction":direction,"transaction_side":"BUY","instrument_key":c.get("instrument_key"),"option_type":c.get("side"),"strike":c.get("strike"),"expiry":c.get("expiry") or chain.get("expiry"),"entry":float(c.get("ltp") or 0),"lot_size":int(c.get("lot_size") or 1),"score":best["score"],"greeks":{"delta":c.get("delta"),"gamma":c.get("gamma"),"theta":c.get("theta"),"vega":c.get("vega"),"iv":c.get("iv"),"pop":c.get("pop")},"technical":best["option_technical"],"news":best["news"],"basis":{"greeks":best["greek_score"],"option_technical":best["technical_score"],"news":best["news_score"],"liquidity":best["liquidity_score"]},"candidates":scored[:5]}

def auto_trade_candidate(symbol: str, options_enabled: bool = True) -> dict[str, Any]:
    key=f"auto-analysis:{str(symbol).upper()}:{int(options_enabled)}"
    cached=CACHE.get(key)
    if cached is not None: return cached
    tfs=["5m","15m","60m","1D"]
    def one(tf):
        try:
            days=30 if tf in {"5m","15m"} else 90 if tf=="60m" else 365
            candles=analysis_candles_robust(symbol,tf,days); ta=technical_analysis(candles); pats=detect_candlestick_patterns(candles,tf)
            return {"timeframe":tf,"signal":ta.get("trend","NEUTRAL"),"technical":ta,"patterns":pats[-3:]}
        except Exception as exc: return {"timeframe":tf,"signal":"N/A","technical":{},"patterns":[],"error":safe_text(exc)}
    with ThreadPoolExecutor(max_workers=4) as pool: items=list(pool.map(one,tfs))
    news=recommendation_news_evidence(symbol)
    buy=sum(1 for x in items if x.get("signal")=="BUY"); sell=sum(1 for x in items if x.get("signal")=="SELL")
    strong_buy=sum(1 for x in items if x.get("signal")=="BUY" and float((x.get("technical") or {}).get("trend_strength") or 0)>=55)
    strong_sell=sum(1 for x in items if x.get("signal")=="SELL" and float((x.get("technical") or {}).get("trend_strength") or 0)>=55)
    ns=1 if news.get("stock",{}).get("signal")=="BUY" else -1 if news.get("stock",{}).get("signal")=="SELL" else 0
    technical_side="BUY" if buy>=3 or (buy>=2 and strong_buy>=2) else "SELL" if sell>=3 or (sell>=2 and strong_sell>=2) else "WAIT"
    if technical_side=="BUY" and ns<0 and float(news.get("stock",{}).get("materiality") or 0)>=65: technical_side="WAIT"
    if technical_side=="SELL" and ns>0 and float(news.get("stock",{}).get("materiality") or 0)>=65: technical_side="WAIT"
    score=max(0,min(99,50+strong_buy*9-strong_sell*9+(buy-sell)*5+(7 if ns>0 and technical_side=="BUY" else -7 if ns<0 and technical_side=="SELL" else 0)))
    result={"symbol":symbol,"signal":technical_side,"score":round(score,1),"timeframes":items,"news":news,"instrument_kind":"EQUITY","basis":[f"{x['timeframe']}: {x['signal']} · RSI {(x.get('technical') or {}).get('rsi')} · ADX {(x.get('technical') or {}).get('adx')} · Trend strength {(x.get('technical') or {}).get('trend_strength')}" for x in items],"reason":f"{technical_side} · score {score:.0f}/99 · {buy} bullish vs {sell} bearish timeframes"}
    if options_enabled and technical_side in {"BUY","SELL"}:
        try:
            opt=option_trade_candidate(symbol,technical_side)
            result["option_candidate"]=opt
            if opt.get("available") and opt.get("score",0)>=62:
                result["trade_instrument"]={"kind":"OPTION","symbol":opt.get("instrument_key"),"transaction_side":"BUY","instrument_key":opt.get("instrument_key"),"display":f"{symbol} {opt.get('option_type')} {opt.get('strike')} {opt.get('expiry')}","entry":opt.get("entry"),"lot_size":opt.get("lot_size"),"option_type":opt.get("option_type"),"strike":opt.get("strike"),"expiry":opt.get("expiry")}
                result["reason"] += f" · selected option {result['trade_instrument']['display']} · option score {opt['score']:.0f}"
        except Exception as exc:
            result["option_candidate"]={"available":False,"reason":safe_text(exc)}
    if not result.get("trade_instrument"):
        entry=float((items[0].get("technical") or {}).get("last") or 0) if items else 0
        result["trade_instrument"]={"kind":"EQUITY","symbol":symbol,"instrument_key":None,"display":symbol,"entry":entry,"lot_size":1,"transaction_side":technical_side}
    ti=result["trade_instrument"]
    if ti.get("entry"):
        if ti.get("kind")=="OPTION":
            opt_ta=(result.get("option_candidate") or {}).get("technical") or {}
            a=float(opt_ta.get("atr") or max(float(ti["entry"])*0.05,0.05))
            # Long premium: cap downside and demand a meaningful upside multiple.
            ti["stop_loss"]=max(0.01,float(ti["entry"])-max(a*1.0,float(ti["entry"])*0.08))
            ti["target"]=float(ti["entry"])+max(a*2.5,float(ti["entry"])*0.20)
        else:
            ta_last=next((x.get("technical") for x in items if x.get("technical",{}).get("last") is not None),{})
            levels=trade_levels(result["signal"],float(ti["entry"]),ta_last.get("atr"),ta_last.get("support"),ta_last.get("resistance"),None,None)
            ti["stop_loss"]=levels.get("stop_loss"); ti["target"]=levels.get("target")
        risk=abs(float(ti["entry"])-float(ti.get("stop_loss") or 0))
        reward=abs(float(ti.get("target") or 0)-float(ti["entry"]))
        rr=(reward/risk) if risk else 0
        ti["risk_reward"]=round(rr,3)
        ti["expected_risk_per_unit"]=round(risk,4)
        ti["expected_reward_per_unit"]=round(reward,4)
        if rr < 2.5 or reward <= 0:
            result["signal"]="WAIT"
            result["reason"] += " · Rejected: risk/reward below 2.5R"
    CACHE.set(key,result,_ANALYSIS_CACHE_TTL)
    return result

def _save_auto_recommendation(user_id: int, analysis: dict[str,Any]) -> dict[str,Any]:
    instrument=analysis.get("trade_instrument") or {}
    symbol=str(instrument.get("symbol") or analysis.get("symbol") or "").upper()
    side=str(analysis.get("signal") or "WAIT").upper()
    entry=instrument.get("entry")
    score=float(analysis.get("score") or 0)
    basis={"analysis":analysis,"options":analysis.get("option_candidate")}
    latest=db_exec("SELECT * FROM recommendations WHERE user_id=? AND COALESCE(underlying,symbol)=? ORDER BY created_at DESC LIMIT 1",[user_id,analysis.get("symbol") or symbol],"one")
    latest_status=str((latest or {}).get("status") or "").upper()
    if latest and latest.get("created_at") and latest_status in {"NEW","GENERATED"} and (datetime.now(timezone.utc)-datetime.fromisoformat(str(latest["created_at"]).replace("Z","+00:00"))).total_seconds()<120 and str(latest.get("recommendation"))==side:
        return latest
    rid=secrets.token_hex(12); now=now_iso()
    db_exec("INSERT INTO recommendations(id,user_id,source,symbol,recommendation,timeframe,entry,target,stop_loss,rationale,technical_basis,news_basis,option_basis,created_at,underlying,instrument_key,instrument_kind,option_side,option_strike,option_expiry,score,status) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",[rid,user_id,"auto",symbol,side,"5m",entry,instrument.get("target"),instrument.get("stop_loss"),analysis.get("reason"),json.dumps(analysis.get("timeframes"),default=str),json.dumps(analysis.get("news"),default=str),json.dumps(analysis.get("option_candidate"),default=str) if analysis.get("option_candidate") else None,now,analysis.get("symbol"),instrument.get("instrument_key"),instrument.get("kind"),instrument.get("option_type"),instrument.get("strike"),instrument.get("expiry"),score,"NEW"] )
    return db_exec("SELECT * FROM recommendations WHERE id=?",[rid],"one")

def _position_mark_and_pnl(user_id: int) -> None:
    rows=db_exec("SELECT * FROM positions WHERE user_id=? AND COALESCE(status,'OPEN')='OPEN'",[user_id],"all")
    if not rows:
        return
    identifiers=[str(p.get("instrument_key") or p.get("symbol")) for p in rows if str(p.get("instrument_key") or p.get("symbol"))]
    quote_rows=[]
    try:
        quote_rows=UPSTOX.quotes(identifiers[:200])
    except Exception:
        quote_rows=[]
    qmap={}
    for q in quote_rows:
        for k in (q.get("instrument_key"), q.get("instrument"), q.get("symbol")):
            if k: qmap[str(k).upper()]=q
    total_unreal=0.0
    for p in rows:
        try:
            ident=str(p.get("instrument_key") or p.get("symbol"))
            q=qmap.get(ident.upper()) or qmap.get(str(p.get("symbol") or "").upper())
            if not q or q.get("ltp") is None: continue
            ltp=float(q.get("ltp") or 0)
            if ltp<=0: continue
            avg=float(p.get("avg_price") or 0); qty=int(p.get("quantity") or 0); side=str(p.get("side") or "BUY").upper()
            pnl=(ltp-avg)*qty if side=="BUY" else (avg-ltp)*qty
            total_unreal+=pnl
            db_exec("UPDATE positions SET unrealized_pnl=?,updated_at=? WHERE id=? AND user_id=?",[pnl,now_iso(),p["id"],user_id])
        except Exception: continue
    db_exec("UPDATE funds SET unrealized_pnl=?,updated_at=? WHERE user_id=?",[total_unreal,now_iso(),user_id])

def _paper_fill(user_id:int, order:dict[str,Any], recommendation_id:str|None=None) -> dict[str,Any]:
    """Paper fill engine with real local funds, long/short netting and reserved capital."""
    symbol=str(order.get("symbol") or "").upper(); key=order.get("instrument_key") or symbol
    requested_side=str(order.get("side") or "BUY").upper(); qty=int(order.get("quantity") or 0)
    price=float(order.get("fill_price") or order.get("price") or 0)
    bucket=str(order.get("fund_bucket") or ("auto_trade" if order.get("auto_trade") else "trading")).lower()
    if bucket not in {"trading","auto_trade","testing"}: bucket="trading"
    if price<=0:
        try: price=float(UPSTOX.quote(str(key)).get("ltp") or 0)
        except Exception: price=0
    if price<=0 or qty<=0: raise HTTPException(503,"Live price unavailable for paper fill")
    pos=db_exec("SELECT * FROM positions WHERE user_id=? AND instrument_key=? AND COALESCE(status,'OPEN')='OPEN'",[user_id,key],"one")
    if pos and pos.get("fund_bucket"):
        bucket=str(pos.get("fund_bucket") or bucket).lower()
    funds=db_exec("SELECT * FROM funds WHERE user_id=?",[user_id],"one") or {}
    free=float(funds.get(f"{bucket}_funds") or 0)
    used=float(funds.get("used") or 0)
    now=now_iso(); notional=price*qty
    if not pos:
        if free+1e-9 < notional: raise HTTPException(422,f"Insufficient {bucket.replace('_',' ')} funds")
        pid=secrets.token_hex(12)
        db_exec(f"UPDATE funds SET {bucket}_funds=?, used=?, updated_at=? WHERE user_id=?",[free-notional,used+notional,now,user_id])
        db_exec("INSERT INTO positions(id,user_id,symbol,instrument_key,side,quantity,avg_price,stop_loss,target,realized_pnl,unrealized_pnl,opened_at,updated_at,recommendation_id,underlying,instrument_kind,status,reserved_value,fund_bucket) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",[pid,user_id,symbol,key,requested_side,qty,price,order.get("stop_loss"),order.get("target"),0,0,now,now,recommendation_id,order.get("underlying") or symbol,order.get("instrument_kind") or ("OPTION" if "NSE_FO" in str(key).upper() else "EQUITY"),"OPEN",notional,bucket])
        return db_exec("SELECT * FROM positions WHERE id=?",[pid],"one")
    old_side=str(pos.get("side") or "BUY").upper(); old_qty=int(pos.get("quantity") or 0); old_avg=float(pos.get("avg_price") or 0); old_reserved=float(pos.get("reserved_value") or (old_avg*old_qty)); pos_bucket=str(pos.get("fund_bucket") or bucket)
    if old_side==requested_side:
        new_qty=old_qty+qty; new_avg=((old_avg*old_qty)+(price*qty))/new_qty; add_reserve=notional
        if free+1e-9 < notional: raise HTTPException(422,f"Insufficient {bucket.replace('_',' ')} funds")
        db_exec(f"UPDATE funds SET {bucket}_funds=?, used=?, updated_at=? WHERE user_id=?",[free-notional,used+notional,now,user_id])
        db_exec("UPDATE positions SET quantity=?,avg_price=?,reserved_value=?,updated_at=?,recommendation_id=COALESCE(?,recommendation_id) WHERE id=? AND user_id=?",[new_qty,new_avg,old_reserved+add_reserve,now,recommendation_id,pos["id"],user_id])
    else:
        close_qty=min(old_qty,qty)
        pnl=(price-old_avg)*close_qty if old_side=="BUY" else (old_avg-price)*close_qty
        release=old_reserved*(close_qty/max(old_qty,1))
        new_free=free+release+pnl; new_used=used-release
        remaining=old_qty-close_qty
        new_qty=qty-close_qty
        if new_qty>0:
            new_reserve=price*new_qty
            if new_free+1e-9 < new_reserve: raise HTTPException(422,"Insufficient funds to reverse into the new position")
            new_free-=new_reserve; new_used+=new_reserve
        db_exec(f"UPDATE funds SET {bucket}_funds=?, used=?, realized_pnl=realized_pnl+?, updated_at=? WHERE user_id=?",[new_free,new_used,pnl,now,user_id])
        if remaining>0:
            db_exec("UPDATE positions SET quantity=?,reserved_value=?,realized_pnl=realized_pnl+?,updated_at=?,recommendation_id=COALESCE(?,recommendation_id) WHERE id=? AND user_id=?",[remaining,max(0,old_reserved-release),pnl,now,recommendation_id,pos["id"],user_id])
        else:
            db_exec("UPDATE positions SET quantity=0,status='CLOSED',exit_price=?,final_pnl=COALESCE(final_pnl,0)+?,realized_pnl=realized_pnl+?,reserved_value=0,unrealized_pnl=0,closed_at=?,updated_at=? WHERE id=? AND user_id=?",[price,pnl,pnl,now,now,pos["id"],user_id])
            if new_qty>0:
                pid=secrets.token_hex(12)
                db_exec("INSERT INTO positions(id,user_id,symbol,instrument_key,side,quantity,avg_price,stop_loss,target,realized_pnl,unrealized_pnl,opened_at,updated_at,recommendation_id,underlying,instrument_kind,status,reserved_value,fund_bucket) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",[pid,user_id,symbol,key,requested_side,new_qty,price,order.get("stop_loss"),order.get("target"),0,0,now,now,recommendation_id,order.get("underlying") or symbol,order.get("instrument_kind") or ("OPTION" if "NSE_FO" in str(key).upper() else "EQUITY"),"OPEN",price*new_qty,bucket])
    return db_exec("SELECT * FROM positions WHERE id=?",[pos["id"]],"one")


async def _auto_trade_cycle_user(user_id:int) -> dict[str,Any]:
    cfg=db_exec("SELECT * FROM auto_trade_configs WHERE user_id=?",[user_id],"one")
    if not cfg or not int(cfg.get("enabled") or 0): return {"enabled":False,"recommendations":0,"executed":0}
    try: configured=json.loads(cfg.get("symbols_json") or "[]")
    except Exception: configured=[]
    watch=user_watchlist_symbols(user_id)
    universe=list(dict.fromkeys([str(x).upper().strip() for x in (configured or watch) if str(x).strip()]))
    if watch: universe=list(dict.fromkeys([*watch,*universe]))
    universe=universe[:30]
    if not universe: return {"enabled":True,"recommendations":0,"executed":0,"reason":"No watchlist symbols configured"}
    executed=0; recs=0; skipped=0
    async def run_symbol(sym: str):
        try:
            analysis=await asyncio.to_thread(auto_trade_candidate,sym,bool(cfg.get("options_enabled")))
            rec=_save_auto_recommendation(user_id,analysis)
            if not rec or str(rec.get("status") or "NEW").upper() not in {"NEW","GENERATED"}: return (0,1)
            signal=str(rec.get("recommendation") or "WAIT").upper(); score=float(rec.get("score") or analysis.get("score") or 0)
            if signal not in {"BUY","SELL"} or score<65:
                db_exec("UPDATE recommendations SET status='NO_TRADE' WHERE id=? AND user_id=?",[rec.get("id"),user_id]); return (0,1)
            ti=analysis.get("trade_instrument") or {}; key=str(ti.get("instrument_key") or sym)
            tx_side=str(ti.get("transaction_side") or ("BUY" if ti.get("kind")=="OPTION" else signal)).upper()
            existing=db_exec("SELECT * FROM positions WHERE user_id=? AND instrument_key=? AND COALESCE(status,'OPEN')='OPEN'",[user_id,key],"one")
            if existing and str(existing.get("side"))==tx_side:
                db_exec("UPDATE recommendations SET status='SKIPPED_ALREADY_OPEN' WHERE id=? AND user_id=?",[rec.get("id"),user_id]); return (0,1)
            funds=db_exec("SELECT auto_trade_funds FROM funds WHERE user_id=?",[user_id],"one") or {}; available=float(funds.get("auto_trade_funds") or 0); cap=float(cfg.get("capital") or 0)
            trade_cap=min(available,cap) if cap>0 else available; entry=float(ti.get("entry") or 0)
            if entry<=0:
                try: entry=float(UPSTOX.quote(key).get("ltp") or 0)
                except Exception: entry=0
            lot=max(1,int(ti.get("lot_size") or 1))
            per_trade_cap=min(trade_cap, max(0.0, trade_cap*0.20))
            qty=lot*max(1,min(10,int(per_trade_cap/max(entry*lot,1)))) if entry>0 else 0
            risk_per_unit=abs(entry-float(ti.get("stop_loss") or entry))
            max_allowed_loss=float(cfg.get("max_loss") or 0)
            if max_allowed_loss>0 and risk_per_unit*qty > max_allowed_loss*0.50:
                db_exec("UPDATE recommendations SET status='SKIPPED_RISK' WHERE id=? AND user_id=?",[rec.get("id"),user_id]); return (0,1)
            if qty<=0 or entry*qty>available or entry*qty>per_trade_cap:
                db_exec("UPDATE recommendations SET status='SKIPPED_FUNDS' WHERE id=? AND user_id=?",[rec.get("id"),user_id]); return (0,1)
            order={"symbol":str(ti.get("display") or ti.get("symbol") or sym),"instrument_key":key,"side":tx_side,"quantity":qty,"price":entry,"fill_price":entry,"paper":1,"product":"I","stop_loss":ti.get("stop_loss"),"target":ti.get("target"),"underlying":sym,"instrument_kind":ti.get("kind") or "EQUITY","fund_bucket":"auto_trade","auto_trade":True}
            oid=secrets.token_hex(12); now=now_iso()
            db_exec("INSERT INTO orders(id,user_id,symbol,instrument_key,side,quantity,order_type,price,trigger_price,stop_loss,target,amo,status,execution_state,product,paper,created_at,updated_at,fund_bucket,recommendation_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",[oid,user_id,order["symbol"],key,tx_side,qty,"MARKET",entry,None,order.get("stop_loss"),order.get("target"),0,"PENDING","PENDING","I",1,now,now,"auto_trade",rec.get("id")])
            try: _paper_fill(user_id,order,rec.get("id"))
            except Exception as exc:
                db_exec("UPDATE orders SET status='REJECTED',execution_state='REJECTED',updated_at=? WHERE id=? AND user_id=?",[now_iso(),oid,user_id]); log.warning("Auto trade fill rejected %s: %s",sym,safe_text(exc)); return (0,1)
            db_exec("UPDATE orders SET status='PAPER_FILLED',execution_state='FILLED',price=?,updated_at=? WHERE id=? AND user_id=?",[entry,now_iso(),oid,user_id])
            db_exec("UPDATE recommendations SET status='EXECUTED',order_id=? WHERE id=? AND user_id=?",[oid,rec.get("id"),user_id])
            await add_notification(user_id,"auto_trade","success",82,f"Auto trade executed · {sym}",f"{signal} recommendation → {tx_side} {qty} of {order['symbol']}",f"auto-exec:{rec.get('id')}")
            return (1,0)
        except Exception as exc:
            log.warning("Auto trade cycle failed for %s/user %s: %s",sym,user_id,safe_text(exc)); return (0,1)
    for i in range(0,len(universe),3):
        batch=universe[i:i+3]
        results=await asyncio.gather(*(run_symbol(sym) for sym in batch))
        recs += len(batch)
        executed += sum(x[0] for x in results); skipped += sum(x[1] for x in results)
    try: _position_mark_and_pnl(user_id)
    except Exception: pass
    return {"enabled":True,"recommendations":recs,"executed":executed,"skipped":skipped,"symbols":universe}


async def _monitor_paper_positions_once() -> None:
    """Mark local paper positions and enforce SL/target/EOD without broker portfolio APIs."""
    users=db_exec("SELECT DISTINCT user_id FROM positions WHERE COALESCE(status,'OPEN')='OPEN'",[],"all")
    for row in users:
        uid=int(row["user_id"])
        positions=db_exec("SELECT * FROM positions WHERE user_id=? AND COALESCE(status,'OPEN')='OPEN' AND quantity>0",[uid],"all")
        if not positions: continue
        idents=[str(p.get("instrument_key") or p.get("symbol")) for p in positions if str(p.get("instrument_key") or p.get("symbol"))]
        try:
            quotes=UPSTOX.quotes(idents[:200])
        except Exception:
            quotes=[]
        qmap={str(q.get("instrument_key") or q.get("symbol") or q.get("instrument")).upper():q for q in quotes if q}
        nse_open=bool(market_session("NSE_EQ").get("active")); mcx_open=bool(market_session("MCX").get("active"))
        for p in positions:
            key=str(p.get("instrument_key") or p.get("symbol")); q=qmap.get(key.upper()) or qmap.get(str(p.get("symbol") or "").upper())
            price=float(q.get("ltp") or 0) if q else 0
            if price<=0:
                try:
                    fq=UPSTOX.ltp(key)
                    price=float(fq.get("ltp") or 0)
                except Exception:
                    price=0
            if price>0:
                side=str(p.get("side") or "BUY").upper(); reason=threshold_crossed(side,price,p.get("stop_loss"),p.get("target"))
                instrument_kind=str(p.get("instrument_kind") or "EQUITY").upper()
                seg="MCX" if "MCX" in instrument_kind or str(key).upper().startswith("MCX") else "NSE_EQ"
                market_open=mcx_open if seg=="MCX" else nse_open
                if reason or not market_open:
                    close_side="SELL" if side=="BUY" else "BUY"
                    order={"symbol":p.get("symbol"),"instrument_key":key,"side":close_side,"quantity":int(p.get("quantity") or 0),"price":price,"fill_price":price,"paper":1,"product":"I","underlying":p.get("underlying"),"instrument_kind":p.get("instrument_kind"),"fund_bucket":p.get("fund_bucket") or "trading"}
                    try:
                        closed=_paper_fill(uid,order,p.get("recommendation_id"))
                        why=reason or "MARKET_CLOSE"
                        await add_notification(uid,"risk_event","success" if float(closed.get("final_pnl") or closed.get("realized_pnl") or 0)>=0 else "warning",95,f"Auto square-off · {p.get('symbol')}",f"{why} · Exit ₹{price:,.2f}",f"auto-squareoff:{p.get('id')}:{why}")
                    except Exception as exc:
                        log.warning("Paper risk close failed for %s/%s: %s",uid,p.get("symbol"),safe_text(exc))
        try: _position_mark_and_pnl(uid)
        except Exception: pass


async def _paper_risk_loop() -> None:
    while True:
        try:
            await _monitor_paper_positions_once()
        except Exception as exc:
            log.warning("Paper risk monitor failed: %s",safe_text(exc))
        await asyncio.sleep(2)


async def _auto_trade_loop() -> None:
    while True:
        try:
            session=market_session("NSE_EQ")
            if session.get("active"):
                users=db_exec("SELECT user_id FROM auto_trade_configs WHERE enabled=1",[],"all")
                for row in users:
                    uid=int(row.get("user_id"));
                    try: await _auto_trade_cycle_user(uid)
                    except Exception as exc: log.warning("Auto trade user cycle failed: %s",safe_text(exc))
        except Exception as exc:
            log.warning("Auto trade loop failed: %s",safe_text(exc))
        await asyncio.sleep(30)

    tfs=["5m","15m","60m","1D"]
    def one(tf):
        try:
            unit="days" if tf=="1D" else "hours" if tf=="60m" else "minutes"; interval="1" if tf in {"1D","60m"} else tf[:-1]; days=30 if tf in {"5m","15m"} else 90 if tf=="60m" else 365
            candles=analysis_candles_robust(symbol,tf,days); ta=technical_analysis(candles); pats=detect_candlestick_patterns(candles,tf)
            return {"timeframe":tf,"signal":ta.get("trend","NEUTRAL"),"technical":ta,"patterns":pats[-3:]}
        except Exception as exc: return {"timeframe":tf,"signal":"N/A","technical":{},"patterns":[],"error":safe_text(exc)}
    with ThreadPoolExecutor(max_workers=3) as pool: items=list(pool.map(one,tfs))
    news=recommendation_news_evidence(symbol); buy=sum(1 for x in items if x.get("signal")=="BUY"); sell=sum(1 for x in items if x.get("signal")=="SELL")
    strong_buy=sum(1 for x in items if x.get("signal")=="BUY" and float((x.get("technical") or {}).get("trend_strength") or 0)>=60)
    strong_sell=sum(1 for x in items if x.get("signal")=="SELL" and float((x.get("technical") or {}).get("trend_strength") or 0)>=60)
    news_score=(1 if news.get("stock",{}).get("signal")=="BUY" else -1 if news.get("stock",{}).get("signal")=="SELL" else 0)
    signal="BUY" if buy>=3 or (buy>=2 and strong_buy>=2 and news_score>=0) else "SELL" if sell>=3 or (sell>=2 and strong_sell>=2 and news_score<=0) else "WAIT"
    score=50 + strong_buy*9 - strong_sell*9 + (buy-sell)*6 + (8 if news_score>0 else -8 if news_score<0 else 0)
    score=max(0,min(99,score))
    basis=[]
    for x in items:
        t=x.get("technical") or {}; basis.append(f"{x['timeframe']}: {x['signal']} · RSI {t.get('rsi')} · ADX {t.get('adx')} · Trend strength {t.get('trend_strength')}")
    basis += [f"Bullish timeframes: {buy}/{len(items)}; strong BUY: {strong_buy}",f"Bearish timeframes: {sell}/{len(items)}; strong SELL: {strong_sell}",f"Stock news: {news.get('stock',{}).get('signal')} · materiality {news.get('stock',{}).get('materiality')}",f"Global news: {news.get('global',{}).get('signal')} · materiality {news.get('global',{}).get('materiality')}","Consensus requires multiple aligned timeframes and no strong conflicting material news."]
    return {"symbol":symbol,"signal":signal,"score":round(score,1),"timeframes":items,"news":news,"basis":basis[:10],"reason":f"{signal} · score {score:.0f}/99 · {buy} bullish vs {sell} bearish timeframes"}

@app.post("/api/auto-trade")
async def auto_trade_control(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    body=await request.json(); enabled=bool(body.get("enabled",False)); capital=float(body.get("capital") or 0); max_loss=float(body.get("max_loss") or 0)
    symbols=[str(x).upper() for x in (body.get("symbols") or []) if str(x).strip()][:30]
    categories=[str(x) for x in (body.get("categories") or [])][:10]; options_enabled=bool(body.get("options_enabled",False))
    if capital<0 or max_loss<0 or (max_loss and capital and max_loss>capital): raise HTTPException(422,"Max loss cannot exceed auto-trade capital")
    funds=db_exec("SELECT * FROM funds WHERE user_id=?",[user["id"]],"one") or {}
    available=float(funds.get("auto_trade_funds") or 0)
    if available<=0 and float(funds.get("trading_funds") or 0)>0:
        has_auto=db_exec("SELECT id FROM positions WHERE user_id=? AND COALESCE(fund_bucket,'trading')='auto_trade' AND COALESCE(status,'OPEN')='OPEN' LIMIT 1",[user["id"]],"one")
        if not has_auto:
            available=float(funds.get("trading_funds") or 0); db_exec("UPDATE funds SET auto_trade_funds=?,updated_at=? WHERE user_id=?",[available,now_iso(),user["id"]])
    if capital>available: raise HTTPException(422,f"Auto trade capital exceeds available auto-trade funds ({available:.2f})")
    market_open = bool(market_session("NSE_EQ").get("active"))
    # Preserve the user's enabled/configured intent after hours; execution remains paper/blocked until open.
    db_exec("INSERT INTO auto_trade_configs(user_id,enabled,capital,max_loss,symbols_json,categories_json,options_enabled,live_execution,updated_at) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(user_id) DO UPDATE SET enabled=excluded.enabled,capital=excluded.capital,max_loss=excluded.max_loss,symbols_json=excluded.symbols_json,categories_json=excluded.categories_json,options_enabled=excluded.options_enabled,updated_at=excluded.updated_at",[user["id"],int(enabled),capital,max_loss,json.dumps(symbols),json.dumps(categories),int(options_enabled),0,now_iso()])
    db_exec("INSERT INTO settings(user_id,key,value_json) VALUES(?,?,?) ON CONFLICT(user_id,key) DO UPDATE SET value_json=excluded.value_json",[user["id"],"auto_trade_enabled",json.dumps(enabled)])
    await add_notification(user["id"],"auto_trade_recommendation","info",40,f"Auto Trade {'enabled' if enabled else 'configured/paused'}",f"Capital ₹{capital:,.0f}; max loss ₹{max_loss:,.0f}")
    return await auto_trade_status(request,user)

@app.get("/api/auto-trade")
async def auto_trade_status(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    row=db_exec("SELECT * FROM auto_trade_configs WHERE user_id=?",[user["id"]],"one")
    if not row:
        row={"user_id":user["id"],"enabled":0,"capital":0,"max_loss":0,"symbols_json":"[]","categories_json":"[]","options_enabled":1,"live_execution":0}
    try: symbols=json.loads(row.get("symbols_json") or "[]")
    except Exception: symbols=[]
    watch=user_watchlist_symbols(user["id"]); universe=list(dict.fromkeys([*watch,*symbols]))[:30]
    history=db_exec("SELECT * FROM recommendations WHERE user_id=? ORDER BY created_at DESC LIMIT 30",[user["id"]],"all")
    suggestions=[]
    for rec in history:
        suggestions.append({"symbol":rec.get("underlying") or rec.get("symbol"),"reason":rec.get("rationale") or "Saved recommendation","analysis":{
            "score":rec.get("score"),
            "signal":rec.get("recommendation"),
            "entry":rec.get("entry"),
            "stop_loss":rec.get("stop_loss"),
            "target":rec.get("target"),
            "status":rec.get("status"),
            "instrument_kind":rec.get("instrument_kind"),
            "option_type":rec.get("option_side"),
            "strike":rec.get("option_strike"),
            "expiry":rec.get("option_expiry")}})
    return {"enabled":bool(row.get("enabled")),"authorized":False,"capital":float(row.get("capital") or 0),"max_loss":float(row.get("max_loss") or 0),"symbols":universe,"watchlist_symbols":watch,"categories":json.loads(row.get("categories_json") or "[]") if row.get("categories_json") else [],"options_enabled":bool(row.get("options_enabled")),"live_execution":False,"suggestions":suggestions[:10],"market":market_session("NSE_EQ"),"market_open":bool(market_session("NSE_EQ").get("active")),"user_id":user["id"]}


def threshold_crossed(side: str, price: float, stop_loss: float | None, target: float | None) -> str | None:
    if stop_loss is None and target is None:
        return None
    if side == "BUY":
        if stop_loss is not None and price <= stop_loss:
            return "STOP_LOSS"
        if target is not None and price >= target:
            return "TARGET"
    else:
        if stop_loss is not None and price >= stop_loss:
            return "STOP_LOSS"
        if target is not None and price <= target:
            return "TARGET"
    return None


@app.post("/api/risk/check/{position_id}")
async def risk_check(position_id: str, request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    pos = db_exec("SELECT * FROM positions WHERE id=? AND user_id=?", [position_id, user["id"]], "one")
    if not pos:
        raise HTTPException(404, "Position not found")
    ltp = UPSTOX.ltp(pos["symbol"])
    price = ltp.get("ltp")
    event = threshold_crossed(pos["side"], float(price), pos.get("stop_loss"), pos.get("target")) if price is not None else None
    return {"position": pos, "ltp": price, "threshold_crossed": event, "gap_aware": True, "timestamp": now_iso()}

# ---------------------------------------------------------------------------
# Error/diagnostic contract
# ---------------------------------------------------------------------------

@app.get("/api/server/logs")
async def server_logs(lines: int = Query(300, ge=20, le=1000), user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    try:
        if not LOG_FILE.exists():
            return {"lines": "No server log file exists yet.", "path": str(LOG_FILE), "timestamp": now_iso()}
        data = LOG_FILE.read_text(encoding="utf-8", errors="replace").splitlines()[-lines:]
        return {"lines": "\n".join(data), "path": str(LOG_FILE), "timestamp": now_iso()}
    except Exception as exc:
        return error_json("SERVER_LOG_UNAVAILABLE", safe_text(exc), 503)

@app.get("/api/errors")
async def errors(request: Request, user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    # Include both user-associated errors and system errors without secrets.
    rows = db_exec("SELECT id,category,provider,status_code,message,context_json,created_at FROM error_events WHERE user_id=? OR user_id IS NULL ORDER BY created_at DESC LIMIT 200", [user["id"]], "all")
    for r in rows:
        with contextlib.suppress(Exception):
            r["context"] = json.loads(r.pop("context_json") or "{}")
    return {"items": rows, "provider_health": {k: dict(v) for k, v in PROVIDER_HEALTH.items()}}

# ---------------------------------------------------------------------------
# WebSocket/event schema
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Upstox Market Data V3 WebSocket bridge
# ---------------------------------------------------------------------------
def _pb_fields(data: bytes):
    i=0; n=len(data)
    while i<n:
        # key = field_number << 3 | wire_type
        key=0; shift=0
        while i<n:
            b=data[i]; i+=1; key |= (b & 0x7f) << shift
            if not b & 0x80: break
            shift += 7
        field=key>>3; wire=key&7
        if wire==0:
            val=0; shift=0
            while i<n:
                b=data[i]; i+=1; val |= (b&0x7f)<<shift
                if not b&0x80: break
                shift += 7
            yield field,wire,val
        elif wire==1:
            yield field,wire,data[i:i+8]; i+=8
        elif wire==2:
            ln=0; shift=0
            while i<n:
                b=data[i]; i+=1; ln |= (b&0x7f)<<shift
                if not b&0x80: break
                shift += 7
            chunk=data[i:i+ln]; i+=ln; yield field,wire,chunk
        elif wire==5:
            yield field,wire,data[i:i+4]; i+=4
        else:
            break

def _pb_ltp(data: bytes):
    import struct
    ltp=None; cp=None; ltt=None; ltq=None
    for field,wire,val in _pb_fields(data):
        if wire==1 and field in (1,4):
            number=struct.unpack('<d',val)[0]
            if field==1: ltp=number
            else: cp=number
        elif wire==0:
            if field==2: ltt=val
            elif field==3: ltq=val
    return {"ltp":ltp,"cp":cp,"ltt":ltt,"ltq":ltq}

def _pb_extract_ltpc(feed_bytes: bytes):
    # Feed -> LTPC, FullFeed -> MarketFullFeed/IndexFullFeed -> LTPC, or FirstLevelWithGreeks -> LTPC.
    for field,wire,val in _pb_fields(feed_bytes):
        if wire!=2: continue
        if field==1:
            return _pb_ltp(val)
        if field==2:
            for ff_field,ff_wire,ff_val in _pb_fields(val):
                if ff_wire==2 and ff_field in (1,2):
                    for inner_field,inner_wire,inner_val in _pb_fields(ff_val):
                        if inner_wire==2 and inner_field==1:
                            return _pb_ltp(inner_val)
        if field==3:
            for inner_field,inner_wire,inner_val in _pb_fields(val):
                if inner_wire==2 and inner_field==1:
                    return _pb_ltp(inner_val)
    return {}

def _decode_upstox_feed(data: bytes):
    feeds={}
    for field,wire,val in _pb_fields(data):
        if field==2 and wire==2:
            key=None; feed_bytes=None
            for ef,ew,ev in _pb_fields(val):
                if ef==1 and ew==2: key=ev.decode('utf-8','ignore')
                elif ef==2 and ew==2: feed_bytes=ev
            if key and feed_bytes:
                feeds[key]=_pb_extract_ltpc(feed_bytes)
    return feeds

class MarketStreamManager:
    def __init__(self) -> None:
        self.lock=threading.RLock()
        self.desired: dict[str,set[int]]=defaultdict(set)
        self.ws=None
        self.thread: threading.Thread|None=None
        self.stop_event=threading.Event()
        self.connected=False
        self.last_ltp: dict[str,float]={}
        self.last_quote: dict[str,dict[str,Any]]={}
        self.key_labels: dict[str,str]={}
        self.last_publish_at: dict[str,float]={}
        self.sdk_streamer=None
        self.sdk_mode=False
        self._rate_limited_until=0.0
        self._fallback_pause_until=0.0
        self._fallback_thread: threading.Thread|None=None

    def _segment(self,key:str)->str:
        k=key.upper()
        if "_INDEX|" in k:
            return "NSE_INDEX" if k.startswith("NSE_INDEX|") else "BSE_INDEX"
        return "MCX" if k.startswith("MCX") or k.startswith("NSE_COM") or "COM" in k else "NSE_EQ"

    def _publish_tick(self,key:str,ltp:float,cp:float|None=None,ltt:Any=None,source:str="websocket",day_open:float|None=None) -> None:
        now=time.time(); label=self.key_labels.get(key)
        with self.lock:
            users=set(self.desired.get(key,set()))
            previous=self.last_ltp.get(key)
            prior=self.last_quote.get(key) or {}
            session_open=day_open if day_open not in (None,0) else prior.get("session_open") or prior.get("open")
            session_change=(float(ltp)-float(session_open)) if session_open not in (None,0) else None
            session_change_pct=(session_change/float(session_open)*100.0) if session_change is not None else None
            self.last_ltp[key]=float(ltp)
            self.last_publish_at[key]=now
            self.last_quote[key]={"instrument_key":key,"symbol":label or key,"ltp":float(ltp),"cp":cp,"open":session_open,"session_open":session_open,"session_change":session_change,"session_change_pct":session_change_pct,"timestamp":ltt or now,"source":source,"received_at":now}
        # Cache the latest tick even when there is no connected browser client.
        # This gives every frontend surface one authoritative value.
        if previous is not None and abs(float(previous)-float(ltp))<1e-12:
            return
        if not users: return
        event={"type":"market_tick","instrument_key":key,"symbol":label,"ltp":float(ltp),"cp":cp,"open":session_open,"session_open":session_open,"session_change":session_change,"session_change_pct":session_change_pct,"ltt":ltt,"timestamp":now_iso(),"source":source}
        if MAIN_LOOP and not MAIN_LOOP.is_closed(): asyncio.run_coroutine_threadsafe(EVENT_BUS.publish(event,users),MAIN_LOOP)

    def user_state(self, user_id:int) -> dict[str,Any]:
        now=time.time()
        with self.lock:
            mapping={key:(self.key_labels.get(key) or key) for key,users in self.desired.items() if int(user_id) in users}
            snapshots=[]
            for key in mapping:
                q=self.last_quote.get(key)
                if q:
                    item=dict(q); item["age_ms"]=round(max(0.0,now-float(q.get("received_at") or now))*1000,1); snapshots.append(item)
            return {"mapping":mapping,"snapshots":snapshots,"connected":bool(self.connected)}

    def snapshot(self, keys:list[str]) -> list[dict[str,Any]]:
        now=time.time(); out=[]
        with self.lock:
            for key in keys[:500]:
                q=self.last_quote.get(key)
                if q:
                    item=dict(q); item["age_ms"]=round(max(0.0,now-float(q.get("received_at") or now))*1000,1); out.append(item)
        return out

    def _market_open(self,key:str)->bool:
        return bool(market_session(self._segment(key)).get("active"))

    def subscribe(self,user_id:int,key:str,label:str|None=None)->None:
        with self.lock:
            if label: self.key_labels[key]=str(label).upper()
            self.desired[key].add(int(user_id))
            self._ensure_thread_locked()
            if self.connected:
                self._send_sub_locked([key])

    def unsubscribe(self,user_id:int,key:str)->None:
        with self.lock:
            users=self.desired.get(key,set()); users.discard(int(user_id))
            if not users:
                self.desired.pop(key,None)
                if self.connected: self._send_unsub_locked([key])

    def _ensure_thread_locked(self)->None:
        self.stop_event.clear()
        if not self.thread or not self.thread.is_alive():
            self.thread=threading.Thread(target=self._run,name="ca-market-feed",daemon=True); self.thread.start()
        if not self._fallback_thread or not self._fallback_thread.is_alive():
            self._fallback_thread=threading.Thread(target=self._rest_fallback_loop,name="ca-market-fallback",daemon=True); self._fallback_thread.start()

    def _authorized_uri(self)->str:
        UPSTOX._require()
        with _UPSTOX_HTTP_SEM, _REQUEST_CONTEXT():
            r=UPSTOX.session.get(UPSTOX_V3_BASE_URL+"/feed/market-data-feed/authorize",timeout=10,headers={"Authorization": f"Bearer {UPSTOX.token}"})
        r.raise_for_status(); data=r.json().get("data") or {}
        return data.get("authorized_redirect_uri") or data.get("authorizedRedirectUri")

    def _send_sub_locked(self,keys:list[str])->None:
        if self.sdk_streamer is not None:
            try: self.sdk_streamer.subscribe(sorted(set(keys)), "ltpc")
            except Exception as exc: log.debug("SDK subscribe failed: %s", safe_text(exc))
            return
        if not self.ws or not keys: return
        msg={"guid":uuid.uuid4().hex,"method":"sub","data":{"mode":"ltpc","instrumentKeys":sorted(set(keys))}}
        payload=json.dumps(msg).encode("utf-8")
        if websocket_client is not None:
            self.ws.send(payload,opcode=websocket_client.ABNF.OPCODE_BINARY)
        else:
            self.ws.send(payload)

    def _send_unsub_locked(self,keys:list[str])->None:
        if self.sdk_streamer is not None:
            try: self.sdk_streamer.unsubscribe(sorted(set(keys)), "ltpc")
            except Exception as exc: log.debug("SDK unsubscribe failed: %s", safe_text(exc))
            return
        if not self.ws or not keys: return
        msg={"guid":uuid.uuid4().hex,"method":"unsub","data":{"mode":"ltpc","instrumentKeys":sorted(set(keys))}}
        payload=json.dumps(msg).encode("utf-8")
        if websocket_client is not None:
            self.ws.send(payload,opcode=websocket_client.ABNF.OPCODE_BINARY)
        else:
            self.ws.send(payload)

    def _handle_sdk_message(self,message:Any)->None:
        try:
            feeds=message.get("feeds") if isinstance(message,dict) else None
            if not isinstance(feeds,dict): return
            def find_ltpc(node):
                if isinstance(node,dict):
                    if isinstance(node.get("ltpc"),dict): return node["ltpc"]
                    for v in node.values():
                        hit=find_ltpc(v)
                        if hit: return hit
                return None
            for key,node in feeds.items():
                ltpc=find_ltpc(node) or {}
                ltp=ltpc.get("ltp")
                if ltp is None: continue
                ltp=float(ltp)
                with self.lock: users=set(self.desired.get(key,set()))
                if not users: continue
                self._publish_tick(key,ltp,ltpc.get("cp"),ltpc.get("ltt"),"websocket")
        except Exception as exc:
            log.debug("SDK market feed decode failed: %s", safe_text(exc))

    def _handle_message(self,message:bytes)->None:
        try:
            feeds=_decode_upstox_feed(message)
            for key,ltpc in feeds.items():
                ltp=ltpc.get("ltp")
                if ltp is None: continue
                ltp=float(ltp)
                with self.lock: users=set(self.desired.get(key,set()))
                if not users: continue
                self._publish_tick(key,ltp,ltpc.get("cp"),ltpc.get("ltt"),"websocket")
        except Exception as exc:
            log.debug("market feed decode failed: %s",safe_text(exc))

    def _run_sdk(self)->None:
        if upstox_client is None: return False
        if MARKET_STREAM_TRANSPORT not in {"websocket", "ws", "sdk"}: return False
        while not self.stop_event.is_set():
            with self.lock:
                keys=[k for k in self.desired if self._market_open(k)]
            if not keys:
                time.sleep(5); continue
            if time.time() < getattr(self,"_rate_limited_until",0.0):
                time.sleep(max(1.0, getattr(self,"_rate_limited_until",0.0)-time.time()))
                continue
            try:
                configuration=upstox_client.Configuration()
                configuration.access_token=UPSTOX_ACCESS_TOKENS[0] if UPSTOX_ACCESS_TOKENS else UPSTOX_ACCESS_TOKEN
                api_client=upstox_client.ApiClient(configuration)
                streamer=upstox_client.MarketDataStreamerV3(api_client)
                self.sdk_streamer=streamer; self.sdk_mode=True
                def on_open(*_):
                    with self.lock:
                        self.connected=True; self._send_sub_locked([k for k in self.desired if self._market_open(k)])
                def on_message(message): self._handle_sdk_message(message)
                def on_error(err):
                    text=safe_text(err)
                    if "429" in text:
                        log.warning("MarketDataStreamerV3 rate limited; pausing reconnects")
                        self._rate_limited_until=time.time()+300
                    else:
                        log.warning("MarketDataStreamerV3 error: %s", text)
                def on_close(*args):
                    with self.lock: self.connected=False
                streamer.on("open", on_open); streamer.on("message", on_message); streamer.on("error", on_error); streamer.on("close", on_close)
                streamer.connect()
                with self.lock: self.connected=False
            except Exception as exc:
                log.warning("Official Upstox V3 SDK stream reconnect: %s", safe_text(exc))
                time.sleep(5)
            finally:
                with self.lock:
                    self.sdk_streamer=None; self.sdk_mode=False; self.connected=False
        return True

    def _rest_fallback_loop(self) -> None:
        """Bulk REST fallback only when the websocket feed is stale/unavailable.
        Keeps UI live without hammering the provider: one bulk quote request per 2s.
        """
        while not self.stop_event.is_set():
            try:
                now=time.time()
                with self.lock:
                    keys=[k for k in self.desired if self._market_open(k)]
                if keys and now >= getattr(self,"_fallback_pause_until",0):
                    try:
                        payload=UPSTOX._get("/market-quote/quotes", {"instrument_key": ",".join(keys)}, ttl=0.5, cache_key="stream-fallback:"+",".join(keys))
                        data=payload.get("data") or {}
                        for key in keys:
                            raw=data.get(key) or {}
                            ltp=raw.get("last_price")
                            if ltp is None: continue
                            self._publish_tick(key,float(ltp),raw.get("cp"),raw.get("timestamp") or raw.get("ltt"),"rest_fallback")
                    except Exception as exc:
                        text=safe_text(exc)
                        if "429" in text:
                            self._fallback_pause_until=now+5
                        log.debug("Market REST fallback failed: %s",text)
            except Exception:
                pass
            time.sleep(1.5)

    def _run(self)->None:
        """Single-owner native Upstox WebSocket loop.
        Never creates more than one upstream WebSocket and never reconnects concurrently.
        """
        if not MARKET_STREAM_ENABLED:
            return
        if MARKET_STREAM_TRANSPORT not in {"websocket", "ws", "native"}:
            return False
        if websocket_client is None and websocket_sync_connect is None:
            log.error("Live market WebSocket unavailable: install websocket-client or websockets")
            return
        backoff = 5.0
        while not self.stop_event.is_set():
            with self.lock:
                keys=[k for k in self.desired if self._market_open(k)]
            if not keys:
                time.sleep(3); continue
            now=time.time()
            if now < self._rate_limited_until:
                time.sleep(min(5.0, max(1.0, self._rate_limited_until-now)))
                continue
            try:
                uri=self._authorized_uri()
                # Exactly one upstream connection owned by this thread.
                if websocket_client is not None:
                    ws=websocket_client.create_connection(uri,timeout=30,enable_multithread=True)
                else:
                    ws=websocket_sync_connect(uri,open_timeout=10,close_timeout=5)
                with self.lock:
                    self.ws=ws; self.connected=True; self._send_sub_locked(keys)
                backoff=5.0
                while not self.stop_event.is_set():
                    with self.lock:
                        active=[k for k in self.desired if self._market_open(k)]
                        self.connected=True
                    if not active:
                        time.sleep(1); continue
                    try:
                        msg=ws.recv()
                    except Exception as exc:
                        text=safe_text(exc)
                        if "429" in text or "Too Many Requests" in text:
                            self._rate_limited_until=time.time()+300
                            log.warning("Upstox market WebSocket rate-limited; no reconnect for 5 minutes")
                        else:
                            log.warning("Upstox market WebSocket receive failed: %s", text)
                        break
                    if msg is None: break
                    if isinstance(msg,bytes): self._handle_message(msg)
                try: ws.close()
                except Exception: pass
            except Exception as exc:
                text=safe_text(exc)
                with self.lock: self.connected=False
                if "429" in text or "Too Many Requests" in text:
                    self._rate_limited_until=time.time()+300
                    log.warning("Upstox market WebSocket rate-limited; pausing all reconnects for 5 minutes")
                else:
                    log.warning("Upstox market WebSocket connection failed: %s", text)
                time.sleep(min(backoff,30.0))
                backoff=min(backoff*2.0,60.0)
            finally:
                with self.lock:
                    self.connected=False
                    self.ws=None

    def stop(self)->None:
        self.stop_event.set()
        with self.lock:
            try:
                if self.ws:self.ws.close()
            except Exception:pass
            try:
                if self.sdk_streamer is not None:
                    self.sdk_streamer.disconnect()
            except Exception: pass
            self.sdk_streamer=None; self.ws=None; self.connected=False

MARKET_STREAM = MarketStreamManager()

@app.post("/api/market/stream/subscribe")
async def market_stream_subscribe(request: Request, user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    body=await request.json(); instrument=str(body.get("instrument") or "").strip()
    if not instrument: raise HTTPException(422,"Instrument is required")
    key,_=UPSTOX.resolve_instrument(instrument)
    MARKET_STREAM.subscribe(user["id"],key,instrument)
    return {"ok":True,"instrument":instrument,"instrument_key":key,"stream":("websocket" if MARKET_STREAM_TRANSPORT in {"websocket","ws","native","sdk"} else "bulk_rest"),"active":MARKET_STREAM._market_open(key),"timestamp":now_iso()}

@app.post("/api/market/stream/subscribe-batch")
async def market_stream_subscribe_batch(request: Request, user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    body = await request.json()
    raw = body.get("instruments") or []
    if not isinstance(raw, list):
        raise HTTPException(422, "instruments must be a list")
    subscribed = []
    unresolved = []
    seen_keys=set()
    for item in raw[:5000]:
        if isinstance(item, str):
            symbol = item.strip()
            instrument_key = ""
        elif isinstance(item, dict):
            symbol = str(item.get("symbol") or "").strip()
            instrument_key = str(item.get("instrument_key") or "").strip()
        else:
            continue
        if not symbol and not instrument_key:
            continue
        try:
            key = instrument_key or UPSTOX.resolve_instrument(symbol)[0]
            if key in seen_keys: continue
            seen_keys.add(key)
            MARKET_STREAM.subscribe(user["id"], key, symbol)
            subscribed.append({"symbol": symbol or key, "instrument_key": key})
        except Exception as exc:
            unresolved.append({"symbol": symbol or None, "reason": safe_text(exc)})
    return {"ok": True, "stream":("websocket" if MARKET_STREAM_TRANSPORT in {"websocket","ws","native","sdk"} else "bulk_rest"), "subscribed": subscribed, "unresolved": unresolved, "count": len(subscribed), "timestamp": now_iso()}

@app.post("/api/market/stream/unsubscribe")
async def market_stream_unsubscribe(request: Request, user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    body=await request.json(); key=str(body.get("instrument_key") or "").strip()
    if key: MARKET_STREAM.unsubscribe(user["id"],key)
    return {"ok":True,"timestamp":now_iso()}

def _sync_user_market_streams(user_id:int) -> dict[str,int]:
    rows=db_exec("SELECT symbol,instrument_key FROM watchlist_members WHERE watchlist_id IN (SELECT id FROM watchlist_groups WHERE user_id=?) ORDER BY position,id",[user_id],"all")
    pos=db_exec("SELECT symbol,instrument_key FROM positions WHERE user_id=? AND COALESCE(status,'OPEN')='OPEN'",[user_id],"all")
    items=[]; seen=set()
    for r in [*rows,*pos]:
        symbol=str(r.get("symbol") or "").strip(); key=str(r.get("instrument_key") or "").strip()
        try:
            if not key and symbol: key,_=UPSTOX.resolve_instrument(symbol)
            if not key or key in seen: continue
            seen.add(key); MARKET_STREAM.subscribe(user_id,key,symbol or key); items.append(key)
        except Exception as exc:
            log.debug("Market stream subscription failed for %s/%s: %s",symbol,key,safe_text(exc))
    return {"count":len(items)}

@app.get("/api/market/stream/snapshot")
async def market_stream_snapshot(instruments: str = Query("", max_length=20000), user: dict[str,Any]=Depends(require_user)) -> dict[str,Any]:
    requested=[x.strip() for x in instruments.split(",") if x.strip()]
    key_rows=[]; keys=[]; seen=set()
    for item in requested[:500]:
        try:
            key,meta=UPSTOX.resolve_instrument(item)
            if key in seen: continue
            seen.add(key); keys.append(key); key_rows.append((item,key,meta))
        except Exception:
            if "|" in item and item not in seen:
                seen.add(item); keys.append(item); key_rows.append((item,item,{}))
    cached=MARKET_STREAM.snapshot(keys)
    cached_map={str(x.get("instrument_key")):x for x in cached}
    now=time.time(); stale_keys=[]
    with MARKET_STREAM.lock:
        for _,key,_ in key_rows:
            q=MARKET_STREAM.last_quote.get(key)
            if not q or now-float(q.get("received_at") or 0)>3.0:
                stale_keys.append(key)
    # One bounded bulk recovery call. This is only executed when the WebSocket cache is stale.
    if stale_keys:
        try:
            payload=UPSTOX._get("/market-quote/quotes", {"instrument_key": ",".join(stale_keys)}, ttl=0.8, cache_key="snapshot-recovery:"+",".join(stale_keys))
            data=payload.get("data") or {}
            for item,key,meta in key_rows:
                if key not in stale_keys: continue
                raw=data.get(key) or {}
                ltp=raw.get("last_price")
                if ltp is None: continue
                cp=raw.get("cp")
                MARKET_STREAM.key_labels[key]=str(item).upper()
                MARKET_STREAM._publish_tick(key,float(ltp),cp,raw.get("timestamp") or raw.get("ltt"),"rest_recovery",raw.get("ohlc",{}).get("open"))
        except Exception as exc:
            log.debug("Market snapshot recovery failed: %s",safe_text(exc))
    items=MARKET_STREAM.snapshot(keys)
    return {"items":items,"connected":bool(MARKET_STREAM.connected),"timestamp":now_iso()}

@app.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    await websocket.accept()
    session = websocket.scope.get("session") or {}
    user_id = session.get("user_id")
    if AUTH_ENABLED and not user_id:
        await websocket.close(code=4401); return
    uid=int(user_id or 0)
    await EVENT_BUS.add(uid,websocket)
    try:
        if MARKET_STREAM_ENABLED and uid:
            try: await asyncio.to_thread(_sync_user_market_streams, uid)
            except Exception as exc: log.debug("Initial market stream sync failed: %s", safe_text(exc))
        if uid:
            try:
                await websocket.send_json({"type":"market_stream_state", **MARKET_STREAM.user_state(uid), "timestamp":now_iso()})
            except Exception as exc:
                log.debug("Initial market stream state send failed: %s", safe_text(exc))
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await EVENT_BUS.remove(uid,websocket)

# ---------------------------------------------------------------------------
# Dashboard bird's-eye view
# ---------------------------------------------------------------------------

def _dashboard_overview_sync(user_id:int, selected_symbol:str|None, fast:bool=False) -> dict[str,Any]:
    watch_rows=db_exec("SELECT symbol,instrument_key,instrument_type,exchange FROM watchlist_members WHERE watchlist_id IN (SELECT id FROM watchlist_groups WHERE user_id=?) ORDER BY position,id",[user_id],"all")
    symbols=[]
    for r in watch_rows:
        s=str(r.get("symbol") or "").upper()
        if s and s not in symbols: symbols.append(s)
    selected=(selected_symbol or (symbols[0] if symbols else "NIFTY")).upper()
    all_symbols=list(dict.fromkeys([*symbols,selected]))[:50]
    try: quotes=UPSTOX.quotes(all_symbols)
    except Exception: quotes=[]
    qmap={str(q.get("symbol") or q.get("instrument") or "").upper():q for q in quotes if q}
    q=qmap.get(selected) or {}
    pos=db_exec("SELECT * FROM positions WHERE user_id=? AND COALESCE(status,'OPEN')='OPEN' ORDER BY updated_at DESC",[user_id],"all")
    orders=db_exec("SELECT * FROM orders WHERE user_id=? ORDER BY created_at DESC LIMIT 20",[user_id],"all")
    recs=db_exec("SELECT * FROM recommendations WHERE user_id=? ORDER BY created_at DESC LIMIT 20",[user_id],"all")
    funds=db_exec("SELECT * FROM funds WHERE user_id=?",[user_id],"one") or {}
    cfg=db_exec("SELECT * FROM auto_trade_configs WHERE user_id=?",[user_id],"one") or {}
    # Fast mode is intentionally local/cached. It must paint immediately and never wait for news/options/TA.
    if fast:
        unreal=0.0
        for p in pos:
            pq=qmap.get(str(p.get("symbol") or "").upper()) or qmap.get(str(p.get("instrument_key") or "").upper())
            if pq and pq.get("ltp") is not None:
                px=float(pq["ltp"]); avg=float(p.get("avg_price") or 0); qty=int(p.get("quantity") or 0); side=str(p.get("side") or "BUY").upper(); unreal += (px-avg)*qty if side=="BUY" else (avg-px)*qty
        db_exec("UPDATE funds SET unrealized_pnl=?,updated_at=? WHERE user_id=?",[unreal,now_iso(),user_id])
        return {"selected_symbol":selected,"watchlist":quotes,"selected_quote":q,"positions":pos,"orders":orders,"recommendations":recs,"funds":funds,"portfolio":{"open_count":len(pos),"unrealized_pnl":unreal,"realized_pnl":float(funds.get("realized_pnl") or 0),"net_pnl":unreal+float(funds.get("realized_pnl") or 0)},"technical":{},"recommendation":({"recommendation":recs[0].get("recommendation"),"confidence":recs[0].get("score"),"entry":recs[0].get("entry"),"stop_loss":recs[0].get("stop_loss"),"target":recs[0].get("target"),"evidence":{}} if recs else {"recommendation":"NO_TRADE"}),"news":{"stock_events":[],"global_events":[]},"options":None,"chart_candles":[],"auto_trade":{"enabled":bool(cfg.get("enabled")),"options_enabled":bool(cfg.get("options_enabled")),"capital":float(cfg.get("capital") or 0),"funds":float(funds.get("auto_trade_funds") or 0),"used":float(funds.get("used") or 0)},"timestamp":now_iso()}

    # Deep dashboard: perform independent upstream work in parallel so a slow provider doesn't serialize everything.
    def candles_job():
        try: return analysis_candles_robust(selected,"5m",5)
        except Exception: return []
    def news_job():
        try: return recommendation_news_evidence(selected)
        except Exception: return {"stock":{"events":[]},"global":{"events":[]}}
    def option_job():
        try: return UPSTOX.option_chain(selected,None)
        except Exception: return None
    with ThreadPoolExecutor(max_workers=3) as pool:
        f1=pool.submit(candles_job); f2=pool.submit(news_job); f3=pool.submit(option_job)
        candles=f1.result(); news=f2.result(); option=f3.result()
    tech=technical_analysis(candles) if candles else {}
    p=pos
    unreal=sum(float(x.get("unrealized_pnl") or 0) for x in p); realized=float(funds.get("realized_pnl") or 0)
    latest=recs[0] if recs else None
    dash_rec={"recommendation":latest.get("recommendation") if latest else tech.get("trend","NO_TRADE"),"confidence":latest.get("score") if latest else tech.get("trend_strength"),"entry":latest.get("entry") if latest else q.get("ltp"),"stop_loss":latest.get("stop_loss") if latest else None,"target":latest.get("target") if latest else None,"evidence":{"technical":tech,"options":latest.get("option_basis") if latest else None}}
    return {"selected_symbol":selected,"watchlist":quotes,"selected_quote":q,"positions":p,"orders":orders,"recommendations":recs,"funds":funds,"portfolio":{"open_count":len(p),"unrealized_pnl":unreal,"realized_pnl":realized,"net_pnl":realized+unreal},"technical":tech,"recommendation":dash_rec,"news":news,"options":option,"chart_candles":candles,"auto_trade":{"enabled":bool(cfg.get("enabled")),"options_enabled":bool(cfg.get("options_enabled")),"capital":float(cfg.get("capital") or 0),"funds":float(funds.get("auto_trade_funds") or 0),"used":float(funds.get("used") or 0),"last_execution":next((r for r in recs if str(r.get("status") or "").upper()=="EXECUTED"),None)},"timestamp":now_iso()}

@app.get("/api/dashboard/overview")
async def dashboard_overview(selected_symbol: str|None = None, fast: int = Query(0, ge=0, le=1), user: dict[str,Any] = Depends(require_user)) -> dict[str,Any]:
    try:
        return await asyncio.to_thread(_dashboard_overview_sync,user["id"],selected_symbol,bool(fast))
    except Exception as exc:
        record_error("dashboard_overview_failure",safe_text(exc),user_id=user["id"])
        return error_json("DASHBOARD_UNAVAILABLE",safe_text(exc),503)

# ---------------------------------------------------------------------------
# Documentation endpoints
# ---------------------------------------------------------------------------

API_CATALOG = {
    "auth": ["POST /api/auth/login", "POST /api/auth/signup", "POST /api/auth/logout", "GET /api/auth/me", "POST /api/auth/password-reset/request", "POST /api/auth/password-reset/confirm", "GET /api/auth/google/start", "GET /api/auth/google/callback"],
    "market": ["GET /api/market/quote/{instrument}", "GET /api/market/ltp/{instrument}", "GET /api/market/candles/{instrument}", "GET /api/market/depth/{instrument}", "GET /api/market/movers", "GET /api/market/session", "GET /api/market/status/{exchange}"],
    "analysis": ["GET /api/analysis/technical/{instrument}", "GET /api/analysis/fundamental/{instrument}", "GET /api/analysis/overall/{instrument}"],
    "options": ["GET /api/options/{underlying}", "GET /api/options/{underlying}/expiries", "GET /api/options/{underlying}/chain", "POST /api/options/{underlying}/buyable"],
    "news": ["GET /api/news/global", "GET /api/news/stock/{instrument}", "GET /api/news/index/{index}", "GET /api/providers/news", "POST /api/news/analyze", "POST /api/news/decision", "GET /api/news/decision/{article_key}"],
    "recommendations": ["POST /api/recommendations/on-demand", "GET /api/recommendations/history", "POST /api/ai/chat"],
    "portfolio": ["GET /api/orders", "POST /api/orders", "PUT /api/orders/{id}", "DELETE /api/orders/{id}", "POST /api/orders/{id}/square-off", "GET /api/positions", "GET /api/holdings", "GET /api/funds"],
    "watchlists": ["GET /api/watchlists", "POST /api/watchlists", "PATCH /api/watchlists/{watchlist_id}", "DELETE /api/watchlists/{watchlist_id}", "POST /api/watchlists/{watchlist_id}/items", "DELETE /api/watchlists/{watchlist_id}/items/{symbol}", "POST /api/watchlists/{watchlist_id}/reorder"],
    "alerts": ["GET /api/notifications", "GET /api/notifications/unread", "POST /api/notifications/read-all", "GET /api/observations"],
    "stream": ["POST /api/market/stream/subscribe", "POST /api/market/stream/subscribe-batch", "POST /api/market/stream/unsubscribe", "GET /api/market/provider-health", "WebSocket /ws/events"],
    "auto_trade": ["GET /api/auto-trade", "POST /api/auto-trade", "POST /api/risk/check/{position_id}"],
    "diagnostics": ["GET /api/errors", "GET /health", "GET /api/dashboard/overview", "WebSocket /ws/events"],
}


@app.get("/api/docs/catalog")
async def docs_catalog() -> dict[str, Any]:
    return {"version": "1.0", "frontend_neutral": True, "api": API_CATALOG, "data_contract": {"provider": "provider or null", "timestamp": "ISO-8601 UTC", "fresh": "boolean when known", "confidence": "number when available", "materiality": "number when available"}}


if __name__ == "__main__":
    if uvicorn is None:
        raise SystemExit("uvicorn is required to run app.py (it is normally preinstalled with this environment).")
    uvicorn.run(app, host=HOST, port=PORT, log_level=LOG_LEVEL.lower(), reload=DEBUG)
