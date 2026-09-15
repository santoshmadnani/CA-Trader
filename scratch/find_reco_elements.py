with open('terminal.html', 'r', encoding='utf-8') as f:
    for idx, line in enumerate(f, 1):
        if 'id="reco' in line or 'data-tab="recommendations"' in line or 'id="tabRecommendations"' in line or 'tab-pane' in line and 'reco' in line:
            print(f"{idx}: {line.strip()[:100]}")

