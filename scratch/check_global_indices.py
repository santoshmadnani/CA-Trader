import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    app = f.read()

for m in re.finditer(r'(?:sgx|dow|s&p|sp500|gift)', app, re.IGNORECASE):
    idx = m.start()
    print("Match in app.py at", idx, ":")
    print(app[max(0, idx-100):min(len(app), idx+300)])
    print("="*60)

