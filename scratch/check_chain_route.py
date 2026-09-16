with open('app.py', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'def normalize_option_chain', text)
if m:
    idx = m.start()
    print("normalize_option_chain:\n", text[idx:idx+1500].encode('ascii', errors='replace').decode('ascii'))

m2 = re.search(r'@app\.get\(["\']/api/market/options/chain', text)
if m2:
    idx2 = m2.start()
    print("API route:\n", text[idx2:idx2+1500].encode('ascii', errors='replace').decode('ascii'))

