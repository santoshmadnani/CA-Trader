import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'def overall_recommendation\(', app):
    idx = m.start()
    print(app[idx:idx+2500])
    print("="*60)

