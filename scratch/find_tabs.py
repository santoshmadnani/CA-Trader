import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'<div[^>]+id=["\'](?:reco|history|recoHistorySection|dashboard)["\'][^>]*>', html):
    idx = m.start()
    print("MATCH:", html[idx:idx+300])
    print("="*60)

