with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
for m in re.finditer(r'--:--:--', text):
    p = m.start()
    print('Found --:--:-- at', p)
    print(text[p-50:p+200].encode('ascii', errors='replace').decode())

