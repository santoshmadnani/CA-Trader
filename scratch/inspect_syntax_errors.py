import sys
from bs4 import BeautifulSoup

sys.stdout.reconfigure(encoding='utf-8')
with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

import re
scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)
soup = BeautifulSoup(content, 'html.parser')
scripts = soup.find_all('script')

sc1 = scripts[1].splitlines()
print(f"Script 1 total lines: {len(sc1)}")
print("Script 1 last 20 lines:")
for i, l in enumerate(sc1[-20:]):
    safe_l = l.encode('ascii', 'replace').decode()
    print(f"  {len(sc1)-20+i+1}: {safe_l}")

sc2 = scripts[2].splitlines()
print(f"\nScript 2 total lines: {len(sc2)}")
line_target = min(4017, len(sc2))
print(f"Script 2 around line {line_target}:")
start_l = max(0, line_target - 15)
end_l = min(len(sc2), line_target + 15)
for i in range(start_l, end_l):
    safe_l = sc2[i].encode('ascii', 'replace').decode()
    print(f"  {i+1}: {safe_l}")

for s_idx in [0, 2, 3]:
    s = scripts[s_idx]
    lines = s.get_text().split('\n')
    print(f"=== SCRIPT #{s_idx+1} (total lines: {len(lines)}) ===")
    if s_idx == 0:
        target = 157
    elif s_idx == 2:
        target = 174
    elif s_idx == 3:
        target = 867
    
    start = max(0, target - 10)
    end = min(len(lines), target + 10)
    for i in range(start, end):
        print(f"{i+1}: {lines[i]}")
    print("=" * 60)
