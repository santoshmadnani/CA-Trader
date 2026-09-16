with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'updateDashboardConfluenceTable\(', text)]
print("Total calls to updateDashboardConfluenceTable:", len(matches))
for idx in matches:
    print(f"At {idx}:", text[idx-40:idx+150].encode('ascii', errors='replace').decode('ascii'))

