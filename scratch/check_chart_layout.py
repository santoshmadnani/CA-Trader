import sys
sys.stdout.reconfigure(encoding='utf-8')
import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Search for chart container CSS and HTML
print("--- Chart CSS Rules ---")
for m in re.finditer(r'(\.chart-[a-zA-Z0-9_\-]+\s*\{[^}]*\})', text):
    print(m.group(1)[:120])

print("\n--- Canvas elements ---")
for m in re.finditer(r'(<canvas[^>]*>)', text):
    print(m.group(1))

print("\n--- Chart panel structure ---")
chart_panel_idx = text.find('id="panel-charts"')
if chart_panel_idx != -1:
    print(text[chart_panel_idx:chart_panel_idx+1500])

