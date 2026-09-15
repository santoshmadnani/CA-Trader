# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

for m in re.finditer(r'id=["\']panel-backtest["\']', text):
    line = text[:m.start()].count('\n') + 1
    print(f"panel-backtest at Line {line}")
    print(text[m.start():m.start()+1500])

print("\n" + "="*60 + "\n")
for m in re.finditer(r'function initBacktest\(', text):
    line = text[:m.start()].count('\n') + 1
    print(f"initBacktest at Line {line}")
    print(text[m.start():m.start()+2500])

