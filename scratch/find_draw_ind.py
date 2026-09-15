content = open('terminal.html', encoding='utf-8', errors='ignore').read()
import re
for m in re.finditer(r'state\.appliedIndicators\.forEach', content):
    p = m.start()
    print('Found indicator render loop at', p)
    print(content[p:p+1200].encode('ascii', errors='replace').decode())

