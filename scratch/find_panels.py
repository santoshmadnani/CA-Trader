import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'<div[^>]+class=["\'][^"\']*panel[^"\']*["\'][^>]*>', html):
    idx = m.start()
    print(html[idx:idx+200])
    print("-"*40)

