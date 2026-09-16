with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

import re
matches = [m.start() for m in re.finditer(r'id=["\'](?:dashRecoCard|recommendationSignal|recoCard|dashboardReco)["\']', text)]
print("Matches:", matches)
for idx in matches:
    print(text[idx-40:idx+300].encode('ascii', errors='replace').decode('ascii'))
    print("="*30)

