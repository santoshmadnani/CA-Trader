import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

idx = app.find('@app.get("/api/market/macro-factors")')
print(app[idx+2000:idx+4500])

