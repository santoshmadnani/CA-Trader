with open('app.py', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
p = text.find('/api/watchlists')
print(text[p:p+1200])

