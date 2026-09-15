import re

with open('app.py', 'r', encoding='utf-8') as f:
    t = f.read()

routes = re.findall(r'@app\.(get|post|put|delete)\(["\']([^"\']+)["\']', t)
for meth, path in routes:
    if any(x in path for x in ['recom', 'fund', 'mover', 'status', 'news', 'analys', 'market']):
        print(f'{meth.upper()} {path}')

