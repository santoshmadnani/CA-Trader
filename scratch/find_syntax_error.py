with open('terminal.html', encoding='utf-8', errors='ignore') as f:
    text = f.read()

import re

scripts = list(re.finditer(r'<script(?:\s+[^>]*)?>(.*?)</script>', text, re.DOTALL))

def check_script(code, offset_line):
    # State machine tokenizer for JavaScript
    i = 0
    n = len(code)
    stack = []
    line = offset_line
    
    in_single = False
    in_double = False
    in_template = False
    in_line_comment = False
    in_block_comment = False
    template_depth = 0
    
    while i < n:
        ch = code[i]
        
        if ch == '\n':
            line += 1
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
            else:
                i += 1
            continue
            
        if in_single:
            if ch == '\\':
                i += 2
            elif ch == "'":
                in_single = False
                i += 1
            else:
                i += 1
            continue
            
        if in_double:
            if ch == '\\':
                i += 2
            elif ch == '"':
                in_double = False
                i += 1
            else:
                i += 1
            continue
            
        if in_template:
            if ch == '\\':
                i += 2
            elif ch == '$' and i + 1 < n and code[i+1] == '{':
                # Expression inside template literal
                stack.append(('${', line))
                in_template = False
                template_depth += 1
                i += 2
            elif ch == '`':
                in_template = False
                i += 1
            else:
                i += 1
            continue
            
        # Not inside string or comment
        if ch == '/' and i + 1 < n:
            if code[i+1] == '/':
                in_line_comment = True
                i += 2
                continue
            elif code[i+1] == '*':
                in_block_comment = True
                i += 2
                continue
                
        if ch == "'":
            in_single = True
            i += 1
            continue
            
        if ch == '"':
            in_double = True
            i += 1
            continue
            
        if ch == '`':
            in_template = True
            i += 1
            continue
            
        if ch in '({[':
            stack.append((ch, line))
            i += 1
            continue
            
        if ch in ')}]':
            matching = {'(': ')', '{': '}', '[': ']'}.get(stack[-1][0] if stack else '', '')
            if stack and stack[-1][0] == '${' and ch == '}':
                stack.pop()
                template_depth -= 1
                in_template = True
                i += 1
                continue
            elif stack and matching == ch:
                stack.pop()
                i += 1
                continue
            else:
                expected = matching if stack else 'none'
                print(f"ERROR on line {line}: Unexpected '{ch}', expected '{expected}' (stack top: {stack[-1] if stack else 'empty'})")
                snippet = code[max(0, i-50):min(n, i+50)]
                print(f"Snippet: {snippet}")
                return False
                
        i += 1
        
    if stack:
        print(f"Unclosed items at end of script (starts line {offset_line}): {stack[-5:]}")
        return False
    return True

for idx, match in enumerate(scripts):
    code = match.group(1)
    offset_line = text[:match.start()].count('\n') + 1
    res = check_script(code, offset_line)
    if res:
        print(f"Script {idx} (line {offset_line}): CLEAN!")

