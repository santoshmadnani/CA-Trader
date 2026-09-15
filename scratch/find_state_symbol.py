content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'state\.symbol\s*=', content):
    p = m.start()
    print('---')
    print(content[p-100:p+200])

