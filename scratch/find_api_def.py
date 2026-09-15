# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
import sys
sys.stdout.reconfigure(encoding='utf-8')

for m in re.finditer(r'\b(api|A)\s*=\s*(?:async\s*)?function|\bconst\s+api\b|\blet\s+api\b|\bfunction\s+api\b|\bconst\s+A\b|\blet\s+A\b|\bfunction\s+A\b', text):
    line = text[:m.start()].count('\n') + 1
    print(f"Line {line}: {text[m.start():m.start()+300]}")
    print("="*60)

