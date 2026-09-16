import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

for m in re.finditer(r'local fallback', html, re.IGNORECASE):
    idx = m.start()
    print("Match in terminal.html at", idx, ":")
    print(html[max(0, idx-100):min(len(html), idx+300)])
    print("="*60)

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'local fallback', app, re.IGNORECASE):
    idx = m.start()
    print("Match in app.py at", idx, ":")
    print(app[max(0, idx-100):min(len(app), idx+300)])
    print("="*60)

