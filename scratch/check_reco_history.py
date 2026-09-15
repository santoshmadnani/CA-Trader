with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

targets = [
    'id="panel-news"',
    'id="panel-backtest"',
    'function loadNews',
    'function renderNewsCard',
    "vp.addEventListener('pointerdown'",
    "vp.addEventListener('pointermove'",
    'function showDrawingTooltip',
    'function findDrawingAt',
    'function drawingHit',
    'function appliedOverlaySeries',
    'deleteRecommendationHistory'
]

for t in targets:
    found = [i+1 for i, line in enumerate(lines) if t in line]
    print(f"{t} -> Lines: {found}")

