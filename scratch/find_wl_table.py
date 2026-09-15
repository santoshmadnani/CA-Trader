with open('app.py', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
for m in re.finditer(r'CREATE TABLE IF NOT EXISTS watch[a-z_]*', text):
    p = m.start()
    print(text[p:p+300])

