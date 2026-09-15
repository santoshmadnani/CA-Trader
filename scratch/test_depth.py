import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

scripts = [m.group(1) for m in re.finditer(r'<script\b[^>]*>(.*?)</script>', html, re.DOTALL)]
sc2 = scripts[2]

# Accurate JS tokenizer for braces
depth = 0
in_str = None
in_comment = False
in_line_comment = False
escaped = False

orig_lines = sc2.split('\n')

for line_idx, line in enumerate(orig_lines):
    i = 0
    in_line_comment = False
    while i < len(line):
        c = line[i]
        nxt = line[i+1] if i+1 < len(line) else ''

        if in_line_comment:
            break
        elif in_comment:
            if c == '*' and nxt == '/':
                in_comment = False
                i += 2
                continue
            i += 1
            continue
        elif in_str:
            if escaped:
                escaped = False
            elif c == '\\':
                escaped = True
            elif c == in_str:
                in_str = None
            i += 1
            continue

        # Not in string or comment
        if c == '/' and nxt == '/':
            in_line_comment = True
            i += 2
            continue
        elif c == '/' and nxt == '*':
            in_comment = True
            i += 2
            continue
        elif c in ("'", '"', '`'):
            in_str = c
            escaped = False
            i += 1
            continue
        elif c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                print(f"*** ACCURATE TOKENIZER: DEPTH HIT 0 at line {line_idx}: {line.strip()[:80]} ***")
        i += 1

    if in_str is not None:
        print(f"*** UNCLOSED STRING {in_str} at line {line_idx} (starts line {line_idx}): {line} ***")
        break
