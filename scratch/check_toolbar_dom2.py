with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()
import re
m2 = re.search(r'<div[^>]*class=["\'][^"\']*chart-toolbar[^"\']*["\']', text)
if m2:
    idx2 = m2.start()
    print(text[idx2+2000:idx2+4500].encode('ascii', errors='replace').decode('ascii'))

