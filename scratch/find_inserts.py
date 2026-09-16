import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'INSERT INTO recommendations', app):
    idx = m.start()
    print("MATCH AT", idx)
    print(app[max(0, idx-400):min(len(app), idx+800)])
    print("="*60)

