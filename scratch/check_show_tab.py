import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'function showTab\(', html):
    idx = m.start()
    print("showTab at", idx)
    print(html[idx:idx+2500])
    print("="*60)

