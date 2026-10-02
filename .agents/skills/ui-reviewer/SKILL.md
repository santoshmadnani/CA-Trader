---
name: ui-reviewer
description: Automated human-grade visual UI auditor. Verifies baseline alignment, dark/light theme integrity, section isolation, and button/metric box symmetry.
---

# UI Reviewer Skill

## Overview
Automated visual auditor that evaluates `terminal.html` as rendered in a real headless browser using the Chrome DevTools Protocol (CDP).

## Usage
Run the visual reviewer anytime a UI tweak or layout modification is made:
```bash
python tools/ui_reviewer.py
```

## Checks Performed
1. **Baseline Alignment**: Asserts `#mainSidebar` and `#dashDualRecoCard` top coordinates match within $\le 2\text{px}$.
2. **Section Separation**: Asserts only the active `.panel` is visible (`display: block`) and all inactive panels are `display: none`.
3. **Dual-Theme Integrity**: Inspects computed background colors of all cards under `data-theme="light"` and `data-theme="dark"`. Ensures light mode has zero dark/black translucent boxes.
4. **Metric Symmetry**: Verifies 4-metric grid integrity (`repeat(4, 1fr)`) and uniform button heights.
5. **Data Freshness**: Flags any blank dashes (`-`, `₹--`, `NaN`) in Watchlist or Recommendations.
