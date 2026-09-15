with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re
scripts = list(re.finditer(r'<script(?:\s+[^>]*)?>(.*?)</script>', text, re.DOTALL))
print(f'Total script tags: {len(scripts)}')

for idx, match in enumerate(scripts):
    s = match.group(1)
    start_pos = match.start()
    line_no = text[:start_pos].count('\n') + 1
    print(f'\n--- Script {idx} (starts around line {line_no}, len: {len(s)}) ---')
    # Check for basic JS syntax issues
    # Count braces, parens, brackets
    curly = s.count('{') - s.count('}')
    paren = s.count('(') - s.count(')')
    square = s.count('[') - s.count(']')
    print(f'Curly: {curly}, Paren: {paren}, Square: {square}')

