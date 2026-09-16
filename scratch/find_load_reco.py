import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'async function loadRecommendations|function loadRecommendations', html):
    idx = m.start()
    print("MATCH AT", idx)
    print(html[idx:idx+2500])
    print("="*60)

