with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

# remove line 2043
lines = text.splitlines()
target_line = lines[2042] # 0-indexed is 2042 (line 2043)
print("Line 2043 content:", target_line)
print("Line 2044 content:", lines[2043])

test_lines = lines[:2042] + lines[2043:]
test_text = "\n".join(test_lines)

import re
clean_html = re.sub(r'<script\b[^>]*>.*?</script>', '', test_text, flags=re.DOTALL | re.IGNORECASE)

stack = []
for i, line in enumerate(clean_html.splitlines()):
    for m in re.finditer(r'(</?div[^>]*>)', line, re.IGNORECASE):
        tag = m.group(1)
        if tag.startswith('</'):
            if stack:
                stack.pop()
        else:
            is_panel = 'class="panel' in tag or "class='panel" in tag
            panel_id = re.search(r'id=["\']([^"\']+)["\']', tag)
            pid = panel_id.group(1) if panel_id else ''
            parent_desc = stack[-1] if stack else 'ROOT'
            if is_panel:
                print(f"Panel '{pid}' at line {i+1} has PARENT: {parent_desc}")
            stack.append(f"{pid or tag[:30]}")

