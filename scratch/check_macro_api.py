import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'@app\.get\(["\']/api/(?:market|analysis)/macro', app):
    idx = m.start()
    print("Match at", idx, ":")
    print(app[idx:idx+2500])
    print("="*60)

