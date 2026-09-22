# AGENT OPERATING MANDATE & PROTOCOL

This document defines the strict, non-negotiable operating rules for the AI Agent working on CA Trader.

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
- **Comprehensive Verification**: Check all sections, buttons, and responsive breakpoints using headless browser scripts and screenshots.
  - Verify every single section (Dashboard, Chart & Technicals, Option Chain, Strategy Builder, Algo Bots, Backtesting, Risk & Journal, Fundamentals, Market Movers).
  - Verify mobile view (< 600px width) and desktop view.
  - Confirm buttons are clickable and no UI elements are blank.
- **User Approval Gate**: **NEVER** deploy to the live server until the user has explicitly reviewed and approved local changes.
- **Server Deployment via PEM & Git (Zero Local File Transfers)**:
  - **NO LAPTOP FILE TRANSFERS**: Never engage in SCP/SFTP file transfers of assets, icons, or manifests from the laptop to avoid Sophos security popups.
  - Push tested code to the GitHub repository.
  - Execute remote git pull / service restart on the EC2 server (`ca-trader-key.pem`).
- **Post-Deploy Live Verification**: Immediately re-verify live production (`https://catrader.site` or server IP) with screenshots, confirming all sections and features are non-blank and operational.

## 4. UI Preservation & Formatting Integrity
- Never distort, break, or clutter the UI layout when making requested changes.
- Keep typography, spacing, dark mode theme consistency (`#1890ff`, `#0b0e14`, `#151b26`), and compactness intact.
- Make targeted, surgically clean modifications only in places asked by the user.

