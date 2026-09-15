import re

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

routes = re.findall(r'@app\.[a-z]+\([\'"]([^\'"]+)[\'"]', text)
print(f'Total routes found: {len(routes)}')
for r in sorted(routes):
    print(' ', r)
