# AGENT OPERATING MANDATE & PROTOCOL

This document defines the strict, non-negotiable operating rules for the AI Agent working on CA Trader.

## 0. AI Efficiency & Token Conservation Mandate (Manifest First)
- **Always Read `app/AI_MANIFEST.json` First**: Never blindly load or grep 1.5MB `terminal.html` or 900KB `app.py`. The manifest indexes all 14 panels, DOM IDs, key JS functions, API endpoints, and broker invariants in 2KB. Reading this first cuts AI token usage by 80% and slashes turnaround time from 58 minutes to 5–10 minutes with 100% precision.
- **Fast Syntax & Tag Health Check (0.1s)**: After editing `terminal.html`, always run:
  `python tools/check_terminal.py`
  Validates `<div>` balance, 14 panel IDs inside `.main`, and essential window exports in 0.1s.

## 1. Make ONLY Changes Requested by User
- Do not make unsolicited refactors, redesigns, or changes outside the explicit scope requested by the user.
- Focus strictly and cleanly on the specific issues, features, and UI elements specified.

## 2. Error Resolution & Solution Memory
- When the user points out an error or bug:
  1. Carefully diagnose the root cause across both frontend (`terminal.html`, `static/js/`, `static/css/`) and backend (`app.py`).
  2. Implement the clean fix.
  3. Document the problem, root cause, and exact solution in `CHANGELOG_MEMORY.md`.
  4. Always reference `CHANGELOG_MEMORY.md` to prevent recurring errors or regressions.

## 3. Strict Local Verification Before Any Server Deployment
- **Local First**: Run the application on a local port (e.g., port 8000).
- **Local Runner**: Start server via `python run_server.py` (which forces `SelectorEventLoop` on Windows to eliminate `[WinError 64]` Proactor socket crashes).
- **Fast Automated Verification (8s)**: Run `python tests/smoke_test.py` to automatically verify authentication, instant dual reco cards, non-zero price change fallback, panel flex alignment, and 1500 candlestick rendering in ~8 seconds.
- **Comprehensive Verification**: Check all sections, buttons, and responsive breakpoints using headless browser scripts and screenshots.
  - Verify every single section (Dashboard, Chart & Technicals, Option Chain, Strategy Builder, Algo Bots, Backtesting, Risk & Journal, Fundamentals, Market Movers).
  - Verify mobile view (< 600px width) and desktop view.
  - Confirm buttons are clickable and no UI elements are blank.
- **User Approval Gate**: **NEVER** deploy to the live server until the user has explicitly reviewed and approved local changes.
- **Server Deployment via PEM & Git (Zero Local File Transfers)**:
  - **NO LAPTOP FILE TRANSFERS**: Never engage in SCP/SFTP file transfers of assets, icons, or manifests from the laptop to avoid Sophos security popups.
  - Push tested code to the GitHub repository.
  - Push tested code to the GitHub repository (`CA-Trader-Bifurcated` branch).
  - Execute remote git pull / service restart on the EC2 server (`ca-trader-key.pem`).
- **Post-Deploy Live Verification**: Immediately re-verify live production (`https://catrader.site` or server IP) with screenshots, confirming all sections and features are non-blank and operational.

## 4. UI Preservation & Formatting Integrity
- Never distort, break, or clutter the UI layout when making requested changes.
- Keep typography, spacing, dark mode theme consistency (`#1890ff`, `#0b0e14`, `#151b26`), and compactness intact.
- Make targeted, surgically clean modifications only in places asked by the user.

