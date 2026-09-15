with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'placeholder=["\'][^"\']*Instrument', text, re.IGNORECASE)
if m:
    p = m.start()
    print('Found placeholder at', p)
    print(text[p-200:p+800].encode('ascii', errors='replace').decode())

