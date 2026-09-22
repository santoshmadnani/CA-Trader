# CA TRADER - PERSISTENT VERSION & CHANGE MEMORY
*Preserving all fixes, preventing regressions, and memorizing solutions.*

---

## CRITICAL IMMUTABLE PRINCIPLES (NEVER REVERT)
1. **Zero Laptop File Transfers**: Never use SCP/SFTP or local file syncing tools for manifests, icons, or assets that trigger Sophos antivirus popups. All server updates must be performed via Git (`git push` from laptop -> `ssh` git pull & docker reload on server).
2. **No Duplicate Elements**: Topbar buttons (Ask CA AI, Panic Exit), Recommendation cards, and badges must remain singletons.
3. **No Unwanted Sections / Notes**: "Trader Notes" must stay removed. No duplicate nav tabs (Fundamentals, Market Movers).
4. **Permanent Greeks in Option Chain**: Delta, Gamma, Theta, Vega, IV columns remain displayed without checkboxes.
5. **Dark Mode Blue Theme**: No jarring white container backgrounds (`#1890ff` accents, dark `#111622` / `#0b0e14`).
6. **Realistic ATR Targets**: Option targets and equity moves must be calibrated to achievable session ATR fractions (never unrealistic 400+ pt moves in 5m).

---

## LOG OF RESOLVED ISSUES & IMPLEMENTATION PATTERNS

### Issue 1: Sophos Antivirus Popups from File Transfers
- **Symptom**: Laptop pops up Sophos allow/block warnings multiple times during deployment due to transferring manifests and icons.
- **Root Cause**: Deployment scripts used SCP/SFTP to transfer files directly from the laptop.
- **Solution & Memory**: Deploy strictly via Git and SSH. Code is committed and pushed to GitHub; the remote server executes `git pull` and restarts services via SSH (`ca-trader-key.pem`). No direct asset transfers from laptop disk.

### Issue 2: Top Bar Buttons Non-Clickable on Phone
- **Symptom**: Top bar buttons (e.g. Ask CA AI, Panic Exit, notifications, profile) do not respond to touches on mobile devices.
- **Root Cause**: Mobile top bar / viewport layout issues: overlapping invisible overlays, excessive z-index on floating panels, or touch event blocking / pointer-events conflicts.
- **Solution & Memory**: Ensure top bar container has proper `z-index: 100`, `pointer-events: auto`, touch targets >= 44px, and no hidden overlay elements capturing pointer events.

### Issue 3: Blank Non-Dashboard Sections (Option Chain, Strategy, Algo, Backtest, Risk, Fundamentals, Market Movers)
- **Symptom**: Clicking sections other than Dashboard and Chart displays blank or non-loading content.
- **Root Cause**: Tab switching logic errors, missing initialization functions on tab activation, unhandled exceptions in section render routines, or API endpoints returning errors.
- **Solution & Memory**: Ensure each tab's activation handler cleanly unhides the container, triggers required data load (`loadOptionChain()`, `loadStrategyBuilder()`, `loadAlgoBots()`, etc.), catches and displays friendly data/fallbacks, and never leaves containers empty.

### Issue 4: Nifty Option Recommendations Expiry & Real Contracts
- **Symptom**: Recommendations show non-existent "NIFTY 24 Sep" options instead of real market expiries (e.g. 22 Sep, 29 Sep).
- **Root Cause**: Hardcoded expiry dates or incorrect expiry calculation in `app.py` / recommendation engine.
- **Solution & Memory**: Use dynamic real exchange expiry calculation for NSE indices (Tuesday for FinNifty, Thursday for Nifty / BankNifty, or monthly last Thursday). Calculate actual calendar dates and validate against real options universe.

### Issue 5: Recommendation 1st Box Not Updating on Watchlist Click
- **Symptom**: When user clicks an item in the watchlist, the 1st card above Call/Put (the Index/Stock recommendation) does not update its title or symbol.
- **Root Cause**: Watchlist item selection listener updates chart/quotes but fails to update the target symbol in `#reco-inst-name` or `updateRecommendationHeader()`.
- **Solution & Memory**: In `selectWatchlistItem` / `onSymbolChange`, explicitly invoke recommendation recalculation and update the symbol label in the primary recommendation card.

---

## SESSION 2 FIXES (2026-09-22 Night)

### Issue 6: News Tab "Request timed out after 4 seconds"
- **Symptom**: News section shows "News feed temporarily unavailable: Request timed out after 4 seconds"
- **Root Cause**: Two bugs:
  1. `/api/news/stock/{sym}` and `/api/news/global` returned HTTP 404 (routes not registered)
  2. These 404 calls were made in background news polling (every 30s) AND by `monitorNewNews()`
