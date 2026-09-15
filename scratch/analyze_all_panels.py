import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

panel_indices = []
for i, line in enumerate(lines):
    m = re.search(r'<div\s+class=["\'][^"\']*panel[^"\']*["\']\s+id=["\']([^"\']+)["\']', line)
    if not m:
        m = re.search(r'<div\s+id=["\']([^"\']+)["\']\s+class=["\'][^"\']*panel[^"\']*["\']', line)
    if m:
        panel_indices.append((i, m.group(1), line.strip()))

print(f"Found {len(panel_indices)} panels:")
for idx, (line_idx, pid, line_text) in enumerate(panel_indices):
    next_line_idx = panel_indices[idx+1][0] if idx+1 < len(panel_indices) else len(lines)
    depth = 0
    for l in range(line_idx, next_line_idx):
        cleaned = re.sub(r'<!--.*?-->', '', lines[l])
        opens = len(re.findall(r'<div\b[^>]*>', cleaned, re.IGNORECASE))
        closes = len(re.findall(r'</div>', cleaned, re.IGNORECASE))
        depth += (opens - closes)
    print(f"Panel {pid} (Line {line_idx+1}..{next_line_idx}): net depth = {depth}")
