---
name: data-freshness-auditor
description: Audits live and fallback market data across all terminal panels to eradicate placeholder dashes, undefined tokens, and sluggish blank states.
---

# Data Freshness Auditor Skill

## Overview
Ensures that all user-facing panels in `terminal.html` (Watchlist, Reco Cards, Market Movers, Options, Funds) always display rich, populated financial numbers even before WebSocket ticks arrive or when the broker API is rate-limited.

## Usage
Run the audit:
```bash
python tools/ui_reviewer.py
```
Check 5 automatically verifies data freshness across Watchlist and Recommendation cards.
