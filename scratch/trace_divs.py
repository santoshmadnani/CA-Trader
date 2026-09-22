with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
import re
import sys, re
import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

import re
# Search around dash-reco-head and dashExcelWorksheetCard
for i, line in enumerate(lines):
    if 'id="dashExcelWorksheetCard"' in line:
        start_line = i
        print(f"dashExcelWorksheetCard is at line {i+1}")
        break

stack = []
for idx in range(1956, 2550):
    line = lines[idx]
    tags = re.finditer(r'(</?div[^>]*>)', line)
    for m in tags:
        tag = m.group(1)
        if tag.startswith('</'):
for i in range(2900, min(3500, len(lines))):
    line = lines[i]
    tokens = re.findall(r'(</?div\b[^>]*>)', line)
    for t in tokens:
        if t.startswith('</div'):
            if stack:
                opened_line, opened_tag = stack.pop()
                if 'panel' in opened_tag:
                    print(f"L{idx+1} {tag} CLOSED PANEL from L{opened_line}: {opened_tag}")
                popped = stack.pop()
                if popped[1] in ['main', 'layout', 'panel-dashboard', 'panel-reco', 'panel-notes', 'panel-charts']:
                    print(f"Line {i+1}: CLOSED {popped[1]} (opened at {popped[0]})")
            else:
                print(f"L{idx+1}: EXTRA CLOSE {tag}")
depth = 0
for i in range(2878, 3345):
    line = lines[i]
    line_num = i + 1
    tokens = re.findall(r'</?div\b[^>]*>', line)
    for t in tokens:
        if t.startswith('</'):
            depth -= 1
            if depth <= 2:
                print(f"Line {line_num} CLOSE: depth -> {depth}")
                print(f"Line {i+1}: EXTRA CLOSING DIV: {t}")
        else:
            tag_id = re.search(r'id=["\']([^"\']+)["\']', tag)
            tag_cls = re.search(r'class=["\']([^"\']+)["\']', tag)
            desc = f"<{tag_cls.group(1) if tag_cls else ''}#{tag_id.group(1) if tag_id else ''}>"
            stack.append((idx+1, desc))
            m = re.search(r'id=["\']([^"\']+)["\']', t) or re.search(r'class=["\']([^"\']+)["\']', t)
            name = m.group(1) if m else 'anon'
            stack.append((i+1, name))

print("\nRemaining on stack:")
for l, d in stack:
    print(f"  L{l}: {d}")

            depth += 1
            if depth <= 3:
                m_id = re.search(r'id=["\']([^"\']+)["\']', t)
                m_cls = re.search(r'class=["\']([^"\']+)["\']', t)
                id_str = f"id={m_id.group(1)}" if m_id else ""
                cls_str = f"class={m_cls.group(1)}" if m_cls else ""
                print(f"Line {line_num} OPEN:  depth -> {depth} ({id_str} {cls_str})")
print(f"\nCurrent open divs at line {min(3500, len(lines))}:")
for s in stack:
    print(f"  Line {s[0]}: {s[1]}")
# Let's inspect lines from line 3480 to 3650
for i in range(max(0, start_line - 10), min(len(lines), start_line + 150)):
    print(f"{i+1}: {lines[i]}", end='')
