import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = c.find('async function fetchOptionChain(')
if p == -1:
    p = c.find('function fetchOptionChain(')
print(f"fetchOptionChain at {p}:")
print(c[p:p+3500])

