# CA Trader — System Architecture, Database Recommendations & Technical Q&A Guide

This document captures the complete architectural analysis, database recommendations, token-saving AI workflows, data source inventory, logging setup, and master overview created for **CA Trader**.

---

## 1. Recommendations for the App Database

| Aspect | Current Status | Recommendation |
| :--- | :--- | :--- |
| **Engine** | Single SQLite file (`/app/data/ca_trader.db`) | **Immediate:** Enable WAL mode (`PRAGMA journal_mode=WAL; PRAGMA busy_timeout=5000;`).<br>**Long term:** Migrate to **PostgreSQL** (AWS RDS / Supabase) with PgBouncer. |
| **Concurrency Risk** | SQLite locks the entire database during writes. High-frequency tick logging combined with concurrent user orders can cause `database is locked` errors. | PostgreSQL provides row-level locking, concurrent writes, and zero file-locking bottlenecks. |
| **Connection Pooling** | Single raw SQLite connection / ad-hoc connections. | Implement connection pooling (e.g. PgBouncer or SQLAlchemy Async Engine) to prevent pool exhaustion. |
| **Backups** | Manual ZIP snapshot during deployments. | Automated daily S3 dumps + Point-in-Time Recovery (PITR). |

---

## 2. Is Our Backend / Frontend Too Long? Are Files Divided Feature-Wise?

### Current Reality
* **Backend (`app.py`)**: **12,386 lines** (~701 KB) — **Monolithic (Not divided)**.
* **Frontend (`terminal.html`)**: **18,111 lines** (~1.1 MB) — **Monolithic (Not divided)**.

### Are They Divided Feature-Wise?
**No.** Both files are currently 100% monolithic single files. Everything (authentication, database schema, Upstox SDK wrappers, Yahoo Finance scrapers, technical indicators, Black-Scholes Greeks calculations, news scrapers, WebSocket handlers, Canvas charting engine, order execution, Sentinel risk advisor, and Admin Passbook) lives inside one single `.py` file and one single `.html` file.

### Why This Hurts Development
1. **High Risk of Regression**: A single naming collision (such as the `article_key` issue in news) or duplicate keyword (such as `async async`) can break the entire application or prevent other unrelated scripts from executing.
2. **Context Latency**: Navigating and searching through 18,000+ lines creates friction and increases processing latency during updates.

### Recommended Modular Directory Structure

```text
backend/
├── core/
│   ├── db.py                 # Database connections & session management
│   ├── config.py             # Environment variables & constants
│   └── security.py           # JWT auth, password hashing & permissions
├── services/
│   ├── upstox_service.py     # Upstox REST & WebSocket clients
│   ├── greeks_engine.py      # Analytical Black-Scholes model
│   ├── sentinel_advisor.py   # Peak P&L tracking, theta decay & exit alerts
│   ├── technical_engine.py   # EMA, Supertrend, RSI, MACD & candlestick patterns
│   └── news_aggregator.py    # Multi-source RSS scraper & Gemini sentiment
└── routers/
    ├── auth.py               # Login, signup, password reset
    ├── chart.py              # Candle history & technical signals
    ├── options.py            # Options chain & strikes resolution
    ├── reco.py               # Multi-factor recommendations & history
    ├── news.py               # CA AI news feed & sentiment scoring
    ├── orders.py             # Paper orders, positions & execution
    └── admin.py              # API passbook & rate-limit auditing

frontend/
├── css/
│   ├── theme.css             # Institutional dark color system & variables
│   ├── layout.css            # Topbar, section bar & grid system
│   └── components.css        # Cards, modals, tags, tooltips & tables
└── js/
    ├── chart_engine.js       # Canvas renderer, crosshair, pinch-zoom & indicators
    ├── sentinel_widget.js    # Floating mini-window, peak P&L & theta burn
    ├── options_desk.js       # Options chain, strikes & Greeks educational modal
    ├── order_desk.js         # Quick order modal, portfolio & trade history
    └── main.js               # Tab routing, WebSockets & notification toasts
```

