content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'loadNewsByCaAi', content):
    p = m.start()
    print('Found loadNewsByCaAi at', p)
    print(content[p-30:p+500].encode('ascii', errors='replace').decode())

