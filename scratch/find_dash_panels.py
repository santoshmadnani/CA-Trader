# -*- coding: utf-8 -*-
with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
for m in re.finditer(r'id=["\'](panel-dashboard|panel-ca_ai_dashboard)["\']', text):
    line = text[:m.start()].count('\n') + 1
    print(f"Line {line}: {m.group(0)}")

