with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

depth = 0
in_template = False
in_single = False
in_double = False
template_stack = []

for line_idx, line in enumerate(lines[4060:8060]):
    cur_line = 4061 + line_idx
    old_depth = depth
    for ch in line:
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    if old_depth == 1 and depth > 1:
        # A top-level function in this IIFE opened
        last_opened = (cur_line, line.strip()[:60])
    if old_depth > 1 and depth == 1:
        # A top-level function in this IIFE closed
        pass

print(f"The unclosed function was opened around: {last_opened}")

