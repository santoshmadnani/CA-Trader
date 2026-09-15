with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
scripts = list(re.finditer(r'<script(?:\s+[^>]*)?>(.*?)</script>', text, re.DOTALL))
s1 = scripts[1].group(1)
start_line = text[:scripts[1].start()].count('\n') + 1

# Walk through line by line
stack = []
for i, line in enumerate(s1.split('\n')):
    current_line_no = start_line + i
    # Strip string literals and comments roughly
    clean = re.sub(r'//.*$', '', line)
    clean = re.sub(r'/\*.*?\*/', '', clean)
    clean = re.sub(r"'(?:\\.|[^'])*'", "''", clean)
    clean = re.sub(r'"(?:\\.|[^"])*"', '""', clean)
    clean = re.sub(r'`(?:\\.|[^`])*`', '``', clean)

    for ch in clean:
        if ch == '{':
            stack.append((ch, current_line_no))
        elif ch == '}':
            if not stack:
                print(f'EXTRA CLOSING BRACE at line {current_line_no}: {line.strip()[:80]}')
            else:
                stack.pop()

print(f'Finished script 1 check. Remaining open braces: {len(stack)}')
if stack:
    print('Unclosed braces at lines:', [item[1] for item in stack[:5]])

