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

