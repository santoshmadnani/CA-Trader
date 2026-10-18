# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

CA Trader is a single-user Indian markets (NSE/BSE/MCX) trading terminal: a FastAPI backend (`app.py`) plus two browser UIs, live at https://catrader.site. `AGENTS.md` holds the binding workspace rules (commit-and-push after every change, no scratch files in the repo, never touch secrets).

## Commands

```bash
pip install -r requirements.txt
python run_server.py                      # local dev on http://127.0.0.1:8000 (forces SelectorEventLoop; avoids WinError 64 on Windows)
python scripts/validate_integrity.py      # REQUIRED before every commit: py_compile + V8 syntax check of every <script> and CSS brace balance in terminal.html
python tests/smoke_test.py                # headless-Chrome smoke test of the classic UI against a running local server (--screenshot optional)
python tools/check_terminal.py            # static DOM checks for terminal.html (div balance, duplicate ids)
python scripts/stockmantra_calibration.py # refit data/signal_calibration.json + data/stockmantra_comparison.json (run on the server, commit both)
```

There is no linter or unit-test suite. To hit authenticated endpoints locally without logging in, start the server with `CA_AUTH_ENABLED=0`.

## Deploy pipeline

`git push origin CA-Trader-Bifurcated` triggers `.github/workflows/deploy_to_oracle.yml`. It SSHes to the Oracle VM (secrets `ORACLE_HOST`, `ORACLE_SSH_KEY`), runs `git reset --hard` in `/home/ubuntu/CA-Trader`, takes one SQLite online backup per day into `backups/` (keeps 2), runs `pip install -r requirements.txt`, restarts systemd `catrader`, and fails the job unless `/health` answers within 30 s. Public traffic reaches uvicorn (127.0.0.1:8000) through a Cloudflare tunnel (systemd `cloudflared`).

- Untracked runtime state lives only on the host and deploys never touch it: `.env`, `ca_trader.sqlite3`, `catrader_telegram.session`, `backups/`, `ca-trader.log`, `data/candles_cache.json`, `data/ui_customization.json`.
- A new dependency must go into `requirements.txt`; the server only gets what the workflow installs.
- To move hosts, see `deploy/setup_server.sh` (bootstrap) and `deploy/catrader.service` (the live unit file).
- Check deploys with `https://api.github.com/repos/santoshmadnani/CA-Trader/actions/runs` and `https://catrader.site/health`.

## Architecture

