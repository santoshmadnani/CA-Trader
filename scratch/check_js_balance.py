import sys
sys.stdout.reconfigure(encoding='utf-8')
from bs4 import BeautifulSoup
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'html.parser')
scripts = soup.find_all('script')

for idx, s in enumerate(scripts):
    code = s.string or ''
    if not code.strip():
        continue
    
    # Check brace, bracket, paren balance
    # Filter out string literals and regex literals to avoid false counts
    in_single = False
    in_double = False
    in_backtick = False
    in_line_comment = False
    in_block_comment = False
    escaped = False
    
    parens = 0
    brackets = 0
    braces = 0
    
    i = 0
    n = len(code)
    errors = []
    
    while i < n:
        c = code[i]
        
        if in_line_comment:
            if c == '\n': in_line_comment = False
            i += 1; continue
        if in_block_comment:
            if c == '*' and i + 1 < n and code[i+1] == '/':
                in_block_comment = False
                i += 2
                continue
            i += 1; continue
            
        if in_single:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == "'": in_single = False
            i += 1; continue
            
        if in_double:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '"': in_double = False
            i += 1; continue
            
        if in_backtick:
            if escaped: escaped = False
            elif c == '\\': escaped = True
            elif c == '`': in_backtick = False
            i += 1; continue
            
        if c == '/' and i + 1 < n:
            if code[i+1] == '/':
                in_line_comment = True
                i += 2; continue
            elif code[i+1] == '*':
                in_block_comment = True
                i += 2; continue
                
        if c == "'": in_single = True; i += 1; continue
        if c == '"': in_double = True; i += 1; continue
        if c == '`': in_backtick = True; i += 1; continue
        
        if c == '(': parens += 1
        elif c == ')':
            parens -= 1
            if parens < 0: errors.append(f"Unexpected ')' around char {i}")
        elif c == '[': brackets += 1
        elif c == ']':
            brackets -= 1
            if brackets < 0: errors.append(f"Unexpected ']' around char {i}")
        elif c == '{': braces += 1
        elif c == '}':
            braces -= 1
            if braces < 0: errors.append(f"Unexpected '}}' around char {i}")
            
        i += 1
        
    print(f"Script #{idx+1}: length={len(code):,} chars | parens={parens} | brackets={brackets} | braces={braces}")
    if in_single or in_double or in_backtick:
        print(f"  [!] Unclosed string literal: single={in_single}, double={in_double}, backtick={in_backtick}")
    if errors:
        print(f"  [!] Errors: {errors[:5]}")

