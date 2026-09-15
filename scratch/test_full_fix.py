with open('terminal.html', 'r', encoding='utf-8', errors='ignore') as f:
    text = f.read()

lines = text.splitlines()
print(f"Original line count: {len(lines)}")
print("Line 2043:", lines[2042])
print("Line 3044:", lines[3043])

# Filter out line 2043 and line 3044 (0-indexed 2042 and 3043)
new_lines = [l for i, l in enumerate(lines) if i not in (2042, 3043)]
print(f"New line count: {len(new_lines)}")

new_text = "\n".join(new_lines)

import re
clean_html = re.sub(r'<script\b[^>]*>.*?</script>', '', new_text, flags=re.DOTALL | re.IGNORECASE)

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

print("\nFinal unclosed tags in markup:")
for s in stack:
    print(" ", s)

