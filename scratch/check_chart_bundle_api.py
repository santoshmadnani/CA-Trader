import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

idx = app.find('/api/analysis/chart-bundle/')
if idx == -1:
    idx = app.find('chart-bundle')
print(app[idx:idx+2500])

