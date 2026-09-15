import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('def search_instruments(')
if p == -1:
    p = c.find('/api/instruments/search')
print(f"search_instruments at {p}:")
print(c[p:p+2500])

