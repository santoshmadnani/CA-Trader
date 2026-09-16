import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

idx = html.find('async function loadChartAiSuggestions')
if idx == -1:
    idx = html.find('function loadChartAiSuggestions')
print(html[idx:idx+2500])

