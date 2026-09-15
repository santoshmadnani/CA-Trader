content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'loadChartPatterns', content):
    p = m.start()
    print('Found loadChartPatterns at', p)
    print(content[p-30:p+300].encode('ascii', errors='replace').decode())

