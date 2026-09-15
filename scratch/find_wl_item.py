content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'wl-item', content):
    p = m.start()
    print('---')
    print(content[p-40:p+180].encode('ascii', errors='replace').decode())

