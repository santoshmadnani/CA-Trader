import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'def (?:auto_trade|background|recomm|poll|refresh|generate_auto)', app):
    idx = m.start()
    print(app[idx:idx+200])
    print("-"*40)

# Check auto reco background tasks
for m in re.finditer(r'async def (?:auto_recommendation|recom|run_auto)', app):
    idx = m.start()
    print(app[idx:idx+200])
    print("-"*40)

