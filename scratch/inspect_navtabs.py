import re

with open('terminal.html', 'r', encoding='utf-8') as f:
    text = f.read()

navtabs = re.findall(r'<button\b[^>]*\bclass=[\'"][^\'"]*navtab[^\'"]*[\'"][^>]*>([\s\S]*?)</button>', text)
for t in navtabs:
    m = re.search(r'data-tab=[\'"]([^\'"]+)[\'"]', t)
    tab = m.group(1) if m else 'NO_DATA_TAB'
    label = re.sub(r'<[^>]+>', '', t).strip()
    print(f"data-tab: '{tab}' -> Label: '{label}'")