- **Solution**: Added `/api/news/stock/{symbol}` and `/api/news/global` endpoints in `app.py` as aliases for the working `/api/news/ca-ai-feed` endpoint. These now return cached results in 30s windows.

### Issue 7: Recommendation History "Request timed out after 4 seconds"
- **Symptom**: Reco History tab shows "Request timed out after 4 seconds"
- **Root Cause**: Backend `/api/recommendations/history` took 13+ seconds (heavy DB query + P&L calc for each row). Frontend timeout was 3500ms.
- **Solution**: 
  1. Added 30-second caching to the backend endpoint (`CACHE.set(cache_key, result, 30.0)`)
  2. Increased frontend timeout to 12000ms in `loadRecommendationHistory()`

### Issue 8: CE/PE Cards Show "Loading CE Contract..." for 12+ Seconds
- **Symptom**: Dashboard CE/PE recommendation cards stay stuck at "Loading CE Contract..." after page load
- **Root Cause**: `renderDualRecoCards()` is called only AFTER the slow `fetchApi('/api/recommendations/{sym}', {timeoutMs:12000})` completes (11-12 seconds). During that wait, the initial HTML placeholder is shown.
- **Solution**: Added an immediate IIFE call `initDualRecoCardsEarly()` right after `window.renderDualRecoCards` is defined. This pre-populates CE/PE cards with ATM strike data using `_getLtp()` fallback values instantly on page load.

### Issue 9: Persistent app.py Syntax Errors (recurring)
- **Symptom**: `py_compile` fails with SyntaxError after context resets
- **Root Cause**: Two recurring bugs that reappear when changes aren't committed:
  1. Duplicate `def fallback_recommendation_quick` header at line ~3107
  2. Truncated string literal `is_mcx = root in {"CRUDEOIL", "GO\n... [truncated for diff preview]` at line ~9270
- **Solution**: Fixed both. Must always run `python -m py_compile app.py && echo "SYNTAX OK"` before server restart.

---

## SESSION 3 FIXES & ARCHITECTURAL ACCELERATION (2026-09-23 Early Morning)

### Issue 10: AI Task Turnaround Time (58 Minutes) & Massive Token Waste
- **Symptom**: AI agents spend 50+ minutes and hundreds of thousands of tokens scanning 1.5MB `terminal.html` and 900KB `app.py` for DOM IDs, functions, and routes.
- **Root Cause**: Lack of a centralized machine-readable index forcing expensive full-text file inspections.
- **Solution & Invariant**: 
  1. Created `app/AI_MANIFEST.json` indexing all 14 panels, DOM IDs, key JS functions, API endpoints, and broker invariants in 2KB. Mandatory AI first read saves ~80% tokens.
  2. Created `app/tools/check_terminal.py` (0.1s static tag & ID balance check).
  3. Created `app/tests/smoke_test.py` (8-second headless automated E2E test verifying all 7 core criteria).

### Issue 11: Windows IOCP [WinError 64] Socket Disconnect Crash
- **Symptom**: When headless Chrome closes after verification, uvicorn terminates abruptly with `[WinError 64] The specified network name is no longer available`.
- **Root Cause**: In Python 3.12+, uvicorn's `asyncio_loop_factory` explicitly hardcodes `ProactorEventLoop` on Windows, ignoring `asyncio.set_event_loop_policy`. Abrupt TCP FIN packets trigger an unhandled IOCP callback error that kills the server.
- **Solution**: Created `app/run_server.py` which patches `uvicorn.loops.asyncio.asyncio_loop_factory = lambda use_subprocess=False: asyncio.SelectorEventLoop`, completely eliminating IOCP crashes.

### Issue 12: Premature Return & Missing 30s Candle Cache in app.py
- **Symptom**: Candlestick fetch took 6-30 seconds on every request, blocking concurrent requests and timing out the browser.
- **Root Cause**: 
  1. Synchronous `analysis_candles_robust` was blocking the FastAPI async event loop.
  2. An accidental duplicate `return JSONResponse(...)` on line 8169 returned before reaching `CACHE.set(ck, payload, 30.0)` on line 8171.
- **Solution**: 
  1. Wrapped call with `await asyncio.to_thread(analysis_candles_robust, ...)`.
  2. Removed premature return so `CACHE.set(ck, payload, 30.0)` caches candles. Result: repeat candle fetches dropped from 6.6s to 0.023s (23ms).

### Issue 13: Hardcoded 4000ms Retry Timeout in Frontend A() and api()
- **Symptom**: Legitimate API calls taking >4s threw `Error: Request timed out after 4 seconds` on retry.
- **Root Cause**: In `terminal.html` lines 6718 and 11732, the retry logic had `timeoutMs: 4000` hardcoded even if the caller requested 15,000ms.
- **Solution**: Updated retry timeout to `Math.max(timeoutMs, 8000)`.

