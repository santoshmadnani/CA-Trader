import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    html = f.read()

print("--- Searching for caAiModal ---")
idx = html.find('caAiModal')
while idx != -1:
    line_no = html.count('\n', 0, idx) + 1
    snippet = html[max(0, idx-50):min(len(html), idx+100)].replace('\n', ' ')
    print(f"Line {line_no}: {snippet}")
    idx = html.find('caAiModal', idx+1)

print("\n--- Searching for AI Chat Send / Input handlers ---")
ai_inputs = re.findall(r'[^\n]*(?:aiChat|sendAi|askCaAi|ask_ca_ai|\/api\/ai)[^\n]*', html, re.IGNORECASE)
print(f"Found {len(ai_inputs)} occurrences")
for line in ai_inputs[:20]:
    print("  ", line.strip()[:140])

