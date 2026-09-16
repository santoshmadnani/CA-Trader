import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'async def [a-zA-Z0-9_]*(?:loop|background|worker|scanner|cron|auto)', app):
    idx = m.start()
    print("MATCH:", app[idx:idx+400])
    print("="*60)

