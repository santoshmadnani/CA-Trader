with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

import re

stack = []
for idx in range(1956, 2550):
    line = lines[idx]
    tags = re.finditer(r'(</?div[^>]*>)', line)
    for m in tags:
        tag = m.group(1)
        if tag.startswith('</'):
            if stack:
                opened_line, opened_tag = stack.pop()
                if 'panel' in opened_tag:
                    print(f"L{idx+1} {tag} CLOSED PANEL from L{opened_line}: {opened_tag}")
            else:
                print(f"L{idx+1}: EXTRA CLOSE {tag}")
        else:
            tag_id = re.search(r'id=["\']([^"\']+)["\']', tag)
            tag_cls = re.search(r'class=["\']([^"\']+)["\']', tag)
            desc = f"<{tag_cls.group(1) if tag_cls else ''}#{tag_id.group(1) if tag_id else ''}>"
            stack.append((idx+1, desc))

print("\nRemaining on stack:")
for l, d in stack:
    print(f"  L{l}: {d}")

