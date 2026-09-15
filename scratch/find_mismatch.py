import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts_with_pos = []
for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL):
    scripts_with_pos.append((m.start(), m.end(), m.group(1)))

sp6, ep6, s6 = scripts_with_pos[6]
base_line = html[:sp6].count('\n') + 1
print(f"Script 6 starts at line {base_line}, len={len(s6)}")

# Find unmatched ) - more ) than (
depth = 0
all_opens = []
unmatched_closes = []
for i, c in enumerate(s6):
    if c == '(':
        depth += 1
        all_opens.append(i)
    elif c == ')':
        depth -= 1
        if depth < 0:
            unmatched_closes.append(i)
            depth = 0
        elif all_opens:
            all_opens.pop()

print(f"Unmatched ) positions: {unmatched_closes}")
print(f"Unmatched ( positions (remaining opens): {all_opens}")
for pos in unmatched_closes[:10]:
    file_line = base_line + s6[:pos].count('\n')
    context = s6[max(0,pos-100):pos+100]
    print(f"\nFile line ~{file_line}, offset={pos}")
    print(f"  context: {repr(context)}")
for pos in all_opens[:10]:
    file_line = base_line + s6[:pos].count('\n')
    context = s6[max(0,pos-100):pos+100]
    print(f"\nOpen paren at file line ~{file_line}, offset={pos}")
    print(f"  context: {repr(context)}")

