import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'id=["\'](?:tab-)?(?:reco|history|dashboard)[^"\']*["\']', html):
    idx = m.start()
    print("MATCH:", html[max(0, idx-50):min(len(html), idx+150)])
    print("="*60)

