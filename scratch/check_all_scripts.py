import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

scripts = list(re.finditer(r'<script\b[^>]*>(.*?)</script>', text, re.DOTALL | re.IGNORECASE))
print(f"Total script tags: {len(scripts)}")

for i, s in enumerate(scripts):
    code = s.group(1)
    start_line = text.count('\n', 0, s.start()) + 1
    end_line = text.count('\n', 0, s.end()) + 1
    
    # Check brace/bracket/parenthesis balance
    stack = []
    in_str = None
    in_comment = False
    in_regex = False
    escaped = False
    errors = []
    
    lines = code.split('\n')
    for line_idx, line in enumerate(lines):
        line_num = start_line + line_idx
        # Check for bad patterns like '... [truncated'
        if '[truncated' in line or '...' in line and 'preview' in line:
            errors.append(f"Line {line_num}: Stray truncation marker found: {line.strip()[:60]}")
    
    # Count braces ignoring simple strings
    # Simple brace counter
    open_c = code.count('{')
    close_c = code.count('}')
    open_p = code.count('(')
    close_p = code.count(')')
    open_b = code.count('[')
    close_b = code.count(']')
    
    print(f"Script #{i+1} (lines {start_line}-{end_line}): len={len(code)}, {{}}: {open_c}/{close_c}, (): {open_p}/{close_p}, []: {open_b}/{close_b}")
    if errors:
        for err in errors:
            print("  ERROR:", err)
