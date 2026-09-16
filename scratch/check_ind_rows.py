import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

idx = html.find('id="indicatorRows"')
print(html[idx-400:idx+600])

