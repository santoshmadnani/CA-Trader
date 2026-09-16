import sys, re
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
    html = f.read()

import re

# Find panel-charts, panel-news, etc and their parent hierarchy
for pid in ['panel-charts', 'panel-news', 'panel-options', 'panel-movers', 'panel-orders', 'panel-funds']:
    pos = text.find(f'id="{pid}"')
    if pos != -1:
        # get preceding 300 chars
        before = text[max(0, pos-300):pos]
        # find last open tag
        print(f"--- Parent context of {pid} ---")
        lines = before.splitlines()[-4:]
        for l in lines:
            print("  ", l.strip()[:100])

idx = html.find('id="chartAiSuggestBtn"')
print(html[max(0, idx-600):min(len(html), idx+400)])
