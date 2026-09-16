import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

scripts = list(re.finditer(r'<script\b[^>]*>(.*?)</script>', text, re.DOTALL | re.IGNORECASE))
print(f"Total script tags: {len(scripts)}")

for i, s in enumerate(scripts):
    code = s.group(1)
    start_line = text.count('\n', 0, s.start()) + 1
    
    # Check for invalid characters or stray markdown / diff markers
    markers = ['<<<<<<<', '=======', '>>>>>>>', '... [truncated', '```']
    for m in markers:
        if m in code:
            idx = code.find(m)
            line_no = start_line + code.count('\n', 0, idx)
            print(f"Script #{i+1} Line {line_no}: Found marker '{m}'")


