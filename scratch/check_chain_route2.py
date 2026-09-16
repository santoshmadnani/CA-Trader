with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m2 = re.search(r'@app\.get\(["\']/api/market/options/chain', text)
if m2:
    idx2 = m2.start()
    print(text[idx2:idx2+2500].encode('ascii', errors='replace').decode('ascii'))

