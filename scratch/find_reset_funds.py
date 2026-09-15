content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'/api/funds/reset', content):
    p = m.start()
    print('Found reset at', p)
    print(content[p-50:p+200].encode('ascii', errors='replace').decode())

