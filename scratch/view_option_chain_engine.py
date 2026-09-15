import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('def option_chain_engine(')
print(f"option_chain_engine at {p}:")
print(c[p:p+3500])