---

## 3. How to Save Tokens and Time When Making Changes through AI

1. **Modular Code Structure**: Once files are split into ~200–400 line modules, the AI only needs to read the specific file being modified (e.g. `routers/options.py`), reducing prompt context by **80–90%** and speeding up response times.
2. **Targeted Instructions**: Provide exact endpoint URLs (e.g. `GET /api/options/{underlying}`) or DOM element IDs (e.g. `#ordersThetaBurn`) so the agent jumps directly to the target block without scanning the entire file.
3. **Small, Focused Iterations**: Group requests into 2–4 related items rather than 25 disparate items at once.
4. **Surgical Diff Tooling**: Use precise line replacement (`replace_file_content`) instead of full file rewrites to preserve tokens and avoid accidental overwrites.

---

## 4. How to Use Django to Improve the App Database

### What Django Brings
* **Declarative ORM**: Clean Python model classes with explicit types, foreign keys, and relationships.
* **Automated Migrations**: `makemigrations` and `migrate` manage database schema changes safely without manual SQL scripts.
* **Built-In Admin Portal (`/admin/`)**: Instant administrative web UI to search, filter, edit users, view orders, and inspect audit trails without writing custom admin views.

### Caveat with FastAPI
CA Trader relies on high-frequency asynchronous WebSockets (`FastAPI + asyncio + uvloop`). Django's standard ORM is synchronous and can introduce overhead in async loops unless wrapped in `sync_to_async` or Django Channels.

### Best Practical Options
1. **Option A (Recommended — No full rewrite)**: Keep FastAPI and add **SQLAlchemy (Async) ORM + Alembic**. This gives the exact same declarative models, connection pooling, and automated schema migrations while keeping 100% of FastAPI's async speed.
2. **Option B (Django Ninja)**: If Django's admin portal is required, use **Django Ninja**—an async FastAPI-compatible framework built directly on top of Django.

---

## 5. Adding a Professional Logger (Visual & Backend) Instead of Server Console

### Backend Structured Logging
* Replace raw `print()` statements with **`loguru`** or Python's `RotatingFileHandler`.
* Write logs to `/app/data/logs/ca_trader.log` with a 50 MB rotation limit and 7-day retention.
* Output structured JSON records:
  ```json
  {
    "timestamp": "2026-09-17T00:55:00.120Z",
    "level": "ERROR",
    "endpoint": "/api/news/ca-ai-feed",
    "user_id": 1,
    "duration_ms": 34,
    "error_message": "NameError: name 'article_key' is not defined",
    "traceback": "..."
  }
  ```

### Frontend / Visual Layout & JavaScript Error Tracking
* Install global error handlers in `terminal.html`:
  ```javascript
  window.onerror = function(msg, url, line, col, error) {
    navigator.sendBeacon('/api/logs/client-error', JSON.stringify({
      msg, url, line, col,
      screen: `${window.innerWidth}x${window.innerHeight}`,
      activeTab: window.currentTab || 'unknown',
      userAgent: navigator.userAgent
    }));
  };
  ```
* **Visual Overflow Detector**: A lightweight observer script that flags any container where `scrollWidth > clientWidth` (content clipping outside cards/boxes).
* Surface these live client errors directly in the **Admin API Passbook** ledger.

---

## 6. Master Inventory of Data Sources

