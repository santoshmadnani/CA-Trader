content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'updateChartRecoBanner', content):
    p = m.start()
    print('Found at', p)
    print(content[p-40:p+100].encode('ascii', errors='replace').decode())

