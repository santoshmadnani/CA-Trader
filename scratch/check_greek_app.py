import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'def [a-zA-Z0-9_]*greek', app, re.IGNORECASE):
    idx = m.start()
    print("Match in app.py at", idx, ":")
    print(app[idx:idx+1200])
    print("="*60)

