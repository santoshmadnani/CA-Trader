# CA Trader Workspace Rules & Operating Protocol

## 0. Efficiency & Token Conservation (Manifest First)
- **Always Read `app/AI_MANIFEST.json` First**: Never blindly read or grep 1.5MB `terminal.html` or 900KB `app.py`. The manifest indexes all 14 panels, DOM IDs, key JS functions, API endpoints, broker invariants, and SQLite tables in 2KB. Reading this first cuts AI token consumption by 80% and turnaround time to minutes.
- **Surgical Line-Bounded Edits**: When modifying `terminal.html` or `app.py`, always use small, line-bounded `replace_file_content` blocks. Never attempt whole-file replacements.

## 1. Database Query Safety
- **Canonical Database**: `ca_trader.sqlite3` (SQLite3, WAL mode).
- **Never Query Basis Blobs**: When querying the `recommendations` table, never execute `SELECT *`. The columns `option_basis`, `news_basis`, and `technical_basis` contain ~60KB of JSON per row (200MB+ in total). Always project explicit lightweight columns (`id`, `symbol`, `recommendation`, `entry`, `target`, `stop_loss`, `final_pnl`, `rationale`, `created_at`, `status`).

## 2. Fast Static Tag & DOM Validation (0.1s)
- After every edit to `terminal.html`, immediately run:
  `python tools/check_terminal.py`
- Confirms zero unclosed/extra `<div>` tags, verifies that all 14 panels remain direct descendants of `.main`, and ensures critical window exports exist.

## 3. Automated Local Verification Suite (8s)
- Run the server locally using `python run_server.py` (forces Windows `SelectorEventLoop` to avoid IOCP `[WinError 64]` disconnect crashes).
- Run `python tests/smoke_test.py` to automatically verify authentication, instant dual reco cards, non-zero price changes, panel flex positioning, and 1,500 candlestick rendering in ~8 seconds.

## 4. UI & Layout Integrity
- Maintain the dark mode palette (`#1890ff`, `#0b0e14`, `#151b26`).
- Preserve the flex layout hierarchy (`.layout > .sidebar + .main`). Never displace panels outside `.main`.

## 5. Zero-Laptop-Transfer Deployment Protocol
- **Strict Prohibition**: Never transfer files directly from the Windows laptop via SCP, SFTP, or rsync to avoid corporate Sophos security popups.
- **Deployment Flow**:
  1. Commit and push to Git: `git push origin CA-Trader-Bifurcated`.
  2. SSH to EC2 (`ubuntu@15.252.81.122`) using `ca-trader-key.pem`.
  3. Pull changes inside `/home/ubuntu/ca-trader-repo`.
  4. Package `/home/ubuntu/46.zip` on the server filesystem.
  5. Run `sudo /home/ubuntu/deploy.sh` and verify container hot-swap.

## 6. Post-Task Efficiency Audit & Self-Optimization Protocol
Upon completing any user request or feature implementation:
1. **Time & Latency Breakdown**: Provide a concise summary of the time elapsed and tools used across the key phases (e.g. Investigation, Code Modification, Local Validation, Git & Production Deployment).
2. **Bottleneck Identification**: Identify if any sub-task consumed disproportionate time or tokens (e.g. repetitive greps, large payload fetches, unbuffered prints, slow SSH roundtrips, or polling).
3. **Immediate Post-Task Hardening**:
   - If a manual grep or discovery took multiple turns, update `app/AI_MANIFEST.json` with the exact function/endpoint mappings.
   - If an endpoint or query was slow, optimize SQL projections or add indexing immediately.
   - If a test or deployment script threw encoding or timeout warnings, fix the script on the spot.
4. **Transparent Preventative Log**: State clearly what preventative fixes were applied so the next session executes even faster and with fewer tokens.

