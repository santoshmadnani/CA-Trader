with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    content = f.read()

import re
scripts = re.findall(r'<script\b[^>]*>(.*?)</script>', content, flags=re.DOTALL | re.IGNORECASE)

sc1 = scripts[1]
lines = sc1.splitlines()

stack = []
for idx, line in enumerate(lines):
    for ch in line:
        if ch in '({[':
            stack.append((idx+1, ch))
        elif ch in ')}]':
            if not stack:
                print(f"L{idx+1}: stray closing {ch}")
            else:
                last_l, last_ch = stack.pop()
                expected = {'(':')', '{':'}', '[':']'}[last_ch]
                if ch != expected:
                    print(f"L{idx+1}: mismatched {ch} (expected {expected} from L{last_l})")

print(f"Unclosed in Script 1 ({len(stack)}):")
for l, ch in stack[-10:]:
    print(f"  Line {l}: {ch} -> {lines[l-1].strip()[:80]}")

