with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
for m in re.finditer(r'(let|var|const)\s+G\b|G\s*=\s*await\s+A\(', text):
    p = m.start()
    print('Found G at', p)
    print(text[p-50:p+300].encode('ascii', errors='replace').decode())

