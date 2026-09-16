import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let's inspect panels
panels = re.findall(r'<div[^>]*class=["\'][^"\']*panel[^"\']*["\'][^>]*id=["\']([^"\']+)["\'][^>]*>', text)
print("Panels found:", panels)

# Let's trace each panel from its start tag to where it closes or next panel starts
pos = 0
for p_id in panels:
    tag = f'id="{p_id}"'
    m_idx = text.find(tag)
    p_start = text.rfind('<div', 0, m_idx)
    print(f"\n--- Panel: {p_id} (starts at char {p_start}) ---")
    
# Let's check panel-alerts
alerts_idx = text.find('id="panel-alerts"')
print("\nAround panel-alerts:")
print(text[alerts_idx-100:alerts_idx+200])

# Let's check the layout closing tags after the last panel
main_idx = text.find('</main>')
if main_idx == -1:
    print("No </main> tag found!")
else:
    print("</main> found at", main_idx)

