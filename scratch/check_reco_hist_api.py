import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

idx = app.find('async def recommendation_history(')
print(app[idx:idx+3500])

