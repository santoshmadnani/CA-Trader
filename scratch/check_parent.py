with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

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

