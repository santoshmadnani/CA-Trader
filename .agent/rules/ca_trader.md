# CA Trader Workspace Rules & Operating Protocol

## 0. Efficiency & Token Conservation (Manifest First)
- **Always Read `app/AI_MANIFEST.json` First**: Never blindly read or grep 1.5MB `terminal.html` or 900KB `app.py`. The manifest indexes all 14 panels, DOM IDs, key JS functions, API endpoints, broker invariants, and SQLite tables in 2KB. Reading this first cuts AI token consumption by 80% and turnaround time to minutes.
- **Surgical Line-Bounded Edits**: When modifying `terminal.html` or `app.py`, always use small, line-bounded `replace_file_content` blocks. Never attempt whole-file replacements.
- **No Stdlib Name Collisions**: Never create scratch scripts in `app/` named after Python standard library modules (e.g., `inspect.py`, `types.py`, `token.py`, `ast.py`, `json.py`). These shadow stdlib modules and break Python compilation and test runners. Always store one-off scratch scripts in the designated brain scratch directory.

## 0.1 Multi-Device Sync Protocol (Phone / External Edits)
- **Mandatory Pre-Task Remote Check**: At the beginning of ANY modification task, Antigravity MUST run `git fetch origin CA-Trader-Bifurcated`.
- **Auto-Detect & Auto-Backup**: If remote commits are detected (e.g. user pushed code from phone, ChatGPT, Gemini, or GitHub Web):
  1. Automatically take a backup of current local work.
  2. Run `git pull origin CA-Trader-Bifurcated` so the laptop folder is instantly updated with the latest changes from GitHub.
  3. Inform the user that remote updates from phone/external devices were synced.
- **Unified Pipeline**: Any subsequent edits are made on top of this latest code and pushed back to GitHub, keeping phone, laptop, and GitHub in perfect sync.

## 1. Database Query Safety
- **Canonical Database**: `ca_trader.sqlite3` (SQLite3, WAL mode).
- **Never Query Basis Blobs**: When querying the `recommendations` table, never execute `SELECT *`. The columns `option_basis`, `news_basis`, and `technical_basis` contain ~60KB of JSON per row (200MB+ in total). Always project explicit lightweight columns (`id`, `symbol`, `recommendation`, `entry`, `target`, `stop_loss`, `final_pnl`, `rationale`, `created_at`, `status`).

## 2. Fast Static Tag & Pre-Commit Integrity Gate (Mandatory /learn Check)
- **Mandatory Pre-Commit & Pre-Deploy Gate**: Before ANY commit, push, or deployment, ALWAYS run:
  `python scripts/validate_integrity.py`
  - Validates Python compilation across `app.py` and `backend/routers/`
  - Validates CSS brace balance across all `<style>` tags in `terminal.html` (prevents WebKit/Safari mobile crashes)
  - Validates full JavaScript syntax across all `<script>` tags in `terminal.html` using the real V8 engine (catches duplicate declarations, unclosed blocks, and syntax errors that cause blank data and disabled buttons)
  - **Zero Tolerance**: If any check fails, do NOT push to Git or deploy until fixed.

## 3. Automated Local Verification Suite (8s)
- Run the server locally using `python run_server.py` (forces Windows `SelectorEventLoop` to avoid IOCP `[WinError 64]` disconnect crashes).
- Run `python tests/smoke_test.py` to automatically verify authentication, instant dual reco cards, non-zero price changes, panel flex positioning, and 1,500 candlestick rendering in ~8 seconds.

## 4. UI & Layout Integrity
- Maintain the dark mode palette (`#1890ff`, `#0b0e14`, `#151b26`).
- Preserve the flex layout hierarchy (`.layout > .sidebar + .main`). Never displace panels outside `.main`.

## 5. Production Deployment Protocol & Corporate IT Safety
- **STRICT CORPORATE IT DIRECTIVE (No Outbound SSH/SCP)**:
  - Following the Sophos security alert on laptop `AMD-122024-0169`, **NEVER** run outbound SSH, SCP, SFTP, or remote PowerShell scripts (e.g. `python tools/deploy_to_oracle.py` or `ssh ubuntu@80.225.236.5`) from this Windows laptop.
  - All deployments must follow the clean Git-mediated workflow:
    1. Run `python scripts/validate_integrity.py` to ensure 100% test pass.
    2. Commit and push cleanly: `git push origin CA-Trader-Bifurcated`.
    3. Production updates are handled on the Oracle server side (auto-sync pull or triggered via server console/webhook), leaving zero EDR/Sophos footprint on the office laptop.
- **Mandatory Production Verification**:
  - Verify `https://catrader.site/health` returns 200 OK via HTTPS.
  - Verify that the live site (`https://catrader.site/terminal`) reflects changes with 0 console syntax errors.

## 6. Post-Task Efficiency Audit & Self-Optimization Protocol
Upon completing any user request or feature implementation:
1. **Time & Latency Breakdown**: Provide a concise summary of the time elapsed and tools used across the key phases (e.g. Investigation, Code Modification, Local Validation, Git & Production Deployment).
2. **Bottleneck Identification**: Identify if any sub-task consumed disproportionate time or tokens (e.g. repetitive greps, large payload fetches, unbuffered prints, slow SSH roundtrips, or polling).
3. **Immediate Post-Task Hardening**:
   - If a manual grep or discovery took multiple turns, update `app/AI_MANIFEST.json` with the exact function/endpoint mappings.
   - If an endpoint or query was slow, optimize SQL projections or add indexing immediately.
   - If a test or deployment script threw encoding or timeout warnings, fix the script on the spot.
4. **Transparent Preventative Log**: State clearly what preventative fixes were applied so the next session executes even faster and with fewer tokens.

