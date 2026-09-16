with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'@app\.get\(["\']/api/positions/\{position_id\}/analysis["\']\)', text)
if m:
    idx = m.start()
    print(text[idx:idx+2500].encode('ascii', errors='replace').decode('ascii'))

