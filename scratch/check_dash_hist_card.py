import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    html = f.read()

idx = html.find('id="dashHistoryCard"')
print(html[idx:idx+1500])

