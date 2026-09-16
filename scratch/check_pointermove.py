with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'vp\.addEventListener\(["\']pointermove["\']', text)
if m:
    idx = m.start()
    print("pointermove listener:\n", text[idx:idx+2500].encode('ascii', errors='replace').decode('ascii'))

