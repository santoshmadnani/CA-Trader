import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

# Script 2 is from line 4060 to 8100 (0-indexed: 4059 to 8099)
code = "".join(lines[4060:8099])

# Let's track brace depth character by character with proper comment/string skipping
depth = 0
in_line_comment = False
in_block_comment = False
in_single_quote = False
in_double_quote = False
in_template = False
template_depth_stack = []

line_num = 4061
col = 0

i = 0
n = len(code)
events = []

while i < n:
    ch = code[i]
    col += 1
    if ch == '\n':
        line_num += 1
        col = 0
        if in_line_comment:
            in_line_comment = False
        i += 1
        continue

    if in_line_comment:
        i += 1
        continue

    if in_block_comment:
        if ch == '*' and i + 1 < n and code[i+1] == '/':
            in_block_comment = False
            i += 2
            col += 1
            continue
        i += 1
        continue

    if in_single_quote:
        if ch == '\\':
            i += 2
            col += 1
            continue
        if ch == "'":
            in_single_quote = False
        i += 1
        continue

    if in_double_quote:
        if ch == '\\':
            i += 2
            col += 1
            continue
        if ch == '"':
            in_double_quote = False
        i += 1
        continue

    if in_template:
        if ch == '\\':
            i += 2
            col += 1
            continue
        if ch == '`':
            in_template = False
            i += 1
            continue
        if ch == '$' and i + 1 < n and code[i+1] == '{':
            # template expression starts
            template_depth_stack.append(depth)
            depth += 1
            in_template = False
            i += 2
            col += 1
            continue
        i += 1
        continue

    # Normal code
    if ch == '/' and i + 1 < n:
        if code[i+1] == '/':
            in_line_comment = True
            i += 2
            col += 1
            continue
        elif code[i+1] == '*':
            in_block_comment = True
            i += 2
            col += 1
            continue

    if ch == "'":
        in_single_quote = True
        i += 1
        continue
    if ch == '"':
        in_double_quote = True
        i += 1
        continue
    if ch == '`':
        in_template = True
        i += 1
        continue

    if ch == '{':
        depth += 1
    elif ch == '}':
        depth -= 1
        if template_depth_stack and depth == template_depth_stack[-1]:
            # Returned from template expression to template string!
            template_depth_stack.pop()
            in_template = True
        if depth == 0:
            events.append((line_num, col, "depth reached 0"))
        elif depth < 0:
            events.append((line_num, col, f"NEGATIVE DEPTH: {depth}"))

    i += 1

print(f"Final depth: {depth}")
for ev in events[-10:]:
    print(ev)

