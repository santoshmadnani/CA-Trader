with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'vp\.addEventListener\(["\']pointermove["\']', text)
if m:
    idx = m.start()
    print(text[idx+1800:idx+3500].encode('ascii', errors='replace').decode('ascii'))

