content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'/api/analysis/patterns', content):
    p = m.start()
    print('Found patterns API at', p)
    print(content[p-50:p+300].encode('ascii', errors='replace').decode())

