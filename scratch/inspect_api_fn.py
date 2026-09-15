# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

for m in re.finditer(r'async function api\(|function A\(|async function A\(|function api\(', text):
    line = text[:m.start()].count('\n') + 1
    print(f"Line {line}: {text[m.start():m.start()+400]}")
    print("="*60)

