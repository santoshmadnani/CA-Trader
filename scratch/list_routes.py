import sys, re
sys.stdout.reconfigure(encoding='utf-8')
with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()
routes = re.findall(r'@app\.(get|post)\(["\']([^"\']+)["\']', c)
for method, path in routes:
    print(f'{method.upper()}: {path}')
