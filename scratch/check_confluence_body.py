import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'dashConfluenceTableBody', html):
    idx = m.start()
    print("Match at", idx, ":")
    print(html[idx:idx+1500])
    print("="*60)

