import sys
sys.stdout.reconfigure(encoding='utf-8')

with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

depth = 0
in_template = False
in_string = False
str_char = ''

for line_idx in range(4060, 8099):
    line = lines[line_idx]
    for c in line:
        if c in ('"', "'", '`'):
            pass # simplified
    # let's just count { and } roughly, or use node.js / esprima or python jslex

