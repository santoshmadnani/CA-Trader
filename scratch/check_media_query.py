import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

idx = 93057
print(html[max(0, idx-300):min(len(html), idx+800)])

