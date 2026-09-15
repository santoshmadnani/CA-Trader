import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

def find_str(pattern):
    results = []
    for i, line in enumerate(lines):
        if pattern in line:
            results.append((i+1, line.strip()[:80]))
    return results

print("chartModeToggle:", find_str("chartModeToggle"))
print("enableEditMode:", find_str("enableEditMode"))
print("computeLocalChartAiSuggestions:", find_str("computeLocalChartAiSuggestions"))
print("loadRecommendationHistory:", find_str("loadRecommendationHistory"))
print("autoAddSymbolBtn:", find_str("autoAddSymbolBtn"))
print("navtab.*backtest:", find_str("backtest"))
print("loadTabData:", find_str("function loadTabData") or find_str("loadTabData"))
print("panel-reco:", find_str("panel-reco"))