| Feature / Metric | Underlying Data Points | Primary Source | Protocol / Mechanism | Refresh Interval | Quota / Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Live Candlesticks** | Open, High, Low, Close, Volume, Ticks | **Upstox Pro API** | Binary WebSocket V3 + REST V2 | Tick-by-tick (<100ms) | 250 REST req/min ceiling |
| **Options Chain** | Strikes, CE/PE LTP, OI, Expiries | **Upstox Options API** | REST JSON | 10s cached TTL | Rate limited per IP |
| **Black-Scholes Greeks** | Delta, Gamma, Theta, Vega, IV | **In-House Analytical Engine** | Vectorized NumPy / SciPy | Instant per tick | Zero external quota |
| **Global Macro Drivers** | GIFT Nifty, Crude Oil, DXY, US 10Y Yield | **Yahoo Finance Realtime** | Asynchronous HTTP Scrapers | 60s cached TTL | Unmetered public use |
| **Financial News Feed** | Breaking Headlines, Summaries, Timestamps | **Google News RSS, Reuters, Mint, ET** | Multi-threaded Async RSS Parser | 120s background task | Unmetered public RSS |
| **News Sentiment & Impact** | Buy/Sell Signals (75%–100%), Materiality | **Google Gemini 2.0 Flash AI** | REST JSON (`google-genai` / REST) | On-demand with cached digests | 1,000,000 TPM limit |
| **Order Flow & Institutional** | FII / DII Net Inflows, Block Deals, PCR | **NSE India Public Reports** | Scheduled HTTP Digest Scrapers | End-of-day + Pre-market snapshots | Public regulatory feed |
| **Paper Ledger & Positions** | Orders, Peak P&L, MTM, User History | **SQLite Database** | Embedded local storage (`/app/data/ca_trader.db`) | Synchronous atomic transactions | Disk space bound (~100 MB) |

---

## 7. What Can I Check Autonomously in the App?

1. **REST Endpoints**: Test HTTP status codes (200, 401, 422, 500), payload structures, and response latency.
2. **Production Container Health**: Execute commands via SSH directly inside the `ca-trader` Docker container on EC2.
3. **Database Integrity**: Check schema definitions, test migrations, verify foreign keys, and audit rows.
4. **Code Syntax & AST**: Validate Python AST and JavaScript syntax to catch errors, missing variables, or duplicate keywords prior to deployment.
5. **DOM & Responsive Layout**: Check for missing element IDs, inspect CSS classes, evaluate container widths, and test mobile viewport compatibility.

---

## 8. Can You Use Me to Regularly Monitor and Fix the App?

**Yes.** You can:
* Use the `/schedule` command to run automated periodic health checks against `https://catrader.site`.
* Have me run regression test suites before and after every production release.
* Ask me to inspect live Docker logs, identify error traces, apply surgical fixes, and auto-deploy updates without service interruption.

---

## 9. Interactive Knowledge Hub & Branch Diagram File

A master interactive guide has been generated in the project root:
📁 **[`ca_trader_guide.html`](file:///C:/Users/SantoshMadnani/Documents/CA_Trader/7/ca_trader_guide.html)**

### Key Modules in the File
1. **Interactive Branch-Wise Data Lineage Diagram**:
   * Root: *CA Trader Recommendation Engine*.
   * Branches: *Technical Analysis*, *Options Chain & Greeks*, *Financial News*, *Global Macro*, and *CA AI Sentinel*.
   * Clicking any branch or data node dynamically opens the **side-by-side inspection card** showing its formula, refresh rate, and upstream API provider.
2. **Comprehensive Feature-Wise User Tutorial**:
   * Step-by-step documentation for terminal navigation, Canvas charting & touch controls, multi-factor recommendation rationale, options chain & pure Greeks, paper execution, and Sentinel profit-retention rules.
   * Includes an interactive **"▶ Start Animated Interactive Tour"** with a glowing simulated cursor walkthrough.
3. **Searchable Trading Terms & Greeks Dictionary**:
   * Instant fuzzy search across 25+ institutional concepts (Delta, Gamma, Theta Hourly Burn Rate, Vega, IV, Peak P&L High-Water Mark, PCR, VWAP, EMA Confluence, Slippage, Supertrend, etc.).
4. **Data Sources & API Integration Matrix**:
   * Complete reference table detailing providers, protocols, update rates, and quota limits.
5. **Institutional Dark Styling**:
   * Styled to match the CA Trader terminal theme (`#070a10`, `#0e1422`, neon cyan `#00e5ff`, emerald `#10b981`, ruby `#ef4444`, and gold `#f59e0b`).