**`app.py` (~17k lines, ~1 MB) is the whole backend.** Read it in targeted slices; never read or grep-dump it whole. The main sections, in file order:
- Config and env (`BASE_DIR`, `DB_PATH`, `AUTH_ENABLED`, `ALLOW_NON_UPSTOX_FALLBACK`), then the SQLite schema and the `db_exec(sql, params, fetch)` helper (`fetch` is `"one"`, `"all"` or `None`; WAL mode; writes are serialised by `_DB_LOCK`).
- `UpstoxAdapter` (singleton `UPSTOX`): quotes, depth, candles, option chains and instrument resolution. Upstox is the only market-data source. Yahoo fills NSE/BSE gaps only when `ALLOW_NON_UPSTOX_FALLBACK=1`, and never for MCX. MCX option chains are built from the Upstox MCX instrument master (`_mcx_option_contracts`).
- Analysis and recommendations: `/api/analysis/overall/{instrument}` (also mounted as `/api/recommendations/{instrument}`) wraps `backend/services/signal_model.py`. That is a 6-factor model (trend, vwap, momentum, price_action, day_change, option_flow) whose weights, gate and confidence buckets come from `data/signal_calibration.json`. Confidence is the measured hit-rate of its bucket, not a floor. `replay_signals_for_day` is the real historical replay behind `/api/recommendations/for-date` and `/api/backtest/100-trades`.
- Paper trading: orders, positions, funds, passbook upload, P&L reports. Real broker positions come from Upstox or are entered as "external" positions.
- Background loops start in `lifespan()`: cache maintenance, auto-trade, paper risk, the auto-recommendation recorder (runs only while that instrument's market is open), the news worker, the Telegram bot, the Stock Mantra Telethon listener, the reco sender and skill discovery. There is also the `ca-market-feed` WebSocket thread, which fans ticks out over `/ws/events`.
- AI: Gemini-backed chat (`/api/ai/*`) is grounded in `build_ai_market_context`. It must not invent setups.
- **Route order matters.** `/api/recommendations/{instrument}` is registered before `/api/recommendations/history`, so `analysis_overall` forwards the literal values `history`, `for-date` and `100-trades` to their handlers. Keep that dispatch in place if you add sibling routes.

**Other backend modules:** `backend/routers/ai_connector.py` is the `/api/mcp/*` router for ChatGPT/Gemini/MCP clients. It authenticates with an `X-API-Key` or Bearer token equal to `CA_MCP_TOKEN`/`CA_AUTH_SECRET`, and includes `/deploy` and a read-only `/sql`. `backend/services/telegram_service.py` holds the Telegram bot, alerts and Stock Mantra parsing. `mcp_server.py` is a stdio MCP bridge to the live site.

**Auth:** session-cookie login (`SessionMiddleware`, secret `CA_AUTH_SECRET`). Admin credentials come from `.env`, with optional Google OAuth. Protect every data or mutating route with `user: dict = Depends(require_user)`, and add `is_admin(user)` for admin-only routes. Unauthenticated page requests redirect to `/login`.

**Frontends** (all plain HTML/JS, no build step):
- `/terminal` and `/` serve `trade.html` + `static/trade/{trade.js,chart.js,trade.css}`. This is the current UI, with TradingView Lightweight Charts vendored in `static/vendor/`.
- `/terminal/classic` serves `terminal.html`. It is the legacy 2 MB single-file UI with 14 panels (`#panel-<name>`, one visible at a time inside `.layout > .sidebar + .main`). Some panels may show blanks where API shapes changed during the rebuild. Edit it surgically, and always rerun `validate_integrity.py`, because one JS syntax error blanks the whole UI.
- `CA_Trader_Login.html` (`/login`), `terminal_selector.html`, `ca_trader_guide.html` (`/guide`), `multi_agent_harness.html` (`/agents`) and `learn_ai/` (`/learn`).

## Rules that bite

- **Sync with GitHub before every task.** Santosh also edits this repo directly on GitHub (through the Claude GitHub connector). Before changing anything, fetch every branch (`git fetch origin '+refs/heads/*:refs/remotes/origin/*'`), compare `origin/CA-Trader-Bifurcated` (the deployed branch) with the local copy, and bring local files up to date first (fast-forward or merge, keeping both sides' changes). Only then start the work.

- **Never fabricate market data.** No synthetic candles, chains, depth, prices or canned "analysis". When Upstox has no data, return an empty or `unavailable` payload and let the UI show "No data". Earlier fabricated features were removed for this reason.
- **Never `SELECT *` from `recommendations`.** `technical_basis`, `news_basis` and `option_basis` hold about 60 KB of JSON per row. Project explicit columns: `id, symbol, recommendation, entry, target, stop_loss, final_pnl, status, created_at`. `recommendations` has no `updated_at` column.
- **Classic-UI mobile safety:** only reassign `canvas.width`/`height` when the size actually changes, cap `devicePixelRatio` at 2, and never force a reflow (`void el.offsetWidth`) inside tick handlers.
- **Dates and timezones:** compute market-session logic in IST (`IST` ZoneInfo) and store timestamps as UTC ISO-8601. Upstox rejects 1-minute history ranges longer than about 30 days (`UDAPI1148`).
- **Server access:** `ssh -i oracle_key.key ubuntu@<ORACLE_HOST>`. Pipe multi-line scripts base64-encoded (`echo <b64> | base64 -d | bash`), because PowerShell adds a BOM and CRs. The VM has 1 GB RAM, so avoid full-table scans and whole-file reads.
