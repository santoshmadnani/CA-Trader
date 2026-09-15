with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
for m in re.finditer(r'marketClock', text):
    p = m.start()
    print('Found marketClock at', p)
    print(text[p-50:p+300].encode('ascii', errors='replace').decode())

