import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = 637000
print(c[p:p+4000])

