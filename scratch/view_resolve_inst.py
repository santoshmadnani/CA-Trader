import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('def resolve_instrument(')
print(c[p:p+1500])

