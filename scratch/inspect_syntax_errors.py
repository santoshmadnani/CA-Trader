with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

import re
scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)

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

