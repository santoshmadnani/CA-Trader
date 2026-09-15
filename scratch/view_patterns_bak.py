import sys

sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html.bak', 'r', encoding='utf-8', errors='ignore') as f:
    c = f.read()

p = 282400
print(c[p:p+5000])

