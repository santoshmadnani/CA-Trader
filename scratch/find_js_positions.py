with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re

for name in ['function showTab(', 'function updateDashboardConfluenceTable(', 'function renderRecommendationCard(', 'function updateLiveCandle(', 'function renderApplied(']:
    idx = text.find(name)
    print(f"{name}: found at {idx}")

