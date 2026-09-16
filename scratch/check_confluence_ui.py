with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
m = re.search(r'function\s+updateDashboardConfluenceTable\s*\(', text)
if m:
    idx = m.start()
    print("updateDashboardConfluenceTable function:\n", text[idx:idx+2500].encode('ascii', errors='replace').decode('ascii'))

# search for dashConfluenceTable HTML
m2 = re.search(r'id=["\']dashConfluenceTable["\']', text)
if not m2:
    m2 = re.search(r'id=["\']dashConfluenceTableBody["\']', text)
if m2:
    idx2 = m2.start()
    print("dashConfluenceTable HTML:\n", text[idx2-200:idx2+600].encode('ascii', errors='replace').decode('ascii'))

