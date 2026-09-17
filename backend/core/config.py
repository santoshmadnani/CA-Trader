import os
import re
import secrets
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
HTML_CANDIDATES = [
    BASE_DIR / "terminal.html",
    BASE_DIR / "CA_Trader_Final.html",
    BASE_DIR / "CA_Trader_Updated.html",
    BASE_DIR / "index.html",
]
LOGIN_HTML_CANDIDATES = [
    BASE_DIR / "CA_Trader_Login.html",
]
HTML_PATH = next((p for p in HTML_CANDIDATES if p.exists()), BASE_DIR / "terminal.html")
LOGIN_HTML_PATH = next((p for p in LOGIN_HTML_CANDIDATES if p.exists()), BASE_DIR / "CA_Trader_Login.html")
FITNESS_HTML_PATH = BASE_DIR / "fitness.html"
TERMINAL_SELECTOR_HTML_PATH = BASE_DIR / "terminal_selector.html"
GUIDE_HTML_PATH = BASE_DIR / "ca_trader_guide.html"

load_dotenv(BASE_DIR / ".env")
load_dotenv(Path.cwd() / ".env")

HOST = os.getenv("FLASK_HOST", os.getenv("HOST", "127.0.0.1"))
PORT = int(os.getenv("FLASK_PORT", os.getenv("PORT", "8000")))
DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
AUTH_ENABLED = os.getenv("CA_AUTH_ENABLED", "1") == "1"
AUTH_IDLE_HOURS = float(os.getenv("CA_AUTH_IDLE_HOURS", "12"))
AUTH_SECRET = os.getenv("CA_AUTH_SECRET") or secrets.token_hex(32)

_configured_db_path = Path(os.getenv("CA_DATABASE_PATH", str(BASE_DIR / "ca_trader.sqlite3")))
_legacy_db_path = _configured_db_path.with_name("ca_trader.db")
DB_PATH = _legacy_db_path if _legacy_db_path.exists() and not _configured_db_path.exists() else _configured_db_path

RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "1") == "1"
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "120"))
UPSTOX_HTTP_SEM = threading.BoundedSemaphore(int(os.getenv("UPSTOX_MAX_CONCURRENCY", "24")))
FITNESS_SELECTOR_EMAILS = {x.strip().lower() for x in os.getenv("CA_TERMINAL_SELECTOR_EMAILS", "").split(",") if x.strip()}
FOOD_SEARCH_CACHE_HOURS = float(os.getenv("FOOD_SEARCH_CACHE_HOURS", "12"))
CORS_ORIGINS = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:8001").split(",") if x.strip()]

UPSTOX_BASE_URL = os.getenv("UPSTOX_BASE_URL", "https://api.upstox.com/v2").rstrip("/")
UPSTOX_V3_BASE_URL = os.getenv("UPSTOX_V3_BASE_URL", "https://api.upstox.com/v3").rstrip("/")
UPSTOX_ACCESS_TOKEN = os.getenv("UPSTOX_ACCESS_TOKEN", "")
MARKET_STREAM_ENABLED = os.getenv("CA_MARKET_STREAM_ENABLED", "1") == "1"
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
NEWS_REFRESH_LOCK = threading.RLock()
NEWS_REFRESH_INFLIGHT: set[str] = set()
NEWS_REFRESH_EXECUTOR = ThreadPoolExecutor(max_workers=4)
ANALYSIS_CACHE_TTL = 20.0

GNEWS_API_KEYS = [v for k, v in sorted(((k, v) for k, v in os.environ.items() if k == "GNEWS_API_KEY" or re.fullmatch(r"GNEWS_API_KEY_[2-9]|GNEWS_API_KEY_10", k)), key=lambda x: (0 if x[0] == "GNEWS_API_KEY" else int(x[0].rsplit("_", 1)[1]))) if v]
NEWSAPI_API_KEYS = [v for k, v in sorted(((k, v) for k, v in os.environ.items() if k == "NEWSAPI_API_KEY" or re.fullmatch(r"NEWSAPI_API_KEY_[2-9]|NEWSAPI_API_KEY_10", k)), key=lambda x: (0 if x[0] == "NEWSAPI_API_KEY" else int(x[0].rsplit("_", 1)[1]))) if v]
UPSTOX_ACCESS_TOKENS = [v for k, v in sorted(((k, v) for k, v in os.environ.items() if k == "UPSTOX_ACCESS_TOKEN" or re.fullmatch(r"UPSTOX_ACCESS_TOKEN_[2-9]|UPSTOX_ACCESS_TOKEN_10", k)), key=lambda x: (0 if x[0] == "UPSTOX_ACCESS_TOKEN" else int(x[0].rsplit("_", 1)[1]))) if v]

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash-high")
AVAILABLE_AI_MODELS = list(dict.fromkeys([
    "gemini-3.8-flash-high",
    "gemini-3.8-flash",
    "gemini-3.7-flash",
    "gemini-3.6-flash",
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-pro",
    "gemini-1.5-flash",
    "antigravity-deep-trader"
]))

USDA_API_KEY = os.getenv("USDA_API_KEY", "DEMO_KEY")
FITNESS_TIMEZONE = ZoneInfo(os.getenv("FITNESS_TIMEZONE", "Asia/Kolkata"))
IST = ZoneInfo("Asia/Kolkata")

