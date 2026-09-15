with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

import re

stack = []
for idx in range(1956, 2444):
    line = lines[idx]
    # find all tags in line in order
    tags = re.findall(r'(</?div[^>]*>)', line)
    for tag in tags:
        if tag.startswith('</'):
            if stack:
                stack.pop()
            else:
                print(f"L{idx+1}: extra close: {tag}")
        else:
            # open tag
            tag_summary = tag[:50]
            stack.append((idx+1, tag_summary))

print(f"Stack size at end: {len(stack)}")
for line_num, tag_str in stack:
    print(f"  Unclosed tag from L{line_num}: {tag_str}")

