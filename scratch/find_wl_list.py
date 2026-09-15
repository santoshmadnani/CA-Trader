with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
for m in re.finditer(r'wl-list', text):
    p = m.start()
    print('Found wl-list at', p)
    print(text[p-50:p+500].encode('ascii', errors='replace').decode())

