# -*- coding: utf-8 -*-
"""
Helper script to test target strings in terminal.html.
"""
from pathlib import Path

path = Path("terminal.html")
content = path.read_text(encoding="utf-8")

checks = [
    ".topbar{",
    ".user-menu{",
    ".navtabs{",
    'id="panel-orders"',
    'id="fundCards"',
    'id="panel-backtest"',
    'id="btChartViewport"',
    'id="mcxOptSelector"',
    'id="maxProfitRecommendationBtn"',
    'id="profileModal"',
    'class="badge ghost"',
    'function drawingHit',
    'function moveDrawing',
    'function renderApplied',
    'function appliedOverlaySeries',
    'function updateChartRecoBanner'
]

for c in checks:
    count = content.count(c)
    print(f"Target '{c}': found {count} times")

