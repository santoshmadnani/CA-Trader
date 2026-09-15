import sys
sys.stdout.reconfigure(encoding='utf-8')

with open(r"c:\Users\SantoshMadnani\Documents\CA_Trader\7\terminal.html", "r", encoding="utf-8") as f:
    lines = f.readlines()

code = "".join(lines[4060:8099])

# Let's track which functions were opened and not closed
stack = []
depth = 0
in_template = False
in_single_quote = False
in_double_quote = False
template_depth_stack = []

line_num = 4061

for line_idx, line in enumerate(lines[4060:8099]):
    cur_line = 4061 + line_idx
    # simple tracker
    for i, ch in enumerate(line):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
    if 8060 <= cur_line <= 8095:
        print(f"Line {cur_line} (depth={depth}): {line.strip()[:60]}")

